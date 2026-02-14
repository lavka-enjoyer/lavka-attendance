"""
Модуль для получения расписания группы через публичное API МИРЭА
С поддержкой повторяющихся событий (RRULE) и исключений (EXDATE)
"""

import calendar
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from dateutil.rrule import rruleset, rrulestr

logger = logging.getLogger(__name__)


class MIREAScheduleCache:
    """Класс для работы с публичным расписанием МИРЭА"""

    BASE_URL = "https://schedule-of.mirea.ru"

    @staticmethod
    async def search_group(group_name: str, limit: int = 15) -> List[Dict]:
        """
        Поиск группы по названию через публичное API МИРЭА.

        Args:
            group_name: Название группы для поиска
            limit: Максимальное количество результатов

        Returns:
            Список найденных групп
        """
        url = f"{MIREAScheduleCache.BASE_URL}/schedule/api/search"
        params = {"limit": limit, "match": group_name}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", [])
            return []
        except Exception as e:
            logger.exception(f"Ошибка при поиске группы: {e}")
            return []

    @staticmethod
    async def get_schedule_ical(schedule_target: int, group_id: int) -> str:
        """
        Получение расписания в формате iCal через публичное API МИРЭА.

        Args:
            schedule_target: Целевой тип расписания
            group_id: ID группы

        Returns:
            Содержимое iCal файла в виде строки
        """
        url = f"{MIREAScheduleCache.BASE_URL}/schedule/api/ical/{schedule_target}/{group_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
            return ""
        except Exception as e:
            logger.exception(f"Ошибка при получении iCal: {e}")
            return ""

    @staticmethod
    def parse_ical_events(ical_content: str) -> List[Dict[str, Any]]:
        """
        Парсинг событий из iCal с поддержкой многострочных значений.

        Args:
            ical_content: Содержимое iCal файла

        Returns:
            Список событий в виде словарей
        """
        events: List[Dict[str, Any]] = []
        current_event: Dict[str, Any] = {}
        in_event: bool = False
        current_key: Optional[str] = None

        for line in ical_content.split("\n"):
            line = line.rstrip("\r")

            if line == "BEGIN:VEVENT":
                in_event = True
                current_event = {}
                current_key = None
            elif line == "END:VEVENT":
                if current_event:
                    events.append(current_event)
                in_event = False
                current_key = None
            elif in_event:
                # Многострочные значения начинаются с пробела
                if line.startswith(" "):
                    if current_key and current_key in current_event:
                        current_event[current_key] += line[1:]
                elif ":" in line:
                    key: str
                    value: str
                    key, value = line.split(":", 1)
                    # Ключи с параметрами (например, DTSTART;TZID=...)
                    if ";" in key:
                        base_key: str = key.split(";")[0]
                        current_event[key] = value
                        current_event[base_key] = value
                        current_key = base_key
                    else:
                        current_event[key] = value
                        current_key = key

        return events

    @staticmethod
    def parse_datetime(dt_string: str) -> Optional[datetime]:
        """
        Парсинг даты и времени из строки формата iCal.

        Args:
            dt_string: Строка с датой/временем

        Returns:
            Объект datetime или None при ошибке парсинга
        """
        try:
            # Убираем Z в конце если есть
            dt_string = dt_string.replace("Z", "")
            if "T" in dt_string:
                return datetime.strptime(dt_string, "%Y%m%dT%H%M%S")
            else:
                return datetime.strptime(dt_string, "%Y%m%d")
        except Exception:
            return None

    @staticmethod
    def parse_exdates_global(ical_content: str) -> Set[datetime.date]:
        """
        Извлечение глобальных дат-исключений (EXDATE) из iCal.

        Args:
            ical_content: Содержимое iCal файла

        Returns:
            Множество дат-исключений (праздников)
        """
        exdates: Set[datetime.date] = set()

        for match in re.finditer(r"EXDATE[^:]*:(.+)", ical_content):
            dates_str: str = match.group(1)
            for date in dates_str.split(","):
                date = date.strip()
                dt: Optional[datetime] = MIREAScheduleCache.parse_datetime(date)
                if dt:
                    exdates.add(dt.date())

        if exdates:
            logger.debug(f"(GLOBAL) Найдено {len(exdates)} дат-исключений (праздники)")
        return exdates

    @staticmethod
    def extract_lesson_type(summary: str) -> str:
        """
        Извлекает тип занятия из названия события.

        Args:
            summary: Название события

        Returns:
            Тип занятия (ЛК, ПР, ЛАБ и т.д.)
        """
        text = summary.upper()

        if text.startswith("ЛК "):
            return "ЛК"
        elif text.startswith("ПР "):
            return "ПР"
        elif text.startswith("ЛАБ "):
            return "ЛАБ"
        elif "ЛЕКЦИЯ" in text or " ЛК" in text:
            return "ЛК"
        elif "ПРАКТИКА" in text or " ПР" in text:
            return "ПР"
        elif "ЛАБОРАТОРНАЯ" in text or " ЛАБ" in text:
            return "ЛАБ"
        elif "ЭКЗАМЕН" in text or " ЭКЗ" in text:
            return "ЭКЗ"
        elif "КОНСУЛЬТАЦИЯ" in text or " КОНС" in text:
            return "КОНС"

        return ""

    @staticmethod
    def _collect_overrides(
        events: List[Dict[str, Any]],
    ) -> Dict[Tuple[str, datetime], Dict[str, Any]]:
        """
        Сбор событий-override по RECURRENCE-ID для замены или отмены отдельных повторений.

        Args:
            events: Список событий из iCal

        Returns:
            Словарь override событий с ключами (UID, datetime)
        """
        overrides: Dict[Tuple[str, datetime], Dict[str, Any]] = {}
        for ev in events:
            # Ищем ключ RECURRENCE-ID (с таймзоной или без)
            rid_key: Optional[str] = next(
                (k for k in ev.keys() if k.startswith("RECURRENCE-ID")), None
            )
            if not rid_key:
                continue
            rid_dt: Optional[datetime] = MIREAScheduleCache.parse_datetime(ev[rid_key])
            uid: Optional[str] = ev.get("UID")
            if not rid_dt or not uid:
                continue
            overrides[(uid, rid_dt)] = (
                ev  # Сохраняем полностью, STATUS может быть CANCELLED
            )
        if overrides:
            logger.debug(f"Найдено override событий: {len(overrides)}")
        return overrides

    @staticmethod
    def _parse_event_exdates(ev: Dict[str, Any]) -> List[datetime]:
        """
        Парсинг EXDATE внутри конкретного события.

        Args:
            ev: Событие из iCal

        Returns:
            Список дат-исключений для данного события
        """
        result: List[datetime] = []
        for k, v in ev.items():
            if k.startswith("EXDATE"):
                for part in v.split(","):
                    part = part.strip()
                    dt: Optional[datetime] = MIREAScheduleCache.parse_datetime(part)
                    if dt:
                        result.append(dt)
        return result

    @staticmethod
    def expand_recurring_events(
        events: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        global_exdates: Set[datetime.date],
    ) -> List[Dict[str, Any]]:
        """
        Раскрытие повторяющихся событий с учётом RRULE, RECURRENCE-ID и EXDATE.

        Args:
            events: Список событий из iCal
            start_date: Начальная дата диапазона
            end_date: Конечная дата диапазона
            global_exdates: Глобальные даты-исключения (праздники)

        Returns:
            Список раскрытых событий
        """
        expanded: List[Dict[str, Any]] = []

        # Собираем override события (RECURRENCE-ID)
        overrides: Dict[Tuple[str, datetime], Dict[str, Any]] = (
            MIREAScheduleCache._collect_overrides(events)
        )

        # События с RRULE
        recurring_events: List[Dict[str, Any]] = [
            ev
            for ev in events
            if "RRULE" in ev
            and not any(k.startswith("RECURRENCE-ID") for k in ev.keys())
        ]
        # Обычные одноразовые события (без RRULE / без RECURRENCE-ID)
        single_events: List[Dict[str, Any]] = [
            ev
            for ev in events
            if "RRULE" not in ev
            and not any(k.startswith("RECURRENCE-ID") for k in ev.keys())
        ]

        # 1. Обрабатываем одиночные события
        for ev in single_events:
            # Пропускаем маркеры недель
            if "VALUE=DATE" in ev.get("DTSTART;VALUE=DATE", ""):
                continue
            # Отменённое целиком одиночное событие
            if ev.get("STATUS", "").upper() == "CANCELLED":
                continue
            dtstart_key: Optional[str] = next(
                (
                    k
                    for k in ev.keys()
                    if k.startswith("DTSTART") and "T" in ev.get(k, "")
                ),
                None,
            )
            if not dtstart_key:
                continue
            dt: Optional[datetime] = MIREAScheduleCache.parse_datetime(ev[dtstart_key])
            if not dt:
                continue
            if start_date <= dt <= end_date and dt.date() not in global_exdates:
                # Проверяем override отмену
                uid: Optional[str] = ev.get("UID")
                override_ev: Optional[Dict[str, Any]] = (
                    overrides.get((uid, dt)) if uid else None
                )
                if override_ev:
                    status: str = override_ev.get("STATUS", "").upper()
                    if status == "CANCELLED":
                        continue  # Отменено
                    # Замена события
                    new_ev: Dict[str, Any] = override_ev.copy()
                    new_ev["_actual_start"] = dt
                    expanded.append(new_ev)
                else:
                    new_ev = ev.copy()
                    new_ev["_actual_start"] = dt
                    expanded.append(new_ev)

        # 2. Обрабатываем повторяющиеся события
        for ev in recurring_events:
            # Пропуск маркеров недель
            if "VALUE=DATE" in ev.get("DTSTART;VALUE=DATE", ""):
                continue
            # Если серия отменена целиком
            if ev.get("STATUS", "").upper() == "CANCELLED":
                continue
            dtstart_key: Optional[str] = next(
                (
                    k
                    for k in ev.keys()
                    if k.startswith("DTSTART") and "T" in ev.get(k, "")
                ),
                None,
            )
            if not dtstart_key:
                continue
            event_start: Optional[datetime] = MIREAScheduleCache.parse_datetime(
                ev[dtstart_key]
            )
            if not event_start:
                continue
            rrule_line: Optional[str] = ev.get("RRULE")
            if not rrule_line:
                continue

            # Безопасное построение набора повторений
            rset: Optional[rruleset] = MIREAScheduleCache._safe_rruleset(
                rrule_line, event_start
            )
            if not rset:
                continue

            # Добавляем EXDATE пер-ивент
            for exdt in MIREAScheduleCache._parse_event_exdates(ev):
                rset.exdate(exdt)

            uid: Optional[str] = ev.get("UID")

            # Получаем повторения в диапазоне
            try:
                occurrences: List[datetime] = rset.between(
                    start_date, end_date, inc=True
                )
            except Exception as e:
                logger.exception(f"Ошибка получения повторений: {e}")
                continue

            for occ in occurrences:
                if occ.date() in global_exdates:
                    continue
                # Override?
                override_ev: Optional[Dict[str, Any]] = (
                    overrides.get((uid, occ)) if uid else None
                )
                if override_ev:
                    status: str = override_ev.get("STATUS", "").upper()
                    if status == "CANCELLED":
                        continue
                    new_ev: Dict[str, Any] = override_ev.copy()
                    new_ev["_actual_start"] = occ
                    expanded.append(new_ev)
                else:
                    new_ev = ev.copy()
                    new_ev["_actual_start"] = occ
                    expanded.append(new_ev)

        # Сортировка
        expanded.sort(key=lambda e: e.get("_actual_start", datetime.min))
        logger.debug(f"Раскрыто (после RRULE/override) событий: {len(expanded)}")
        return expanded

    @staticmethod
    def _safe_rruleset(rrule_line: str, event_start: datetime) -> Optional[rruleset]:
        """
        Безопасный парсинг RRULE с обработкой ошибок таймзоны.

        Args:
            rrule_line: Строка с RRULE
            event_start: Время начала события

        Returns:
            Объект rruleset или None при ошибке парсинга
        """
        rset: rruleset = rruleset()
        try:
            rr = rrulestr(rrule_line, dtstart=event_start)
            rset.rrule(rr)
            return rset
        except Exception as e:
            msg: str = str(e)
            if "UNTIL values must be specified in UTC" in msg:
                # 1-й fallback: убрать Z после UNTIL
                sanitized: str = re.sub(
                    r"UNTIL=(\d{8}T\d{6})Z", r"UNTIL=\1", rrule_line
                )
                try:
                    rr = rrulestr(sanitized, dtstart=event_start)
                    rset2: rruleset = rruleset()
                    rset2.rrule(rr)
                    logger.debug(
                        f"Fallback sanitize UNTIL: '{rrule_line}' -> '{sanitized}'"
                    )
                    return rset2
                except Exception:
                    # 2-й fallback: полностью удалить UNTIL
                    sanitized2: str = re.sub(r"UNTIL=\d{8}T\d{6}Z?", "", rrule_line)
                    # Чистим двойные ;
                    sanitized2 = re.sub(r";{2,}", ";", sanitized2).rstrip(";")
                    try:
                        rr = rrulestr(sanitized2, dtstart=event_start)
                        rset3: rruleset = rruleset()
                        rset3.rrule(rr)
                        logger.debug(
                            f"Fallback remove UNTIL: '{rrule_line}' -> '{sanitized2}'"
                        )
                        return rset3
                    except Exception as e3:
                        logger.exception(
                            f"RRULE окончательно не разобран (remove UNTIL fail): {e3}"
                        )
            logger.exception(f"Ошибка парсинга RRULE: {e}. RRULE='{rrule_line}'")
            return None

    @staticmethod
    async def get_month_schedule(
        group_name: str, year: int, month: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получение расписания группы на месяц

        Args:
            group_name: Название группы
            year: Год
            month: Месяц (1-12)

        Returns:
            Словарь {дата: [список занятий]}
        """
        logger.debug(f"Получение расписания для {group_name} на {year}-{month:02d}")

        # Ищем группу
        groups: List[Dict[str, Any]] = await MIREAScheduleCache.search_group(group_name)
        if not groups:
            logger.debug(f"Группа {group_name} не найдена")
            return {}

        selected_group: Dict[str, Any] = groups[0]
        logger.debug(f"Найдена группа: {selected_group.get('fullTitle', group_name)}")

        # Получаем iCal
        ical_content: str = await MIREAScheduleCache.get_schedule_ical(
            selected_group["scheduleTarget"], selected_group["id"]
        )

        if not ical_content:
            logger.debug("Не удалось получить iCal")
            return {}

        # Парсим события
        events: List[Dict[str, Any]] = MIREAScheduleCache.parse_ical_events(
            ical_content
        )
        logger.debug(f"Найдено событий в iCal: {len(events)}")

        # Глобальные EXDATE (если имеются)
        global_exdates: Set[datetime.date] = MIREAScheduleCache.parse_exdates_global(
            ical_content
        )

        # Определяем диапазон дат месяца
        start_date: datetime = datetime(year, month, 1)
        days_in_month: int = calendar.monthrange(year, month)[1]
        end_date: datetime = datetime(year, month, days_in_month, 23, 59, 59)

        # Раскрываем события на месяц
        expanded: List[Dict[str, Any]] = MIREAScheduleCache.expand_recurring_events(
            events, start_date, end_date, global_exdates
        )

        # Группируем по датам
        schedule_by_date: Dict[str, List[Dict[str, Any]]] = {}

        for event in expanded:
            actual_start: Optional[datetime] = event.get("_actual_start")
            if not actual_start:
                continue
            date_str: str = actual_start.strftime("%Y-%m-%d")
            time_str: str = actual_start.strftime("%H:%M")

            summary: str = event.get("SUMMARY", "")
            location: str = event.get("LOCATION", "").replace("\n", " ")

            lesson_type: str = MIREAScheduleCache.extract_lesson_type(summary)

            # Пропускаем события без типа
            if not lesson_type:
                continue

            lesson: Dict[str, str] = {
                "time": time_str,
                "type": lesson_type,
                "subject": summary,
                "room": location,
            }

            if date_str not in schedule_by_date:
                schedule_by_date[date_str] = []

            schedule_by_date[date_str].append(lesson)

        # Дедупликация занятий (иногда iCal содержит дубли с одинаковыми полями)
        for d, lessons in list(schedule_by_date.items()):
            seen: Set[Tuple[str, str, str, str]] = set()
            unique: List[Dict[str, str]] = []
            for lesson in lessons:
                key: Tuple[str, str, str, str] = (
                    lesson["time"],
                    lesson["type"],
                    lesson["subject"],
                    lesson["room"],
                )
                if key not in seen:
                    seen.add(key)
                    unique.append(lesson)
            schedule_by_date[d] = unique

        logger.debug(f"Дат с занятиями: {len(schedule_by_date)}")
        if schedule_by_date:
            dates_list: List[str] = sorted(schedule_by_date.keys())
            logger.debug(f"Первая дата: {dates_list[0]}, последняя: {dates_list[-1]}")

            # Выводим первые 3 даты с занятиями для отладки
            for date_str in dates_list[:3]:
                lessons: List[Dict[str, str]] = schedule_by_date[date_str]
                lessons_info: List[str] = [
                    f"{les['type']} {les['time']}" for les in lessons
                ]
                logger.debug(f"{date_str}: {len(lessons)} занятий - {lessons_info}")

        return schedule_by_date

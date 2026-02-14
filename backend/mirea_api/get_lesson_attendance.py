"""
Модуль для получения статистики посещаемости по конкретному занятию.
Использует blackboxprotobuf для декодирования protobuf без схемы.
"""

import logging
import struct
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .protobuf_decoder import (
    ATTENDANCE_REPORT_TYPEDEF,
    DISCIPLINES_TYPEDEF,
    VISITING_LOGS_TYPEDEF,
    decode_grpc_response_bytes,
    ensure_list,
    get_field,
    get_nested,
    parse_person_name,
    timestamp_to_datetime,
)

logger = logging.getLogger(__name__)


class AttendanceParser:
    """Парсер статистики посещаемости из protobuf данных с использованием blackboxprotobuf."""

    def parse_students(self, message: Dict[str, Any]) -> Dict[str, Dict]:
        """
        Парсит секцию студентов из декодированного сообщения.

        Args:
            message: Декодированное protobuf сообщение

        Returns:
            Словарь {student_uuid: {fio, first_name, surname, patronymic, uuid}}
        """
        students = {}

        # Field 2 содержит список студентов
        students_data = ensure_list(get_field(message, "2", []))

        for student in students_data:
            if not isinstance(student, dict):
                continue

            student_uuid = get_field(student, "1", "")
            first_name = get_field(student, "2", "")
            surname = get_field(student, "3", "")

            # Отчество в поле 4.1
            patronymic = ""
            patronymic_data = get_field(student, "4")
            if patronymic_data:
                if isinstance(patronymic_data, dict):
                    patronymic = get_field(patronymic_data, "1", "")
                elif isinstance(patronymic_data, str):
                    patronymic = patronymic_data

            if student_uuid and (first_name or surname):
                fio = parse_person_name(student, short=True)
                students[student_uuid] = {
                    "fio": fio,
                    "first_name": first_name,
                    "surname": surname,
                    "patronymic": patronymic,
                    "uuid": student_uuid,
                }

        return students

    def parse_lessons(
        self, message: Dict[str, Any]
    ) -> Tuple[List[Dict], Dict[int, Dict[str, int]]]:
        """
        Парсит занятия и посещаемость из декодированного сообщения.

        Args:
            message: Декодированное protobuf сообщение

        Returns:
            Кортеж (список_занятий, словарь_посещаемости)
        """
        lessons = []
        attendance: Dict[int, Dict[str, int]] = defaultdict(dict)

        # Field 1 содержит занятия
        lessons_data = ensure_list(get_field(message, "1", []))

        for lesson_index, lesson_wrapper in enumerate(lessons_data):
            if not isinstance(lesson_wrapper, dict):
                continue

            # Field 1.1 содержит информацию о занятии
            lesson_info = get_field(lesson_wrapper, "1", {})
            if not isinstance(lesson_info, dict):
                continue

            # Время занятия из field 1.1.1.1 (timestamp начала)
            start_ts = get_nested(lesson_info, "1", "1", "1", default=0)
            end_ts = get_nested(lesson_info, "1", "2", "1", default=0)

            # Тип занятия из field 1.1.2
            lesson_type = get_field(lesson_info, "2", "ЛК")

            # UUID занятия из field 1.1.3
            lesson_uuid = get_field(lesson_info, "3", "")

            # Форматируем дату и время
            date_str = f"Lesson {lesson_index + 1}"
            time_str = ""

            if isinstance(start_ts, int) and start_ts > 1000000000:
                dt = timestamp_to_datetime(start_ts)
                if dt:
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M")

            lessons.append(
                {
                    "type": lesson_type,
                    "date": date_str,
                    "time": time_str,
                    "index": lesson_index,
                    "uuid": lesson_uuid,
                }
            )

            # Field 1.2 содержит записи посещаемости студентов (repeated)
            attendance_records = ensure_list(get_field(lesson_wrapper, "2", []))

            for record in attendance_records:
                if not isinstance(record, dict):
                    continue

                # Field 2.1 = student UUID
                student_uuid = get_field(record, "1", "")

                # Field 2.3 содержит статус посещения
                # Field 2.3.2 = status code (1=Н, 2=У, 3=+)
                status_info = get_field(record, "3")
                if isinstance(status_info, dict):
                    status = get_field(status_info, "2", 0)
                    if student_uuid and isinstance(status, int):
                        attendance[lesson_index][student_uuid] = status
                elif get_field(record, "4") is not None:
                    # Field 4 = пустой dict означает что студент не отмечен
                    if student_uuid:
                        attendance[lesson_index][student_uuid] = 0

        return lessons, dict(attendance)

    def parse(self, content: bytes) -> Dict:
        """
        Полный парсинг данных статистики.

        Args:
            content: Байтовые данные protobuf

        Returns:
            Словарь с ключами students, lessons, attendance
        """
        message = decode_grpc_response_bytes(content, ATTENDANCE_REPORT_TYPEDEF)

        if not message:
            return {"students": {}, "lessons": [], "attendance": {}}

        students = self.parse_students(message)
        lessons, attendance = self.parse_lessons(message)

        return {"students": students, "lessons": lessons, "attendance": attendance}


async def get_visiting_logs(
    cookies: list,
    user_agent: Optional[str] = None,
) -> List[Dict]:
    """
    Получить список доступных журналов (семестров).

    Args:
        cookies: Список куки для авторизации
        user_agent: User-Agent для запроса

    Returns:
        Список словарей с информацией о семестрах
    """
    url = "https://attendance.mirea.ru/rtu_tc.attendance.api.VisitingLogService/GetAvailableVisitingLogsOfStudent"

    headers = {
        "Content-Type": "application/grpc-web+proto",
        "Accept": "*/*",
        "x-grpc-web": "1",
        "x-requested-with": "XMLHttpRequest",
        "Origin": "https://attendance-app.mirea.ru",
        "Referer": "https://attendance-app.mirea.ru/",
        "User-Agent": user_agent
        or "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    }

    request_body = bytes([0x00, 0x00, 0x00, 0x00, 0x00])

    connector = aiohttp.TCPConnector()

    async with aiohttp.ClientSession(connector=connector) as session:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        session.cookie_jar.update_cookies(cookies_dict)

        async with session.post(
            url,
            headers=headers,
            data=request_body,
        ) as response:
            if response.status != 200:
                return []

            content = await response.read()
            message = decode_grpc_response_bytes(content, VISITING_LOGS_TYPEDEF)

            if not message:
                return []

            visiting_logs = []

            # Field 1 содержит список журналов
            logs_data = ensure_list(get_field(message, "1", []))

            for log_wrapper in logs_data:
                if not isinstance(log_wrapper, dict):
                    continue

                # Field 1.1 содержит информацию о журнале
                log_info = get_field(log_wrapper, "1", {})
                if not isinstance(log_info, dict):
                    continue

                # Field 1.1.1 = log UUID
                log_uuid = get_field(log_info, "1", "")

                # Field 1.1.2 = group name
                group_name = get_field(log_info, "2", "")

                # Field 1.1.6 содержит информацию о семестре
                semester_info = get_field(log_info, "6", {})
                semester_name = ""
                if isinstance(semester_info, dict):
                    semester_name = get_field(semester_info, "2", "")

                if log_uuid and group_name:
                    visiting_logs.append(
                        {
                            "id": log_uuid,
                            "group": group_name,
                            "semester": semester_name,
                        }
                    )

            return visiting_logs


async def get_disciplines(
    visiting_log_id: str,
    cookies: list,
    user_agent: Optional[str] = None,
) -> List[Dict]:
    """
    Получить список дисциплин для журнала.

    Args:
        visiting_log_id: ID журнала посещений
        cookies: Список куки для авторизации
        user_agent: User-Agent для запроса

    Returns:
        Список словарей с информацией о дисциплинах
    """
    url = "https://attendance.mirea.ru/rtu_tc.attendance.api.DisciplineService/GetAvailableDisciplines"

    headers = {
        "Content-Type": "application/grpc-web+proto",
        "Accept": "*/*",
        "x-grpc-web": "1",
        "x-requested-with": "XMLHttpRequest",
        "Origin": "https://attendance-app.mirea.ru",
        "Referer": "https://attendance-app.mirea.ru/",
        "User-Agent": user_agent
        or "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    }

    # Формируем protobuf request
    visiting_log_bytes = visiting_log_id.encode("utf-8")

    protobuf_data = (
        bytes([0x0A, len(visiting_log_bytes)])  # Field 1: visiting_log_id
        + visiting_log_bytes
    )

    request_body = struct.pack(">BI", 0x00, len(protobuf_data)) + protobuf_data

    connector = aiohttp.TCPConnector()

    async with aiohttp.ClientSession(connector=connector) as session:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        session.cookie_jar.update_cookies(cookies_dict)

        async with session.post(
            url,
            headers=headers,
            data=request_body,
        ) as response:
            if response.status != 200:
                return []

            content = await response.read()
            message = decode_grpc_response_bytes(content, DISCIPLINES_TYPEDEF)

            if not message:
                return []

            disciplines = []

            # Field 1 содержит список дисциплин (repeated)
            disc_data = ensure_list(get_field(message, "1", []))

            for disc in disc_data:
                if not isinstance(disc, dict):
                    continue

                # Field 1.1 = UUID, Field 1.2 = name
                disc_uuid = get_field(disc, "1", "")
                disc_name = get_field(disc, "2", "")

                if disc_uuid and disc_name:
                    disciplines.append(
                        {
                            "id": disc_uuid,
                            "name": disc_name.strip(),
                        }
                    )

            return disciplines


async def get_attendance_report(
    discipline_id: str,
    visiting_log_id: str,
    cookies: list,
    user_agent: Optional[str] = None,
) -> bytes:
    """
    Получить отчет о посещаемости.

    ВАЖНО: API ожидает параметры в обратном порядке!

    Args:
        discipline_id: ID дисциплины
        visiting_log_id: ID журнала посещений
        cookies: Список куки для авторизации
        user_agent: User-Agent для запроса

    Returns:
        Байтовые данные отчета о посещаемости
    """
    url = "https://attendance.mirea.ru/rtu_tc.attendance.api.AttendanceService/GetAttendanceVisitingLogReportForDiscipline"

    headers = {
        "Content-Type": "application/grpc-web+proto",
        "Accept": "*/*",
        "x-grpc-web": "1",
        "x-requested-with": "XMLHttpRequest",
        "Origin": "https://attendance-app.mirea.ru",
        "Referer": "https://attendance-app.mirea.ru/",
        "User-Agent": user_agent
        or "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    }

    # Параметры в protobuf идут в обратном порядке
    discipline_bytes = discipline_id.encode("utf-8")
    visiting_log_bytes = visiting_log_id.encode("utf-8")

    protobuf_data = (
        bytes([0x0A, len(discipline_bytes)])
        + discipline_bytes
        + bytes([0x12, len(visiting_log_bytes)])
        + visiting_log_bytes
    )

    request_body = struct.pack(">BI", 0x00, len(protobuf_data)) + protobuf_data

    connector = aiohttp.TCPConnector()

    async with aiohttp.ClientSession(connector=connector) as session:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        session.cookie_jar.update_cookies(cookies_dict)

        async with session.post(
            url,
            headers=headers,
            data=request_body,
        ) as response:
            content = await response.read()
            if response.status == 200 and len(content) > 0:
                return content

            return b""


async def get_lesson_attendance_data(
    cookies: list,
    lesson_date: str,  # Формат: "YYYY-MM-DD"
    lesson_time: str,  # Формат: "HH:MM"
    lesson_type: str,  # "ЛК", "ПР", "ЛАБ"
    lesson_subject: str,  # Название предмета
    lesson_index_in_day: int = 0,  # Индекс пары в дне (если несколько пар одного типа)
    db=None,
    user_agent: Optional[str] = None,
    tg_user_id: Optional[int] = None,
) -> list:
    """
    Получить данные о посещаемости для конкретного занятия.

    Args:
        cookies: Список куки для авторизации
        lesson_date: Дата занятия в формате YYYY-MM-DD
        lesson_time: Время занятия в формате HH:MM
        lesson_type: Тип занятия (ЛК, ПР, ЛАБ)
        lesson_subject: Название предмета
        lesson_index_in_day: Индекс пары в дне при наличии нескольких пар одного типа
        db: Объект базы данных
        user_agent: User-Agent для запроса
        tg_user_id: ID пользователя в Telegram

    Returns:
        Список [результат_с_данными_студентов]
    """
    try:
        logger.info(
            f"Получение данных о посещаемости для: {lesson_subject}, {lesson_date}, {lesson_time}, {lesson_type}"
        )

        # Получаем список семестров
        logs = await get_visiting_logs(cookies, user_agent)
        if not logs:
            logger.warning("Не удалось получить список семестров")
            return [None]

        logger.info(f"Найдено семестров: {len(logs)}")
        # Берем текущий семестр (первый в списке - самый актуальный)
        current_log = logs[0]
        logger.info(
            f"Выбран семестр: {current_log['semester']} ({current_log['group']})"
        )

        # Получаем список дисциплин для этого семестра
        disciplines = await get_disciplines(current_log["id"], cookies, user_agent)
        if not disciplines:
            logger.warning("Не удалось получить список дисциплин")
            return [None]

        logger.info(f"Найдено дисциплин: {len(disciplines)}")
        for i, disc in enumerate(disciplines):
            logger.debug(f"  {i + 1}. {disc['name']}")

        # Ищем нужную дисциплину по названию (улучшенный поиск)
        target_discipline = None

        # Нормализуем название предмета для поиска
        normalized_subject = lesson_subject.lower().strip()

        # Сначала ищем точное совпадение
        for disc in disciplines:
            if normalized_subject == disc["name"].lower().strip():
                target_discipline = disc
                logger.info(f"Найдено точное совпадение дисциплины: {disc['name']}")
                break

        # Если точного совпадения нет, ищем частичное
        if not target_discipline:
            for disc in disciplines:
                disc_name_lower = disc["name"].lower()
                # Проверяем вхождение в обе стороны
                if (
                    normalized_subject in disc_name_lower
                    or disc_name_lower in normalized_subject
                ):
                    target_discipline = disc
                    logger.info(
                        f"Найдено частичное совпадение дисциплины: {disc['name']}"
                    )
                    break

        # Если всё еще не нашли, проверяем по ключевым словам
        if not target_discipline:
            # Разбиваем название на слова
            subject_words = set(normalized_subject.split())
            best_match = None
            best_match_count = 0

            for disc in disciplines:
                disc_words = set(disc["name"].lower().split())
                # Считаем совпадающие слова
                common_words = subject_words & disc_words
                if len(common_words) > best_match_count:
                    best_match_count = len(common_words)
                    best_match = disc

            if best_match and best_match_count > 0:
                target_discipline = best_match
                logger.info(
                    f"Найдено совпадение по ключевым словам: {best_match['name']} ({best_match_count} слов)"
                )

        if not target_discipline:
            logger.warning(
                f"Не удалось найти дисциплину для предмета: {lesson_subject}"
            )
            logger.debug(f"Доступные дисциплины: {[d['name'] for d in disciplines]}")
            return [None]

        logger.info(f"Получение отчета для дисциплины: {target_discipline['name']}")
        # Получаем отчет о посещаемости
        report_data = await get_attendance_report(
            target_discipline["id"],
            current_log["id"],
            cookies,
            user_agent,
        )

        if not report_data:
            logger.warning("Не удалось получить отчет о посещаемости")
            return [None]

        logger.info(f"Получен отчет, размер: {len(report_data)} байт")

        # Парсим данные
        parser = AttendanceParser()
        parsed = parser.parse(report_data)

        students = parsed["students"]
        lessons = parsed["lessons"]
        attendance = parsed["attendance"]

        logger.info(f"Распарсено: студентов={len(students)}, занятий={len(lessons)}")

        # Ищем нужное занятие по дате и типу
        target_lesson = None
        lesson_index = None

        logger.info(
            f"Ищем занятие: дата={lesson_date}, тип={lesson_type}, индекс в дне={lesson_index_in_day}"
        )

        # Ищем по дате и типу, игнорируя время (может быть разница в часовых поясах)
        matching_lessons = []
        for lesson in lessons:
            # Сравниваем даты - приводим обе к формату YYYY-MM-DD
            lesson_date_str = lesson["date"]

            # Если дата в формате DD.MM или DD.MM.YYYY, преобразуем
            try:
                if "." in lesson_date_str:
                    parts = lesson_date_str.split(".")
                    if len(parts) == 2:  # DD.MM
                        # Добавляем год из lesson_date
                        year = lesson_date.split("-")[0]
                        lesson_date_formatted = (
                            f"{year}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                        )
                    elif len(parts) == 3:  # DD.MM.YYYY
                        lesson_date_formatted = (
                            f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                        )
                    else:
                        lesson_date_formatted = lesson_date_str
                elif (
                    "-" in lesson_date_str and len(lesson_date_str) == 10
                ):  # уже YYYY-MM-DD
                    lesson_date_formatted = lesson_date_str
                else:
                    lesson_date_formatted = lesson_date_str

                if (
                    lesson_date_formatted == lesson_date
                    and lesson["type"] == lesson_type
                ):
                    matching_lessons.append(lesson)
            except Exception as e:
                logger.debug(f"Ошибка сравнения дат: {e}")
                continue

        if not matching_lessons:
            logger.warning(f"Не найдено занятий для: {lesson_date}, тип={lesson_type}")
            return [None]

        # Сортируем по индексу (порядок в журнале)
        matching_lessons.sort(key=lambda x: x["index"])

        logger.info(
            f"Найдено {len(matching_lessons)} занятий {lesson_type} на {lesson_date}:"
        )
        for i, l in enumerate(matching_lessons):
            logger.debug(
                f"  {i}. {l['type']} {l['date']} {l['time']} (index={l['index']})"
            )

        # Берем занятие по индексу (первая в журнале = первая в расписании)
        if lesson_index_in_day >= len(matching_lessons):
            logger.warning(
                f"Индекс {lesson_index_in_day} больше количества занятий {len(matching_lessons)}"
            )
            # Берем последнее
            lesson_index_in_day = len(matching_lessons) - 1

        target_lesson = matching_lessons[lesson_index_in_day]
        lesson_index = target_lesson["index"]

        logger.info(f"Выбрано занятие #{lesson_index_in_day}: {target_lesson}")

        # Получаем список студентов с их статусами для этого занятия
        lesson_attendance = attendance.get(lesson_index, {})
        logger.info(f"Найдено записей посещаемости: {len(lesson_attendance)}")

        result = {
            "lesson": target_lesson,
            "students": [],
            "total_lessons": len(
                lessons
            ),  # Общее количество пар по этому предмету в семестре
        }

        for student_uuid, status in lesson_attendance.items():
            student_info = students.get(student_uuid, {})
            fio = student_info.get("fio", f"UUID:{student_uuid[:8]}")

            # Маппинг статусов
            status_text = ""
            if status == 3:
                status_text = "+"  # Был
            elif status == 2:
                status_text = "У"  # Уважительная причина
            elif status == 0 or status == 1:
                status_text = "Н"  # Не был

            result["students"].append(
                {"fio": fio, "status": status_text, "status_code": status}
            )

        # Сортируем студентов по ФИО
        result["students"].sort(key=lambda x: x["fio"])

        logger.info(f"Готово! Найдено студентов: {len(result['students'])}")
        return [result]

    except Exception as e:
        logger.error(f"Ошибка при получении данных о посещаемости: {e}", exc_info=True)
        raise

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Декодер расписания MIREA API с использованием blackboxprotobuf.
Использует автоматическое определение схемы protobuf.
"""

import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import blackboxprotobuf

from backend.mirea_api.protobuf_decoder import get_field

logger = logging.getLogger(__name__)

# Московский часовой пояс
MOSCOW_TZ = timezone(timedelta(hours=3))

# Схема для MIREA Schedule API (сгенерирована blackboxprotobuf)
# Структура: Root -> Field 2 (wrapper) -> Field 3 (lesson)
SCHEDULE_TYPEDEF = {
    "2": {
        "type": "message",
        "message_typedef": {
            "2": {"type": "int"},
            "3": {
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},  # UUID занятия
                    "2": {
                        "type": "message",
                        "message_typedef": {"1": {"type": "int"}},
                    },  # timestamp начала
                    "3": {
                        "type": "message",
                        "message_typedef": {"1": {"type": "int"}},
                    },  # timestamp конца
                    "4": {
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "bytes"},
                            "2": {"type": "string"},
                        },
                    },  # предмет
                    "5": {
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "bytes"},
                            "2": {"type": "string"},
                        },
                    },  # тип занятия
                    "6": {
                        "type": "message",
                        "message_typedef": {
                            "1": {"type": "string"},
                            "2": {"type": "string"},
                            "3": {"type": "string"},
                        },
                    },  # аудитория
                    "7": {
                        "type": "message",
                        "message_typedef": {  # преподаватель
                            "1": {"type": "string"},  # UUID
                            "2": {"type": "string"},  # Имя
                            "3": {"type": "string"},  # Фамилия
                            "4": {
                                "type": "message",
                                "message_typedef": {"1": {"type": "string"}},
                            },  # Отчество
                        },
                    },
                    "8": {
                        "type": "message",
                        "message_typedef": {
                            "1": {
                                "type": "message",
                                "message_typedef": {"1": {"type": "int"}},
                            }
                        },
                    },
                    "9": {"type": "int"},  # статус посещения
                },
            },
        },
    }
}


def skip_grpc_header(data: bytes) -> bytes:
    """
    Убирает gRPC-Web заголовок если есть.

    Формат: [1 byte flags][4 bytes big-endian length][payload]
    Flags: 0x00 = data frame, 0x80 = trailer frame (пустой ответ)
    """
    if len(data) < 5:
        return b""

    # 0x80 - trailer frame (пустой ответ, только grpc-status)
    if data[0] == 0x80:
        return b""

    # 0x00 - data frame
    if data[0] == 0x00:
        length = int.from_bytes(data[1:5], "big")
        if length == 0:
            return b""
        if 5 + length <= len(data):
            return data[5 : 5 + length]

    return data


def _parse_teacher(teacher_data: Dict[str, Any]) -> Optional[str]:
    """
    Парсит информацию о преподавателе.

    Структура:
    - "1": UUID преподавателя
    - "2": Имя
    - "3": Фамилия
    - "4": {"1": Отчество}
    """
    name = get_field(teacher_data, "2", "")  # Имя
    surname = get_field(teacher_data, "3", "")  # Фамилия
    patronymic = ""

    patronymic_data = get_field(teacher_data, "4")
    if patronymic_data:
        if isinstance(patronymic_data, dict):
            patronymic = get_field(patronymic_data, "1", "")
        elif isinstance(patronymic_data, str):
            patronymic = patronymic_data

    # Очищаем от непечатных символов
    if name:
        name = "".join(c for c in name if c.isalpha() or c.isspace()).strip()
    if surname:
        surname = "".join(c for c in surname if c.isalpha() or c.isspace()).strip()
    if patronymic:
        patronymic = "".join(
            c for c in patronymic if c.isalpha() or c.isspace()
        ).strip()

    if surname and name:
        name_initial = name[0] if name else ""
        if patronymic:
            patronymic_initial = patronymic[0]
            return f"{surname} {name_initial}. {patronymic_initial}."
        else:
            return f"{surname} {name_initial}."

    if surname:
        return surname
    return None


def _parse_lesson(
    lesson_data: Dict[str, Any], wrapper_status: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Парсит одно занятие из декодированных данных.

    Структура:
    - "1": UUID занятия
    - "2": {"1": timestamp начала}
    - "3": {"1": timestamp конца}
    - "4": {"1": UUID дисциплины, "2": название}
    - "5": {"1": UUID типа, "2": тип (ЛК/ПР/ЗАЧ/КП/Э/Конс)}
    - "6": {"1": UUID аудитории, "2": номер, "3": здание (С-20, В-78)}
    - "7": преподаватель
    - "8": {"1": {"1": timestamp подтверждения}} - если -62135596800, то не подтверждено

    Статус определяется по wrapper_status:
    - 1 = "Н" (не был)
    - 3 = "+" (был)
    Но только если field 8.1.1 содержит валидный timestamp (подтверждено)
    """
    lesson: Dict[str, Any] = {}

    # UUID занятия
    uuid_val = get_field(lesson_data, "1")
    if uuid_val:
        lesson["uuid"] = uuid_val

    # Время начала
    start_dt = None
    time_start = get_field(lesson_data, "2")
    if time_start and isinstance(time_start, dict):
        ts = get_field(time_start, "1")
        if ts and isinstance(ts, int) and 1700000000 <= ts <= 1900000000:
            start_dt = datetime.fromtimestamp(ts, tz=MOSCOW_TZ)

    # Время конца
    end_dt = None
    time_end = get_field(lesson_data, "3")
    if time_end and isinstance(time_end, dict):
        ts = get_field(time_end, "1")
        if ts and isinstance(ts, int) and 1700000000 <= ts <= 1900000000:
            end_dt = datetime.fromtimestamp(ts, tz=MOSCOW_TZ)

    # Форматируем время и дату
    if start_dt and end_dt:
        lesson["time"] = (
            f"{start_dt.hour:02d}:{start_dt.minute:02d} - {end_dt.hour:02d}:{end_dt.minute:02d}"
        )
        lesson["date"] = f"{start_dt.year}-{start_dt.month:02d}-{start_dt.day:02d}"

    # Предмет
    subject_data = get_field(lesson_data, "4")
    if subject_data and isinstance(subject_data, dict):
        subject = get_field(subject_data, "2")
        if subject:
            lesson["subject"] = subject

    # Тип занятия
    type_data = get_field(lesson_data, "5")
    if type_data and isinstance(type_data, dict):
        lesson_type = get_field(type_data, "2")
        if lesson_type:
            lesson["type"] = lesson_type

    # Аудитория и здание
    room_data = get_field(lesson_data, "6")
    if room_data and isinstance(room_data, dict):
        room_value = get_field(room_data, "2")
        # Иногда room_value может быть dict вместо string
        if isinstance(room_value, str):
            lesson["room"] = room_value

        building_value = get_field(room_data, "3")
        if isinstance(building_value, str):
            lesson["building"] = building_value

    # Преподаватель (может быть один или список)
    teacher_data = get_field(lesson_data, "7")
    if teacher_data:
        if isinstance(teacher_data, list) and len(teacher_data) > 0:
            # Берём первого преподавателя
            teacher = _parse_teacher(teacher_data[0])
        elif isinstance(teacher_data, dict):
            teacher = _parse_teacher(teacher_data)
        else:
            teacher = None
        if teacher:
            lesson["teacher"] = teacher

    # Проверяем timestamp подтверждения в field 8.1.1
    # -62135596800 = год 0001 (default/unset) - занятие не подтверждено
    confirmation_ts = None
    field_8 = get_field(lesson_data, "8")
    if field_8 and isinstance(field_8, dict):
        field_8_1 = get_field(field_8, "1")
        if isinstance(field_8_1, dict):
            confirmation_ts = get_field(field_8_1, "1")

    # Определяем статус
    # Если confirmation_ts невалидный (default value), статус пустой
    if confirmation_ts is None or confirmation_ts < 1000000000:
        # Занятие не подтверждено - нет статуса
        lesson["status"] = ""
    else:
        # Занятие подтверждено - определяем статус по wrapper_status
        # wrapper_status: 1 = "Н" (не был), 3 = "+" (был)
        if wrapper_status == 3:
            lesson["status"] = "+"
        elif wrapper_status == 1:
            lesson["status"] = "Н"
        else:
            lesson["status"] = ""

    # Проверяем что есть минимум данных
    if lesson.get("time") or lesson.get("subject"):
        return lesson
    return None


def _ensure_list(value: Any) -> List[Any]:
    """Преобразует значение в список если это не список."""
    if isinstance(value, list):
        return value
    return [value]


class ScheduleDecoder:
    """Декодер расписания MIREA с использованием blackboxprotobuf."""

    def __init__(self, b64_data: str):
        """
        Args:
            b64_data: Base64-encoded ответ от API
        """
        raw = base64.b64decode(b64_data)
        self.content = skip_grpc_header(raw)
        self._message: Optional[Dict[str, Any]] = None
        self._typedef: Optional[Dict[str, Any]] = None

    def _decode(self) -> Dict[str, Any]:
        """Декодирует protobuf сообщение."""
        if self._message is None:
            # Проверяем на пустые данные
            if not self.content or len(self.content) < 2:
                logger.debug("Пустой ответ от API")
                self._message = {}
                return self._message

            try:
                self._message, self._typedef = blackboxprotobuf.decode_message(
                    self.content, SCHEDULE_TYPEDEF
                )
            except Exception as e:
                logger.warning(f"Ошибка декодирования со схемой: {e}")
                try:
                    self._message, self._typedef = blackboxprotobuf.decode_message(
                        self.content
                    )
                except Exception as e2:
                    logger.warning(f"Ошибка декодирования без схемы: {e2}")
                    self._message = {}
        return self._message

    def parse(
        self, disciplines_list: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Парсит расписание.

        Args:
            disciplines_list: Список дисциплин для fuzzy matching

        Returns:
            Список занятий
        """
        message = self._decode()
        lessons = []

        # Структура: Root -> "2" (wrapper) -> "3" (lesson)
        wrappers_data = get_field(message, "2")
        if not wrappers_data:
            logger.debug("Поле 2 не найдено в сообщении")
            return lessons

        wrappers = _ensure_list(wrappers_data)

        for wrapper in wrappers:
            if not isinstance(wrapper, dict):
                continue

            lesson_data = get_field(wrapper, "3")
            if not lesson_data:
                continue

            # Статус из wrapper["2"]: 1 = Н (не был), 3 = + (был)
            wrapper_status = get_field(wrapper, "2")

            lesson_items = _ensure_list(lesson_data)

            for lesson_data in lesson_items:
                if not isinstance(lesson_data, dict):
                    continue

                lesson = _parse_lesson(lesson_data, wrapper_status)
                if lesson:
                    lessons.append(lesson)

        # Fuzzy matching с полным списком дисциплин
        if disciplines_list:
            for lesson in lessons:
                if lesson.get("subject"):
                    current_subject = lesson["subject"].lower().strip()
                    matched = None

                    # 1. Точное совпадение
                    for disc in disciplines_list:
                        if current_subject == disc.lower().strip():
                            matched = disc
                            break

                    # 2. Частичное совпадение
                    if not matched:
                        for disc in disciplines_list:
                            disc_lower = disc.lower()
                            if (
                                current_subject in disc_lower
                                or disc_lower in current_subject
                            ):
                                matched = disc
                                break

                    # 3. По ключевым словам
                    if not matched:
                        subject_words = set(current_subject.split())
                        best_match = None
                        best_count = 0
                        for disc in disciplines_list:
                            disc_words = set(disc.lower().split())
                            common = subject_words & disc_words
                            if len(common) > best_count:
                                best_count = len(common)
                                best_match = disc
                        if best_match and best_count > 0:
                            matched = best_match

                    if matched:
                        lesson["subject"] = matched

        logger.debug(f"Parsed {len(lessons)} lessons")
        return lessons


def parse_schedule(
    b64_data: str, disciplines_list: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Парсит base64 ответ расписания в список занятий.

    Args:
        b64_data: Base64-encoded строка с ответом от API
        disciplines_list: Список полных названий дисциплин для сопоставления

    Returns:
        Список занятий с полями:
            - uuid: ID занятия
            - time: время (например, "10:40 - 12:10")
            - date: дата (например, "2025-11-14")
            - room: номер аудитории (например, "425")
            - building: здание (С-20, В-78, СДО)
            - subject: название предмета
            - teacher: преподаватель (Фамилия И. О.)
            - type: тип занятия (ЛК, ПР, ЗАЧ, КП, Э, Конс)
            - status: статус посещения ("Н", "+", "")
    """
    decoder = ScheduleDecoder(b64_data)
    return decoder.parse(disciplines_list=disciplines_list)

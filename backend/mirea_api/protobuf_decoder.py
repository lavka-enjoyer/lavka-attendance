#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIREA Attendance API - Protobuf Decoder
=======================================

Утилиты для декодирования gRPC-Web protobuf ответов от MIREA API.
Использует blackboxprotobuf для автоматического определения схемы.

Схемы (typedef) для различных эндпоинтов находятся в отдельном файле:
    from backend.mirea_api.protobuf_schemas import SCHEDULE_TYPEDEF, ...

Пример использования:
    from backend.mirea_api.protobuf_decoder import decode_grpc_response
    from backend.mirea_api.protobuf_schemas import ME_INFO_TYPEDEF

    message = decode_grpc_response(base64_response, ME_INFO_TYPEDEF)
"""

import base64
import logging
import struct
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import blackboxprotobuf

# Реэкспорт схем для обратной совместимости
from backend.mirea_api.protobuf_schemas import (
    ACS_EVENTS_TYPEDEF,
    ATTENDANCE_REPORT_TYPEDEF,
    BRS_TYPEDEF,
    DISCIPLINES_TYPEDEF,
    ME_INFO_TYPEDEF,
    SCHEDULE_TYPEDEF,
    VISITING_LOGS_TYPEDEF,
)

logger = logging.getLogger(__name__)

# Московский часовой пояс
MOSCOW_TZ = timezone(timedelta(hours=3))


# =============================================================================
# gRPC-Web Header Processing
# =============================================================================

def skip_grpc_header(data: bytes) -> bytes:
    """
    Убирает gRPC-Web заголовок и trailer если есть.

    gRPC-Web формат: [1 byte flags][4 bytes big-endian length][payload]
    Flags: 0x00 = data frame, 0x80 = trailer frame (пустой ответ)

    Args:
        data: Raw bytes ответа от API

    Returns:
        Protobuf payload без заголовка
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


# =============================================================================
# Protobuf Decoding
# =============================================================================

def decode_grpc_response(
    b64_data: str,
    typedef: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Декодирует base64 gRPC-Web ответ в dict.

    Args:
        b64_data: Base64-encoded строка с ответом от API
        typedef: Опциональная схема protobuf для более точного декодирования

    Returns:
        Декодированное сообщение как dict
    """
    try:
        raw = base64.b64decode(b64_data)
        content = skip_grpc_header(raw)

        if not content or len(content) < 2:
            logger.debug("Пустой ответ от API")
            return {}

        if typedef:
            try:
                message, _ = blackboxprotobuf.decode_message(content, typedef)
                return message
            except Exception as e:
                logger.warning(f"Ошибка декодирования со схемой: {e}")

        # Декодируем без схемы
        message, _ = blackboxprotobuf.decode_message(content)
        return message

    except Exception as e:
        logger.warning(f"Ошибка декодирования protobuf: {e}")
        return {}


def decode_grpc_response_bytes(
    content: bytes,
    typedef: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Декодирует raw bytes gRPC-Web ответ в dict.

    Args:
        content: Raw bytes ответа от API
        typedef: Опциональная схема protobuf

    Returns:
        Декодированное сообщение как dict
    """
    try:
        data = skip_grpc_header(content)

        if not data or len(data) < 2:
            logger.debug("Пустой ответ от API")
            return {}

        if typedef:
            try:
                message, _ = blackboxprotobuf.decode_message(data, typedef)
                return message
            except Exception as e:
                logger.warning(f"Ошибка декодирования со схемой: {e}")

        message, _ = blackboxprotobuf.decode_message(data)
        return message

    except Exception as e:
        logger.warning(f"Ошибка декодирования protobuf: {e}")
        return {}


# =============================================================================
# Helper Functions
# =============================================================================

def ensure_list(value: Any) -> List[Any]:
    """
    Преобразует значение в список если это не список.

    blackboxprotobuf может вернуть один элемент как dict вместо списка,
    эта функция нормализует результат.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_field(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Безопасно получает поле из dict, учитывая альтернативные ключи blackboxprotobuf.

    blackboxprotobuf может создавать ключи вида "1-1", "1-2" при конфликтах типов.
    Эта функция сначала пробует точный ключ, затем варианты с суффиксами.

    Args:
        data: Словарь с данными
        key: Ключ поля (например, "1")
        default: Значение по умолчанию

    Returns:
        Найденное значение или default
    """
    if not isinstance(data, dict):
        return default

    # Сначала пробуем точный ключ
    if key in data:
        return data[key]

    # Пробуем варианты с суффиксами (1-1, 1-2, ...)
    for suffix in range(1, 5):
        alt_key = f"{key}-{suffix}"
        if alt_key in data:
            return data[alt_key]

    return default


def get_nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Безопасно получает вложенное значение из dict.

    Учитывает альтернативные ключи blackboxprotobuf (например, "1-1" вместо "1").

    Args:
        data: Исходный словарь
        *keys: Путь ключей (например, "1", "2", "1")
        default: Значение по умолчанию

    Returns:
        Найденное значение или default

    Example:
        >>> get_nested({"1": {"2": {"3": "value"}}}, "1", "2", "3")
        "value"
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = get_field(current, key)
        if current is None:
            return default
    return current


# =============================================================================
# Type Conversions
# =============================================================================

def fixed64_to_double(value: Union[int, bytes]) -> float:
    """
    Конвертирует fixed64 (int или bytes) в double.

    В protobuf double хранится как 8-байтное значение.
    blackboxprotobuf может вернуть его как int (fixed64) или bytes.
    Эта функция корректно конвертирует оба варианта.

    Args:
        value: fixed64 значение (int или bytes)

    Returns:
        float значение

    Example:
        >>> fixed64_to_double(4626322717216342016)
        40.0
    """
    if isinstance(value, bytes):
        if len(value) == 8:
            return struct.unpack('<d', value)[0]
        return 0.0
    if isinstance(value, int):
        try:
            b = struct.pack('<Q', value)  # unsigned long long (8 bytes)
            return struct.unpack('<d', b)[0]
        except struct.error:
            return 0.0
    return 0.0


def timestamp_to_datetime(ts: int) -> Optional[datetime]:
    """
    Конвертирует Unix timestamp в datetime с московским временем.

    Args:
        ts: Unix timestamp в секундах

    Returns:
        datetime объект или None если timestamp невалидный
    """
    # Проверка на валидный диапазон (2020-2030)
    if not isinstance(ts, int) or ts < 1577836800 or ts > 1893456000:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=MOSCOW_TZ)
    except (ValueError, OSError):
        return None


# =============================================================================
# FIO (Name) Formatting
# =============================================================================

def format_fio(
    first_name: str = "",
    last_name: str = "",
    patronymic: str = "",
    short: bool = True
) -> str:
    """
    Форматирует ФИО.

    Args:
        first_name: Имя
        last_name: Фамилия
        patronymic: Отчество
        short: Если True, возвращает "Фамилия И. О.", иначе полное ФИО

    Returns:
        Отформатированное ФИО

    Example:
        >>> format_fio("Иван", "Иванов", "Иванович", short=True)
        "Иванов И. И."
        >>> format_fio("Иван", "Иванов", "Иванович", short=False)
        "Иванов Иван Иванович"
    """
    # Очищаем от непечатных символов
    first_name = "".join(c for c in first_name if c.isalpha() or c.isspace()).strip()
    last_name = "".join(c for c in last_name if c.isalpha() or c.isspace()).strip()
    patronymic = "".join(c for c in patronymic if c.isalpha() or c.isspace()).strip()

    if short:
        if last_name and first_name:
            if patronymic:
                return f"{last_name} {first_name[0]}. {patronymic[0]}."
            return f"{last_name} {first_name[0]}."
        return last_name or first_name
    else:
        parts = [last_name, first_name, patronymic]
        return " ".join(p for p in parts if p)


def parse_person_name(person_data: Dict[str, Any], short: bool = True) -> str:
    """
    Парсит ФИО из стандартной структуры MIREA API.

    Структура:
    - "1": UUID человека (опционально)
    - "2": Имя
    - "3": Фамилия
    - "4": {"1": Отчество}

    Args:
        person_data: Dict с данными о человеке
        short: Если True, возвращает "Фамилия И. О."

    Returns:
        Отформатированное ФИО
    """
    if not isinstance(person_data, dict):
        return ""

    first_name = person_data.get("2", "")
    last_name = person_data.get("3", "")
    patronymic = ""

    if "4" in person_data:
        patronymic_data = person_data["4"]
        if isinstance(patronymic_data, dict):
            patronymic = patronymic_data.get("1", "")
        elif isinstance(patronymic_data, str):
            patronymic = patronymic_data

    return format_fio(first_name, last_name, patronymic, short)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Schemas (re-exported from protobuf_schemas)
    "ME_INFO_TYPEDEF",
    "DISCIPLINES_TYPEDEF",
    "ACS_EVENTS_TYPEDEF",
    "VISITING_LOGS_TYPEDEF",
    "BRS_TYPEDEF",
    "ATTENDANCE_REPORT_TYPEDEF",
    "SCHEDULE_TYPEDEF",
    # Constants
    "MOSCOW_TZ",
    # gRPC functions
    "skip_grpc_header",
    "decode_grpc_response",
    "decode_grpc_response_bytes",
    # Helpers
    "ensure_list",
    "get_field",
    "get_nested",
    # Conversions
    "fixed64_to_double",
    "timestamp_to_datetime",
    # FIO
    "format_fio",
    "parse_person_name",
]

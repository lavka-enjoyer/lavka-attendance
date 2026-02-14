"""
Модуль для получения календаря занятий (количество пар по дням)
Использует прямой endpoint GetDailyLessonsCountForSemesterOfAvailableVisitingLogs
"""

import logging
from typing import Any, Dict, List, Optional

import aiohttp
import blackboxprotobuf

logger = logging.getLogger(__name__)

# Схема для GetDailyLessonsCountForSemesterOfAvailableVisitingLogs
CALENDAR_TYPEDEF = {
    "1": {
        "type": "message",
        "message_typedef": {
            "1": {"type": "int"},  # Количество пар
            "2": {
                "type": "message",
                "message_typedef": {
                    "1": {"type": "int"},  # Год
                    "2": {"type": "int"},  # Месяц
                    "3": {"type": "int"},  # День
                },
            },
            "3": {"type": "int"},  # Флаг (опционально)
        },
    }
}


def _skip_grpc_header(data: bytes) -> bytes:
    """Убирает gRPC-Web заголовок."""
    if len(data) < 5:
        return b""
    if data[0] == 0x80:  # Trailer frame
        return b""
    if data[0] == 0x00:
        length = int.from_bytes(data[1:5], "big")
        if length == 0:
            return b""
        if 5 + length <= len(data):
            return data[5 : 5 + length]
    return data


def _parse_calendar_response(content: bytes) -> Dict[str, Dict[str, Dict[int, int]]]:
    """
    Парсит ответ GetDailyLessonsCountForSemesterOfAvailableVisitingLogs.

    Структура:
    {
        "1": [
            {"1": 4, "2": {"1": 2025, "2": 12, "3": 1}},  # 4 пары 1 декабря 2025
            ...
        ]
    }

    Returns:
        {"2025": {"12": {1: 4, 2: 3, ...}}, ...}
    """
    protobuf_data = _skip_grpc_header(content)

    if not protobuf_data or len(protobuf_data) < 2:
        return {}

    try:
        message, _ = blackboxprotobuf.decode_message(protobuf_data, CALENDAR_TYPEDEF)
    except Exception as e:
        logger.warning(f"Ошибка декодирования со схемой: {e}")
        try:
            message, _ = blackboxprotobuf.decode_message(protobuf_data)
        except Exception as e2:
            logger.warning(f"Ошибка декодирования без схемы: {e2}")
            return {}

    calendar: Dict[str, Dict[str, Dict[int, int]]] = {}

    if "1" not in message:
        return calendar

    entries = message["1"]
    if not isinstance(entries, list):
        entries = [entries]

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        count = entry.get("1", 0)
        date_info = entry.get("2", {})

        if not isinstance(date_info, dict):
            continue

        year = date_info.get("1")
        month = date_info.get("2")
        day = date_info.get("3")

        if not all([year, month, day]):
            continue

        year_str = str(year)
        month_str = f"{month:02d}"

        if year_str not in calendar:
            calendar[year_str] = {}
        if month_str not in calendar[year_str]:
            calendar[year_str][month_str] = {}

        calendar[year_str][month_str][day] = count

    return calendar


def _encode_varint(value: int) -> bytes:
    """Кодирует число в varint формат protobuf."""
    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _build_calendar_request(start_ts: int, end_ts: int) -> bytes:
    """
    Создаёт protobuf запрос для GetDailyLessonsCountForSemesterOfAvailableVisitingLogs.

    Структура:
    - Field 2: {Field 1: start_timestamp}
    - Field 3: {Field 1: end_timestamp}
    """
    # Field 2.1 = start_ts
    start_varint = _encode_varint(start_ts)
    field_2_1 = bytes([0x08]) + start_varint  # field 1, varint
    field_2 = bytes([0x12, len(field_2_1)]) + field_2_1  # field 2, length-delimited

    # Field 3.1 = end_ts
    end_varint = _encode_varint(end_ts)
    field_3_1 = bytes([0x08]) + end_varint  # field 1, varint
    field_3 = bytes([0x1A, len(field_3_1)]) + field_3_1  # field 3, length-delimited

    payload = field_2 + field_3

    # gRPC-Web header: flags(1) + length(4) + payload
    return bytes([0x00, 0x00, 0x00, 0x00, len(payload)]) + payload


async def get_daily_lessons_count(
    cookies: List[Dict[str, Any]],
    user_agent: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
) -> Optional[Dict[str, Dict[str, Dict[int, int]]]]:
    """
    Получить количество занятий по дням для указанного периода.

    Использует прямой endpoint GetDailyLessonsCountForSemesterOfAvailableVisitingLogs.

    Args:
        cookies: Список куки для авторизации
        user_agent: User-Agent для запроса
        start_ts: Unix timestamp начала периода (опционально, по умолчанию -2 месяца)
        end_ts: Unix timestamp конца периода (опционально, по умолчанию +3 месяца)

    Returns:
        Словарь с календарем занятий:
        {"2025": {"12": {1: 4, 2: 3, ...}}, "2026": {"01": {14: 1, ...}}}
    """
    from datetime import datetime, timedelta

    API_BASE = "https://attendance.mirea.ru/rtu_tc.attendance.api"
    URL = f"{API_BASE}.LessonService/GetDailyLessonsCountForSemesterOfAvailableVisitingLogs"

    # Заголовки как в оригинальном запросе - БИНАРНЫЙ формат
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/grpc-web+proto",
        "Origin": "https://attendance-app.mirea.ru",
        "Referer": "https://attendance-app.mirea.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "x-grpc-web": "1",
        "x-requested-with": "XMLHttpRequest",
        "pulse-app-type": "pulse-app",
        "pulse-app-version": "1.5.9+4499",
    }

    if user_agent:
        headers["User-Agent"] = user_agent

    try:
        # Если даты не указаны, используем значения по умолчанию
        now = datetime.now()
        if start_ts is None:
            start_date = now - timedelta(days=60)  # ~2 месяца назад
            start_ts = int(start_date.timestamp())
        if end_ts is None:
            end_date = now + timedelta(days=90)  # ~3 месяца вперёд
            end_ts = int(end_date.timestamp())

        # Создаём БИНАРНЫЙ protobuf запрос
        request_body = _build_calendar_request(start_ts, end_ts)
        logger.debug(
            f"Calendar request: start_ts={start_ts}, end_ts={end_ts}, body_hex={request_body.hex()}"
        )

        # Cookie header напрямую
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        headers["Cookie"] = cookie_header

        async with aiohttp.ClientSession() as session:
            async with session.post(
                URL,
                headers=headers,
                data=request_body,  # БИНАРНЫЕ данные
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                logger.debug(f"Calendar API response status: {response.status}")
                if response.status != 200:
                    logger.warning(f"Ошибка API: статус {response.status}")
                    return None

                # Ответ тоже БИНАРНЫЙ
                content = await response.read()
                logger.debug(f"Calendar API response length: {len(content)} bytes")
                if len(content) > 0:
                    logger.debug(f"Calendar API first 50 bytes: {content[:50].hex()}")

        if not content or len(content) < 10:
            logger.debug("Пустой ответ от API")
            return None

        calendar = _parse_calendar_response(content)

        if calendar:
            total_days = sum(
                len(days) for months in calendar.values() for days in months.values()
            )
            logger.debug(f"Получено {total_days} дней с занятиями")

        return calendar if calendar else None

    except Exception as e:
        logger.error(f"Ошибка получения календаря: {e}", exc_info=True)
        return None

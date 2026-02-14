#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для получения событий ACS (система контроля доступа) и определения
статуса нахождения в вузе. Использует blackboxprotobuf для декодирования.
"""

import logging
import re
import struct
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from backend.database import DBModel
from backend.mirea_api.protobuf_decoder import (
    ACS_EVENTS_TYPEDEF,
    MOSCOW_TZ,
    decode_grpc_response_bytes,
    ensure_list,
    get_field,
    get_nested,
    timestamp_to_datetime,
)

from .get_cookies import generate_random_mobile_user_agent

logger = logging.getLogger(__name__)


def parse_acs_events(grpc_response_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Парсит ответ gRPC с событиями ACS.

    Структура ответа:
    - Field 1 (repeated): События
      - Field 1: UUID события
      - Field 2: {1: timestamp}
      - Field 3: access_point_from {1: uuid, 2: name}
      - Field 4: access_point_to {1: uuid, 2: name}

    Args:
        grpc_response_bytes: Байтовые данные ответа gRPC

    Returns:
        Список словарей с событиями ACS
    """
    message = decode_grpc_response_bytes(grpc_response_bytes, ACS_EVENTS_TYPEDEF)

    if not message:
        logger.debug("Пустой ответ от ACS API")
        return []

    events = []
    event_items = ensure_list(get_field(message, "1", []))

    for item in event_items:
        if not isinstance(item, dict):
            continue

        event = {}

        # Field 1: UUID события
        event_uuid = item.get("1", "")
        if event_uuid and len(str(event_uuid)) == 36:
            event["event_uuid"] = str(event_uuid)

        # Field 2: Timestamp {1: int}
        ts_data = item.get("2", {})
        if isinstance(ts_data, dict):
            ts = ts_data.get("1")
            if ts and isinstance(ts, int):
                dt = timestamp_to_datetime(ts)
                if dt:
                    event["timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                    event["date"] = dt.strftime("%Y-%m-%d")
                    event["time"] = dt.strftime("%H:%M:%S")

        # Field 3: access_point_from
        from_data = item.get("3", {})
        if isinstance(from_data, dict):
            event["access_point_from"] = {
                "access_point_uuid": from_data.get("1", ""),
                "access_point_name": from_data.get("2", ""),
            }

        # Field 4: access_point_to
        to_data = item.get("4", {})
        if isinstance(to_data, dict):
            event["access_point_to"] = {
                "access_point_uuid": to_data.get("1", ""),
                "access_point_name": to_data.get("2", ""),
            }

        if event.get("event_uuid") or event.get("timestamp"):
            events.append(event)

    logger.debug(f"Распарсено {len(events)} событий ACS")
    return events


def build_acs_request(user_uuid: str, date: datetime) -> bytes:
    """
    Создает protobuf запрос для получения событий ACS.

    Args:
        user_uuid: UUID пользователя
        date: Дата для запроса (в московском времени GMT+3)

    Returns:
        bytes: Готовый gRPC запрос
    """
    # Field 1: user_uuid (string)
    uuid_bytes = user_uuid.encode("utf-8")
    field1 = bytes([0x0A, len(uuid_bytes)]) + uuid_bytes

    # Field 2: TimeRange (submessage)
    # Начало дня (00:00:00 по МСК)
    start_moscow = datetime(
        date.year, date.month, date.day, 0, 0, 0, tzinfo=MOSCOW_TZ
    )
    # Конец дня (23:59:59 по МСК)
    end_moscow = datetime(
        date.year, date.month, date.day, 23, 59, 59, tzinfo=MOSCOW_TZ
    )

    # Конвертируем в UTC timestamp для API
    start_ts = int(start_moscow.timestamp())
    end_ts = int(end_moscow.timestamp())

    def encode_varint(value: int) -> bytes:
        result = []
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)

    start_ts_bytes = encode_varint(start_ts)
    end_ts_bytes = encode_varint(end_ts)

    # TimeRange submessage
    # Field 1: from (submessage with field 1 = timestamp)
    from_msg = bytes([0x0A, len(start_ts_bytes) + 1, 0x08]) + start_ts_bytes
    # Field 2: to (submessage with field 1 = timestamp)
    to_msg = bytes([0x12, len(end_ts_bytes) + 1, 0x08]) + end_ts_bytes

    time_range = from_msg + to_msg
    field2 = bytes([0x12, len(time_range)]) + time_range

    # Field 3: page number (varint) = 1
    field3 = bytes([0x18, 0x01])

    # Field 5: page size (varint) = 40
    field5 = bytes([0x28, 0x02])

    # Собираем protobuf
    protobuf_data = field1 + field2 + field3 + field5

    # Добавляем gRPC заголовок
    request_body = struct.pack(">BI", 0x00, len(protobuf_data)) + protobuf_data

    return request_body


async def get_user_uuid(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> str:
    """
    Получает UUID пользователя из GetMeInfo.

    Args:
        cookies: Список куки для авторизации
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        UUID пользователя

    Raises:
        Exception: При ошибке получения UUID
    """
    try:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

        url = "https://attendance.mirea.ru/rtu_tc.rtu_attend.app.UserService/GetMeInfo"
        headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "*/*",
            "x-grpc-web": "1",
            "x-requested-with": "XMLHttpRequest",
            "Origin": "https://attendance-app.mirea.ru",
            "Referer": "https://attendance-app.mirea.ru/",
            "User-Agent": (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            ),
        }

        request_body = bytes([0x00, 0x00, 0x00, 0x00, 0x00])

        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(cookies_dict)
            async with session.post(
                url,
                data=request_body,
                headers=headers,
                timeout=4,
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка запроса к {url}. Код: {response.status}")
                content = await response.read()

        # Убираем gRPC заголовок
        if len(content) > 5 and content[0] == 0x00:
            content = content[5:]

        # Ищем UUID (первый UUID в ответе - это UUID пользователя)
        uuid_pattern = rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        match = re.search(uuid_pattern, content)
        if match:
            return match.group().decode("ascii")

        raise Exception("Не удалось найти UUID пользователя")

    except Exception as e:
        logger.error(f"Ошибка при получении UUID пользователя: {e}")
        raise


async def get_acs_events_for_date(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    date: datetime,
    user_agent: Optional[str] = None,
) -> List[Dict]:
    """
    Получить события ACS за указанную дату.

    Args:
        cookies: Список куки для авторизации
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        date: Дата для получения событий
        user_agent: User-Agent для запроса

    Returns:
        Список словарей с событиями ACS

    Raises:
        Exception: При ошибках запроса
    """
    try:
        # Получаем UUID пользователя
        user_uuid = await get_user_uuid(cookies, tg_user_id, db, user_agent)
        logger.info(f"UUID пользователя: {user_uuid}")

        # Формируем запрос
        request_body = build_acs_request(user_uuid, date)

        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

        url = "https://attendance.mirea.ru/rtu_tc.rtu_attend.humanpass.HumanPassService/GetHumanAcsEvents"
        headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "*/*",
            "x-grpc-web": "1",
            "x-requested-with": "XMLHttpRequest",
            "Origin": "https://attendance-app.mirea.ru",
            "Referer": "https://attendance-app.mirea.ru/",
            "User-Agent": (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            ),
        }

        logger.info(f"Запрашиваем события ACS за {date.strftime('%Y-%m-%d')}...")

        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(cookies_dict)
            async with session.post(
                url,
                data=request_body,
                headers=headers,
                timeout=4,
            ) as response:
                if response.status != 200:
                    logger.warning(f"Ошибка: HTTP {response.status}")
                    return []

                content = await response.read()

        logger.info(f"Получен ответ: {len(content)} байт")

        # Парсим ответ
        events = parse_acs_events(content)

        return events

    except Exception as e:
        logger.error(f"Ошибка при получении событий ACS: {e}")
        raise


def determine_university_status(events: List[Dict]) -> Dict:
    """
    Определяет, находится ли человек в университете на основе событий ACS.

    Args:
        events: Список событий ACS

    Returns:
        Словарь со статусом и деталями
    """
    if not events:
        return {
            "is_inside_university": False,
            "last_event_time": None,
            "last_event_details": "Нет данных о проходах за этот день",
        }

    # Сортируем события по времени
    sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""))
    last_event = sorted_events[-1]

    # Смотрим на последнюю запись:
    # Если access_point_to = "Неконтролируемая территория" → ВХОД → В УНИВЕРСИТЕТЕ
    # Если access_point_from = "Неконтролируемая территория" → ВЫХОД → НЕ в университете
    last_from = last_event.get("access_point_from", {})
    last_from_name = last_from.get("access_point_name", "")
    last_to = last_event.get("access_point_to", {})
    last_to_name = last_to.get("access_point_name", "")

    is_inside = last_to_name == "Неконтролируемая территория"

    return {
        "is_inside_university": is_inside,
        "last_event_time": last_event.get("time"),
        "last_event_details": f"{'ВХОД' if is_inside else 'ВЫХОД'} (from: {last_from_name} → to: {last_to_name})",
    }

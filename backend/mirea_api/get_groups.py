#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для получения групп пользователя из MIREA API.
Использует blackboxprotobuf для декодирования protobuf ответов.
"""

import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp

from backend.database import DBModel
from backend.mirea_api.get_cookies import generate_random_mobile_user_agent
from backend.mirea_api.protobuf_decoder import (
    VISITING_LOGS_TYPEDEF,
    decode_grpc_response,
    ensure_list,
    get_field,
    get_nested,
)

logger = logging.getLogger(__name__)

# Паттерн для названия группы: 4 русские буквы, тире, 2 цифры, тире, 2 цифры
GROUP_PATTERN = re.compile(r"[А-ЯЁа-яё]{4}-\d{2}-\d{2}")


def parse_visiting_logs(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Парсит ответ GetAvailableVisitingLogsOfStudent.

    Структура ответа:
    - Field 1 (repeated): Logs
      - Field 1: Log info
        - Field 1: log UUID
        - Field 2: group name (например, "ИКБО-01-23")
        - Field 4: semester UUID
        - Field 6: Semester info
          - Field 1: semester UUID
          - Field 2: semester name (например, "Осень 25-26")
      - Field 2: некий int
      - Field 3: некий int
      - Field 4: human UUID

    Args:
        message: Декодированное protobuf сообщение

    Returns:
        Список логов с информацией о группах и семестрах
    """
    logs = []
    log_items = ensure_list(get_field(message, "1", []))

    for item in log_items:
        if not isinstance(item, dict):
            continue

        log_entry = {}

        # Field 1: Log info wrapper
        log_info = item.get("1", {})
        if isinstance(log_info, dict):
            # Field 1: log UUID
            log_uuid = log_info.get("1", "")
            if log_uuid:
                log_entry["log_uuid"] = log_uuid

            # Field 2: group name
            group_name = log_info.get("2", "")
            if group_name:
                log_entry["group_name"] = group_name

            # Field 4: semester UUID
            semester_uuid = log_info.get("4", "")
            if semester_uuid:
                log_entry["semester_uuid"] = semester_uuid

            # Field 6: Semester info
            semester_info = log_info.get("6", {})
            if isinstance(semester_info, dict):
                sem_name = semester_info.get("2", "")
                if sem_name:
                    log_entry["semester_name"] = sem_name

        # Field 4: human UUID
        human_uuid = item.get("4", "")
        if human_uuid:
            log_entry["human_uuid"] = human_uuid

        if log_entry.get("group_name") or log_entry.get("log_uuid"):
            logs.append(log_entry)

    logger.debug(f"Распарсено {len(logs)} логов посещаемости")
    return logs


async def _query_get_group(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Отправляет POST-запрос к эндпоинту GetAvailableVisitingLogsOfStudent.

    Args:
        cookies: Список куки в виде словарей
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        Декодированное protobuf сообщение

    Raises:
        Exception: При ошибках запроса
    """
    try:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

        url = "https://attendance.mirea.ru/rtu_tc.attendance.api.VisitingLogService/GetAvailableVisitingLogsOfStudent"
        headers = {
            "Accept": "application/grpc-web-text",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "attendance-app-type": "student-app",
            "attendance-app-version": "1.0.0+1281",
            "Content-Type": "application/grpc-web-text",
            "Origin": "https://attendance-app.mirea.ru",
            "Referer": "https://attendance-app.mirea.ru/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            ),
            "X-Grpc-Web": "1",
            "x-requested-with": "XMLHttpRequest",
            "X-User-Agent": "grpc-web-javascript/0.1",
        }

        # Пустое тело запроса (base64 encoded)
        request_body = "AAAAAAA="

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
                response_text = await response.text()

        # Декодируем protobuf ответ
        message = decode_grpc_response(response_text, VISITING_LOGS_TYPEDEF)
        return message

    except Exception as e:
        logger.error(f"Ошибка при получении группы: {e}")
        raise


def _semester_sort_key(semester_name: str) -> tuple:
    """
    Возвращает ключ сортировки для названия семестра.
    Формат: "Осень 25-26" или "Весна 25-26".
    Осень старше Весны в одном учебном году (осень идёт первой).

    Returns:
        Кортеж (год_окончания, сезон) — чем больше, тем новее семестр.
        Сезон: Осень=1, Весна=0 (осень новее при одинаковом годе)
    """
    if not semester_name:
        return (0, 0)
    try:
        parts = semester_name.strip().split()
        season = parts[0].lower() if parts else ""
        years = parts[1] if len(parts) > 1 else "0-0"
        end_year = int(years.split("-")[1]) if "-" in years else 0
        season_order = 1 if "осень" in season else 0
        return (end_year, season_order)
    except Exception:
        return (0, 0)


async def get_group(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> list:
    """
    Получает данные с эндпоинта GetAvailableVisitingLogsOfStudent и
    извлекает из них все группы.

    Группы сортируются по семестру — актуальная (из последнего семестра) идёт последней,
    чтобы groups[0][-1] всегда возвращал текущую группу студента.

    Args:
        cookies: Список куки в виде словарей
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        Список [список_групп]. Если групп не найдено – [[]]
    """
    try:
        message = await _query_get_group(cookies, tg_user_id, db, user_agent)
        logs = parse_visiting_logs(message)

        # Сортируем логи по семестру от старого к новому
        logs.sort(key=lambda log: _semester_sort_key(log.get("semester_name", "")))

        # Извлекаем уникальные группы в порядке от старых к новым семестрам
        # Так groups[-1] будет группой из актуального семестра
        groups = []
        seen = set()
        for log in logs:
            group_name = log.get("group_name", "")
            if group_name and GROUP_PATTERN.match(group_name):
                if group_name in seen:
                    # Если группа уже есть — переставляем её в конец (более новый семестр)
                    groups.remove(group_name)
                groups.append(group_name)
                seen.add(group_name)

        logger.debug(f"Группы пользователя {tg_user_id} (от старых к новым): {groups}")
        return [groups]
    except Exception as e:
        raise e


async def get_visiting_logs_full(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Получает полную информацию о логах посещаемости.

    В отличие от get_group, возвращает полную информацию:
    - log_uuid: UUID лога
    - group_name: Название группы
    - semester_uuid: UUID семестра
    - semester_name: Название семестра
    - human_uuid: UUID человека

    Args:
        cookies: Список куки в виде словарей
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        Список логов с полной информацией
    """
    message = await _query_get_group(cookies, tg_user_id, db, user_agent)
    return parse_visiting_logs(message)

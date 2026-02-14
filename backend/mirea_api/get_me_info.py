#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для получения информации о пользователе из MIREA API.
Использует blackboxprotobuf для декодирования protobuf ответов.
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from backend.database import DBModel
from backend.mirea_api.protobuf_decoder import (
    ME_INFO_TYPEDEF,
    decode_grpc_response,
    format_fio,
    get_nested,
)

from .get_cookies import generate_random_mobile_user_agent

logger = logging.getLogger(__name__)


def parse_me_info(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Парсит ответ GetMeInfo.

    Структура ответа:
    - Field 1: Wrapper
      - Field 1: User Info
        - Field 1: UUID пользователя
        - Field 2: Имя
        - Field 3: Фамилия
        - Field 4: {1: Отчество}
        - Field 5: claims (repeated)
        - Field 6: email
        - Field 7: preferences (JSON)
      - Field 2: logout URL

    Args:
        message: Декодированное protobuf сообщение

    Returns:
        Словарь с информацией о пользователе
    """
    result = {}

    if not message:
        logger.warning("Пустое сообщение")
        return result

    logger.debug(f"Структура сообщения: {list(message.keys())}")

    # get_nested автоматически обрабатывает альтернативные ключи blackboxprotobuf (1-1, 1-2, ...)
    user_info = get_nested(message, "1", "1", default={})

    if not user_info:
        logger.warning(f"Не удалось найти информацию о пользователе. Ключи: {list(message.keys())}")
        return result

    # UUID пользователя
    uuid = user_info.get("1", "")
    if uuid:
        result["uuid"] = uuid

    # Имя
    first_name = user_info.get("2", "")
    if first_name:
        result["first_name"] = first_name

    # Фамилия
    last_name = user_info.get("3", "")
    if last_name:
        result["last_name"] = last_name

    # Отчество
    patronymic_data = user_info.get("4", {})
    patronymic = ""
    if isinstance(patronymic_data, dict):
        patronymic = patronymic_data.get("1", "")
    elif isinstance(patronymic_data, str):
        patronymic = patronymic_data
    if patronymic:
        result["patronymic"] = patronymic

    # Email
    email = user_info.get("6", "")
    if email:
        result["email"] = email

    # Форматируем полное ФИО
    if first_name or last_name:
        result["fio"] = format_fio(first_name, last_name, patronymic, short=False)
        result["fio_short"] = format_fio(first_name, last_name, patronymic, short=True)

    logger.debug(f"Распарсена информация о пользователе: {result.get('fio_short', '')}")
    return result


async def _query_me_info(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> list:
    """
    Отправляет POST-запрос к эндпоинту GetMeInfo с использованием переданных куки.

    Args:
        cookies: Список куки в виде словарей
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        Список [ФИО пользователя]

    Raises:
        Exception: При ошибках запроса
    """
    try:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

        url = "https://attendance.mirea.ru/rtu_tc.rtu_attend.app.UserService/GetMeInfo"
        headers = {
            "Accept": "application/grpc-web-text",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "attendance-app-type": "student-app",
            "attendance-app-version": "1.0.0+1273",
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

        # Тело запроса (base64 encoded)
        request_body = (
            "AAAAACwKKGh0dHBzOi8vYXR0ZW5kYW5jZS1hcHAubWlyZWEucnUvc2VydmljZXMYAQ=="
        )

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
        logger.debug(f"Длина ответа: {len(response_text)}, начало: {response_text[:50]}...")
        message = decode_grpc_response(response_text, ME_INFO_TYPEDEF)
        logger.debug(f"Декодированное сообщение: {message}")

        # Парсим информацию о пользователе
        user_info = parse_me_info(message)

        # Возвращаем полное ФИО для обратной совместимости
        fio = user_info.get("fio", "")
        return [fio] if fio else []

    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        raise


async def get_me_info_data(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> list:
    """
    Получает данные с эндпоинта GetMeInfo с использованием переданных куки.

    Если декодированное сообщение пустое, выбрасывает Exception, чтобы
    в месте вызова можно было выполнить дополнительные действия.

    Args:
        cookies: Список куки в виде словарей
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        Список [ФИО пользователя]

    Raises:
        Exception: При пустом ответе или ошибках запроса
    """
    result = await _query_me_info(cookies, tg_user_id, db, user_agent)
    logger.debug(f"Результат get_me_info: {result}")
    if result:
        return result
    raise Exception(
        "Декодированное сообщение пустое. Проверьте переданные куки или обновите данные для входа."
    )


async def get_me_info_full(
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Получает полную информацию о пользователе из GetMeInfo.

    В отличие от get_me_info_data, возвращает словарь со всеми полями:
    - uuid: UUID пользователя
    - first_name: Имя
    - last_name: Фамилия
    - patronymic: Отчество
    - email: Email
    - fio: Полное ФИО
    - fio_short: Сокращённое ФИО (Фамилия И. О.)

    Args:
        cookies: Список куки в виде словарей
        tg_user_id: ID пользователя в Telegram
        db: Объект базы данных
        user_agent: User-Agent для запроса

    Returns:
        Словарь с информацией о пользователе

    Raises:
        Exception: При ошибках запроса
    """
    try:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

        url = "https://attendance.mirea.ru/rtu_tc.rtu_attend.app.UserService/GetMeInfo"
        headers = {
            "Accept": "application/grpc-web-text",
            "Content-Type": "application/grpc-web-text",
            "Origin": "https://attendance-app.mirea.ru",
            "Referer": "https://attendance-app.mirea.ru/",
            "X-Grpc-Web": "1",
            "x-requested-with": "XMLHttpRequest",
            "User-Agent": (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            ),
        }

        request_body = (
            "AAAAACwKKGh0dHBzOi8vYXR0ZW5kYW5jZS1hcHAubWlyZWEucnUvc2VydmljZXMYAQ=="
        )

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

        message = decode_grpc_response(response_text, ME_INFO_TYPEDEF)
        return parse_me_info(message)

    except Exception as e:
        logger.error(f"Ошибка при получении полной информации о пользователе: {e}")
        raise

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для самостоятельного подтверждения посещения занятий в MIREA API.

TODO: Получить реальные protobuf схемы для SelfApproveAttendance эндпоинта
      и мигрировать на blackboxprotobuf. Текущая реализация использует
      простой парсинг UTF-8 строк из ответа.
      Нужно перехватить запросы к SelfApproveAttendance и создать typedef.
"""

import base64
import logging
import re
from typing import Optional

import aiohttp

from backend.database import DBModel

from .get_cookies import generate_random_mobile_user_agent

logger = logging.getLogger(__name__)


def encode_guid(guid: str) -> str:
    """
    Кодирует входную строку GUID в специальный формат и возвращает Base64-строку.

    Args:
        guid: Строка GUID для кодирования

    Returns:
        Base64-кодированная строка в формате protobuf
    """
    guid_bytes = guid.encode("ascii")
    guid_length = len(guid_bytes)
    proto_message = bytes([0x0A, guid_length]) + guid_bytes
    total_length = len(proto_message)
    final_bytes = b"\x00\x00\x00\x00" + bytes([total_length]) + proto_message
    return base64.b64encode(final_bytes).decode("ascii")


def recursive_base64_decode(s: str, max_iterations: int = 2) -> str:
    """
    Рекурсивно декодирует строку из Base64.

    Args:
        s: Base64 закодированная строка
        max_iterations: Максимальное количество итераций декодирования

    Returns:
        Декодированная строка
    """
    current = s.strip()
    for _ in range(max_iterations):
        try:
            decoded_bytes = base64.b64decode(current, validate=True)
            decoded_str = decoded_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"Ошибка декодирования base64: {e}")
            break

        # Если результат выглядит как Base64, пробуем декодировать ещё раз
        if decoded_str and re.fullmatch(r"[A-Za-z0-9+/=]+", decoded_str.strip()):
            current = decoded_str.strip()
        else:
            return decoded_str
    return current


def decode_grpc_response(encoded_str: str) -> str:
    """
    Декодирует Base64-строку из ответа gRPC-web и возвращает читаемое сообщение.

    Args:
        encoded_str: Base64-кодированная строка ответа gRPC

    Returns:
        Декодированное читаемое сообщение
    """
    try:
        decoded_bytes = base64.b64decode(encoded_str)
    except Exception as e:
        return f"Ошибка декодирования Base64: {str(e)}"

    # gRPC-web формат: первые 5 байт - header (1 флаг + 4 длина), затем protobuf
    # Пропускаем header и извлекаем все UTF-8 строки из protobuf

    result_parts = []
    i = 5  # Пропускаем gRPC-web header

    while i < len(decoded_bytes):
        # Ищем начало UTF-8 строки (русские буквы начинаются с 0xD0 или 0xD1)
        if i + 1 < len(decoded_bytes) and decoded_bytes[i] in (0xD0, 0xD1):
            # Пытаемся извлечь русскую строку
            start = i
            while i < len(decoded_bytes):
                # Русские UTF-8 символы: 0xD0-0xD1 + второй байт, или пробел, или дефис
                if decoded_bytes[i] in (0xD0, 0xD1) and i + 1 < len(decoded_bytes):
                    i += 2
                elif decoded_bytes[i] in (0x20, 0x2D):  # пробел или дефис
                    i += 1
                else:
                    break

            if i > start:
                try:
                    text = decoded_bytes[start:i].decode("utf-8", errors="ignore")
                    if len(text) > 1:  # Минимум 2 символа
                        result_parts.append(text.strip())
                except Exception:
                    pass
        else:
            i += 1

    # Возвращаем уникальные части через разделитель
    unique_parts = []
    for part in result_parts:
        if part and part not in unique_parts:
            unique_parts.append(part)

    return (
        " | ".join(unique_parts)
        if unique_parts
        else decoded_bytes.decode("utf-8", errors="replace")
    )


async def send_self_approve_attendance(
    token: str,
    cookies: list,
    tg_user_id: int,
    db: DBModel,
    user_agent: Optional[str] = None,
) -> list:
    """
    Отправляет запрос к эндпоинту SelfApproveAttendance с использованием переданных куки.

    Если в ответе получен статус 401, выбрасывается ошибка для обработки на стороне вызывающего кода.

    Аргументы:
      token (str): GUID токен.
      cookies (list): Список куки в виде словарей.

    Возвращает:
      Декодированное сообщение.
    """
    try:

        encoded_token = encode_guid(token)

        url = "https://attendance.mirea.ru/rtu_tc.attendance.api.StudentService/SelfApproveAttendance"

        headers = {
            "Accept": "application/grpc-web-text",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "attendance-app-type": "student-app",
            "attendance-app-version": "1.0.0+1273",
            "baggage": (
                "sentry-environment=production,sentry-release=1.0.0%2B1273,"
                "sentry-public_key=37febb3f2d7ebcb778a7f43e0d6aed71,"
                "sentry-trace_id=21c869222f324851b453bfb8bf17ab01,"
                "sentry-sample_rate=0.001,"
                "sentry-transaction=%2Flessons%2Fvisiting-logs%2Fselfapprove,"
                "sentry-sampled=false"
            ),
            "Content-Type": "application/grpc-web-text",
            "Origin": "https://attendance-app.mirea.ru",
            "Referer": "https://attendance-app.mirea.ru/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "sentry-trace": "21c869222f324851b453bfb8bf17ab01-857a6458e2bf2072-0",
            "User-Agent": (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            ),
            "X-Grpc-Web": "1",
            "x-requested-with": "XMLHttpRequest",
            "X-User-Agent": "grpc-web-javascript/0.1",
        }

        async def do_request(session: aiohttp.ClientSession):
            async with session.post(
                url,
                data=encoded_token,
                headers=headers,
            ) as response:
                status = response.status
                text = await response.text()
                return status, text

        async with aiohttp.ClientSession() as session:

            # Устанавливаем переданные куки
            cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
            session.cookie_jar.update_cookies(cookies_dict)

            status, response_text = await do_request(session)
            # Если получен статус 401 – выбрасываем ошибку для обработки вызывающим кодом
            if status == 401:
                raise Exception("Ошибка 401: Unauthorized. Проверьте переданные куки.")
            if status != 200:
                raise Exception(f"Ошибка запроса, код: {status}")

        logger.debug(f"RAW gRPC response_text: {repr(response_text)}")

        decoded_response = decode_grpc_response(response_text)

        logger.debug(f"Decoded response: {repr(decoded_response)}")

        if not decoded_response:
            raise Exception("Декодированное сообщение пустое после обработки ответа.")
        return [decoded_response]

    except Exception as e:
        logger.error(f"Ошибка при самостоятельном подтверждении посещения: {e}")
        raise

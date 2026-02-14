#!/usr/bin/env python3
"""
Модуль для проверки целостности данных, полученных через Telegram.WebApp.initData.

Функция verify_init_data выполняет следующие действия:
1. Разбирает строку запроса (initData) в словарь.
2. Извлекает значение поля "hash" и удаляет его из словаря.
3. Формирует строку проверки (data_check_string), сортируя оставшиеся ключи по алфавиту и объединяя их в формате "ключ=значение" через символ перевода строки.
4. Вычисляет секретный ключ как HMAC‑SHA256 от токена бота с ключом "WebAppData".
5. Вычисляет HMAC‑SHA256 от data_check_string и сравнивает полученное значение с переданным hash.
6. Если проверка прошла успешно, извлекает из поля "user" идентификатор Telegram-пользователя (tg_userid).

Если проверка не проходит или необходимые данные отсутствуют, функция выбрасывает ValueError.
"""


import hashlib
import hmac
import json
from urllib.parse import parse_qs, unquote_plus

from fastapi import HTTPException


def verify_init_data(init_data: str, bot_token: str) -> int:
    """
    Проверяет целостность данных, полученных через Telegram.WebApp.initData.

    Args:
        init_data: Строка инициализации от Telegram Mini App
        bot_token: Токен бота для проверки подлинности

    Returns:
        Telegram ID пользователя

    Raises:
        ValueError: Если проверка не прошла или данные некорректны
        HTTPException: При других ошибках аутентификации
    """
    try:
        decoded_data = unquote_plus(init_data)

        # Пробуем найти "user=" ...
        try:
            if "user=" in decoded_data:
                user_start = decoded_data.index("user=") + 5
                user_end = decoded_data.find("&", user_start)
                if user_end == -1:
                    user_end = len(decoded_data)
                user_data = decoded_data[user_start:user_end]
                user_dict = json.loads(unquote_plus(user_data))

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

        # Парсим параметры
        params = dict(parse_qs(decoded_data))
        params = {k: v[0] for k, v in params.items()}

        received_hash = params.pop("hash", "")
        if not received_hash:
            raise ValueError("Missing 'hash' field in initData")

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret_key = hmac.new(
            "WebAppData".encode(), bot_token.encode(), hashlib.sha256
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(received_hash, calculated_hash):
            raise ValueError("Invalid hash: data integrity check failed")

        tg_userid = user_dict.get("id")
        if not tg_userid:
            raise ValueError("Не удалось извлечь tg_userid из данных пользователя")

        return tg_userid

    except HTTPException:
        raise
    except Exception as e:
        raise ValueError(f"Authentication failed: {str(e)}")

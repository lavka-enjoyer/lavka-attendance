import base64
import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import aiohttp
import blackboxprotobuf
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr

from backend.config import BOT_TOKEN

logger = logging.getLogger(__name__)

# Схема protobuf для Google Authenticator Export (otpauth-migration://)
MIGRATION_TYPEDEF = {
    "1": {  # otp_parameters (repeated)
        "type": "message",
        "message_typedef": {
            "1": {"type": "bytes"},   # secret (raw bytes)
            "2": {"type": "string"},  # name (account name)
            "3": {"type": "string"},  # issuer
            "4": {"type": "int"},     # algorithm (1=SHA1)
            "5": {"type": "int"},     # digits (1=6 digits)
            "6": {"type": "int"},     # type (2=TOTP)
        }
    }
}


async def send_telegram_message(
    chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Отправляет сообщение через Telegram API.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()


async def send_telegram_invoice(
    chat_id: int, invoice_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Отправляет счет Telegram для оплаты в Telegram Stars.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendInvoice"

    payload = {
        "chat_id": chat_id,
        "title": invoice_data["title"],
        "description": invoice_data["description"],
        "payload": invoice_data["payload"],
        "provider_token": invoice_data["provider_token"],
        "currency": invoice_data["currency"],
        "prices": invoice_data["prices"],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()


async def answer_callback_query(
    callback_query_id: str, text: str = ""
) -> Dict[str, Any]:
    """
    Отвечает на callback-запрос от inline-кнопки.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"

    payload = {"callback_query_id": callback_query_id}

    if text:
        payload["text"] = text

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()


async def answer_pre_checkout_query(
    query_id: str, error_message: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Отвечает на pre_checkout_query от Telegram.

    Args:
        query_id: Идентификатор запроса.
        error_message: Сообщение об ошибке, если платеж не может быть обработан.
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery"

        if error_message:
            payload = {
                "pre_checkout_query_id": query_id,
                "ok": False,
                "error_message": error_message,
            }
        else:
            payload = {"pre_checkout_query_id": query_id, "ok": True}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()
    except Exception as e:
        logger.error(
            f"Ошибка при ответе на pre_checkout_query: {str(e)}", exc_info=True
        )
        return None


async def get_telegram_file(file_id: str) -> Optional[bytes]:
    """
    Скачивает файл из Telegram по file_id.

    Args:
        file_id: ID файла в Telegram

    Returns:
        Содержимое файла в байтах или None при ошибке
    """
    try:
        # Получаем путь к файлу
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"file_id": file_id}) as response:
                result = await response.json()
                if not result.get("ok"):
                    logger.error(f"Ошибка получения file_path: {result}")
                    return None
                file_path = result["result"]["file_path"]

            # Скачиваем файл
            download_url = (
                f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            )
            async with session.get(download_url) as response:
                if response.status == 200:
                    return await response.read()
                logger.error(f"Ошибка скачивания файла: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла из Telegram: {e}", exc_info=True)
        return None


def _parse_migration_payload(data_b64: str) -> List[Tuple[str, str]]:
    """
    Декодирует protobuf данные из Google Authenticator Export.

    Args:
        data_b64: Base64-закодированные protobuf данные

    Returns:
        Список кортежей (secret_base32, issuer)
    """
    try:
        # Декодируем base64
        raw_data = base64.b64decode(data_b64)

        # Декодируем protobuf
        message, _ = blackboxprotobuf.decode_message(raw_data, MIGRATION_TYPEDEF)

        results = []
        otp_params = message.get("1", [])

        # Если один элемент, преобразуем в список
        if isinstance(otp_params, dict):
            otp_params = [otp_params]

        for param in otp_params:
            # Получаем raw secret bytes
            secret_bytes = param.get("1", b"")
            if isinstance(secret_bytes, str):
                secret_bytes = secret_bytes.encode("latin-1")

            # Конвертируем в base32
            secret_base32 = base64.b32encode(secret_bytes).decode("utf-8").rstrip("=")

            # Получаем issuer (поле 3) или name (поле 2)
            issuer = param.get("3", "")
            name = param.get("2", "")

            # Иногда issuer в name через двоеточие: "MIREA:user@mail.ru"
            if not issuer and ":" in name:
                issuer = name.split(":")[0]

            results.append((secret_base32, issuer or name))

        return results

    except Exception as e:
        logger.error(f"Ошибка при парсинге migration payload: {e}", exc_info=True)
        return []


def parse_totp_qr(image_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Парсит QR-код с TOTP секретом из изображения.
    Поддерживает как обычные otpauth://totp/ URI,
    так и otpauth-migration:// из Google Authenticator Export.

    Args:
        image_bytes: Изображение в байтах

    Returns:
        Tuple (secret, issuer) или (None, None) при ошибке
    """
    try:
        # Открываем изображение
        image = Image.open(io.BytesIO(image_bytes))

        # Декодируем QR-код
        decoded_objects = decode_qr(image)

        if not decoded_objects:
            logger.warning("QR-код не найден на изображении")
            return None, None

        for obj in decoded_objects:
            data = obj.data.decode("utf-8")

            # Проверяем формат Google Authenticator Export (otpauth-migration://)
            if data.startswith("otpauth-migration://"):
                logger.info("Обнаружен QR-код экспорта Google Authenticator")
                parsed = urlparse(data)
                params = parse_qs(parsed.query)

                data_param = params.get("data", [None])[0]
                if not data_param:
                    logger.warning("Параметр data не найден в migration URI")
                    continue

                # URL может быть закодирован
                data_param = unquote(data_param)

                # Парсим protobuf
                otp_entries = _parse_migration_payload(data_param)

                if not otp_entries:
                    logger.warning("Не удалось извлечь OTP записи из migration payload")
                    continue

                # Ищем запись от MIREA среди всех
                for secret, issuer in otp_entries:
                    if is_mirea_totp(issuer):
                        logger.info(f"Найден MIREA TOTP ключ: issuer={issuer}")
                        return secret, issuer

                # Если MIREA не найден, но есть только одна запись - вернём её с issuer
                # (пусть вызывающий код решит, подходит ли она)
                if len(otp_entries) == 1:
                    secret, issuer = otp_entries[0]
                    logger.info(f"Единственная запись в экспорте: issuer={issuer}")
                    return secret, issuer

                # Несколько записей, но MIREA не найден
                issuers = [i for _, i in otp_entries]
                logger.warning(f"MIREA ключ не найден среди {len(otp_entries)} записей: {issuers}")
                return None, f"Найдено {len(otp_entries)} ключей, но MIREA среди них нет"

            # Проверяем обычный формат otpauth://totp/
            elif data.startswith("otpauth://totp/"):
                # Парсим URI: otpauth://totp/issuer:account?secret=XXX&issuer=XXX
                parsed = urlparse(data)
                params = parse_qs(parsed.query)

                secret = params.get("secret", [None])[0]
                issuer = params.get("issuer", [None])[0]

                # Также пробуем получить issuer из пути
                if not issuer and parsed.path:
                    path_part = parsed.path.lstrip("/")
                    if ":" in path_part:
                        issuer = unquote(path_part.split(":")[0])

                return secret, issuer

        logger.warning("TOTP URI не найден в QR-коде")
        return None, None

    except Exception as e:
        logger.error(f"Ошибка при парсинге QR-кода: {e}", exc_info=True)
        return None, None


def is_mirea_totp(issuer: str) -> bool:
    """
    Проверяет, является ли TOTP ключ от MIREA.

    Args:
        issuer: Издатель TOTP ключа

    Returns:
        True если это ключ от MIREA
    """
    if not issuer:
        return False

    issuer_lower = issuer.lower()
    mirea_patterns = ["mirea", "rtu", "мирэа", "рту", "keycloak-edu"]

    return any(pattern in issuer_lower for pattern in mirea_patterns)

import asyncio
import logging

import aiohttp

from backend.config import BOT_TOKEN

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """
    Отправляет сообщение в Telegram через Bot API.
    Возвращает True если успешно, False если ошибка.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    return True
                else:
                    logger.warning(
                        f"Ошибка отправки сообщения {chat_id}: {response.status}"
                    )
                    return False
    except Exception as e:
        logger.error(f"Исключение при отправке сообщения {chat_id}: {e}")
        return False


async def send_marking_notifications(
    successful_user_ids: list, discipline: str = None
) -> dict:
    """
    Рассылает уведомления об успешной отметке всем отмеченным студентам.

    Args:
        successful_user_ids: список tg_id успешно отмеченных студентов
        discipline: название дисциплины (может быть None)

    Returns:
        dict с результатами: {"sent": количество_отправленных, "failed": количество_неудачных}
    """
    if not successful_user_ids:
        return {"sent": 0, "failed": 0}

    # Если discipline нет - не отправляем уведомления
    if not discipline:
        logger.debug("Discipline пустой - уведомления не отправляются")
        return {"sent": 0, "failed": 0}

    # Формируем текст сообщения
    message = f"✅ Тебя отметили на паре\n\n<b>{discipline}</b>"

    # Отправляем сообщения конкурентно
    tasks = [send_telegram_message(user_id, message) for user_id in successful_user_ids]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    sent = sum(1 for r in results if r is True)
    failed = len(results) - sent

    logger.info(f"Рассылка уведомлений: отправлено {sent}, ошибок {failed}")

    return {"sent": sent, "failed": failed}

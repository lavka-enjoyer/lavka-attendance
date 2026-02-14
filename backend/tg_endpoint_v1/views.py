import logging
from typing import Any, Dict

import requests
from fastapi import APIRouter, Request

from backend.admin_endpoint_v1.crud import _create_user_part_1_new
from backend.config import (
    BOT_USERNAME,
    DONATE_BOT_USERNAME,
    DONATE_URL,
    NEWS_CHANNEL_URL,
    WEBAPP_URL,
)
from backend.utils_helper import TELEGRAM_API_URL, db, user_states

from .crud import (
    answer_callback_query,
    answer_pre_checkout_query,
    get_telegram_file,
    is_mirea_totp,
    parse_totp_qr,
    send_telegram_invoice,
    send_telegram_message,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["webhook"])


@router.post("/telegram-webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """
    Обрабатывает входящие вебхуки от Telegram.

    Args:
        request: HTTP запрос с данными от Telegram

    Returns:
        Словарь с результатом обработки

    Note:
        Обрабатывает команды /start и /donate.
        Поддерживает реферальные ссылки формата /start ref_xxx.
        Обрабатывает токены внешней авторизации.
    """
    try:
        # Получаем данные из запроса
        data = await request.json()

        if "message" in data:
            message = data["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            user_agent = message.get("from", {}).get("user_agent", "")

            # Обрабатываем команду /start
            if text.strip().lower().startswith("/start"):
                # Проверяем, есть ли параметр ref_ в команде /start
                parts = text.strip().split()
                if len(parts) > 1 and parts[1].startswith("ref_"):
                    # Это реферальная ссылка
                    ref_code = parts[1]
                    ref_url = f"https://t.me/{BOT_USERNAME}?start={ref_code}"

                    # Регистрируем пользователя с использованием реферальной ссылки
                    await db.connect()
                    try:
                        result = await _create_user_part_1_new(
                            db, chat_id, url=ref_url, user_agent=user_agent
                        )

                        if isinstance(result, list) and result[0] is None:
                            # Успешная регистрация
                            success_message = "🎉 Вы успешно зарегистрировались по реферальной ссылке!"
                            if not result[1]:
                                success_message += (
                                    "\n⚠️ Внимание: вы зарегистрированы без прокси."
                                )
                            await send_telegram_message(chat_id, success_message)
                        else:
                            # Ошибка при регистрации
                            error_message = (
                                result.get("Exception", "Неизвестная ошибка")
                                if isinstance(result, dict)
                                else "Неизвестная ошибка"
                            )
                            if "user already exists" in str(error_message):
                                await send_telegram_message(
                                    chat_id, "Вы уже зарегистрированы в системе."
                                )
                            elif "add_data_for_login_with_reff" in error_message:
                                await send_telegram_message(
                                    chat_id, f'{error_message.split(":")[1]}'
                                )
                            else:
                                await send_telegram_message(
                                    chat_id, f"Ошибка при регистрации: {error_message}"
                                )
                    except Exception as e:
                        logger.error(
                            f"Ошибка при регистрации пользователя: {str(e)}",
                            exc_info=True,
                        )
                        await send_telegram_message(
                            chat_id, f"Произошла ошибка: {str(e)}"
                        )
                    finally:
                        await db.disconnect()

                    # После регистрации показываем стандартное сообщение с кнопкой запуска Web App
                    webapp_button = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "Отметка посещаемости",
                                    "web_app": {"url": WEBAPP_URL},
                                }
                            ],
                            [
                                {
                                    "text": "🤝 Поддержать проект",
                                    "callback_data": "donate_stars",
                                }
                            ],
                        ]
                    }
                    welcome_message = (
                        "👋 Привет! Я бот для отметки посещаемости.\n\n"
                        "Нажмите на кнопку ниже, чтобы запустить приложение для отметки посещаемости.\n\n"
                        f"Подпишись пожалуйста на новостной канал!\n{NEWS_CHANNEL_URL}\nТам всегда актуальная инфа"
                    )
                    await send_telegram_message(chat_id, welcome_message, webapp_button)
                    return {"ok": True}
                # Проверяем, есть ли параметр donate в команде /start
                elif "donate" in text.strip().lower():
                    # Выполняем логику команды /donate
                    donate_info_message = (
                        "🙏 Спасибо за желание поддержать проект!\n\n"
                        "Ваша поддержка помогает нам развивать сервис и делать его лучше. "
                        "Вы можете пожертвовать любую сумму, которая будет конвертирована в Telegram Stars.\n\n"
                        f"Иные способы поддержки здесь: @{DONATE_BOT_USERNAME}"
                    )

                    # Клавиатура с кнопкой для пожертвования через Telegram Stars
                    donate_button = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "Пожертвовать Telegram Stars",
                                    "callback_data": "donate_stars",
                                }
                            ],
                            [
                                {
                                    "text": "СБП / Карта",
                                    "url": DONATE_URL,
                                }
                            ],
                        ]
                    }

                    # Отправляем информационное сообщение с кнопкой
                    await send_telegram_message(
                        chat_id, donate_info_message, donate_button
                    )
                    return {"ok": True}
                else:
                    # Стандартная логика команды /start
                    # Создаем клавиатуру с кнопкой для запуска Web App
                    webapp_button = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "Отметка посещаемости",
                                    "web_app": {"url": WEBAPP_URL},
                                }
                            ],
                            [
                                {
                                    "text": "🤝 Поддержать проект",
                                    "callback_data": "donate_stars",
                                }
                            ],
                        ]
                    }
                    # Отправляем приветственное сообщение с кнопкой запуска Web App
                    welcome_message = (
                        "👋 Привет! Я бот для отметки посещаемости.\n\n"
                        "Нажмите на кнопку ниже, чтобы запустить приложение для отметки посещаемости.\n\n"
                        f"Подпишись пожалуйста на новостной канал!\n{NEWS_CHANNEL_URL}\nТам всегда актуальная инфа"
                    )
                    await send_telegram_message(chat_id, welcome_message, webapp_button)
                    return {"ok": True}

            # Обрабатываем токены внешней авторизации (UUID или длинные строки)
            elif len(text.strip()) >= 20 and not text.startswith("/"):
                token = text.strip()
                try:
                    await db.connect()
                    # Проверяем, существует ли такой токен
                    token_data = await db.get_external_token(token)

                    if token_data:
                        if token_data["status"] == "pending":
                            # Проверяем, существует ли пользователь
                            user = await db.get_user_by_id(chat_id)
                            if user:
                                # Подтверждаем токен
                                await db.approve_external_token(token, chat_id)
                                await send_telegram_message(
                                    chat_id,
                                    "✅ Авторизация успешна!\n\n"
                                    f"Ваш Telegram ID: {chat_id}\n"
                                    "Теперь вы можете использовать внешний сервис.",
                                )
                            else:
                                await send_telegram_message(
                                    chat_id,
                                    "❌ Вы не зарегистрированы в системе.\n"
                                    "Сначала пройдите регистрацию через /start",
                                )
                        elif token_data["status"] == "approved":
                            await send_telegram_message(
                                chat_id, "ℹ️ Этот токен уже был подтвержден ранее."
                            )
                        elif token_data["status"] == "rejected":
                            await send_telegram_message(
                                chat_id, "ℹ️ Этот токен был отклонен."
                            )
                    # Если токен не найден - просто игнорируем (может быть обычное сообщение)
                except Exception as e:
                    logger.error(f"Ошибка при обработке токена: {e}", exc_info=True)
                finally:
                    await db.disconnect()
                return {"ok": True}

            # Обрабатываем команду /delete_totp
            elif text.strip().lower() == "/delete_totp":
                try:
                    await db.connect()
                    user = await db.get_user_by_id(chat_id)
                    if not user:
                        await send_telegram_message(
                            chat_id,
                            "❌ Вы не зарегистрированы в системе.",
                        )
                        return {"ok": True}

                    has_secret = await db.has_totp_secret(chat_id)
                    if not has_secret:
                        await send_telegram_message(
                            chat_id,
                            "ℹ️ У вас нет сохранённого TOTP-ключа.",
                        )
                        return {"ok": True}

                    await db.delete_totp_secret(chat_id)
                    await send_telegram_message(
                        chat_id,
                        "✅ TOTP-ключ удалён.\n\n"
                        "Теперь вам нужно будет вводить код вручную при входе в MIREA.",
                    )
                    logger.info(f"TOTP secret deleted for user {chat_id}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении TOTP: {e}", exc_info=True)
                    await send_telegram_message(
                        chat_id, f"❌ Ошибка: {str(e)}"
                    )
                finally:
                    await db.disconnect()
                return {"ok": True}

            # Обрабатываем команду /donate
            elif text.strip().lower() == "/donate":
                # Создаем сообщение о пожертвовании и кнопку
                donate_info_message = (
                    "🙏 Спасибо за желание поддержать проект!\n\n"
                    "Ваша поддержка помогает нам развивать сервис и делать его лучше. "
                    "Вы можете пожертвовать любую сумму, которая будет конвертирована в Telegram Stars.\n\n"
                    f"Иные способы поддержки здесь: @{DONATE_BOT_USERNAME}"
                )

                # Клавиатура с кнопкой для пожертвования через Telegram Stars
                donate_button = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "Пожертвовать Telegram Stars",
                                "callback_data": "donate_stars",
                            }
                        ],
                        [
                            {
                                "text": "СБП / Карта",
                                "url": DONATE_URL,
                            }
                        ],
                    ]
                }

                # Отправляем информационное сообщение с кнопкой
                await send_telegram_message(chat_id, donate_info_message, donate_button)
                return {"ok": True}
            # Обрабатываем фото с QR-кодом для автоматического TOTP
            elif "photo" in message:
                photos = message.get("photo", [])
                if photos:
                    # Берём фото наибольшего размера
                    largest_photo = max(photos, key=lambda p: p.get("file_size", 0))
                    file_id = largest_photo.get("file_id")

                    try:
                        await db.connect()

                        # Проверяем, зарегистрирован ли пользователь
                        user = await db.get_user_by_id(chat_id)
                        if not user:
                            await send_telegram_message(
                                chat_id,
                                "❌ Вы не зарегистрированы в системе.\n"
                                "Сначала пройдите регистрацию через /start",
                            )
                            return {"ok": True}

                        # Скачиваем фото
                        image_bytes = await get_telegram_file(file_id)
                        if not image_bytes:
                            await send_telegram_message(
                                chat_id,
                                "❌ Не удалось загрузить изображение. Попробуйте ещё раз.",
                            )
                            return {"ok": True}

                        # Парсим QR-код
                        secret, issuer = parse_totp_qr(image_bytes)

                        if not secret:
                            # Проверяем, есть ли сообщение об ошибке в issuer
                            if issuer and "ключей" in str(issuer):
                                # Это сообщение о нескольких ключах без MIREA
                                await send_telegram_message(
                                    chat_id,
                                    f"❌ {issuer}\n\n"
                                    "Пожалуйста, экспортируйте только ключ от MIREA.\n"
                                    "В Google Authenticator выберите один конкретный аккаунт "
                                    "для экспорта.",
                                )
                            else:
                                await send_telegram_message(
                                    chat_id,
                                    "❌ QR-код не найден или не содержит TOTP-ключ.\n\n"
                                    "Убедитесь, что вы отправляете скриншот с QR-кодом "
                                    "из Google Authenticator (функция «Экспорт аккаунтов»).",
                                )
                            return {"ok": True}

                        # Проверяем, что это ключ от MIREA
                        if not is_mirea_totp(issuer):
                            await send_telegram_message(
                                chat_id,
                                f"❌ Этот ключ не от MIREA.\n\n"
                                f"Издатель: {issuer or 'не указан'}\n\n"
                                "Пожалуйста, экспортируйте только ключ от аккаунта MIREA/РТУ.",
                            )
                            return {"ok": True}

                        # Сохраняем секрет
                        await db.set_totp_secret(chat_id, secret)

                        await send_telegram_message(
                            chat_id,
                            "✅ TOTP-ключ успешно сохранён!\n\n"
                            "Теперь код двухфакторной аутентификации будет "
                            "вводиться автоматически при входе в систему MIREA.\n\n"
                            "Вы можете удалить этот ключ в любой момент, "
                            "отправив команду /delete_totp",
                        )
                        logger.info(f"TOTP secret saved for user {chat_id}")

                    except Exception as e:
                        logger.error(
                            f"Ошибка при обработке QR-кода: {str(e)}", exc_info=True
                        )
                        await send_telegram_message(
                            chat_id,
                            f"❌ Произошла ошибка при обработке QR-кода: {str(e)}",
                        )
                    finally:
                        await db.disconnect()

                    return {"ok": True}

            elif (
                chat_id in user_states
                and user_states[chat_id] == "awaiting_donation_amount"
                and text.strip().isdigit()
            ):
                # Получаем сумму в рублях
                amount_rub = int(text.strip())

                # Конвертируем рубли в Telegram Stars
                # Точный курс: 1.89 руб = 1 Star
                star_amount = max(1, int(amount_rub / 1.68))  # Минимум 1 Star
                # Создаем и отправляем счет
                await send_telegram_invoice(
                    chat_id,
                    {
                        "title": "Поддержка проекта",
                        "description": f"Пожертвование {amount_rub} рублей ({star_amount} Telegram Stars)",
                        "payload": f"donate_{chat_id}_{amount_rub}",
                        "provider_token": "",  # Пустая строка для платежей в Telegram Stars
                        "currency": "XTR",  # Код для Telegram Stars
                        "prices": [
                            {
                                "label": "Пожертвование",
                                "amount": star_amount,  # Для Telegram Stars это прямое количество звезд
                            }
                        ],
                    },
                )

                # Сбрасываем состояние пользователя
                del user_states[chat_id]

                return {"ok": True}

            # Обрабатываем callback-запросы от inline-кнопок
        elif "callback_query" in data:
            callback_query = data["callback_query"]
            callback_chat_id = (
                callback_query.get("message", {}).get("chat", {}).get("id")
            )
            callback_data = callback_query.get("data", "")

            # Если нажата кнопка пожертвования через Telegram Stars
            if callback_data == "donate_stars":
                # Отправляем запрос о сумме доната
                donate_message = "Пожалуйста, укажите сумму в рублях, которую вы хотели бы пожертвовать:"
                await send_telegram_message(callback_chat_id, donate_message)

                # Сохраняем состояние пользователя (ожидание суммы доната)
                user_states[callback_chat_id] = "awaiting_donation_amount"

                # Отвечаем на callback запрос, чтобы убрать загрузку с кнопки
                await answer_callback_query(callback_query.get("id", ""))

                return {"ok": True}

        # ДОБАВЛЯЕМ НОВЫЙ ОБРАБОТЧИК: Обрабатываем pre_checkout_query
        elif "pre_checkout_query" in data:
            pre_checkout_query = data["pre_checkout_query"]
            query_id = pre_checkout_query.get("id", "")

            # Отвечаем на pre_checkout_query, подтверждая, что всё в порядке
            await answer_pre_checkout_query(query_id)

            return {"ok": True}

        return {
            "ok": True
        }  # Просто подтверждаем получение для всех остальных сообщений
    except Exception as e:
        logger.error(f"Ошибка в обработке вебхука: {str(e)}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.get("/set-webhook")
async def set_webhook(webhook_url: str) -> Dict[str, Any]:
    """
    Устанавливает вебхук для бота Telegram.

    Args:
        webhook_url: Полный URL для вебхука (должен включать https://)

    Returns:
        Словарь со статусом установки вебхука
    """
    try:
        # URL для установки вебхука
        url = f"{TELEGRAM_API_URL}/setWebhook"

        # Данные для запроса
        data = {
            "url": webhook_url,
            "allowed_updates": [
                "message"
            ],  # Ограничиваем типы обновлений только сообщениями
        }

        # Отправляем запрос на установку вебхука
        response = requests.post(url, json=data)
        result = response.json()

        if result.get("ok"):
            return {"status": "success", "result": result}
        else:
            return {"status": "error", "result": result}

    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.get("/get-webhook-info")
async def get_webhook_info() -> Dict[str, Any]:
    """
    Получает информацию о текущем вебхуке бота.

    Returns:
        Словарь с информацией о вебхуке
    """
    try:
        url = f"{TELEGRAM_API_URL}/getWebhookInfo"
        response = requests.get(url)
        return response.json()

    except Exception as e:
        logger.error(
            f"Ошибка при получении информации о вебхуке: {str(e)}", exc_info=True
        )
        return {"status": "error", "message": str(e)}

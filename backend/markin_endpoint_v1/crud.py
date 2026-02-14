import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import HttpUrl

from backend.attendance import self_approve
from backend.database import DBModel
from backend.telegram_notifications import send_marking_notifications
from backend.utils_helper import db, log_user_action, marking_sessions

logger = logging.getLogger(__name__)


def _take_token(url: str) -> str:
    """
    Извлекает токен из URL параметра запроса.

    Args:
        url: URL с токеном в параметре запроса

    Returns:
        Токен в виде строки
    """
    token_url = url.split("?")[1]
    return token_url[token_url.index("=") + 1 :]


async def _send_approve(db: DBModel, tg_user_id: int, url: HttpUrl) -> Dict[str, Any]:
    """
    Отправляет запрос на подтверждение посещаемости для одного пользователя.

    Args:
        db: Экземпляр модели базы данных
        tg_user_id: ID пользователя в Telegram
        url: URL для подтверждения

    Returns:
        Словарь с результатом подтверждения
    """
    try:
        send_url = _take_token(str(url))
        user_agent = await db.get_user_agent(tg_user_id)
        res = await self_approve(db, tg_user_id, send_url, user_agent)
        logger.info(f"Approve result for user {tg_user_id}: {res}")
        return res
    except Exception as e:
        logger.error(
            f"Error in _send_approve for user {tg_user_id}: {e}", exc_info=True
        )
        return {"status": str(e)}


def extract_info(text: str) -> Dict[str, str]:
    """
    Извлекает информацию о группе и дисциплине из текста результата отметки.
    Формат входа: "А-20 | Системы искусственного интеллекта | ПР | Иванов Иван | БСБО-31-24 | ..."
    """
    logger.debug(f"extract_info получил текст: {text}")

    if not text:
        return {"group": "none", "strok": "none"}

    if len(str(text).strip()) < 5:
        return {"group": "none", "strok": "none"}

    try:
        # Извлечение группы по формату: БСБО-31-24
        group_match = re.search(r"\b[А-ЯЁ]{4}-\d{2}-\d{2}\b", text)
        group = group_match.group() if group_match else "none"

        # Если текст содержит разделитель " | " - новый формат
        if " | " in text:
            parts = [p.strip() for p in text.split(" | ")]

            discipline_candidates = []
            for part in parts:
                # Пропускаем группу
                if re.match(r"^[А-ЯЁ]{4}-\d{2}-\d{2}$", part):
                    continue
                # Пропускаем короткие части (ПР, ЛК, СР, А-20)
                if len(part) <= 5:
                    continue
                # Пропускаем сезоны
                if part in ("Осень", "Весна"):
                    continue
                # Пропускаем ФИО (1-3 слова, все с заглавной)
                words = part.split()
                if 1 <= len(words) <= 3 and all(
                    w[0].isupper() and len(w) < 15 for w in words if w
                ):
                    continue

                discipline_candidates.append(part)

            # Берём самую длинную часть как дисциплину
            discipline = (
                max(discipline_candidates, key=len) if discipline_candidates else "none"
            )
        else:
            # Старый формат
            text_before_group = text[: group_match.start()] if group_match else text
            filtered_text = re.sub(r"[^А-Яа-яЁё\s]", "", text_before_group)
            filtered_text = re.sub(r"\s+", " ", filtered_text).strip()
            discipline = filtered_text if filtered_text else "none"

        return {"group": group, "strok": discipline}
    except Exception as e:
        logger.error(f"Ошибка при извлечении информации: {e}", exc_info=True)
        return {"group": "none", "strok": "none"}


async def mark_single_user(
    db: DBModel,
    user_id: int,
    token: str,
    user_agent: Optional[str] = None,
) -> Any:
    """
    Отмечает посещаемость для одного пользователя и возвращает сырое тело ответа.

    Args:
        db: Экземпляр модели базы данных
        user_id: ID пользователя
        token: Токен для отметки
        user_agent: User-Agent браузера (необязательный)

    Returns:
        Результат отметки посещаемости
    """
    try:
        # Используем существующую функцию из attendance.py
        result = await self_approve(db, user_id, token, user_agent)
        # Возвращаем результат как есть, без обработки
        return result
    except Exception as e:
        logger.error(
            f"Ошибка при отметке посещаемости для пользователя {user_id}: {e}",
            exc_info=True,
        )
        raise Exception(f"Ошибка при отметке посещаемости: {str(e)}")


async def process_marking_session(session_id: str) -> None:
    """
    Обрабатывает сессию массовой отметки асинхронно без остановки при ошибках.

    Args:
        session_id: Идентификатор сессии массовой отметки
    """
    session = marking_sessions[session_id]
    await db.connect()

    # Создаем директорию для логов если её нет
    logs_dir = "marking_logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_file = f"{logs_dir}/marking_session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def write_to_log(message: str) -> None:
        """
        Записывает сообщение в лог-файл сессии с временной меткой.

        Args:
            message: Сообщение для записи в лог
        """
        with open(log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")

    try:
        session["status"] = "processing"
        write_to_log(
            f"Начало обработки сессии {session_id}. Пользователей для отметки: {len(session['remaining'])}"
        )

        # Загружаем ФИО для всех пользователей из БД
        all_user_ids = session["remaining"].copy()
        fio_map = await db.get_fio_bulk(all_user_ids)

        # Инициализируем user_results если его нет
        if "user_results" not in session:
            session["user_results"] = []

        # Получаем список оставшихся пользователей и токен
        remaining_users = session["remaining"].copy()
        token = session["token"]
        batch_size = 3

        # Обрабатываем пользователей пакетами
        for i in range(0, len(remaining_users), batch_size):
            batch = remaining_users[i : i + batch_size]
            tasks = []

            # Создаем задачи для параллельной обработки
            for user_id in batch:
                user_agent = await db.get_user_agent(user_id)

                task = asyncio.create_task(
                    mark_single_user(db, user_id, token, user_agent)
                )
                tasks.append((user_id, task))

            # Ждем выполнения всех задач в пакете
            for user_id, task in tasks:
                try:
                    # Получаем результат отметки
                    result = await task

                    # Логируем необработанное "сырое" тело ответа сервера
                    logger.info(f"User {user_id} - RAW SERVER RESPONSE: {result}")
                    write_to_log(
                        f"User {user_id} - RAW SERVER RESPONSE: {repr(result)}"
                    )

                    # Обрабатываем результат для дальнейшей логики
                    processed_result = extract_info(result)
                    write_to_log(
                        f"User {user_id} - Processed result: {processed_result}"
                    )

                    # Получаем ФИО пользователя
                    user_fio = fio_map.get(user_id, f"ID: {user_id}")

                    # Проверяем на истечение токена (если оба поля "none")
                    if (
                        processed_result["group"] == "none"
                        and processed_result["strok"] == "none"
                    ):
                        # Токен возможно истек, но продолжаем процесс - просто логируем
                        write_to_log(
                            f"WARNING: Возможно истек QR код для пользователя {user_id}. Результат: {repr(result)}"
                        )
                        session["failed"] += 1
                        session["processed"] += 1

                        # Добавляем результат с ФИО
                        session["user_results"].append(
                            {
                                "tg_id": user_id,
                                "fio": user_fio,
                                "success": False,
                                "error": "QR код истёк или неверный ответ",
                            }
                        )

                        # Удаляем пользователя из списка оставшихся
                        if user_id in session["remaining"]:
                            session["remaining"].remove(user_id)

                        # Продолжаем со следующим пользователем вместо остановки всего процесса
                        continue

                    # Успешная отметка
                    session["successful"] += 1
                    session["processed"] += 1

                    # Сохраняем результат
                    session["results"].append(
                        {"tg_id": user_id, "result": processed_result}
                    )

                    # Добавляем результат с ФИО
                    session["user_results"].append(
                        {"tg_id": user_id, "fio": user_fio, "success": True}
                    )

                    # Удаляем пользователя из списка оставшихся
                    if user_id in session["remaining"]:
                        session["remaining"].remove(user_id)

                    # Сохраняем информацию о группе и дисциплине (если еще не сохранено)
                    if not session["group"] and processed_result["group"] != "none":
                        session["group"] = processed_result["group"]

                    if (
                        not session["discipline"]
                        and processed_result["strok"] != "none"
                    ):
                        session["discipline"] = processed_result["strok"]

                except Exception as e:
                    # Получаем ФИО пользователя
                    user_fio = fio_map.get(user_id, f"ID: {user_id}")

                    # Обрабатываем ошибку для этого пользователя
                    session["failed"] += 1
                    session["processed"] += 1

                    # Детальное логирование ошибки
                    write_to_log(f"ERROR for user {user_id}: {str(e)}")

                    # Добавляем результат с ФИО
                    session["user_results"].append(
                        {
                            "tg_id": user_id,
                            "fio": user_fio,
                            "success": False,
                            "error": str(e),
                        }
                    )

                    # Удаляем пользователя из списка оставшихся, так как для него уже была попытка отметки
                    if user_id in session["remaining"]:
                        session["remaining"].remove(user_id)

        # Сессия завершена
        if len(session["remaining"]) == 0:
            session["status"] = "completed"
            session["completed"] = True
            write_to_log(
                f"Сессия завершена. Успешно: {session['successful']}, С ошибками: {session['failed']}"
            )
        else:
            # Если остались необработанные пользователи (что не должно случаться при новой логике)
            session["status"] = "partially_completed"
            write_to_log(
                f"Сессия частично завершена. Осталось пользователей: {len(session['remaining'])}"
            )

        # Логируем завершение массовой отметки
        await log_user_action(
            action_type="mass_mark_completed",
            tg_user_id=session["owner_id"],
            details={
                "session_id": session_id,
                "total": session["total"],
                "successful": session["successful"],
                "failed": session["failed"],
                "group": session["group"],
                "discipline": session["discipline"],
            },
        )

        # Рассылка уведомлений успешно отмеченным студентам
        successful_ids = [
            r["tg_id"]
            for r in session.get("user_results", [])
            if r.get("success") is True
        ]
        if successful_ids:
            await send_marking_notifications(
                successful_user_ids=successful_ids, discipline=session.get("discipline")
            )

    except Exception as e:
        # Обрабатываем общие ошибки
        error_msg = f"Общая ошибка при обработке сессии: {str(e)}"
        write_to_log(error_msg)
        session["error"] = str(e)
        session["status"] = "error"

        # Логируем ошибку при обработке массовой отметки
        await log_user_action(
            action_type="mass_mark_error",
            tg_user_id=session["owner_id"],
            details={
                "session_id": session_id,
                "error": str(e),
                "processed": session["processed"],
                "remaining": len(session["remaining"]),
            },
            status="failure",
        )
    finally:
        write_to_log("Завершение сессии и отключение от БД")
        await db.disconnect()

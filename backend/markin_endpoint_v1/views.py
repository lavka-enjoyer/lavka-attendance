import asyncio
import logging
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from backend.auth import verify_init_data
from backend.config import BOT_TOKEN
from backend.utils_helper import db, log_user_action, marking_sessions

from .crud import _send_approve, _take_token, extract_info, process_marking_session
from .schemas import ContinueMarkingData, MassApproveData, SendApprove

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Markin Endpoint"])


@router.post("/send_approve")
async def send_approve(data: SendApprove) -> Dict[str, Any]:
    """
    Отправка ссылки для подтверждения посещаемости.

    Args:
        data: Данные с initData и URL для подтверждения

    Returns:
        Словарь с результатом подтверждения
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        # Сохраняем оригинальный результат для отладки
        original_result = await _send_approve(db, tg_user_id, data.url)
        logger.info(
            f"Результат _send_approve для пользователя {tg_user_id}: {original_result}"
        )

        # Обрабатываем результат
        processed_result = extract_info(original_result)
        logger.info(
            f"Обработанный результат для пользователя {tg_user_id}: {processed_result}"
        )

        # Логируем успешную отметку посещаемости
        await log_user_action(
            action_type="self_approve",
            tg_user_id=tg_user_id,
            details={
                "url": data.url,
                "group": processed_result.get("group", "none"),
                "discipline": processed_result.get("strok", "none"),
            },
        )

        return {"result": processed_result}
    except Exception as e:
        logger.error(
            f"Ошибка в send_approve для пользователя {tg_user_id}: {e}", exc_info=True
        )
        # Логируем неудачную попытку отметки
        await log_user_action(
            action_type="self_approve",
            tg_user_id=tg_user_id,
            details={"url": data.url, "error": str(e)},
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.post("/start_mass_marking")
async def start_mass_marking(data: MassApproveData) -> Dict[str, str]:
    """
    Начинает процесс массовой отметки посещаемости.

    Args:
        data: Данные с initData, URL и списком выбранных пользователей

    Returns:
        Словарь с идентификатором сессии (session_id)
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        # Извлекаем токен из URL
        token = _take_token(data.url)

        # Создаем уникальный идентификатор сессии
        session_id = str(uuid.uuid4())

        # Создаем структуру данных сессии
        marking_sessions[session_id] = {
            "owner_id": tg_user_id,
            "token": token,
            "started_at": time.time(),
            "status": "starting",
            "total": len(data.selectedUsers),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "user_results": [],  # Список результатов с ФИО: [{tg_id, fio, success, error?}]
            "remaining": data.selectedUsers.copy(),
            "completed": False,
            "error": None,
            "discipline": "",
            "group": "",
        }

        # Логируем начало массовой отметки
        await log_user_action(
            action_type="mass_mark_start",
            tg_user_id=tg_user_id,
            details={
                "session_id": session_id,
                "users_count": len(data.selectedUsers),
                "selected_users": data.selectedUsers,
                "url": data.url,
            },
        )

        # Запускаем асинхронную задачу для обработки отметок
        asyncio.create_task(process_marking_session(session_id))

        # Возвращаем ID сессии
        return {"session_id": session_id}
    except Exception as e:
        logger.error(
            f"Ошибка при начале массовой отметки для пользователя {tg_user_id}: {e}",
            exc_info=True,
        )
        # Логируем ошибку при начале массовой отметки
        await log_user_action(
            action_type="mass_mark_start",
            tg_user_id=tg_user_id,
            details={
                "url": data.url,
                "users_count": len(data.selectedUsers),
                "error": str(e),
            },
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/get_marking_status/{session_id}")
async def get_marking_status(session_id: str) -> Dict[str, Any]:
    """
    Получает текущий статус процесса массовой отметки.

    Args:
        session_id: Идентификатор сессии

    Returns:
        Словарь со статусом и прогрессом отметки
    """
    if session_id not in marking_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Сессия отметки не найдена"
        )

    # Возвращаем текущий статус сессии
    return marking_sessions[session_id]


@router.post("/continue_marking")
async def continue_marking(data: ContinueMarkingData) -> Dict[str, Any]:
    """
    Продолжает отметку оставшихся пользователей с новым QR-кодом.

    Args:
        data: Данные с initData, session_id и новым URL

    Returns:
        Словарь со статусом продолжения и количеством оставшихся пользователей
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    if data.session_id not in marking_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Сессия отметки не найдена"
        )

    session = marking_sessions[data.session_id]

    # Проверяем, что запрос на продолжение отметки исходит от владельца сессии
    if session["owner_id"] != tg_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой сессии отметки",
        )

    try:
        # Извлекаем новый токен из URL
        new_token = _take_token(data.url)

        # Логируем продолжение массовой отметки
        await log_user_action(
            action_type="mass_mark_continue",
            tg_user_id=tg_user_id,
            details={
                "session_id": data.session_id,
                "remaining_users": len(session["remaining"]),
                "url": data.url,
            },
        )

        # Обновляем сессию
        session["token"] = new_token
        session["status"] = "continuing"
        session["error"] = None

        # Запускаем новую асинхронную задачу для обработки оставшихся отметок
        asyncio.create_task(process_marking_session(data.session_id))

        return {"status": "processing", "remaining": len(session["remaining"])}
    except Exception as e:
        logger.error(
            f"Ошибка при продолжении массовой отметки для пользователя {tg_user_id}: {e}",
            exc_info=True,
        )
        # Логируем ошибку при продолжении массовой отметки
        await log_user_action(
            action_type="mass_mark_continue",
            tg_user_id=tg_user_id,
            details={
                "session_id": data.session_id,
                "url": data.url,
                "remaining_users": len(session["remaining"]),
                "error": str(e),
            },
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

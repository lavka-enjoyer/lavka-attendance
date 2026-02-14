import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import verify_init_data
from backend.config import BOT_TOKEN
from backend.dependencies import init_data
from backend.utils_helper import db, log_user_action

from .crud import (
    _get_group_users,
    _get_other_group_users,
    _get_unique_group,
    _get_user_info_safe,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["groups"])


@router.get("/get_group_users")
async def get_group_users(initData: str):
    """
    Получает всех пользователей из той же группы, что и аутентифицированный пользователь.
    Возвращает список пользователей с их ФИО, tg_id и статусом allowConfirm.
    """
    try:
        tg_userid = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        await db.init_tables()

        # Получаем список пользователей из той же группы
        rows = await _get_group_users(db, tg_userid)

        if not rows:
            # Логируем попытку получения пустого списка группы
            await log_user_action(
                action_type="get_group", tg_userid=tg_userid, details={"users_count": 0}
            )
            return {"users": []}

        rows = list(set(rows))

        # Обрабатываем пользователей небольшими партиями для лучшей производительности
        users = []
        # batch_size = 3  # Обрабатываем по 3 пользователя за раз

        # for i in range(0, len(rows), batch_size):
        #     batch = rows[i:i + batch_size]
        #     batch_tasks = []
        #
        #     # Создаем задачи для получения информации о пользователях
        #     for row in batch:
        #         task = asyncio.create_task(_get_user_info_safe(db, row['tg_userid'], row['allowconfirm']))
        #         batch_tasks.append(task)
        #
        #     # Ждем завершения выполнения этой партии
        #     batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        #
        #     # Обрабатываем результаты из этой партии
        #     for result in batch_results:
        #         if result and not isinstance(result, Exception):
        #             users.append(result)
        batch_tasks = []

        # Создаем задачи для получения информации о пользователях
        for row in rows:
            task = asyncio.create_task(
                _get_user_info_safe(db, row["tg_userid"], row["allowconfirm"])
            )
            batch_tasks.append(task)

        # Ждем завершения выполнения этой партии
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Обрабатываем результаты из этой партии
        for result in batch_results:
            if result and not isinstance(result, Exception):
                users.append(result)

        # Логируем успешное получение списка группы
        try:
            group_name = "unknown"
            if rows and len(rows) > 0 and "group_name" in rows[0]:
                group_name = rows[0]["group_name"]

            await log_user_action(
                action_type="get_group",
                tg_userid=tg_userid,
                details={"group_name": group_name, "users_count": len(users)},
            )
        except Exception as log_error:
            logger.warning(f"Ошибка при логировании get_group: {str(log_error)}")

        return {"users": users}
    except Exception as e:
        # Логируем ошибку при получении списка группы
        await log_user_action(
            action_type="get_group",
            tg_userid=tg_userid,
            details={"error": str(e)},
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.get("/get_other_group_users")
async def get_other_group_users(initData: str, group_name: str):
    """
    Получает всех пользователей из указанной группы.
    Возвращает список пользователей с их ФИО, tg_id и статусом allowConfirm.
    """
    try:
        tg_userid = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        await db.init_tables()

        # Получаем список пользователей из указанной группы
        rows = await _get_other_group_users(db, group_name)

        if not rows:
            # Логируем попытку получения пустого списка другой группы
            await log_user_action(
                action_type="get_other_group",
                tg_userid=tg_userid,
                details={"group_name": group_name, "users_count": 0},
            )

            return {"users": []}

        # Обрабатываем пользователей небольшими партиями для лучшей производительности
        users = []
        batch_size = 3  # Обрабатываем по 3 пользователя за раз

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            batch_tasks = []

            # Создаем задачи для получения информации о пользователях
            for row in batch:
                task = asyncio.create_task(
                    _get_user_info_safe(db, row["tg_userid"], row["allowconfirm"])
                )
                batch_tasks.append(task)

            # Ждем завершения выполнения этой партии
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Обрабатываем результаты из этой партии
            for result in batch_results:
                if result and not isinstance(result, Exception):
                    users.append(result)

        # Логируем успешное получение списка другой группы
        await log_user_action(
            action_type="get_other_group",
            tg_userid=tg_userid,
            details={"group_name": group_name, "users_count": len(users)},
        )
        return {"users": users}
    except Exception as e:
        # Логируем ошибку при получении списка другой группы
        await log_user_action(
            action_type="get_other_group",
            tg_userid=tg_userid,
            details={"group_name": group_name, "error": str(e)},
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.get("/get_available_groups")
async def get_available_groups(initData: str = Depends(init_data)):
    """
    Получает список всех доступных групп в системе.
    """
    try:
        await db.connect()

        rows = await _get_unique_group(db)

        groups = [row["group_name"] for row in rows]
        return {"groups": groups}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()

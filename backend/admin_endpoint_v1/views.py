import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.audit import audit_service
from backend.auth import verify_init_data
from backend.config import ADMIN_LEVEL_SUPER, BOT_TOKEN
from backend.dependencies import init_data
from backend.utils_helper import db

from .crud import (
    _check_email_code_session,
    _create_user_part_1_new,
    _get_all,
    _get_all_admin,
    _get_count,
    _submit_email_code,
    _update_user,
)
from .schemas import (
    BulkDeleteRequest,
    BulkEditRequest,
    BulkImportRequest,
    CheckEmailCodeSession,
    CreateUserNew,
    DeleteUserByAdmin,
    SetAdminLevel,
    SubmitEmailCode,
    UpdateUser,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Admin"])


@router.patch("/update_user")
async def updt_user(data: UpdateUser) -> Dict[str, Any]:
    """
    Обновляет данные пользователя.

    Args:
        data: Данные для обновления пользователя

    Returns:
        Словарь с информацией об обновлении

    Note:
        Не поддерживает обновление админ лвла.
        При вводе логина и пароля группа вставляется автоматически.
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in update_user: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))
    try:
        await db.connect()
        res = await _update_user(db, tg_user_id, data)
        if not isinstance(res, Exception):
            return {"info": res}
        return res
    except Exception as ex:
        logger.error(f"Error in update_user for {tg_user_id}: {ex}", exc_info=True)
        return {"Exception": str(ex)}
    finally:
        await db.disconnect()


@router.post("/create_user")
async def create_user_new_part_1(data: CreateUserNew) -> Dict[str, Any]:
    """
    Создает нового пользователя в системе.

    Args:
        data: Данные для создания пользователя (initData, login, password, user_agent)

    Returns:
        Словарь с результатом создания и информацией о пользователе

    Note:
        При наличии логина и пароля проверяет их и автоматически добавляет группу.
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)

        await db.connect()
        res = await _create_user_part_1_new(
            db, tg_user_id, data.login, data.password, data.user_agent
        )
        if not isinstance(res, dict):
            return {
                "detail": "Success",
                "info": res,
            }
        return res

    except ValueError as err:
        logger.error(f"Auth error in create_user: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    except Exception as e:
        logger.error(f"Error in create_user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )

    finally:

        await db.disconnect()


@router.get("/get_count_users")
async def get_count(tg_user_id: int = Depends(init_data)) -> Dict[str, Any]:
    """
    Получает общее количество пользователей в системе.

    Args:
        tg_user_id: ID пользователя (из токена)

    Returns:
        Словарь с количеством пользователей
    """
    try:
        await db.connect()
        res = await _get_count(db)
        if not isinstance(res, dict):
            return {"Users count": res}
        return res
    except Exception as e:
        logger.error(f"Error in get_count for {tg_user_id}: {e}", exc_info=True)
        return f"detail: {str(e)}"
    finally:
        await db.disconnect()


@router.get("/get_all_users")
async def get_users_all(
    offset: int, group_name: Optional[str] = None, tg_user_id: int = Depends(init_data)
) -> Any:
    """
    Получает список всех пользователей с пагинацией.

    Args:
        offset: Смещение для пагинации
        group_name: Название группы для фильтрации (необязательный)
        tg_user_id: ID пользователя (из токена)

    Returns:
        Список пользователей
    """
    try:
        await db.connect()
        return await _get_all(db, tg_user_id, offset, group_name)

    except Exception as e:
        logger.error(f"Error in get_users_all for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    finally:
        await db.disconnect()


@router.get("/get_all_admin")
async def get_all_admin(tg_user_id: int = Depends(init_data)) -> Any:
    """
    Получает список всех администраторов системы.

    Args:
        tg_user_id: ID пользователя (из токена)

    Returns:
        Список администраторов
    """
    try:
        await db.connect()
        return await _get_all_admin(db, tg_user_id)
    except Exception as e:
        logger.error(f"Error in get_all_admin for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    finally:
        await db.disconnect()


@router.delete("/admin/delete_user")
async def admin_delete_user(data: DeleteUserByAdmin) -> Dict[str, str]:
    """
    Удаление пользователя администратором.

    Args:
        data: Данные с initData и ID пользователя для удаления

    Returns:
        Словарь со статусом операции

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_delete_user: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        await db.delete_user_by_admin(tg_user_id, data.target_tg_userid)
        return {"status": "success", "message": "Пользователь успешно удален"}
    except Exception as e:
        logger.error(f"Error in admin_delete_user for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.post("/admin/set_admin_level")
async def admin_set_level(data: SetAdminLevel) -> Dict[str, str]:
    """
    Изменение уровня администратора.

    Args:
        data: Данные с initData, ID пользователя и новым уровнем админа

    Returns:
        Словарь со статусом операции

    Note:
        Требуется admin_lvl >= 3.
        Уровни: 0 - обычный, 1 - модератор, 2 - админ, 3 - старший админ, 4 - суперадмин, 5 - владелец
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_set_level: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        await db.set_admin_level(tg_user_id, data.target_tg_userid, data.admin_level)
        return {
            "status": "success",
            "message": f"Уровень админа изменен на {data.admin_level}",
        }
    except Exception as e:
        logger.error(f"Error in admin_set_level for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.get("/admin/search_users")
async def admin_search_users(
    query: str, offset: int = 0, tg_user_id: int = Depends(init_data)
) -> Dict[str, Any]:
    """
    Поиск пользователей по логину, группе, ФИО или Telegram ID.

    Args:
        query: Поисковый запрос
        offset: Смещение для пагинации
        tg_user_id: ID пользователя (из токена)

    Returns:
        Словарь со списком найденных пользователей

    Note:
        Требуется admin_lvl >= 2
    """
    try:
        await db.connect()
        users = await db.search_users(tg_user_id, query, offset)
        return {"users": users}
    except Exception as e:
        logger.error(
            f"Error in admin_search_users for {tg_user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.get("/admin/stats")
async def admin_get_stats(tg_user_id: int = Depends(init_data)) -> Dict[str, Any]:
    """
    Получить статистику для админ-панели.

    Args:
        tg_user_id: ID пользователя (из токена)

    Returns:
        Словарь со статистикой системы

    Note:
        Требуется admin_lvl >= 1
    """
    try:
        await db.connect()
        stats = await db.get_admin_stats(tg_user_id)
        return stats
    except Exception as e:
        logger.error(f"Error in admin_get_stats for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.post("/submit_email_code")
async def submit_email_code(data: SubmitEmailCode) -> Dict[str, Any]:
    """
    Отправляет код из email для завершения проверки.

    Args:
        data: Данные с initData и email кодом

    Returns:
        Словарь с результатом:
        - success=True и groups при успехе
        - requires_email_code=True если код неверный
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in submit_email_code: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        result = await _submit_email_code(db, tg_user_id, data.email_code)
        return result
    except Exception as e:
        logger.error(f"Error in submit_email_code for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
    finally:
        await db.disconnect()


@router.get("/check_email_code_session")
async def check_email_code_session(initData: str) -> Dict[str, Any]:
    """
    Проверяет наличие активной email code сессии для пользователя.

    Args:
        initData: Telegram Mini App initData

    Returns:
        Словарь с has_session=True если есть активная сессия
    """
    try:
        tg_user_id = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in check_email_code_session: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        result = await _check_email_code_session(db, tg_user_id)
        return result
    except Exception as e:
        logger.error(
            f"Error in check_email_code_session for {tg_user_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
    finally:
        await db.disconnect()


# ============== Bulk Operations ==============


@router.delete("/admin/bulk_delete")
async def admin_bulk_delete(data: BulkDeleteRequest) -> Dict[str, Any]:
    """
    Массовое удаление пользователей.

    Args:
        data: Данные с initData и списком ID пользователей для удаления

    Returns:
        Словарь с результатами операции (deleted, failed, errors)

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_bulk_delete: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        result = await db.bulk_delete_users(tg_user_id, data.target_tg_userids)

        # Log the action
        await audit_service.log_bulk_delete(
            admin_tg_userid=tg_user_id,
            deleted_ids=result["deleted"],
            failed_ids=result["failed"],
        )

        return {
            "status": "success",
            "deleted": result["deleted"],
            "failed": result["failed"],
            "errors": result["errors"],
        }
    except Exception as e:
        logger.error(f"Error in admin_bulk_delete for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.patch("/admin/bulk_edit")
async def admin_bulk_edit(data: BulkEditRequest) -> Dict[str, Any]:
    """
    Массовое редактирование пользователей.

    Args:
        data: Данные с initData, списком ID пользователей и полями для обновления

    Returns:
        Словарь с результатами операции (updated, failed, errors)

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_bulk_edit: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()

        # Build updates dict from non-None fields
        updates = {}
        if data.allowConfirm is not None:
            updates["allowConfirm"] = data.allowConfirm
        if data.admin_lvl is not None:
            updates["admin_lvl"] = data.admin_lvl
        if data.group_name is not None:
            updates["group_name"] = data.group_name

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет полей для обновления",
            )

        result = await db.bulk_edit_users(tg_user_id, data.target_tg_userids, updates)

        # Log the action
        await audit_service.log_admin_action(
            admin_tg_userid=tg_user_id,
            action_type=audit_service.ACTION_BULK_EDIT,
            target_type=audit_service.TARGET_USER,
            new_value={
                "updated_ids": result["updated"],
                "updates": updates,
            },
        )

        return {
            "status": "success",
            "updated": result["updated"],
            "failed": result["failed"],
            "errors": result["errors"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin_bulk_edit for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.post("/admin/bulk_import")
async def admin_bulk_import(data: BulkImportRequest) -> Dict[str, Any]:
    """
    Массовый импорт пользователей.

    Args:
        data: Данные с initData и списком пользователей для импорта

    Returns:
        Словарь с результатами операции (created, failed, errors)

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_bulk_import: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()

        # Check admin permissions
        admin = await db.check_admin_user(tg_user_id, ADMIN_LEVEL_SUPER)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )

        created = []
        failed = []
        errors = []

        for user_data in data.users:
            try:
                # Check if user exists
                existing = await db.get_user_by_id(user_data.tg_userid)
                if existing:
                    failed.append(user_data.tg_userid)
                    errors.append(f"{user_data.tg_userid}: Пользователь уже существует")
                    continue

                # Create user
                if user_data.login and user_data.password:
                    await db.create_user(
                        tg_userid=user_data.tg_userid,
                        group_name=user_data.group_name or "",
                        login=user_data.login,
                        password=user_data.password,
                        allowConfirm=user_data.allowConfirm,
                    )
                else:
                    await db.create_user_simple(
                        tg_userid=user_data.tg_userid,
                        login=user_data.login,
                        password=user_data.password,
                        group=user_data.group_name,
                    )

                # Update FIO if provided
                if user_data.fio:
                    await db.update_fio(user_data.tg_userid, user_data.fio)

                # Set admin level if not default
                if user_data.admin_lvl > 0:
                    await db.pool.execute(
                        "UPDATE users SET admin_lvl = $1 WHERE tg_userid = $2",
                        user_data.admin_lvl,
                        user_data.tg_userid,
                    )

                created.append(user_data.tg_userid)
            except Exception as e:
                failed.append(user_data.tg_userid)
                errors.append(f"{user_data.tg_userid}: {str(e)}")

        # Log the action
        await audit_service.log_admin_action(
            admin_tg_userid=tg_user_id,
            action_type=audit_service.ACTION_BULK_IMPORT,
            target_type=audit_service.TARGET_USER,
            new_value={
                "created": created,
                "failed": failed,
                "total_created": len(created),
            },
        )

        return {
            "status": "success",
            "created": created,
            "failed": failed,
            "errors": errors,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin_bulk_import for {tg_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


# ============== Data Export ==============


@router.get("/admin/export/users")
async def admin_export_users(
    format: str = "csv", tg_user_id: int = Depends(init_data)
) -> StreamingResponse:
    """
    Экспорт списка пользователей в CSV или Excel формат.

    Args:
        format: Формат экспорта ("csv" или "xlsx")
        tg_user_id: ID пользователя (из токена)

    Returns:
        Файл CSV или Excel со списком пользователей

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        await db.connect()
        users = await db.get_all_users_for_export(tg_user_id)

        # Log the action
        await audit_service.log_admin_action(
            admin_tg_userid=tg_user_id,
            action_type=audit_service.ACTION_EXPORT_DATA,
            target_type=audit_service.TARGET_USER,
            new_value={"format": format, "count": len(users)},
        )

        if format == "xlsx":
            # Excel export
            try:
                from openpyxl import Workbook

                wb = Workbook()
                ws = wb.active
                ws.title = "Users"

                # Headers
                headers = [
                    "tg_userid",
                    "group_name",
                    "login",
                    "allowConfirm",
                    "admin_lvl",
                    "fio",
                ]
                ws.append(headers)

                # Data
                for user in users:
                    ws.append(
                        [
                            user["tg_userid"],
                            user.get("group_name", ""),
                            user.get("login", ""),
                            user.get("allowconfirm", True),
                            user.get("admin_lvl", 0),
                            user.get("fio", ""),
                        ]
                    )

                # Save to buffer
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)

                return StreamingResponse(
                    output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    },
                )
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="openpyxl не установлен",
                )
        else:
            # CSV export
            output = io.StringIO()
            writer = csv.writer(output)

            # Headers
            writer.writerow(
                ["tg_userid", "group_name", "login", "allowConfirm", "admin_lvl", "fio"]
            )

            # Data
            for user in users:
                writer.writerow(
                    [
                        user["tg_userid"],
                        user.get("group_name", ""),
                        user.get("login", ""),
                        user.get("allowconfirm", True),
                        user.get("admin_lvl", 0),
                        user.get("fio", ""),
                    ]
                )

            output.seek(0)

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in admin_export_users for {tg_user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


# ============== Analytics Dashboard ==============


@router.get("/admin/analytics/dashboard")
async def admin_analytics_dashboard(
    days: int = 30, tg_user_id: int = Depends(init_data)
) -> Dict[str, Any]:
    """
    Получить расширенную аналитику для админ-панели.

    Args:
        days: Количество дней для анализа (по умолчанию 30)
        tg_user_id: ID пользователя (из токена)

    Returns:
        Словарь с аналитическими данными:
        - total_users, total_groups, total_admins, users_with_login
        - activity_by_day - активность по дням
        - top_groups - топ групп по пользователям
        - actions_stats - статистика по типам действий
        - error_stats - статистика ошибок

    Note:
        Требуется admin_lvl >= 1
    """
    try:
        await db.connect()
        analytics = await db.get_analytics_data(tg_user_id, days)
        return analytics
    except Exception as e:
        logger.error(
            f"Error in admin_analytics_dashboard for {tg_user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


# ============== Audit Logs ==============


@router.get("/admin/audit-logs")
async def admin_get_audit_logs(
    initData: str = Query(..., description="Telegram initData"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(20, ge=1, le=100, description="Количество записей на странице"),
    action_type: Optional[str] = Query(None, description="Тип действия"),
    admin_id: Optional[int] = Query(None, description="ID администратора"),
    target_type: Optional[str] = Query(None, description="Тип цели"),
) -> Dict[str, Any]:
    """
    Получить аудит-логи админских действий.

    Args:
        initData: Telegram initData для аутентификации
        page: Номер страницы (начиная с 1)
        limit: Количество записей на странице
        action_type: Фильтр по типу действия
        admin_id: Фильтр по ID админа
        target_type: Фильтр по типу цели

    Returns:
        Словарь с логами и информацией о пагинации

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        tg_user_id = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_get_audit_logs: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()

        # Check admin permissions
        admin = await db.check_admin_user(tg_user_id, ADMIN_LEVEL_SUPER)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )

        # Convert page to offset
        offset = (page - 1) * limit

        logs = await db.get_audit_logs(
            admin_tg_userid=admin_id,
            action_type=action_type,
            target_type=target_type,
            offset=offset,
            limit=limit,
            date_from=None,
            date_to=None,
        )

        total = await db.get_audit_logs_count(
            admin_tg_userid=admin_id,
            action_type=action_type,
            target_type=target_type,
            date_from=None,
            date_to=None,
        )

        # Convert datetime objects to ISO format for JSON serialization
        for log in logs:
            if log.get("created_at"):
                log["created_at"] = log["created_at"].isoformat()

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in admin_get_audit_logs for {tg_user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()


@router.get("/admin/user-action-logs")
async def admin_get_user_action_logs(
    initData: str = Query(..., description="Telegram initData"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(20, ge=1, le=100, description="Количество записей на странице"),
    action_type: Optional[str] = Query(None, description="Тип действия"),
    user_id: Optional[int] = Query(None, description="ID пользователя"),
    status: Optional[str] = Query(None, description="Статус (success/failure)"),
) -> Dict[str, Any]:
    """
    Получить логи действий пользователей.

    Args:
        initData: Telegram initData для аутентификации
        page: Номер страницы (начиная с 1)
        limit: Количество записей на странице
        action_type: Фильтр по типу действия
        user_id: Фильтр по ID пользователя
        status: Фильтр по статусу

    Returns:
        Словарь с логами, статистикой и информацией о пагинации

    Note:
        Требуется admin_lvl >= 3
    """
    try:
        tg_user_id = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        logger.error(f"Auth error in admin_get_user_action_logs: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()

        # Check admin permissions
        admin = await db.check_admin_user(tg_user_id, ADMIN_LEVEL_SUPER)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )

        # Convert page to offset
        offset = (page - 1) * limit

        logs = await db.get_user_action_logs(
            actor_tg_userid=user_id,
            target_tg_userid=None,
            action_type=action_type,
            status=status,
            offset=offset,
            limit=limit,
            date_from=None,
            date_to=None,
        )

        total = await db.get_user_action_logs_count(
            actor_tg_userid=user_id,
            target_tg_userid=None,
            action_type=action_type,
            status=status,
            date_from=None,
            date_to=None,
        )

        # Get stats for today
        stats = await db.get_user_action_logs_stats()

        # Convert datetime objects to ISO format for JSON serialization
        for log in logs:
            if log.get("created_at"):
                log["created_at"] = log["created_at"].isoformat()

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "stats": stats,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in admin_get_user_action_logs for {tg_user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        await db.disconnect()

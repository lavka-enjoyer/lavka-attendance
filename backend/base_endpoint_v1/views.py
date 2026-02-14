from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, status

from backend.auth import verify_init_data
from backend.config import BOT_TOKEN, TRUSTED_SERVICE_API_KEY
from backend.utils_helper import db, log_user_action

from .crud import (
    _check_user,
    _delete_user_by_id,
    _edit_allow_confirm,
    _get_group_university_status,
    _get_university_status,
)
from .schemas import (
    CheckUserError,
    CheckUserNeeds2FA,
    CheckUserNeedsLogin,
    DeleteUser,
    EditAllowConfirm,
    OperationError,
    OperationSuccess,
)

router = APIRouter(prefix="/api", tags=["Base endpoint"])


@router.get("/checker")
async def check_user(
    initData: Optional[str] = None,
    tg_userid: Optional[int] = None,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_service_api_key: Optional[str] = Header(None, alias="X-Service-API-Key")
) -> Dict[str, Any]:
    """
    Проверяет наличие пользователя.

    Поддерживает три способа авторизации:
    1. initData - данные из Telegram WebApp (проверка HMAC)
    2. Authorization: Bearer <token> - external auth token
    3. X-Service-API-Key + tg_userid - для доверенных сервисов (боты, внутренние сервисы)
    """
    tg_user_id = None

    # Способ 1: initData (Telegram WebApp)
    if initData:
        try:
            tg_user_id = verify_init_data(initData, BOT_TOKEN)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    # Способ 2: Bearer token (external auth)
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        try:
            await db.connect()
            token_data = await db.get_external_token(token)

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            if token_data["status"] != "approved":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token not approved"
                )

            tg_user_id = token_data["tg_userid"]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        finally:
            await db.disconnect()

    # Способ 3: Service API Key (для доверенных сервисов)
    elif x_service_api_key and tg_userid:
        if not TRUSTED_SERVICE_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Service API key not configured"
            )

        if x_service_api_key != TRUSTED_SERVICE_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service API key"
            )

        tg_user_id = tg_userid

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide initData, Authorization header, or X-Service-API-Key with tg_userid"
        )

    try:
        await db.connect()
        await db.init_tables()
        result = await _check_user(db, tg_user_id)

        if isinstance(result, CheckUserError):
            return {"ok": False, "data": {}, "msg": result.message}
        if isinstance(result, CheckUserNeedsLogin):
            return {"ok": False, "needs_login": True, "msg": result.message}
        if isinstance(result, CheckUserNeeds2FA):
            return {"ok": False, "needs_2fa": True, "msg": result.message}

        # Проверяем наличие сохранённого TOTP секрета
        has_totp_secret = await db.has_totp_secret(tg_user_id)

        # result is CheckUserSuccess
        return {
            "group": result.user_info["group_name"],
            "allowConfirm": result.user_info["allowconfirm"],
            "FIO": result.fio,
            "admin_lvl": result.user_info["admin_lvl"],
            "has_totp_secret": has_totp_secret,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.patch("/edit_allow_confirm")
async def edit_ac(data: EditAllowConfirm) -> Dict[str, str]:
    """
    Изменение флага allowConfirm.
    Ожидается initData и значение allowConfirm.
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))
    try:
        await db.connect()
        result = await _edit_allow_confirm(db, tg_user_id, data.allowConfirm)

        # Логируем изменение разрешения на отметку
        is_success = isinstance(result, OperationSuccess)
        await log_user_action(
            action_type="toggle_permission",
            tg_user_id=tg_user_id,
            details={"new_status": data.allowConfirm},
            status="success" if is_success else "failure",
        )

        if is_success:
            return {"status": "Успешно"}
        else:
            return {
                "status": (
                    result.error
                    if isinstance(result, OperationError)
                    else "Не удалось обновить данные"
                )
            }
    except Exception as ex:
        # Логируем ошибку при изменении разрешения
        await log_user_action(
            action_type="toggle_permission",
            tg_user_id=tg_user_id,
            details={"new_status": data.allowConfirm, "error": str(ex)},
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex)
        )
    finally:
        await db.disconnect()


@router.delete("/delete")
async def delete_user_by_id(data: DeleteUser) -> Dict[str, Any]:
    """
    Удаление пользователя по ID.
    """
    try:
        tg_user_id = verify_init_data(data.initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        result = await _delete_user_by_id(db, tg_user_id)
        if isinstance(result, OperationSuccess):
            return {"status": True}
        return {"error": result.error}
    except Exception as e:
        return {"error": str(e)}
    finally:
        await db.disconnect()


@router.get("/university_status")
async def get_university_status(initData: str) -> Dict[str, Any]:
    """
    Получает статус нахождения пользователя в университете
    на основе событий системы контроля доступа (ACS)
    """
    try:
        tg_user_id = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        result = await _get_university_status(db, tg_user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()


@router.get("/group_university_status")
async def get_group_university_status(initData: str) -> Dict[str, Any]:
    """
    Получает статус нахождения всех активированных студентов группы в университете
    на основе событий системы контроля доступа (ACS)
    """
    try:
        tg_user_id = verify_init_data(initData, BOT_TOKEN)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    try:
        await db.connect()
        result = await _get_group_university_status(db, tg_user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        await db.disconnect()

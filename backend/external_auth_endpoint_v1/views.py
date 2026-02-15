import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from fastapi import APIRouter, Header, HTTPException, Query

from backend.attendance import _handle_2fa_result, complete_2fa_login, send_2fa_notification
from backend.auth import verify_init_data
from backend.config import BOT_TOKEN, TRUSTED_SERVICE_API_KEY
from backend.mirea_api.get_cookies import TwoFactorRequired, get_cookies
from backend.utils_helper import db

from .schemas import (
    CredentialsResponse,
    MireaTokenResponse,
    SubmitTotpRequest,
    SubmitTotpResponse,
    TokenRegisterRequest,
    TokenRegisterResponse,
    TokenStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external-auth", tags=["external-auth"])

def _derive_fernet_key(token: str) -> bytes:
    """Derive a Fernet key from the auth token."""
    digest = hashlib.sha256(token.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _check_service_api_key(api_key: str) -> None:
    """Validate the service API key using constant-time comparison."""
    if not TRUSTED_SERVICE_API_KEY:
        raise HTTPException(status_code=500, detail="Service API key not configured")
    if not api_key or not hmac.compare_digest(api_key, TRUSTED_SERVICE_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid service API key")


def _check_token_expiration(token_data: dict) -> None:
    """Check if token has expired."""
    expires_at = token_data.get("expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")


@router.post("/register", response_model=TokenRegisterResponse)
async def register_token(
    request: TokenRegisterRequest,
    x_service_api_key: str = Header(None, alias="X-Service-API-Key"),
):
    """
    Endpoint для регистрации токена от стороннего сервиса.
    Требует X-Service-API-Key для аутентификации сервиса.
    """
    _check_service_api_key(x_service_api_key)

    try:
        await db.connect()

        # Проверяем, не существует ли уже такой токен
        existing_token = await db.get_external_token(request.token)
        if existing_token:
            raise HTTPException(status_code=400, detail="Token already exists")

        # Вычисляем время истечения
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=request.expires_in_minutes
        )

        # Создаем токен в БД
        await db.create_external_token(
            token=request.token,
            expires_at=expires_at,
            service_name=request.service_name,
        )

        return TokenRegisterResponse(
            status="success",
            token=request.token,
            expires_at=expires_at.isoformat(),
            message="Token registered successfully. User should send this token to Telegram bot.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()


@router.get("/status/{token}", response_model=TokenStatusResponse)
async def check_token_status(
    token: str,
    x_service_api_key: str = Header(None, alias="X-Service-API-Key"),
):
    """
    Endpoint для проверки статуса токена (polling).
    Требует X-Service-API-Key для аутентификации сервиса.
    """
    _check_service_api_key(x_service_api_key)

    try:
        await db.connect()

        token_data = await db.get_external_token(token)

        if not token_data:
            return TokenStatusResponse(status="not_found", message="Token not found")

        # Возвращаем текущий статус
        if token_data["status"] == "approved":
            return TokenStatusResponse(
                status="approved",
                tg_userid=token_data["tg_userid"],
                message="Token approved by user",
            )
        elif token_data["status"] == "rejected":
            return TokenStatusResponse(
                status="rejected", message="Token rejected by user"
            )
        else:  # pending
            return TokenStatusResponse(
                status="pending", message="Waiting for user confirmation"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking token status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()


# /approve endpoint removed — tokens are approved ONLY through the Telegram bot
# (webhook handler in tg_endpoint_v1/views.py, line ~196-236).
# This prevents unauthenticated token approval by arbitrary callers.


@router.delete("/reject/{token}")
async def reject_token(
    token: str,
    x_service_api_key: str = Header(None, alias="X-Service-API-Key"),
):
    """
    Endpoint для отклонения токена.
    Требует X-Service-API-Key для аутентификации сервиса.
    """
    _check_service_api_key(x_service_api_key)

    try:
        await db.connect()

        token_data = await db.get_external_token(token)

        if not token_data:
            raise HTTPException(status_code=404, detail="Token not found")

        if token_data["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="Token already processed",
            )

        await db.reject_external_token(token)

        return {"status": "success", "message": "Token rejected"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()


@router.get("/verify")
async def verify_token(authorization: str = Header(None)):
    """
    Endpoint для проверки токена при запросах от стороннего сервиса.
    Сторонний сервис использует этот endpoint, передавая токен в заголовке Authorization.
    Возвращает информацию о пользователе, если токен валиден.
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        # Извлекаем токен из заголовка (формат: "Bearer <token>")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401, detail="Invalid authorization header format"
            )

        token = parts[1]

        await db.connect()

        token_data = await db.get_external_token(token)

        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Проверяем статус и срок действия
        if token_data["status"] != "approved":
            raise HTTPException(status_code=401, detail="Token not approved")
        _check_token_expiration(token_data)

        # Получаем информацию о пользователе
        user = await db.get_user_by_id(token_data["tg_userid"])

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "status": "success",
            "user": {
                "tg_userid": user["tg_userid"],
                "group_name": user.get("group_name"),
                "login": user.get("login"),
                "admin_lvl": user.get("admin_lvl", 0),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()


@router.get("/credentials", response_model=CredentialsResponse)
async def get_credentials(
    authorization: str = Header(None),
    target_tg_userid: int = Query(None),
):
    """
    Endpoint для получения логина и пароля MIREA.

    Используется внешним прокси-сервером для самостоятельной авторизации в MIREA.
    Прокси может затем обрабатывать 2FA на своём IP.

    Параметры:
    - authorization: Bearer токен (обязательный)
    - target_tg_userid: ID пользователя для получения credentials (опционально, для админов)
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401, detail="Invalid authorization header format"
            )

        token = parts[1]

        await db.connect()

        token_data = await db.get_external_token(token)

        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid token")

        if token_data["status"] != "approved":
            raise HTTPException(status_code=401, detail="Token not approved")
        _check_token_expiration(token_data)

        # Определяем какого пользователя запрашиваем
        requester_tg_userid = token_data["tg_userid"]

        if target_tg_userid and target_tg_userid != requester_tg_userid:
            # Проверяем права - нужно быть в одной группе
            requester = await db.get_user(requester_tg_userid)
            target_user = await db.get_user(target_tg_userid)

            if not requester or not target_user:
                raise HTTPException(status_code=404, detail="User not found")

            if requester.get("group_name") != target_user.get("group_name"):
                raise HTTPException(
                    status_code=403,
                    detail="You can only get credentials for users in your group"
                )

            user = target_user
        else:
            user = await db.get_user(requester_tg_userid)

        if not user:
            raise HTTPException(status_code=404, detail="User not found in database")

        # Проверяем наличие логина и пароля
        if not user.get("login") or not user.get("hashed_password"):
            raise HTTPException(
                status_code=400,
                detail="User credentials not found. Please set up login and password first",
            )

        # Получаем TOTP секрет и credential_id для авто-2FA
        target_id = target_tg_userid if (target_tg_userid and target_tg_userid != requester_tg_userid) else requester_tg_userid
        totp_secret = await db.get_totp_secret(target_id)
        totp_credential_id = await db.get_totp_credential_id(target_id)

        # Получаем сохранённые cookies
        cookie_record = await db.get_cookie(target_id)
        stored_cookies = cookie_record.get("cookies") if cookie_record else None

        # Шифруем credentials + TOTP + cookies токеном запрашивающего
        payload = {
            "l": user["login"],
            "p": user["hashed_password"],
            "ts": totp_secret,
            "tc": totp_credential_id,
            "sc": stored_cookies,
        }
        fernet = Fernet(_derive_fernet_key(token))
        encrypted_data = fernet.encrypt(
            json.dumps(payload).encode()
        ).decode()

        return CredentialsResponse(
            status="success",
            encrypted_data=encrypted_data,
            group_name=user.get("group_name"),
            message="Credentials retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()


@router.get("/mirea-token", response_model=MireaTokenResponse)
async def get_mirea_token(
    authorization: str = Header(None), initData: str = Query(None)
):
    """
    Endpoint для получения токена/cookies MIREA.

    Поддерживает два способа авторизации:
    1. Через external auth token (Header: Authorization: Bearer <token>)
    2. Через Telegram initData (Query param: initData)

    Возвращает cookies для использования в запросах к API MIREA.
    """
    tg_userid = None

    try:
        await db.connect()

        # Способ 1: Авторизация через external auth token
        if authorization:
            parts = authorization.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                raise HTTPException(
                    status_code=401, detail="Invalid authorization header format"
                )

            token = parts[1]
            token_data = await db.get_external_token(token)

            if not token_data:
                raise HTTPException(status_code=401, detail="Invalid token")

            if token_data["status"] != "approved":
                raise HTTPException(status_code=401, detail="Token not approved")
            _check_token_expiration(token_data)

            tg_userid = token_data["tg_userid"]

        # Способ 2: Авторизация через Telegram initData
        elif initData:
            try:
                tg_userid = verify_init_data(initData, BOT_TOKEN)
            except ValueError as err:
                raise HTTPException(status_code=401, detail=str(err))

        else:
            raise HTTPException(
                status_code=401,
                detail="Authorization required. Provide either Authorization header or initData parameter",
            )

        # Получаем данные пользователя из БД
        user = await db.get_user(tg_userid)

        if not user:
            raise HTTPException(status_code=404, detail="User not found in database")

        # Проверяем наличие логина и пароля
        if not user.get("login") or not user.get("hashed_password"):
            raise HTTPException(
                status_code=400,
                detail="User credentials not found. Please set up login and password first",
            )

        # Получаем user_agent если есть
        user_agent = await db.get_user_agent(tg_userid)

        # Получаем cookies от MIREA
        try:
            cookies_result = await get_cookies(
                user_login=user["login"],
                password=user["hashed_password"],
                user_agent=user_agent,
                tg_user_id=tg_userid,
                db=db,
            )

            # Проверяем, не требуется ли 2FA
            if isinstance(cookies_result, TwoFactorRequired):
                # Сохраняем сессию 2FA и отправляем уведомление пользователю
                await _handle_2fa_result(
                    db, tg_userid, cookies_result, user_agent, source="external"
                )
                await send_2fa_notification(db, tg_userid, source="external")
                raise HTTPException(
                    status_code=403,
                    detail="2FA required. User has been notified to enter TOTP code in Mini App.",
                )

            cookies = (
                cookies_result[0]
                if isinstance(cookies_result, list)
                else cookies_result
            )

            # Сохраняем cookies в БД для последующего использования
            import json

            await db.create_cookie(tg_userid, json.dumps(cookies))

            return MireaTokenResponse(
                status="success",
                cookies=cookies,
                message="MIREA cookies obtained successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error obtaining MIREA cookies: {error_msg}", exc_info=True)
            if "логин" in error_msg.lower() or "пароль" in error_msg.lower():
                raise HTTPException(
                    status_code=401,
                    detail="Invalid MIREA credentials. Please update your login and password",
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to obtain MIREA cookies",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_mirea_token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()


@router.post("/submit-totp", response_model=SubmitTotpResponse)
async def submit_totp(
    request: SubmitTotpRequest,
    authorization: str = Header(None),
):
    """
    Отправляет TOTP код для завершения двухфакторной аутентификации.

    Требует Authorization header с токеном, полученным ранее.
    После успешной отправки возвращает cookies MIREA.
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401, detail="Invalid authorization header format"
            )

        token = parts[1]

        await db.connect()

        token_data = await db.get_external_token(token)

        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid token")

        if token_data["status"] != "approved":
            raise HTTPException(status_code=401, detail="Token not approved")
        _check_token_expiration(token_data)

        tg_userid = token_data["tg_userid"]

        # Проверяем наличие TOTP сессии
        totp_session = await db.get_totp_session(tg_userid)
        if not totp_session:
            raise HTTPException(
                status_code=400,
                detail="No 2FA session found. Request mirea-token first.",
            )

        # Отправляем TOTP код
        result = await complete_2fa_login(db, tg_userid, request.totp_code)

        if isinstance(result, TwoFactorRequired):
            # Неверный код, нужно повторить
            return SubmitTotpResponse(
                status="invalid_code",
                message="Invalid TOTP code. Please try again.",
            )

        # Успех - получаем свежие cookies
        import json

        cookie_record = await db.get_cookie(tg_userid)
        if cookie_record and cookie_record.get("cookies"):
            cookies = json.loads(cookie_record["cookies"])
            return SubmitTotpResponse(
                status="success",
                message="2FA completed successfully",
                cookies=cookies,
            )
        else:
            return SubmitTotpResponse(
                status="success",
                message="2FA completed, but cookies not found. Try mirea-token again.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_totp: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await db.disconnect()

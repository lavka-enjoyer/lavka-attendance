from fastapi import Header, HTTPException, Query, status

from backend.auth import verify_init_data
from backend.config import BOT_TOKEN
from backend.utils_helper import db


# для гет запросов - поддержка initData И external auth token
async def init_data(initData: str = Query(None), authorization: str = Header(None)):
    """
    Универсальная dependency для авторизации.

    Поддерживает два способа:
    1. initData - Telegram Mini App initData (Query param)
    2. Authorization: Bearer <token> - External auth token (Header)

    Возвращает tg_userid авторизованного пользователя.
    """
    # Способ 1: External auth token (приоритет)
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            try:
                await db.connect()
                token_data = await db.get_external_token(token)

                if not token_data:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid external auth token",
                    )

                if token_data["status"] != "approved":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="External auth token not approved",
                    )

                return token_data["tg_userid"]
            finally:
                await db.disconnect()

    # Способ 2: Telegram initData
    if initData:
        try:
            tg_userid = verify_init_data(initData, BOT_TOKEN)
            return tg_userid
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)
            )

    # Ни один способ не предоставлен
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization required. Provide either initData or Authorization header with Bearer token",
    )


# Обратная совместимость - старый способ только через initData
def init_data_only(initData: str = Query(...)):
    """
    Dependency только для initData (для обратной совместимости).

    Args:
        initData: Строка инициализации Telegram Mini App

    Returns:
        Telegram ID пользователя

    Raises:
        HTTPException: Если проверка initData не прошла
    """
    try:
        tg_userid = verify_init_data(initData, BOT_TOKEN)
        return tg_userid
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

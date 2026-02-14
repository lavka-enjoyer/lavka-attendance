import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.attendance import _handle_2fa_result, send_2fa_notification, try_auto_2fa
from backend.dependencies import init_data
from backend.mirea_api.get_acs_events import (
    determine_university_status,
    get_acs_events_for_date,
)
from backend.mirea_api.get_cookies import get_cookies, TwoFactorRequired
from backend.utils_helper import db

from .schemas import (
    GroupUserForNfc,
    GroupUsersListResponse,
    MireaCookiesResponse,
    NfcCardAddRequest,
    NfcCardAddResponse,
    NfcCardDeleteResponse,
    NfcCardResponse,
    NfcCardsListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nfc", tags=["nfc"])

MOSCOW_TZ = timezone(timedelta(hours=3))


async def get_user_university_status(tg_userid: int) -> dict:
    """
    Проверяет, находится ли пользователь в университете по событиям ACS за сегодня.

    Args:
        tg_userid: Telegram ID пользователя

    Returns:
        Словарь с ключами is_in_university (bool/None) и last_event_time (str/None)
    """
    try:
        # Получаем данные пользователя
        user = await db.get_user(tg_userid)
        if not user or not user.get("login") or not user.get("hashed_password"):
            return {"is_in_university": None, "last_event_time": None}

        user_agent = await db.get_user_agent(tg_userid)
        today_moscow = datetime.now(MOSCOW_TZ)

        # Сначала пробуем кэшированные куки из БД (быстро, без логина в MIREA)
        cookie_record = await db.get_cookie(tg_userid)
        if cookie_record and cookie_record.get("cookies"):
            try:
                cached_cookies = json.loads(cookie_record["cookies"])
                events = await get_acs_events_for_date(
                    cookies=cached_cookies,
                    tg_user_id=tg_userid,
                    db=db,
                    date=today_moscow,
                    user_agent=user_agent,
                )
                status = determine_university_status(events)
                return {
                    "is_in_university": status["is_inside_university"],
                    "last_event_time": status["last_event_time"],
                }
            except Exception as e:
                logger.debug(f"Cached cookies failed for {tg_userid}: {e}")

        # Кэшированные куки не сработали — получаем новые через логин
        cookies_result = await get_cookies(
            user_login=user["login"],
            password=user["hashed_password"],
            user_agent=user_agent,
            tg_user_id=tg_userid,
            db=db,
        )

        # Проверяем что не требуется 2FA
        if isinstance(cookies_result, TwoFactorRequired):
            logger.warning(f"2FA required for university status check, tg_userid={tg_userid}")

            # Пробуем автоматическую 2FA (если у пользователя сохранён totp_secret)
            auto_result = await try_auto_2fa(db, tg_userid, cookies_result, user_agent)
            if auto_result:
                cookies = auto_result["cookies"]
                await db.create_cookie(tg_userid, json.dumps(cookies))
                logger.info(f"Auto-2FA succeeded for university status, tg_userid={tg_userid}")
            else:
                # Авто-2FA не удалась — сохраняем сессию и уведомляем в Telegram
                await _handle_2fa_result(db, tg_userid, cookies_result, user_agent, source="refresh")
                await send_2fa_notification(db, tg_userid, source="refresh")
                return {"is_in_university": None, "last_event_time": None, "needs_totp": True}
        else:
            cookies = (
                cookies_result[0] if isinstance(cookies_result, list) else cookies_result
            )
            # Кэшируем новые куки
            await db.create_cookie(tg_userid, json.dumps(cookies))

        # Получаем события ACS с новыми куками
        events = await get_acs_events_for_date(
            cookies=cookies,
            tg_user_id=tg_userid,
            db=db,
            date=today_moscow,
            user_agent=user_agent,
        )

        # Определяем статус
        status = determine_university_status(events)
        return {
            "is_in_university": status["is_inside_university"],
            "last_event_time": status["last_event_time"],
        }

    except Exception as e:
        logger.error(f"Error getting university status for {tg_userid}: {e}")
        return {"is_in_university": None, "last_event_time": None}


@router.post("/cards", response_model=NfcCardAddResponse)
async def add_nfc_card(request: NfcCardAddRequest, tg_userid: int = Depends(init_data)):
    """
    Добавить NFC карту.

    - card_id: ID NFC карты
    - tg_userid: (опционально) привязка к пользователю бота
    - name: имя владельца карты
    """
    try:
        await db.connect()

        # Получаем группу пользователя, который добавляет карту
        user = await db.get_user_by_id(tg_userid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        owner_group = user.get("group_name")
        if not owner_group:
            raise HTTPException(status_code=400, detail="User has no group assigned")

        # Если указан tg_userid для привязки, проверяем что этот пользователь существует
        linked_tg_userid = request.tg_userid
        card_name = request.name

        if linked_tg_userid:
            linked_user = await db.get_user_by_id(linked_tg_userid)
            if not linked_user:
                raise HTTPException(status_code=404, detail="Linked user not found")
            # Проверяем что он из той же группы
            if linked_user.get("group_name") != owner_group:
                raise HTTPException(
                    status_code=400, detail="Linked user is from different group"
                )
            # Если name не указан, берём fio из БД
            if not card_name:
                card_name = (
                    linked_user.get("fio")
                    or linked_user.get("login")
                    or f"User {linked_tg_userid}"
                )
        else:
            # Если нет tg_userid, name обязателен
            if not card_name:
                raise HTTPException(
                    status_code=400,
                    detail="Name is required when tg_userid is not provided",
                )

        # Добавляем карту
        await db.create_nfc_card(
            card_id=request.card_id,
            name=card_name,
            owner_group=owner_group,
            added_by=tg_userid,
            tg_userid=linked_tg_userid,
        )

        # Получаем созданную карту
        card = await db.get_nfc_card_by_id(request.card_id, owner_group)

        return NfcCardAddResponse(
            status="success",
            message="NFC card added successfully",
            card=NfcCardResponse(
                id=card["id"],
                card_id=card["card_id"],
                tg_userid=card["tg_userid"],
                name=card["name"],
                owner_group=card["owner_group"],
                added_by=card["added_by"],
                created_at=card["created_at"],
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        await db.disconnect()


@router.get("/cards", response_model=NfcCardsListResponse)
async def get_nfc_cards(tg_userid: int = Depends(init_data)):
    """
    Получить все NFC карты из группы пользователя.
    Для карт с привязанным tg_userid проверяется статус нахождения в университете.
    """
    try:
        await db.connect()

        # Получаем группу пользователя
        user = await db.get_user_by_id(tg_userid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        owner_group = user.get("group_name")
        if not owner_group:
            raise HTTPException(status_code=400, detail="User has no group assigned")

        # Получаем все карты группы
        cards = await db.get_nfc_cards_by_group(owner_group)

        result_cards = []
        for card in cards:
            # Определяем имя для отображения
            display_name = card["name"]

            # Если есть привязанный пользователь, берём актуальное ФИО из БД
            if card["tg_userid"]:
                linked_user = await db.get_user_by_id(card["tg_userid"])
                if linked_user:
                    display_name = (
                        linked_user.get("fio")
                        or linked_user.get("login")
                        or card["name"]
                    )

            card_response = NfcCardResponse(
                id=card["id"],
                card_id=card["card_id"],
                tg_userid=card["tg_userid"],
                name=display_name,
                owner_group=card["owner_group"],
                added_by=card["added_by"],
                created_at=card["created_at"],
            )

            # Если есть привязанный пользователь, проверяем статус
            if card["tg_userid"]:
                status = await get_user_university_status(card["tg_userid"])
                card_response.is_in_university = status["is_in_university"]
                card_response.last_event_time = status["last_event_time"]

            result_cards.append(card_response)

        return NfcCardsListResponse(status="success", cards=result_cards)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        await db.disconnect()


@router.delete("/cards/{card_id}", response_model=NfcCardDeleteResponse)
async def delete_nfc_card(card_id: int, tg_userid: int = Depends(init_data)):
    """
    Удалить NFC карту.
    Карту можно удалить только из своей группы.
    """
    try:
        await db.connect()

        # Получаем группу пользователя
        user = await db.get_user_by_id(tg_userid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        owner_group = user.get("group_name")
        if not owner_group:
            raise HTTPException(status_code=400, detail="User has no group assigned")

        # Проверяем что карта существует
        existing_card = await db.get_nfc_card_by_id(card_id, owner_group)
        if not existing_card:
            raise HTTPException(
                status_code=404, detail="NFC card not found in your group"
            )

        # Удаляем карту
        deleted = await db.delete_nfc_card(card_id, owner_group)

        if deleted:
            return NfcCardDeleteResponse(
                status="success", message="NFC card deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete NFC card")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        await db.disconnect()


@router.get("/group-users", response_model=GroupUsersListResponse)
async def get_group_users_for_nfc(tg_userid: int = Depends(init_data)):
    """
    Получить список пользователей группы для выбора при добавлении NFC карты.
    Возвращает пользователей из группы запрашивающего.
    """
    try:
        await db.connect()

        # Получаем группу пользователя
        user = await db.get_user_by_id(tg_userid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        owner_group = user.get("group_name")
        if not owner_group:
            raise HTTPException(status_code=400, detail="User has no group assigned")

        # Получаем пользователей группы
        users = await db.get_users_in_group_for_nfc(owner_group)

        result_users = []
        for u in users:
            # Используем fio если есть, иначе login
            name = u.get("fio") or u.get("login") or f"User {u['tg_userid']}"
            result_users.append(GroupUserForNfc(
                tg_userid=u["tg_userid"],
                name=name,
                needs_totp=u.get("needs_totp", False),
            ))

        return GroupUsersListResponse(status="success", users=result_users)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        await db.disconnect()


@router.get("/mirea-cookies", response_model=MireaCookiesResponse)
async def get_mirea_cookies_for_user(
    target_tg_userid: int, tg_userid: int = Depends(init_data)
):
    """
    Получить cookies MIREA для пользователя из своей группы.

    Используется для NFC приложения - получить cookies другого человека
    для использования его пропуска.

    - target_tg_userid: Telegram ID пользователя, чьи cookies нужны
    """
    try:
        await db.connect()

        # Получаем группу запрашивающего пользователя
        requester = await db.get_user_by_id(tg_userid)
        if not requester:
            raise HTTPException(status_code=404, detail="Requester not found")

        requester_group = requester.get("group_name")
        if not requester_group:
            raise HTTPException(
                status_code=400, detail="Requester has no group assigned"
            )

        # Получаем целевого пользователя
        target_user = await db.get_user(target_tg_userid)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

        # Проверяем что пользователь из той же группы
        target_user_full = await db.get_user_by_id(target_tg_userid)
        if target_user_full.get("group_name") != requester_group:
            raise HTTPException(
                status_code=403, detail="Target user is from different group"
            )

        # Проверяем наличие логина и пароля
        if not target_user.get("login") or not target_user.get("hashed_password"):
            raise HTTPException(
                status_code=400, detail="Target user has no credentials configured"
            )

        # Получаем user_agent целевого пользователя
        user_agent = await db.get_user_agent(target_tg_userid)

        # Получаем cookies
        try:
            cookies_result = await get_cookies(
                user_login=target_user["login"],
                password=target_user["hashed_password"],
                user_agent=user_agent,
                tg_user_id=target_tg_userid,
                db=db,
            )

            # Обработка 2FA
            if isinstance(cookies_result, TwoFactorRequired):
                logger.warning(f"2FA required for mirea-cookies, target_tg_userid={target_tg_userid}")

                # Пробуем автоматическую 2FA
                auto_result = await try_auto_2fa(db, target_tg_userid, cookies_result, user_agent)
                if auto_result:
                    cookies = auto_result["cookies"]
                    await db.create_cookie(target_tg_userid, json.dumps(cookies))
                    logger.info(f"Auto-2FA succeeded for mirea-cookies, target_tg_userid={target_tg_userid}")
                else:
                    # Авто-2FA не удалась — сохраняем сессию и уведомляем
                    await _handle_2fa_result(db, target_tg_userid, cookies_result, user_agent, source="refresh")
                    await send_2fa_notification(db, target_tg_userid, source="refresh")

                    display_name = (
                        target_user_full.get("fio")
                        or target_user_full.get("login")
                        or f"User {target_tg_userid}"
                    )
                    return MireaCookiesResponse(
                        status="2fa_required",
                        tg_userid=target_tg_userid,
                        name=display_name,
                        cookies={},
                        message="Пользователю нужно ввести TOTP в Mini App бота",
                    )
            else:
                cookies = (
                    cookies_result[0]
                    if isinstance(cookies_result, list)
                    else cookies_result
                )

            # Преобразуем в dict для ответа
            cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

            # Получаем имя для отображения
            display_name = (
                target_user_full.get("fio")
                or target_user_full.get("login")
                or f"User {target_tg_userid}"
            )

            return MireaCookiesResponse(
                status="success",
                tg_userid=target_tg_userid,
                name=display_name,
                cookies=cookies_dict,
                message="MIREA cookies obtained successfully",
            )

        except Exception as e:
            error_msg = str(e)
            if "логин" in error_msg.lower() or "пароль" in error_msg.lower():
                raise HTTPException(
                    status_code=401, detail="Invalid MIREA credentials for target user"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to obtain MIREA cookies: {error_msg}",
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        await db.disconnect()

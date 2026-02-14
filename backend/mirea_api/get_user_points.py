#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для получения баллов БРС (балльно-рейтинговой системы) из MIREA API.
Использует blackboxprotobuf для декодирования protobuf ответов.
"""
import asyncio
import logging
import struct
from typing import Any, Dict, List, Optional

import aiohttp

from backend.database import DBModel
from backend.mirea_api.get_cookies import generate_random_mobile_user_agent
from backend.mirea_api.protobuf_decoder import (
    BRS_TYPEDEF,
    decode_grpc_response_bytes,
    ensure_list,
    fixed64_to_double,
    get_field,
    get_nested,
)
from backend.mirea_api.get_groups import _query_get_group

logger = logging.getLogger(__name__)


def decode_grpc_response(grpc_response_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Декодирует ответ БРС API с помощью blackboxprotobuf.

    Структура ответа:
    - Field 1: Report (контейнер)
      - Field 1 (repeated): Row (предмет)
        - Field 1: Discipline Info
          - Field 1: Название дисциплины
          - Field 2: UUID дисциплины
        - Field 2 (repeated): Score Entry
          - Field 1: UUID категории
          - Field 2: Значение (fixed64 -> double)
        - Field 3: Total Score (fixed64 -> double)
      - Field 2 (repeated): Column Group
        - Field 1: Тип категории (int)
        - Field 2 (repeated): Column Definition
          - Field 1: UUID категории
          - Field 2: Название категории
          - Field 3: Описание
          - Field 4: Максимальный балл (int)

    Args:
        grpc_response_bytes: Байтовые данные ответа gRPC

    Returns:
        Список предметов с баллами
    """
    # Декодируем protobuf
    message = decode_grpc_response_bytes(grpc_response_bytes, BRS_TYPEDEF)

    if not message:
        logger.warning("Пустой ответ от БРС API")
        return []

    # Получаем контейнер отчёта (Field 1)
    report = get_field(message, "1", {})
    if not report:
        logger.warning("Не удалось найти данные отчета (Field 1)")
        return []

    rows = []
    columns_info = {}  # uuid -> {'name': str, 'max': float}

    # Парсим категории (Field 2 в report)
    column_groups = ensure_list(get_field(report, "2", []))
    for group in column_groups:
        if not isinstance(group, dict):
            continue

        # Field 2 в группе - определения колонок
        columns = ensure_list(group.get("2", []))
        for col in columns:
            if not isinstance(col, dict):
                continue

            col_uuid = col.get("1", "")
            col_name = col.get("2", "")
            col_max = col.get("4", 0)

            if col_uuid:
                columns_info[col_uuid] = {
                    "uuid": col_uuid,
                    "name": col_name,
                    "max": float(col_max) if col_max else 0.0,
                }

    # Парсим строки с предметами (Field 1 в report)
    discipline_rows = ensure_list(get_field(report, "1", []))
    for row in discipline_rows:
        if not isinstance(row, dict):
            continue

        row_data = {"scores": {}}

        # Discipline Info (Field 1)
        disc_info = row.get("1", {})
        if isinstance(disc_info, dict):
            # Field 1 - название, Field 2 - UUID
            row_data["name"] = disc_info.get("1", "")
            row_data["uuid"] = disc_info.get("2", "")

        # Score entries (Field 2, repeated)
        score_entries = ensure_list(row.get("2", []))
        for entry in score_entries:
            if not isinstance(entry, dict):
                continue

            score_uuid = entry.get("1", "")
            score_value = entry.get("2")

            if score_uuid and score_value is not None:
                # Конвертируем fixed64 в double
                row_data["scores"][score_uuid] = fixed64_to_double(score_value)

        # Total score (Field 3) - fixed64 -> double
        total_value = row.get("3")
        if total_value is not None:
            row_data["total"] = fixed64_to_double(total_value)
        else:
            row_data["total"] = 0.0

        if row_data.get("name"):
            rows.append(row_data)

    # Адаптивное создание порядка категорий
    preferred_order = [
        "Текущий контроль",
        "Семестровый контроль",
        "Посещения",
        "Достижения",
    ]
    ordered_categories = []

    # Добавляем категории из предпочтительного списка
    for cat_name in preferred_order:
        for uuid, col_info in columns_info.items():
            if col_info.get("name") == cat_name:
                ordered_categories.append((uuid, col_info))
                break

    # Добавляем остальные категории
    for uuid, col_info in columns_info.items():
        if uuid not in [cat[0] for cat in ordered_categories]:
            ordered_categories.append((uuid, col_info))

    # Формируем результат
    result = []
    for row in rows:
        item = {
            "name": row.get("name", "Unknown"),
            "fields": {},
            "categories": [],
        }

        # Добавляем информацию о всех категориях
        for idx, (uuid, col_info) in enumerate(ordered_categories):
            cat_name = col_info.get("name", "Unknown")
            max_score = col_info.get("max", 0)
            current_score = row.get("scores", {}).get(uuid, 0.0)

            item["categories"].append({
                "name": cat_name,
                "now": current_score,
                "max": max_score,
                "uuid": uuid,
            })

        # Для обратной совместимости сохраняем старый формат fields
        legacy_mapping = {
            "Текущий контроль": "field2",
            "Посещения": "field3",
            "Достижения": "field4",
            "Семестровый контроль": "field5",
        }

        for uuid, score in row.get("scores", {}).items():
            col_info = columns_info.get(uuid, {})
            cat_name = col_info.get("name", "")
            max_score = col_info.get("max", 0)
            field_key = legacy_mapping.get(cat_name)

            if field_key:
                item["fields"][field_key] = {
                    1: score,
                    2: max_score,
                }

        # Добавляем общий балл
        item["fields"]["field6"] = row.get("total", 0.0)

        result.append(item)

    logger.debug(f"Распарсено {len(result)} предметов из БРС")
    return result


def fill_missing_fields(fields_dict: Dict) -> Dict:
    """
    Добавляет отсутствующие ключи 1 и 2 со значением 0 и преобразует в now/max.

    Args:
        fields_dict: Словарь с полями для обработки

    Returns:
        Словарь с добавленными и преобразованными полями
    """
    if 1 not in fields_dict:
        fields_dict[1] = 0
    if 2 not in fields_dict:
        fields_dict[2] = 0

    fields_dict["now"] = fields_dict.pop(1)
    fields_dict["max"] = fields_dict.pop(2)
    return dict(sorted(fields_dict.items(), reverse=True))


async def _get_points(
    cookies: list,
    db: DBModel,
    user_agent: Optional[str] = None,
    tg_user_id: Optional[int] = None,
) -> list:
    """
    Запрашивает баллы БРС через API.

    Args:
        cookies: Список куки для авторизации
        db: Объект базы данных
        user_agent: User-Agent для запроса
        tg_user_id: ID пользователя в Telegram

    Returns:
        Список [байтовые_данные_ответа]

    Raises:
        Exception: При ошибках запроса
    """
    try:
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        logger.info("[БРС API] Запрос к API БРС")
        url = "https://attendance.mirea.ru/rtu_tc.attendance.api.LearnRatingScoreService/GetLearnRatingScoreReportForStudentInVisitingLogV2"

        SEMESTR_UUID = await _query_get_group(
            cookies, tg_user_id, db, user_agent
        )
        SEMESTR_UUID = SEMESTR_UUID.get("1")[0].get("1").get("1")

        uuid_bytes = SEMESTR_UUID.encode("utf-8")
        # Protobuf: Field 1 (String) = STUDENT_UUID
        payload = bytes([0x0A, len(uuid_bytes)]) + uuid_bytes
        # gRPC-Web header: 0x00 (compressed flag) + 4 bytes length (big endian)
        grpc_header = bytes([0x00]) + struct.pack(">I", len(payload))
        request_body = grpc_header + payload

        headers = {
            "Content-Type": "application/grpc-web+proto",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "attendance-app-type": "student-app",
            "attendance-app-version": "1.0.0+1273",
            "x-grpc-web": "1",
            "x-requested-with": "XMLHttpRequest",
            "Origin": "https://attendance-app.mirea.ru",
            "Referer": "https://attendance-app.mirea.ru/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": (
                user_agent
                if user_agent is not None
                else generate_random_mobile_user_agent()
            ),
        }

        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(cookies_dict)
            async with session.post(
                url,
                data=request_body,
                headers=headers,
                timeout=4,
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка запроса к {url}. Код: {response.status}")
                response_bytes = await response.read()

                logger.info(f"[БРС API] Получен ответ. Статус: {response.status}")
                logger.debug(f"[БРС API] Длина ответа: {len(response_bytes)} байт")

        return [response_bytes]

    except Exception as e:
        logger.error(f"Ошибка при получении баллов БРС: {e}")
        raise


async def _get_points_data(
    cookies: list,
    db: DBModel,
    user_agent: Optional[str] = None,
    tg_user_id: Optional[int] = None,
) -> list:
    """
    Получает и форматирует данные о баллах БРС.

    Args:
        cookies: Список куки для авторизации
        db: Объект базы данных
        user_agent: User-Agent для запроса
        tg_user_id: ID пользователя в Telegram

    Returns:
        Список [форматированные_данные]

    Raises:
        Exception: При ошибках обработки данных
    """
    try:
        logger.debug("_get_points_data called")
        res = await _get_points(cookies, db, user_agent, tg_user_id)
        logger.debug(
            f"_get_points returned, response type: {type(res[0])}, length: {len(res[0])}"
        )
        subjects = decode_grpc_response(res[0])
        logger.debug(f"decode_grpc_response returned {len(subjects)} subjects")

        # Преобразование данных в адаптивный формат
        formatted_data = []
        for item in subjects:
            new_item = {"Дисциплина": item["name"], "fields": {}}

            # Добавляем все категории динамически
            if "categories" in item:
                for category in item["categories"]:
                    cat_name = category["name"]
                    max_score = category["max"]
                    now_score = category["now"]

                    field_key = f"{cat_name} (Макс. {int(max_score)})"
                    new_item["fields"][field_key] = {"now": now_score, "max": max_score}

            # Добавляем общий балл
            if "field6" in item.get("fields", {}):
                new_item["fields"]["Всего баллов (Макс. 100)"] = item["fields"]["field6"]

            formatted_data.append(new_item)

        logger.debug(f"Returning formatted_data for {len(formatted_data)} subjects")
        return [formatted_data]
    except Exception as e:
        logger.error(f"Exception in _get_points_data: {e}", exc_info=True)
        raise e

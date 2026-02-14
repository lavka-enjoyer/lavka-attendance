import datetime
import json
import logging

from backend.config import BOT_TOKEN, DSN, ENCRYPTION_KEY
from backend.database import DBModel

# Dictionary to store active marking sessions
marking_sessions = {}

# Глобальная переменная для хранения состояний пользователей
# В реальном приложении лучше использовать базу данных
user_states = {}

db = DBModel(DSN, ENCRYPTION_KEY)
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

try:
    # Создаем отдельный логгер для действий пользователя
    action_logger = logging.getLogger("user_actions")
    action_logger.setLevel(logging.INFO)

    # Очищаем обработчики, если они уже были установлены
    if action_logger.handlers:
        for handler in action_logger.handlers:
            action_logger.removeHandler(handler)

    # Создаем обработчик для файла
    file_handler = logging.FileHandler("user_actions.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    # Добавляем обработчики к логгеру
    action_logger.addHandler(file_handler)
    action_logger.addHandler(console_handler)

    # Отключаем передачу сообщений родительскому логгеру
    action_logger.propagate = False
except Exception as e:
    logging.error(f"Ошибка при настройке логирования: {str(e)}")


# Функция для логирования действий пользователя
async def log_user_action(
    action_type, tg_user_id=None, tg_userid=None, details=None, status="success"
):
    """
    Логирует действия пользователя в формате JSON для удобного парсинга.

    Args:
        action_type (str): Тип действия (self_approve, mass_mark, get_group, get_other_group, toggle_permission)
        tg_user_id (int): ID пользователя в Telegram (предпочтительное имя)
        tg_userid (int): ID пользователя в Telegram (deprecated, для обратной совместимости)
        details (dict, optional): Дополнительные детали действия
        status (str, optional): Статус выполнения (success/failure)
    """
    # Поддержка обоих вариантов именования для обратной совместимости
    user_id = tg_user_id if tg_user_id is not None else tg_userid

    try:
        if details is None:
            details = {}

        # Убедимся, что все значения в details являются сериализуемыми
        safe_details = {}
        for key, value in details.items():
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                safe_details[key] = value
            else:
                safe_details[key] = str(value)

        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action_type,
            "tg_userid": str(user_id),  # Преобразуем в строку для безопасности
            "status": status,
            "details": safe_details,
        }

        log_str = json.dumps(log_entry, ensure_ascii=False)
        action_logger.info(log_str)
    except Exception as e:
        logging.error(f"Ошибка при логировании: {str(e)}")

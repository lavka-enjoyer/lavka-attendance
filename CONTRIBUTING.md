# Руководство для контрибьюторов

Спасибо за интерес к проекту MireApprove! Это руководство поможет вам начать вносить вклад в развитие проекта.

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Сообщение о багах](#сообщение-о-багах)
- [Предложение новых функций](#предложение-новых-функций)
- [Отправка изменений](#отправка-изменений)
- [Стиль кода](#стиль-кода)
- [Тестирование](#тестирование)
- [Структура проекта](#структура-проекта)

## Быстрый старт

### Требования

- Python 3.10+
- Poetry
- Docker и Docker Compose
- PostgreSQL (или использовать Docker)

### Установка для разработки

1. Склонируйте репозиторий:
```bash
git clone https://github.com/lavka-enjoyer/lavka-attendance.git
cd mireapprove
```

2. Установите зависимости:
```bash
poetry install
```

3. Скопируйте `.env.example` в `.env` и заполните переменные:
```bash
cp .env.example .env
```

4. Запустите PostgreSQL через Docker:
```bash
docker compose up -d db
```

5. Запустите сервер разработки:
```bash
poetry run uvicorn backend.main:app --reload
```

### Запуск через Docker

```bash
docker compose up --build
```

## Сообщение о багах

Перед созданием issue убедитесь, что:
- Баг воспроизводится на последней версии
- Похожий issue ещё не создан

### Формат issue для бага

```
**Описание**
Краткое описание проблемы.

**Шаги воспроизведения**
1. Перейти в '...'
2. Нажать на '...'
3. Увидеть ошибку

**Ожидаемое поведение**
Что должно происходить.

**Фактическое поведение**
Что происходит на самом деле.

**Окружение**
- ОС: [например, Ubuntu 22.04]
- Python: [например, 3.11]
- Версия проекта: [например, 0.1.0]

**Логи/скриншоты**
Если применимо.
```

## Предложение новых функций

Создайте issue с тегом `feature` и опишите:
- Какую проблему решает функция
- Как она должна работать
- Примеры использования

## Отправка изменений

### Процесс

1. Создайте форк репозитория
2. Создайте ветку для изменений:
```bash
git checkout -b feature/название-функции
# или
git checkout -b fix/описание-бага
```

3. Внесите изменения и закоммитьте:
```bash
git add .
git commit -m "feat: добавлена новая функция X"
```

4. Убедитесь что тесты проходят:
```bash
poetry run pytest
```

5. Отправьте изменения:
```bash
git push origin feature/название-функции
```

6. Создайте Pull Request

### Формат коммитов

Используем [Conventional Commits](https://www.conventionalcommits.org/ru/):

- `feat:` — новая функциональность
- `fix:` — исправление бага
- `docs:` — изменения в документации
- `test:` — добавление/изменение тестов
- `refactor:` — рефакторинг кода
- `chore:` — обновление зависимостей, конфигов

Примеры:
```
feat: добавлена авторизация через NFC
fix: исправлена ошибка при парсинге расписания
docs: обновлён README
test: добавлены тесты для auth модуля
```

### Требования к Pull Request

- [ ] Код соответствует стилю проекта
- [ ] Добавлены тесты для новой функциональности
- [ ] Все тесты проходят
- [ ] Обновлена документация (если нужно)
- [ ] PR содержит понятное описание изменений

## Стиль кода

### Python

- Следуем PEP 8
- Максимальная длина строки: 120 символов
- Используем type hints
- Docstrings для публичных функций

```python
async def create_user(
    self,
    tg_userid: int,
    group_name: str,
    login: str,
    password: str
) -> bool:
    """
    Создаёт нового пользователя.

    Args:
        tg_userid: Telegram ID пользователя
        group_name: Название группы (например, ИКБО-01-23)
        login: Логин для системы посещаемости
        password: Пароль (будет зашифрован)

    Returns:
        True если пользователь создан успешно
    """
    ...
```

### Именование

- Переменные и функции: `snake_case`
- Классы: `PascalCase`
- Константы: `UPPER_SNAKE_CASE`
- Приватные методы: `_prefix`

### Логирование

Используйте `logger` вместо `print()`:

```python
import logging

logger = logging.getLogger(__name__)

# Вместо print("Error:", e)
logger.error(f"Ошибка при обработке: {e}")
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
poetry run pytest

# С покрытием
poetry run pytest --cov=backend --cov-report=html

# Конкретный файл
poetry run pytest tests/test_auth.py

# Конкретный тест
poetry run pytest tests/test_auth.py::TestVerifyInitData::test_valid_init_data_returns_user_id
```

### Написание тестов

- Тесты располагаются в `tests/`
- Имя файла: `test_<module>.py`
- Имя функции: `test_<что_тестируем>`
- Используем pytest и pytest-asyncio

```python
import pytest
from backend.auth import verify_init_data

class TestVerifyInitData:
    def test_missing_hash_raises_error(self, bot_token):
        """Отсутствие hash должно вызывать ошибку."""
        init_data = "user=%7B%22id%22%3A123%7D"

        with pytest.raises(ValueError, match="Missing 'hash'"):
            verify_init_data(init_data, bot_token)
```

## Структура проекта

```
mireapprove/
├── backend/
│   ├── admin_endpoint_v1/     # Админ-панель API
│   ├── base_endpoint_v1/      # Базовые endpoints (auth, user)
│   ├── group_endpoint_v1/     # Группы
│   ├── schedule_endpoint_v1/  # Расписание
│   ├── tg_endpoint_v1/        # Telegram интеграция
│   ├── external_auth_endpoint_v1/  # Внешняя авторизация
│   ├── nfc_endpoint_v1/       # NFC карты
│   ├── mirea_api/             # Интеграция с системой посещаемости MIREA
│   │   ├── protobuf_schemas.py  # Схемы protobuf для API (можно копировать)
│   │   ├── protobuf_decoder.py  # Утилиты декодирования
│   │   └── ...                  # Модули работы с API
│   ├── schedule_proto/        # Декодирование protobuf расписания
│   ├── telegram_notifications/ # Telegram уведомления
│   ├── auth.py                # Аутентификация Telegram Mini App
│   ├── database.py            # Модель базы данных
│   ├── config.py              # Конфигурация
│   └── main.py                # Точка входа FastAPI
├── telegram-mini-app/         # React фронтенд
├── tests/                     # Тесты
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

### Структура endpoint модуля

Каждый endpoint содержит:
- `views.py` — HTTP handlers (роуты)
- `crud.py` — операции с БД
- `schemas.py` — Pydantic модели
- `dependencies.py` — зависимости FastAPI

## Вопросы

Если что-то непонятно — создайте issue с тегом `question` или напишите в обсуждениях.

---

Ещё раз спасибо за ваш вклад!

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MireApprove is a system for automating attendance tracking at MIREA university with a Telegram Bot Mini App interface. The backend is FastAPI (Python 3.10+), frontend is React 19, and data is stored in PostgreSQL 15 with Fernet encryption for sensitive fields.

## Build & Run Commands

```bash
# Backend development
poetry install
poetry run uvicorn backend.main:app --reload --port 8001

# Run tests
poetry run pytest
poetry run pytest --cov=backend              # with coverage
poetry run pytest tests/test_auth.py -v      # single file

# Frontend (from telegram-mini-app/)
npm install
npm run dev      # dev server
npm run build    # production build
npm run lint

# Docker
docker-compose up -d                    # start services
docker-compose down -v                  # stop and remove volumes
docker logs mireapprove-app-new         # view logs
```

## Architecture

### Backend Structure (`/backend`)

- **main.py** - FastAPI app entry point; registers 9 routers, mounts static files, serves SPA
- **config.py** - Environment variables (DSN, BOT_TOKEN, ENCRYPTION_KEY, SUPER_ADMIN)
- **database.py** - `DBModel` class with asyncpg connection pooling and Fernet encryption for passwords
- **auth.py** - `verify_init_data()` validates Telegram Mini App HMAC-SHA256 signatures
- **dependencies.py** - `init_data()` dependency supports both Telegram initData and external Bearer tokens
- **attendance.py** - Core attendance confirmation logic

### Endpoint Pattern

Each endpoint module follows: `views.py` (routes), `crud.py` (DB operations), `schemas.py` (Pydantic models), optional `dependencies.py`.

Endpoint modules:
- `base_endpoint_v1` - Auth, user info, permissions
- `admin_endpoint_v1` - Admin operations, referrals
- `tg_endpoint_v1` - Telegram bot webhook
- `external_auth_endpoint_v1` - Third-party service authentication
- `group_endpoint_v1`, `schedule_endpoint_v1`, `points_endpoint_v1`, `markin_endpoint_v1`, `nfc_endpoint_v1`

### External API Integration (`/backend/mirea_api`)

Modules for interacting with MIREA's attendance system:
- `protobuf_schemas.py` - **Схемы protobuf для всех эндпоинтов MIREA API**
- `protobuf_decoder.py` - Утилиты для декодирования gRPC-Web
- `get_cookies.py` - Session management
- `get_schedule.py`, `get_lesson_attendance.py` - Schedule and attendance data
- `get_user_points.py` - БРС (балльно-рейтинговая система)
- `get_acs_events.py` - События турникетов (ACS)
- `get_me_info.py` - Информация о пользователе
- `get_groups.py` - Группы и семестры
- `self_approve_attendance.py` - Auto-confirmation logic
- `lessons_cost_cache.py` - Caching layer

---

## Использование MIREA API в своём проекте

Файлы `protobuf_schemas.py` и `protobuf_decoder.py` можно использовать как основу для создания собственных проектов, работающих с API системы посещаемости MIREA.

### Быстрый старт

```bash
pip install blackboxprotobuf aiohttp
```

```python
import base64
import aiohttp
import blackboxprotobuf

# Копируем нужные схемы из protobuf_schemas.py
SCHEDULE_TYPEDEF = { ... }  # см. protobuf_schemas.py

def skip_grpc_header(data: bytes) -> bytes:
    """Убирает 5-байтовый gRPC-Web заголовок."""
    if len(data) < 5 or data[0] != 0x00:
        return data
    length = int.from_bytes(data[1:5], "big")
    return data[5:5+length] if 5+length <= len(data) else data

async def get_schedule(cookies: dict) -> dict:
    url = "https://attendance.mirea.ru/rtu_tc.attendance.api.ScheduleService/GetScheduleForStudent"
    headers = {
        "Content-Type": "application/grpc-web+proto",
        "x-grpc-web": "1",
        "Origin": "https://attendance-app.mirea.ru"
    }
    # Запрос с временным диапазоном (protobuf)
    request_body = b"\x00\x00\x00\x00\x00"  # пустой запрос

    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.post(url, data=request_body, headers=headers) as resp:
            raw = await resp.read()

    content = skip_grpc_header(raw)
    message, _ = blackboxprotobuf.decode_message(content, SCHEDULE_TYPEDEF)
    return message
```

### Структура файлов

```
protobuf_schemas.py    # Только схемы (typedef) - скопируй в свой проект
protobuf_decoder.py    # Утилиты декодирования - опционально
```

### Доступные схемы

| Схема | Эндпоинт | Описание |
|-------|----------|----------|
| `SCHEDULE_TYPEDEF` | ScheduleService/GetScheduleForStudent | Расписание с посещаемостью |
| `ME_INFO_TYPEDEF` | UserService/GetMeInfo | Информация о пользователе |
| `BRS_TYPEDEF` | LearnRatingScoreService/GetLearnRating... | Баллы БРС |
| `ACS_EVENTS_TYPEDEF` | HumanPassService/GetHumanAcsEvents | Проходы через турникеты |
| `VISITING_LOGS_TYPEDEF` | VisitingLogService/GetAvailableVisiting... | Семестры и группы |
| `DISCIPLINES_TYPEDEF` | DisciplineService/GetAvailableDisciplines | Список дисциплин |
| `ATTENDANCE_REPORT_TYPEDEF` | VisitingLogService/GetAttendanceVisiting... | Отчёт посещаемости |

### API Reference

**Base URL:** `https://attendance.mirea.ru/`

**Headers:**
```
Content-Type: application/grpc-web+proto (или application/grpc-web-text для base64)
x-grpc-web: 1
x-requested-with: XMLHttpRequest
Origin: https://attendance-app.mirea.ru
```

**Авторизация:** Cookies после OAuth через https://login.mirea.ru/

### gRPC-Web формат

Все ответы имеют 5-байтовый заголовок:
```
[1 byte flags][4 bytes length BE][protobuf payload]
```
- `flags=0x00` — data frame
- `flags=0x80` — trailer frame (пустой ответ)

### Особенности парсинга

**fixed64 → double (для БРС баллов):**
```python
import struct
def fixed64_to_double(value: int) -> float:
    return struct.unpack('<d', struct.pack('<Q', value))[0]

# Пример: 4626322717216342016 → 40.0
```

**Статусы посещаемости:**
- `1` = "Н" (не был)
- `2` = "У" (уважительная причина)
- `3` = "+" (присутствовал)

**Определение подтверждения занятия:**
1. Проверить `field 8.1.1` — timestamp подтверждения
2. Если `< 1000000000` → занятие не подтверждено
3. Если подтверждено, `wrapper["2"]`: `1`="Н", `3`="+"`

### Protocol Buffers (`/backend/schedule_proto`)

Schedule data uses protobuf encoding. `improved_schedule_decoder.py` handles decoding MIREA API responses using `blackboxprotobuf` library (package `bbpb`).

#### Декодирование с blackboxprotobuf

Используем библиотеку [blackboxprotobuf](https://github.com/nccgroup/blackboxprotobuf) для декодирования protobuf без .proto схемы:

```python
import blackboxprotobuf

# Декодирование без схемы (автоопределение типов)
message, typedef = blackboxprotobuf.decode_message(protobuf_bytes)

# Декодирование с заданной схемой (быстрее и надёжнее)
message, typedef = blackboxprotobuf.decode_message(protobuf_bytes, SCHEDULE_TYPEDEF)
```

#### gRPC-Web Framing

Ответы имеют 5-байтовый заголовок перед protobuf данными:
```
[1 byte flags][4 bytes big-endian length][protobuf payload]
```

Пример: `00 00 00 05 CC` = flags=0, length=1484, затем 1484 байта protobuf

#### Схема расписания (SCHEDULE_TYPEDEF)

```python
SCHEDULE_TYPEDEF = {
    "2": {  # Wrapper (repeated)
        "type": "message",
        "message_typedef": {
            "2": {"type": "int"},  # СТАТУС: 1=Н (не был), 3=+ (был)
            "3": {  # Lesson
                "type": "message",
                "message_typedef": {
                    "1": {"type": "string"},      # UUID занятия
                    "2": {"type": "message", "message_typedef": {"1": {"type": "int"}}},  # timestamp начала
                    "3": {"type": "message", "message_typedef": {"1": {"type": "int"}}},  # timestamp конца
                    "4": {"type": "message", "message_typedef": {"2": {"type": "string"}}},  # предмет
                    "5": {"type": "message", "message_typedef": {"2": {"type": "string"}}},  # тип (ЛК/ПР/ЗАЧ/КП/Э/Конс)
                    "6": {"type": "message", "message_typedef": {  # аудитория
                        "2": {"type": "string"},  # номер (326, 145б, Дистанционно)
                        "3": {"type": "string"}   # группа (ИКБО-01-23, С-20, СДО)
                    }},
                    "7": {"type": "message", "message_typedef": {  # преподаватель
                        "2": {"type": "string"},  # Имя
                        "3": {"type": "string"},  # Фамилия
                        "4": {"type": "message", "message_typedef": {"1": {"type": "string"}}}  # Отчество
                    }},
                    "8": {"type": "message", "message_typedef": {  # подтверждение
                        "1": {"type": "message", "message_typedef": {"1": {"type": "int"}}}  # timestamp (-62135596800 = не подтверждено)
                    }}
                }
            }
        }
    }
}
```

**Логика определения статуса:**
1. Проверить `field 8.1.1` - timestamp подтверждения
   - Если `-62135596800` или < 1000000000 → занятие не подтверждено, статус пустой
2. Если подтверждено, смотреть `wrapper["2"]`:
   - `1` → "Н" (не был)
   - `3` → "+" (был)

#### Пример декодированного сообщения

```python
# Raw output от blackboxprotobuf.decode_message()
{
    "2": {
        "2": 3,  # wrapper status: 3 = был (+)
        "3": {
            "1": "0199f04a-2b81-70fb-bc1d-07ada872e53c",
            "2": {"1": 1764582000},  # Unix timestamp начала
            "3": {"1": 1764587400},  # Unix timestamp конца
            "4": {"2": "Операционные системы"},
            "5": {"2": "ПР"},
            "6": {"2": "426а", "3": "С-20"},
            "7": {"2": "Екатерина", "3": "Белякова", "4": {"1": "Владимировна"}},
            "8": {"1": {"1": 1760673016}}  # timestamp подтверждения (валидный = подтверждено)
        }
    }
}

# После парсинга parse_schedule()
{
    "uuid": "0199f04a-2b81-70fb-bc1d-07ada872e53c",
    "time": "12:40 - 14:10",
    "date": "2025-12-01",
    "subject": "Операционные системы",
    "type": "ПР",
    "room": "426а",
    "group": "С-20",
    "teacher": "Белякова Е. В.",
    "status": "+"  # wrapper["2"]=3 + валидный timestamp → "+"
}
```

#### Использование

```python
from backend.schedule_proto.improved_schedule_decoder import parse_schedule

# b64_data - base64 ответ от MIREA API
lessons = parse_schedule(b64_data, disciplines_list=["Математический анализ", ...])

for lesson in lessons:
    print(f"{lesson['date']} {lesson['time']} | {lesson['type']} | {lesson['subject']}")
```

#### Генерация новой схемы

Если MIREA изменит формат API, можно сгенерировать новую схему:

```python
import blackboxprotobuf

# Декодируем без схемы - библиотека автоматически определит типы
message, new_typedef = blackboxprotobuf.decode_message(protobuf_bytes)

# new_typedef содержит автоматически определённую схему
# Скопируйте её в SCHEDULE_TYPEDEF в improved_schedule_decoder.py
print(new_typedef)
```

### Frontend (`/telegram-mini-app`)

React 19 SPA with Vite, Tailwind CSS, and shadcn/ui components. Key components:
- `MainScreen.jsx`, `LoginForm.jsx` - Entry points
- `ScheduleScreen.jsx`, `MarkSelfScreen.jsx` - Core features
- `ui/` - Reusable shadcn components

## Database Schema

Key tables in `database.py`:
- **users** - tg_userid (PK), group_name, login, hashed_password (encrypted), allowConfirm, admin_lvl, user_agent, fio
- **approved** - Attendance records per user
- **external_auth_tokens** - Third-party auth with status workflow (pending → approved/rejected)
- **nfc_cards** - NFC card to user mapping
- **totp_sessions** - Temporary 2FA sessions (tg_userid, session_cookies, otp_action_url, credential_id, expires_at, last_notification_sent)

## Authentication

Two auth methods handled by `init_data()` dependency:
1. **Telegram Mini App** - Query param `initData` verified via HMAC-SHA256 with bot token
2. **External Bearer** - Header `Authorization: Bearer <token>` for third-party services

## Key Patterns

- All DB operations are async using asyncpg
- Passwords encrypted with `cryptography.Fernet` before storage
- Rate limiting: 100 requests/minute
- Use parametrized SQL queries (no string concatenation)

## Environment Variables

Required in `.env`:
```
DSN=postgresql://postgres:<password>@postgres/mireapprove
ENCRYPTION_KEY=<fernet-key>
BOT_TOKEN=<telegram-bot-token>
BOT_USERNAME=<bot-username>
SUPER_ADMIN=<admin-telegram-id>
```

Generate Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Adding New Endpoints

1. Create module under `backend/<name>_endpoint_v1/`
2. Add `views.py` with APIRouter, `crud.py` for DB ops, `schemas.py` for models
3. Register router in `main.py`
4. Use `init_data` dependency for authentication

## Development Rules

### Testing Requirements

When making significant changes, **always add or update tests**:

- **New functions/classes** — add unit tests in `tests/test_<module>.py`
- **Bug fixes** — add regression test that reproduces the bug
- **New endpoints** — add integration tests for all routes
- **Auth/security changes** — mandatory test coverage

Run tests before committing:
```bash
poetry run pytest tests/ -v
```

Test structure:
```
tests/
├── conftest.py          # Shared fixtures
├── test_auth.py         # Auth module tests
├── test_database.py     # Database operations tests
├── test_endpoints.py    # API endpoint tests
└── test_2fa.py          # Two-factor authentication tests
```

### Documentation Updates

When adding new features, update documentation:

- **New endpoint module** — add to "Endpoint modules" list in this file and update `CONTRIBUTING.md` project structure
- **New environment variable** — add to "Environment Variables" section
- **Changed project structure** — update `CONTRIBUTING.md` "Структура проекта" section
- **New development workflow** — update `CONTRIBUTING.md` relevant section

### Wiki Documentation

Project wiki is located at: https://github.com/mixelka75/mireapprove/wiki

Wiki repository is cloned to: `/home/mixelka/Mirea/mireapprove-wiki`

**When to update wiki:**
- Changes to MIREA API integration (`/backend/mirea_api/`) — update `MIREA-API-Integration.md`
- Changes to protobuf decoding (`/backend/schedule_proto/`) — update `Protobuf-Decoding.md`
- Changes to authentication (`auth.py`, `dependencies.py`) — update `Authentication.md`
- Changes to database schema (`database.py`) — update `Database-Schema.md`
- New/changed API endpoints — update `API-Endpoints.md`
- Frontend changes — update `Frontend-Architecture.md`

**How to update wiki:**
```bash
cd /home/mixelka/Mirea/mireapprove-wiki
# Edit relevant .md files
git add -A && git commit -m "docs: update <section>" && git push
```

Wiki pages:
- `Home.md` — Project overview
- `MIREA-API-Integration.md` — External API documentation
- `Protobuf-Decoding.md` — Protobuf parsing details
- `Authentication.md` — Auth mechanisms
- `Database-Schema.md` — DB tables and methods
- `API-Endpoints.md` — REST API reference
- `Frontend-Architecture.md` — React Mini App
- `Development-Guide.md` — Developer guide

### Git Push Workflow

Синхронизация в lavka-attendance происходит автоматически при пуше в main (через GitHub Actions CI).
Достаточно пушить только в `origin` (mixelka75/mireapprove).

### Code Style

- Use `logger` instead of `print()` for all output
- Add type hints to all functions
- Add docstrings to public functions
- Follow existing patterns in the codebase

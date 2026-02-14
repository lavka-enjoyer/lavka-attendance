# External Authentication API

## Описание

Система внешней авторизации позволяет сторонним сервисам авторизовывать пользователей через Telegram бота.

## Универсальная авторизация

**Все endpoint'ы бэкенда** поддерживают два способа авторизации:

1. **Telegram initData** (Query param): `?initData=...`
2. **External Auth Token** (Header): `Authorization: Bearer <token>`

Это означает, что после успешной авторизации через Telegram бота, вы можете использовать полученный токен для доступа к **любому** endpoint'у API.

## Схема работы

```
1. Сторонний сервис генерирует JWT токен
2. Сервис регистрирует токен на нашем бэкенде (POST /api/external-auth/register)
3. Сервис показывает токен пользователю
4. Пользователь отправляет токен боту в Telegram
5. Бот подтверждает токен (POST /api/external-auth/approve)
6. Сторонний сервис периодически проверяет статус (GET /api/external-auth/status/{token})
7. После подтверждения, сервис использует токен для запросов (GET /api/external-auth/verify)
```

## API Endpoints

### 1. Регистрация токена

**POST** `/api/external-auth/register`

Регистрирует новый токен для авторизации.

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "service_name": "my-service",
  "expires_in_minutes": 10
}
```

**Response:**
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-12-02T12:30:00",
  "message": "Token registered successfully. User should send this token to Telegram bot."
}
```

**Errors:**
- `400` - Token already exists
- `500` - Internal server error

---

### 2. Проверка статуса токена (Polling)

**GET** `/api/external-auth/status/{token}`

Проверяет текущий статус токена. Используется для polling.

**Response:**
```json
{
  "status": "pending",
  "tg_userid": null,
  "message": "Waiting for user confirmation"
}
```

**Возможные статусы:**
- `pending` - ожидает подтверждения
- `approved` - подтвержден (tg_userid будет заполнен)
- `rejected` - отклонен
- `expired` - истек срок действия
- `not_found` - токен не найден

**Errors:**
- `500` - Internal server error

---

### 3. Подтверждение токена (через бота)

**POST** `/api/external-auth/approve`

Подтверждает токен и связывает его с пользователем Telegram.

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tg_userid": 123456789
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Token approved successfully"
}
```

**Errors:**
- `400` - Token expired or already processed
- `404` - Token or user not found
- `500` - Internal server error

---

### 4. Отклонение токена

**DELETE** `/api/external-auth/reject/{token}`

Отклоняет токен авторизации.

**Response:**
```json
{
  "status": "success",
  "message": "Token rejected"
}
```

**Errors:**
- `400` - Token already processed
- `404` - Token not found
- `500` - Internal server error

---

### 5. Проверка токена для запросов

**GET** `/api/external-auth/verify`

Проверяет токен и возвращает информацию о пользователе.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "status": "success",
  "user": {
    "tg_userid": 123456789,
    "group_name": "ИКБО-01-21",
    "login": "user_login",
    "admin_lvl": 0
  }
}
```

**Errors:**
- `401` - Invalid or expired token, or not approved
- `404` - User not found
- `500` - Internal server error

---

## Примеры использования

### Python (Сторонний сервис)

См. файл `example_external_service.py` для полного примера.

Основной flow:
```python
import jwt
import requests
import time

# 1. Генерируем токен
token = jwt.encode({"service": "my-app"}, "secret", algorithm="HS256")

# 2. Регистрируем токен
response = requests.post(
    "https://your-domain.com/api/external-auth/register",
    json={"token": token, "expires_in_minutes": 10}
)

# 3. Показываем токен пользователю
print(f"Отправьте этот токен боту: {token}")

# 4. Polling - проверяем статус каждые 3 секунды
while True:
    status = requests.get(
        f"https://your-domain.com/api/external-auth/status/{token}"
    ).json()

    if status["status"] == "approved":
        print(f"Авторизован! User ID: {status['tg_userid']}")
        break
    elif status["status"] in ["rejected", "expired"]:
        print("Авторизация не удалась")
        break

    time.sleep(3)

# 5. Используем токен для запросов
user_info = requests.get(
    "https://your-domain.com/api/external-auth/verify",
    headers={"Authorization": f"Bearer {token}"}
).json()
```

### Telegram Bot

См. файл `example_telegram_bot.py` для полного примера.

Основная логика:
```python
from telegram import Update
from telegram.ext import MessageHandler, filters
import requests

async def handle_token(update: Update, context):
    token = update.message.text
    tg_userid = update.effective_user.id

    # Подтверждаем токен
    response = requests.post(
        "https://your-domain.com/api/external-auth/approve",
        json={"token": token, "tg_userid": tg_userid}
    )

    if response.status_code == 200:
        await update.message.reply_text("✅ Авторизация успешна!")
    else:
        await update.message.reply_text("❌ Ошибка авторизации")
```

---

## База данных

### Таблица: `external_auth_tokens`

| Поле | Тип | Описание |
|------|-----|----------|
| token | TEXT | JWT токен (PRIMARY KEY) |
| tg_userid | BIGINT | ID пользователя Telegram (NULL до подтверждения) |
| status | TEXT | Статус: pending/approved/rejected |
| created_at | TIMESTAMP | Время создания |
| expires_at | TIMESTAMP | Время истечения |
| service_name | TEXT | Название стороннего сервиса |

---

## Безопасность

1. **Время жизни токенов**: По умолчанию 10 минут. Можно настроить при регистрации.

2. **Проверка пользователя**: Перед подтверждением токена проверяется существование пользователя в системе.

3. **Одноразовые токены**: Токен может быть подтвержден только один раз.

4. **Автоматическая очистка**: Истекшие токены можно удалять через `db.delete_expired_tokens()`.

5. **HTTPS**: В продакшене используйте HTTPS для всех запросов.

---

## Рекомендации

1. **Polling interval**: Рекомендуется проверять статус каждые 2-5 секунд.

2. **Timeout**: Устанавливайте максимальное время ожидания (например, 5 минут).

3. **UI/UX**: Показывайте пользователю QR-код с токеном для удобства.

4. **Валидация JWT**: Используйте подписанные JWT токены с вашим секретным ключом.

5. **Логирование**: Логируйте все попытки авторизации для анализа.

---

## Развертывание

После внесения изменений:

```bash
# Пересоберите Docker образ
docker build -t mireapprove:latest .

# Перезапустите контейнеры
docker-compose down
docker-compose up -d

# Проверьте логи
docker logs mireapprove-app
```

API доступно по адресу: `https://your-domain.com/api/external-auth/`

Swagger документация: `https://your-domain.com/docs`

## Тестирование API

Вы можете протестировать API прямо сейчас:

```bash
# Пример регистрации токена
curl -X POST "https://your-domain.com/api/external-auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "test_token_123",
    "service_name": "test-service",
    "expires_in_minutes": 10
  }'

# Проверка статуса токена
curl "https://your-domain.com/api/external-auth/status/test_token_123"
```

---

### 6. Получение токена MIREA

**GET** `/api/external-auth/mirea-token`

Получает cookies для авторизации в системе MIREA (attendance.mirea.ru).

**Авторизация (один из вариантов):**

1. Header: `Authorization: Bearer <external_auth_token>`
2. Query param: `initData=<telegram_init_data>`

**Response (успех):**
```json
{
  "status": "success",
  "cookies": [
    {
      "name": ".AspNetCore.Cookies",
      "value": "CfDJ8...",
      "domain": "attendance.mirea.ru",
      "path": "/",
      "secure": true
    }
  ],
  "message": "MIREA cookies obtained successfully"
}
```

**Errors:**
- `400` - User credentials not found (логин/пароль не настроены)
- `401` - Invalid token или Invalid MIREA credentials
- `404` - User not found
- `503` - Proxy service unavailable
- `500` - Internal server error

**Примеры использования:**

```bash
# Через external auth token
curl "https://your-domain.com/api/external-auth/mirea-token" \
  -H "Authorization: Bearer your_approved_token"

# Через Telegram initData
curl "https://your-domain.com/api/external-auth/mirea-token?initData=user%3D..."
```

**Python пример:**

```python
import requests

# После успешной авторизации через Telegram
token = "your_approved_token"

# Получаем cookies MIREA
response = requests.get(
    "https://your-domain.com/api/external-auth/mirea-token",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    data = response.json()
    mirea_cookies = data["cookies"]

    # Теперь можно использовать cookies для запросов к MIREA API
    session = requests.Session()
    for cookie in mirea_cookies:
        session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))

    # Пример запроса к MIREA
    # response = session.get("https://attendance.mirea.ru/api/...")
    print(f"Получено {len(mirea_cookies)} cookies")
else:
    print(f"Ошибка: {response.json()}")
```

---

## Полный flow: Авторизация + Получение MIREA токена

```
┌─────────────────┐                    ┌──────────────┐                    ┌─────────────┐
│ Внешний сервис  │                    │   Бэкенд     │                    │ Telegram    │
│                 │                    │              │                    │ бот         │
└────────┬────────┘                    └──────┬───────┘                    └──────┬──────┘
         │                                    │                                   │
         │ 1. POST /register (token)          │                                   │
         │ ─────────────────────────────────> │                                   │
         │                                    │                                   │
         │     ← token registered             │                                   │
         │                                    │                                   │
         │ 2. Показать токен пользователю     │                                   │
         │    "Отправьте этот код боту"       │                                   │
         │                                    │                                   │
         │                                    │  3. Пользователь отправляет токен │
         │                                    │ <────────────────────────────────  │
         │                                    │                                   │
         │                                    │  4. POST /approve                 │
         │                                    │ <────────────────────────────────  │
         │                                    │                                   │
         │                                    │     → approved                    │
         │                                    │ ─────────────────────────────────>│
         │                                    │                                   │
         │ 5. GET /status/{token} (polling)   │                                   │
         │ ─────────────────────────────────> │                                   │
         │                                    │                                   │
         │     ← status: approved, tg_userid  │                                   │
         │                                    │                                   │
         │ 6. GET /mirea-token                │                                   │
         │    Authorization: Bearer token     │                                   │
         │ ─────────────────────────────────> │                                   │
         │                                    │                                   │
         │     ← MIREA cookies                │                                   │
         │                                    │                                   │
         │ 7. Использовать cookies для        │                                   │
         │    запросов к MIREA API            │                                   │
         ▼                                    ▼                                   ▼
```

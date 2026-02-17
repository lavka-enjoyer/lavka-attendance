<div align="center">

# MireApprove

**Автоматизация учёта посещаемости МИРЭА**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)

Telegram Mini App для студентов МИРЭА — отметка посещаемости, расписание, баллы БРС

</div>

---

## Установка на сервер (одной командой)

```bash
bash <(curl -Ls https://raw.githubusercontent.com/lavka-enjoyer/lavka-attendance/main/install.sh)
```

Скрипт автоматически установит Docker, Nginx, SSL сертификат и настроит всё необходимое.

---

## Скриншоты

<p align="center">
  <img src="docs/screenshots/main.png" width="180" alt="Главный экран">
  <img src="docs/screenshots/schedule.png" width="180" alt="Расписание">
  <img src="docs/screenshots/points.png" width="180" alt="Баллы БРС">
  <img src="docs/screenshots/university-status.png" width="180" alt="Кто в универе">
  <img src="docs/screenshots/mass-marking.png" width="180" alt="Массовая отметка">
</p>

## Возможности

| Функция | Описание |
|---------|----------|
| **Отметка посещаемости** | Автоматическое подтверждение присутствия на занятиях |
| **Расписание** | Просмотр актуального расписания с индикацией текущей пары |
| **БРС баллы** | Мониторинг текущих баллов по всем предметам |
| **Кто в универе** | Статус присутствия одногруппников в университете |
| **Массовая отметка** | Отметка нескольких студентов за раз (для админов) |
| **NFC поддержка** | Отметка через NFC карты (опционально) |

## Технологии

<table>
<tr><td><b>Backend</b></td><td>FastAPI, Python 3.10+, asyncpg, APScheduler</td></tr>
<tr><td><b>Frontend</b></td><td>React 19, Vite, Tailwind CSS, shadcn/ui</td></tr>
<tr><td><b>Database</b></td><td>PostgreSQL 15</td></tr>
<tr><td><b>Security</b></td><td>Fernet encryption, HMAC-SHA256 (Telegram auth)</td></tr>
<tr><td><b>Deploy</b></td><td>Docker, Docker Compose</td></tr>
</table>

## Быстрый старт

### Требования

- Docker и Docker Compose
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/lavka-enjoyer/lavka-attendance.git
cd mireapprove

# 2. Создать .env файл
cp .env.example .env

# 3. Заполнить переменные окружения (см. ниже)
nano .env

# 4. Запустить
docker compose up -d --build

# 5. Проверить
docker compose ps
```

### Переменные окружения

```env
# Обязательные
POSTGRES_PASSWORD=secure_password
DSN=postgresql://postgres:secure_password@postgres/mireapprove
ENCRYPTION_KEY=<fernet-key>
BOT_TOKEN=<telegram-bot-token>
BOT_USERNAME=<bot-username>
SUPER_ADMIN=<your-telegram-id>
```

<details>
<summary>Как сгенерировать ENCRYPTION_KEY</summary>

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
</details>

### Доступ

| Сервис | URL |
|--------|-----|
| API | http://localhost:8001 |
| Swagger Docs | http://localhost:8001/docs |
| Mini App | Через Telegram бота |

## Разработка

<details>
<summary>Локальный запуск без Docker</summary>

**Backend:**
```bash
poetry install
poetry run uvicorn backend.main:app --reload --port 8001
```

**Frontend:**
```bash
cd telegram-mini-app
npm install
npm run dev
```
</details>

<details>
<summary>Тесты</summary>

```bash
poetry run pytest tests/ -v
poetry run pytest --cov=backend  # с покрытием
```
</details>

<details>
<summary>Структура проекта</summary>

```
mireapprove/
├── backend/
│   ├── main.py                 # FastAPI приложение
│   ├── config.py               # Конфигурация
│   ├── database.py             # Модель БД с шифрованием
│   ├── auth.py                 # Telegram WebApp авторизация
│   ├── attendance.py           # Логика посещаемости
│   ├── base_endpoint_v1/       # Базовые эндпоинты
│   ├── admin_endpoint_v1/      # Админ панель
│   ├── schedule_endpoint_v1/   # Расписание
│   ├── points_endpoint_v1/     # БРС баллы
│   ├── attenApi/               # Интеграция с MIREA API
│   └── decencproto/            # Protobuf декодеры
├── telegram-mini-app/
│   ├── src/
│   │   ├── components/         # React компоненты
│   │   ├── services/           # API сервисы
│   │   └── App.jsx
│   └── vite.config.js
├── tests/
├── docker-compose.yml
└── Dockerfile
```
</details>

## API

Документация: `/docs` после запуска.

**Аутентификация:**
- Telegram Mini App — автоматическая через `initData`
- External Token — Bearer токен для сторонних сервисов

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/v1/user/info
```

Подробнее:
- [Примеры использования API](docs/API_EXAMPLES.md)
- [Внешняя авторизация](docs/EXTERNAL_AUTH_API.md)
- [NFC API](docs/NFC_API.md)

## Участие в разработке

Мы рады вкладу в проект! См. [CONTRIBUTING.md](CONTRIBUTING.md)

## Безопасность

Политика безопасности: [SECURITY.md](SECURITY.md)

## Лицензия

[MIT License](LICENSE)


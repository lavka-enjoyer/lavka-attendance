FROM node:20-slim AS frontend

WORKDIR /app/frontend
COPY telegram-mini-app/package.json telegram-mini-app/package-lock.json* ./
RUN npm ci
COPY telegram-mini-app/ ./

# Vite встраивает VITE_* переменные при сборке
ARG VITE_API_URL=""
ARG VITE_SUPPORT_USERNAME=""
ARG VITE_NEWS_CHANNEL_URL=""
ARG VITE_BOT_USERNAME=""
ARG VITE_DEMO_MODE="false"
ENV VITE_API_URL=$VITE_API_URL \
    VITE_SUPPORT_USERNAME=$VITE_SUPPORT_USERNAME \
    VITE_NEWS_CHANNEL_URL=$VITE_NEWS_CHANNEL_URL \
    VITE_BOT_USERNAME=$VITE_BOT_USERNAME \
    VITE_DEMO_MODE=$VITE_DEMO_MODE

RUN NODE_OPTIONS="--max-old-space-size=512" npm run build

FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей (libzbar для pyzbar - парсинг QR-кодов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry через pip (более надёжно чем официальный installer)
RUN pip install --no-cache-dir poetry

# Настройка Poetry для создания виртуального окружения внутри проекта
ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock /app/

# Устанавливаем зависимости через Poetry
RUN poetry install --no-root --only main

# Копируем собранный фронтенд из предыдущего этапа
COPY --from=frontend /app/frontend/dist /app/static

# Копируем бэкенд-код
COPY backend/ /app/backend/
COPY start-prod.sh /app/start.sh
RUN chmod +x /app/start.sh

# Создаём непривилегированного пользователя
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Даём appuser доступ к файлам приложения и логам
RUN chown -R appuser:appgroup /app/backend/ /app/static/ /app/.venv/ \
    && mkdir -p /app/marking_logs && chown -R appuser:appgroup /app/marking_logs \
    && touch /app/user_actions.log && chown appuser:appgroup /app/user_actions.log

# Переключаемся на непривилегированного пользователя
USER appuser

# Открываем порт для бэкенда
EXPOSE 8001

# Команда запуска
CMD ["/app/start.sh"]
#!/bin/bash
# Запуск бэкенда в режиме production
cd /app && poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8001
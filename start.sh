#!/bin/bash
# Запуск бэкенда в режиме production
cd /app && uvicorn backend.main:app --host 0.0.0.0 --port 8001
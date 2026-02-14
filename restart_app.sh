#!/bin/bash
# Нужно для пересборки образа, не трогая бд

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для опроса пользователя
ask_yes_no() {
    while true; do
        read -p "$1 " yn
        case $yn in
            [Yy]* ) return 0;;  # Возвращает true
            [Nn]* ) return 1;;  # Возвращает false
            * ) echo "Пожалуйста, ответьте y (да) или n (нет).";;
        esac
    done
}

# Спрашиваем пользователя, нужно ли сохранить proxy_info.json из Docker
echo -e "${YELLOW}Хотите сохранить proxy_info.json из контейнера?${NC}"
if ask_yes_no "(y/n):"; then
    echo -e "${YELLOW}Удаляем локальный proxy_info.json...${NC}"
    rm -f proxy_info.json

    echo -e "${YELLOW}Копируем актуальный proxy_info.json из контейнера...${NC}"
    if docker cp mireapprove-app-new:/app/backend/proxy_info.json backend/proxy_info.json; then
        echo -e "${GREEN}Файл успешно скопирован!${NC}"
    else
        echo -e "${RED}Ошибка при копировании файла. Возможно, контейнер не запущен.${NC}"
        echo -e "${YELLOW}Продолжить перезапуск без сохранения proxy_info.json?${NC}"
        if ask_yes_no "(y/n):"; then
            echo -e "${YELLOW}Продолжаем без сохранения proxy_info.json...${NC}"
        else
            echo -e "${RED}Операция отменена.${NC}"
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}Пропускаем сохранение proxy_info.json из контейнера.${NC}"
fi

echo -e "${YELLOW}Останавливаем контейнеры...${NC}"
docker-compose stop

echo -e "${YELLOW}Удаляем контейнеры БЕЗ удаления томов...${NC}"
docker-compose rm -f

echo -e "${YELLOW}Пересобираем образы...${NC}"
docker-compose build --no-cache

echo -e "${YELLOW}Запускаем новые контейнеры...${NC}"
docker-compose up -d

# Ждем немного для стабилизации
sleep 2

# Проверка, что контейнеры запустились
if docker ps | grep -q "mireapprove-app-new"; then
    echo -e "\n${GREEN}┌────────────────────────────────────┐${NC}"
    echo -e "${GREEN}│                                    │${NC}"
    echo -e "${GREEN}│     Приложение перезапущено!       │${NC}"
    echo -e "${GREEN}│                                    │${NC}"
    echo -e "${GREEN}└────────────────────────────────────┘${NC}"

    echo -e "\n${BLUE}Анекдот дня:${NC}"
    echo -e "Программист спрашивает жену:
- Дорогая, что тебе подарить на день рождения?
- Ой, да мне ничего не надо...
Так и передал в Docker контейнер: FROM scratch"
else
    echo -e "\n${RED}Ошибка: контейнеры не запустились!${NC}"
    docker-compose logs app
fi

echo -e "\n${YELLOW}Для просмотра логов: ${NC}docker logs mireapprove-app-new"
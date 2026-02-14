#!/bin/bash

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                        MireApprove Installer v1.0                         ║
# ║                                                                           ║
# ║  Автоматический установщик системы учёта посещаемости МИРЭА               ║
# ║                                                                           ║
# ║  Использование:                                                           ║
# ║  bash <(curl -Ls https://raw.githubusercontent.com/lavka-enjoyer/lavka-attendance/main/install.sh)
# ║                                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

set -e

# ===== НАСТРОЙКИ РЕПОЗИТОРИЯ (измените при форке) =====
REPO_URL="https://github.com/lavka-enjoyer/lavka-attendance"
REPO_BRANCH="main"
# ======================================================

# ===== КОНСТАНТЫ =====
PROJECT_DIR="/opt/mireapprove"
LOG_DIR="/var/log/mireapprove"
INSTALL_LOG="$LOG_DIR/install.log"
UPDATE_LOG="$LOG_DIR/update.log"
VERSION="1.0.0"

# ===== ЦВЕТА =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color
BOLD='\033[1m'
DIM='\033[2m'

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
DOMAIN=""
BOT_TOKEN=""
BOT_USERNAME=""
SUPER_ADMIN=""
APP_PORT="8001"
POSTGRES_PASSWORD=""
ENCRYPTION_KEY=""
SERVER_IP=""
NEWS_CHANNEL_URL=""
DONATE_URL=""

# ===== UI ФУНКЦИИ =====

print_logo() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"

    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║    ███╗   ███╗██╗██████╗ ███████╗ █████╗ ██████╗ ██████╗      ║
    ║    ████╗ ████║██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗     ║
    ║    ██╔████╔██║██║██████╔╝█████╗  ███████║██████╔╝██████╔╝     ║
    ║    ██║╚██╔╝██║██║██╔══██╗██╔══╝  ██╔══██║██╔═══╝ ██╔═══╝      ║
    ║    ██║ ╚═╝ ██║██║██║  ██║███████╗██║  ██║██║     ██║          ║
    ║    ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝          ║
    ║                                                               ║
EOF
    echo -e "    ║              ${WHITE}Автоматический установщик v${VERSION}${CYAN}                ║"
    echo -e "    ║                                                               ║"
    echo -e "    ╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    local step=$1
    local total=$2
    local message=$3
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}${BOLD}  ШАГ ${step}/${total}: ${message}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}  ℹ $1${NC}"
}

print_dim() {
    echo -e "${DIM}    $1${NC}"
}

print_box() {
    local title=$1
    local emoji=$2
    echo -e "\n${PURPLE}╭─────────────────────────────────────────────────────────────────╮${NC}"
    echo -e "${PURPLE}│  ${emoji} ${WHITE}${BOLD}${title}${NC}${PURPLE}$(printf '%*s' $((58 - ${#title})) '')│${NC}"
    echo -e "${PURPLE}╰─────────────────────────────────────────────────────────────────╯${NC}\n"
}

print_separator() {
    echo -e "${GRAY}  ─────────────────────────────────────────────────────────────${NC}"
}

spinner() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0

    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) % 10 ))
        printf "\r${CYAN}  ${spin:$i:1} ${message}...${NC}"
        sleep 0.1
    done
    printf "\r"
}

ask_input() {
    local prompt=$1
    local default=$2
    local var_name=$3
    local secret=$4

    if [ -n "$default" ]; then
        echo -e "${WHITE}  ${prompt} ${DIM}[${default}]${NC}: \c"
    else
        echo -e "${WHITE}  ${prompt}: ${NC}\c"
    fi

    if [ "$secret" = "true" ]; then
        read -s input
        echo ""
    else
        read input
    fi

    if [ -z "$input" ] && [ -n "$default" ]; then
        input="$default"
    fi

    eval "$var_name=\"$input\""
}

ask_yes_no() {
    local prompt=$1
    local default=$2

    if [ "$default" = "y" ]; then
        echo -e "${WHITE}  ${prompt} ${DIM}[Y/n]${NC}: \c"
    else
        echo -e "${WHITE}  ${prompt} ${DIM}[y/N]${NC}: \c"
    fi

    read answer
    answer=${answer:-$default}

    case "$answer" in
        [Yy]* ) return 0;;
        * ) return 1;;
    esac
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$INSTALL_LOG"
}

# ===== ПРОВЕРКИ СИСТЕМЫ =====

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Этот скрипт должен быть запущен от имени root"
        echo -e "${YELLOW}  Используйте: sudo bash install.sh${NC}"
        exit 1
    fi
    print_success "Права root подтверждены"
}

check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION_ID=$VERSION_ID
    else
        print_error "Не удалось определить операционную систему"
        exit 1
    fi

    case "$OS" in
        ubuntu)
            if [[ "${VERSION_ID%%.*}" -lt 20 ]]; then
                print_error "Требуется Ubuntu 20.04 или новее (у вас $VERSION_ID)"
                exit 1
            fi
            print_success "Операционная система: Ubuntu $VERSION_ID"
            ;;
        debian)
            if [[ "${VERSION_ID%%.*}" -lt 10 ]]; then
                print_error "Требуется Debian 10 или новее (у вас $VERSION_ID)"
                exit 1
            fi
            print_success "Операционная система: Debian $VERSION_ID"
            ;;
        *)
            print_error "Неподдерживаемая ОС: $OS"
            echo -e "${YELLOW}  Поддерживаются: Ubuntu 20.04+, Debian 10+${NC}"
            exit 1
            ;;
    esac
}

check_architecture() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            print_success "Архитектура: x86_64 (AMD64)"
            ;;
        aarch64|arm64)
            print_success "Архитектура: ARM64"
            ;;
        *)
            print_error "Неподдерживаемая архитектура: $arch"
            exit 1
            ;;
    esac
}

check_disk_space() {
    local available=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available" -lt 2 ]; then
        print_error "Недостаточно места на диске (требуется минимум 2GB, доступно ${available}GB)"
        exit 1
    fi
    print_success "Свободное место: ${available}GB"
}

check_memory() {
    local total_mem=$(free -m | awk 'NR==2 {print $2}')
    if [ "$total_mem" -lt 512 ]; then
        print_warning "Мало оперативной памяти (${total_mem}MB). Рекомендуется минимум 1GB"
    else
        print_success "Оперативная память: ${total_mem}MB"
    fi
}

get_server_ip() {
    SERVER_IP=$(curl -s --max-time 10 https://api.ipify.org 2>/dev/null || \
                curl -s --max-time 10 https://ifconfig.me 2>/dev/null || \
                curl -s --max-time 10 https://icanhazip.com 2>/dev/null)

    if [ -z "$SERVER_IP" ]; then
        print_error "Не удалось определить внешний IP сервера"
        exit 1
    fi
    print_success "Внешний IP сервера: $SERVER_IP"
}

check_port() {
    local port=$1
    if ss -tuln 2>/dev/null | grep -q ":${port} " || netstat -tuln 2>/dev/null | grep -q ":${port} "; then
        return 1  # порт занят
    fi
    return 0  # порт свободен
}

find_free_port() {
    local ports=(8001 8002 8003 8004 8080 8081 3000 3001 9000 9001)
    for port in "${ports[@]}"; do
        if check_port "$port"; then
            echo "$port"
            return
        fi
    done
    echo ""
}

get_port_process() {
    local port=$1
    ss -tlnp 2>/dev/null | grep ":${port} " | awk '{print $NF}' | sed 's/.*"\(.*\)".*/\1/' | head -1
}

handle_port_conflict() {
    if ! check_port "$APP_PORT"; then
        local process=$(get_port_process "$APP_PORT")
        local free_port=$(find_free_port)

        print_box "ПОРТ $APP_PORT УЖЕ ЗАНЯТ" "⚠️"
        echo -e "  Порт ${YELLOW}$APP_PORT${NC} используется другим приложением."
        [ -n "$process" ] && echo -e "  Занят процессом: ${CYAN}$process${NC}"
        echo ""

        if [ -n "$free_port" ]; then
            echo -e "  ${GREEN}Свободные порты:${NC} $(find_free_ports_list)"
            echo ""
            ask_input "Введите альтернативный порт" "$free_port" "APP_PORT"

            # Проверяем новый порт
            if ! check_port "$APP_PORT"; then
                print_error "Порт $APP_PORT тоже занят!"
                exit 1
            fi
            print_success "Будет использован порт: $APP_PORT"
        else
            print_error "Не найдено свободных портов!"
            exit 1
        fi
    fi
}

find_free_ports_list() {
    local ports=(8001 8002 8003 8004 8080 8081 3000 3001)
    local free_ports=""
    for port in "${ports[@]}"; do
        if check_port "$port"; then
            [ -n "$free_ports" ] && free_ports+=", "
            free_ports+="$port"
        fi
    done
    echo "$free_ports"
}

# ===== УСТАНОВКА ЗАВИСИМОСТЕЙ =====

install_packages() {
    print_info "Обновление списка пакетов..."
    apt-get update -qq >> "$INSTALL_LOG" 2>&1

    local packages=(
        apt-transport-https
        ca-certificates
        curl
        gnupg
        lsb-release
        nginx
        certbot
        python3-certbot-nginx
        git
        openssl
        dnsutils
    )

    print_info "Установка необходимых пакетов..."
    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            apt-get install -y -qq "$pkg" >> "$INSTALL_LOG" 2>&1
            print_dim "Установлен: $pkg"
        fi
    done

    print_success "Все пакеты установлены"
}

install_docker() {
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version | awk '{print $3}' | tr -d ',')
        print_success "Docker уже установлен (v$docker_version)"
        return
    fi

    print_info "Установка Docker..."

    # Добавляем GPG ключ Docker
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Добавляем репозиторий
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq >> "$INSTALL_LOG" 2>&1
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin >> "$INSTALL_LOG" 2>&1

    systemctl start docker
    systemctl enable docker >> "$INSTALL_LOG" 2>&1

    print_success "Docker установлен"
}

# ===== ГЕНЕРАЦИЯ КЛЮЧЕЙ =====

generate_postgres_password() {
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
    print_success "Пароль PostgreSQL сгенерирован"
}

generate_encryption_key() {
    # Пробуем через Python (правильный Fernet ключ)
    if command -v python3 &> /dev/null; then
        ENCRYPTION_KEY=$(python3 -c "
try:
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())
except ImportError:
    import base64, os
    print(base64.urlsafe_b64encode(os.urandom(32)).decode())
" 2>/dev/null)
    fi

    # Fallback через openssl
    if [ -z "$ENCRYPTION_KEY" ]; then
        ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
    fi

    print_success "Ключ шифрования сгенерирован"
}

# ===== КОНФИГУРАТОР =====

configure_domain() {
    print_box "НАСТРОЙКА ДОМЕНА" "🌐"

    echo -e "  Для работы Telegram Mini App необходим домен с HTTPS."
    echo -e "  ${DIM}Пример: app.example.com или mireapprove.yourdomain.ru${NC}"
    echo ""

    while true; do
        ask_input "Введите домен" "" "DOMAIN"

        if [ -z "$DOMAIN" ]; then
            print_error "Домен не может быть пустым"
            continue
        fi

        # Убираем протокол если есть
        DOMAIN=$(echo "$DOMAIN" | sed 's|https\?://||' | sed 's|/.*||')

        # Простая валидация домена
        if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$ ]]; then
            print_error "Некорректный формат домена"
            continue
        fi

        break
    done

    print_success "Домен: $DOMAIN"
}

show_dns_instructions() {
    print_box "НАСТРОЙКА DNS" "📝"

    echo -e "  Создайте DNS запись для домена ${CYAN}$DOMAIN${NC}:"
    echo ""
    echo -e "  ${WHITE}┌──────────┬──────────────────────────┬──────────────────────────┐${NC}"
    echo -e "  ${WHITE}│${NC} ${BOLD}Тип${NC}      ${WHITE}│${NC} ${BOLD}Имя${NC}                      ${WHITE}│${NC} ${BOLD}Значение${NC}                 ${WHITE}│${NC}"
    echo -e "  ${WHITE}├──────────┼──────────────────────────┼──────────────────────────┤${NC}"

    # Определяем поддомен
    local subdomain=$(echo "$DOMAIN" | cut -d. -f1)
    local root_domain=$(echo "$DOMAIN" | cut -d. -f2-)

    if [ "$subdomain" = "$root_domain" ]; then
        echo -e "  ${WHITE}│${NC} A        ${WHITE}│${NC} @                        ${WHITE}│${NC} ${GREEN}$SERVER_IP${NC}               ${WHITE}│${NC}"
    else
        printf "  ${WHITE}│${NC} A        ${WHITE}│${NC} %-24s ${WHITE}│${NC} ${GREEN}%-24s${NC} ${WHITE}│${NC}\n" "$subdomain" "$SERVER_IP"
    fi

    echo -e "  ${WHITE}└──────────┴──────────────────────────┴──────────────────────────┘${NC}"
    echo ""
    echo -e "  ${DIM}Если домен уже указывает на этот сервер, просто нажмите Enter.${NC}"
    echo -e "  ${DIM}DNS записи обычно применяются за 5-10 минут.${NC}"
    echo ""
}

wait_for_dns() {
    print_info "Проверка DNS..."

    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        local domain_ip=$(dig +short "$DOMAIN" 2>/dev/null | tail -1)

        if [ "$domain_ip" = "$SERVER_IP" ]; then
            print_success "DNS настроен правильно!"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            echo ""
            echo -e "  ${YELLOW}DNS пока не применился${NC}"
            echo -e "  IP сервера:  ${GREEN}$SERVER_IP${NC}"
            echo -e "  IP домена:   ${RED}${domain_ip:-не найден}${NC}"
            echo ""

            if ask_yes_no "Повторить проверку?" "y"; then
                ((attempt++))
                echo -e "  ${DIM}Ожидание 10 секунд...${NC}"
                sleep 10
            else
                print_warning "Продолжаем без проверки DNS. SSL может не сработать!"
                return 0
            fi
        else
            print_warning "DNS проверка не пройдена, но продолжаем установку"
            return 0
        fi
    done
}

configure_telegram() {
    print_box "НАСТРОЙКА TELEGRAM БОТА" "🤖"

    echo -e "  Для работы приложения нужен Telegram бот."
    echo -e "  Если у вас его нет, создайте бота:"
    echo ""
    echo -e "  ${CYAN}1.${NC} Откройте ${WHITE}@BotFather${NC} в Telegram"
    echo -e "  ${CYAN}2.${NC} Отправьте ${WHITE}/newbot${NC}"
    echo -e "  ${CYAN}3.${NC} Следуйте инструкциям"
    echo -e "  ${CYAN}4.${NC} Скопируйте токен бота"
    echo ""
    print_separator
    echo ""

    # BOT_TOKEN
    while true; do
        ask_input "Токен бота (от @BotFather)" "" "BOT_TOKEN"

        if [ -z "$BOT_TOKEN" ]; then
            print_error "Токен не может быть пустым"
            continue
        fi

        # Простая валидация токена (формат: 123456789:ABC-DEF...)
        if [[ ! "$BOT_TOKEN" =~ ^[0-9]+:.+$ ]]; then
            print_error "Неверный формат токена"
            continue
        fi

        break
    done

    # BOT_USERNAME
    while true; do
        ask_input "Юзернейм бота (без @)" "" "BOT_USERNAME"

        if [ -z "$BOT_USERNAME" ]; then
            print_error "Юзернейм не может быть пустым"
            continue
        fi

        # Убираем @ если есть
        BOT_USERNAME=$(echo "$BOT_USERNAME" | sed 's/^@//')
        break
    done

    print_success "Бот: @$BOT_USERNAME"
}

configure_admin() {
    print_box "НАСТРОЙКА АДМИНИСТРАТОРА" "👤"

    echo -e "  Укажите Telegram ID администратора."
    echo -e "  ${DIM}Узнать свой ID можно у бота @userinfobot${NC}"
    echo ""

    while true; do
        ask_input "Telegram ID администратора" "" "SUPER_ADMIN"

        if [ -z "$SUPER_ADMIN" ]; then
            print_error "ID не может быть пустым"
            continue
        fi

        # Проверка что это число
        if ! [[ "$SUPER_ADMIN" =~ ^[0-9]+$ ]]; then
            print_error "ID должен содержать только цифры"
            continue
        fi

        break
    done

    print_success "Администратор: $SUPER_ADMIN"
}

configure_optional() {
    print_box "ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ (опционально)" "⚙️"

    echo -e "  ${DIM}Нажмите Enter чтобы пропустить${NC}"
    echo ""

    ask_input "Ссылка на канал новостей" "" "NEWS_CHANNEL_URL"
    ask_input "Ссылка на донат" "" "DONATE_URL"

    echo ""
}

# ===== SSL =====

obtain_ssl_certificate() {
    print_box "ПОЛУЧЕНИЕ SSL СЕРТИФИКАТА" "🔒"

    echo -e "  ${YELLOW}SSL сертификат ОБЯЗАТЕЛЕН для работы Telegram Mini App!${NC}"
    echo -e "  ${DIM}Без HTTPS бот не сможет открыть веб-приложение.${NC}"
    echo ""

    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        print_info "Попытка $attempt из $max_attempts..."

        # Останавливаем nginx если запущен
        systemctl stop nginx 2>/dev/null || true

        # Получаем сертификат в standalone режиме
        if certbot certonly --standalone \
            --non-interactive \
            --agree-tos \
            --register-unsafely-without-email \
            --domains "$DOMAIN" \
            >> "$INSTALL_LOG" 2>&1; then

            print_success "SSL сертификат получен!"

            # Настраиваем автообновление сертификатов
            setup_ssl_auto_renewal

            return 0
        fi

        # Ошибка получения сертификата
        echo ""
        print_error "Не удалось получить SSL сертификат"
        echo ""

        local domain_ip=$(dig +short "$DOMAIN" 2>/dev/null | tail -1)

        echo -e "  ${WHITE}┌─────────────────────────────────────────────────────────┐${NC}"
        echo -e "  ${WHITE}│${NC} IP сервера:   ${GREEN}$SERVER_IP${NC}$(printf '%*s' $((32 - ${#SERVER_IP})) '')${WHITE}│${NC}"
        if [ "$domain_ip" = "$SERVER_IP" ]; then
            echo -e "  ${WHITE}│${NC} IP домена:    ${GREEN}$domain_ip${NC} ${GREEN}✓${NC}$(printf '%*s' $((29 - ${#domain_ip})) '')${WHITE}│${NC}"
        else
            echo -e "  ${WHITE}│${NC} IP домена:    ${RED}${domain_ip:-не найден}${NC} ${RED}← Не совпадает!${NC}$(printf '%*s' $((14 - ${#domain_ip})) '')${WHITE}│${NC}"
        fi
        echo -e "  ${WHITE}└─────────────────────────────────────────────────────────┘${NC}"
        echo ""

        echo -e "  Возможные причины:"
        echo -e "  ${DIM}• DNS записи ещё не применились (может занять от 5 минут до 48 часов)${NC}"
        echo -e "  ${DIM}• Порт 80 заблокирован файрволом${NC}"
        echo -e "  ${DIM}• Домен указывает на другой IP${NC}"
        echo ""

        echo -e "  ${YELLOW}⚠️  SSL ОБЯЗАТЕЛЕН для работы Telegram Mini App!${NC}"
        echo ""

        echo -e "  Варианты:"
        echo -e "  ${WHITE}[1]${NC} Повторить попытку"
        echo -e "  ${WHITE}[2]${NC} Выйти и попробовать позже"
        echo ""

        read -p "  Выберите (1-2): " choice

        case "$choice" in
            1)
                ((attempt++))
                echo -e "  ${DIM}Ожидание 30 секунд перед повторной попыткой...${NC}"
                sleep 30
                ;;
            2|*)
                echo ""
                print_error "Установка прервана"
                echo -e "  ${YELLOW}Убедитесь что DNS записи настроены правильно и повторите установку.${NC}"
                exit 1
                ;;
        esac
    done

    print_error "Не удалось получить SSL сертификат после $max_attempts попыток"
    exit 1
}

setup_ssl_auto_renewal() {
    print_info "Настройка автообновления SSL сертификатов..."

    # Certbot автоматически создаёт таймер, но убедимся что он активен
    if systemctl list-timers | grep -q "certbot"; then
        systemctl enable certbot.timer >> "$INSTALL_LOG" 2>&1
        systemctl start certbot.timer >> "$INSTALL_LOG" 2>&1
        print_success "Автообновление SSL включено (certbot.timer)"
    else
        # Создаём свой таймер если certbot не создал
        cat > /etc/systemd/system/certbot-renewal.timer << EOF
[Unit]
Description=Certbot SSL renewal timer

[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF

        cat > /etc/systemd/system/certbot-renewal.service << EOF
[Unit]
Description=Certbot SSL renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx"
EOF

        systemctl daemon-reload
        systemctl enable certbot-renewal.timer >> "$INSTALL_LOG" 2>&1
        systemctl start certbot-renewal.timer >> "$INSTALL_LOG" 2>&1
        print_success "Автообновление SSL настроено (certbot-renewal.timer)"
    fi

    log "SSL auto-renewal configured"
}

# ===== NGINX =====

configure_nginx() {
    print_info "Настройка Nginx..."

    local nginx_config="/etc/nginx/sites-available/mireapprove-$DOMAIN"
    local nginx_enabled="/etc/nginx/sites-enabled/mireapprove-$DOMAIN"

    cat > "$nginx_config" << EOF
# MireApprove configuration for $DOMAIN
# Автоматически создано установщиком $(date '+%Y-%m-%d %H:%M:%S')

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Ancestors "https://web.telegram.org https://t.me";

    client_max_body_size 20M;

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Telegram webhook
    location /telegram/ {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
    }

    # Static files with caching
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Frontend (SPA fallback)
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

    # Создаём симлинк
    ln -sf "$nginx_config" "$nginx_enabled"

    # Проверяем конфигурацию
    if nginx -t >> "$INSTALL_LOG" 2>&1; then
        systemctl restart nginx
        print_success "Nginx настроен для домена $DOMAIN"
    else
        print_error "Ошибка в конфигурации Nginx"
        nginx -t
        exit 1
    fi
}

# ===== УСТАНОВКА ПРИЛОЖЕНИЯ =====

clone_repository() {
    print_info "Клонирование репозитория..."

    if [ -d "$PROJECT_DIR/.git" ]; then
        print_info "Репозиторий уже существует, обновляем..."
        cd "$PROJECT_DIR"
        git fetch origin >> "$INSTALL_LOG" 2>&1
        git reset --hard "origin/$REPO_BRANCH" >> "$INSTALL_LOG" 2>&1
    else
        rm -rf "$PROJECT_DIR"
        git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$PROJECT_DIR" >> "$INSTALL_LOG" 2>&1
    fi

    print_success "Репозиторий загружен"
}

create_env_file() {
    print_info "Создание конфигурации..."

    cat > "$PROJECT_DIR/.env" << EOF
# MireApprove Configuration
# Автоматически создано установщиком $(date '+%Y-%m-%d %H:%M:%S')

# Database
POSTGRES_DB=mireapprove
POSTGRES_USER=mireapprove
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_PORT=5432

# App connection
DSN=postgresql://mireapprove:$POSTGRES_PASSWORD@postgres/mireapprove

# Security
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Telegram Bot
BOT_TOKEN=$BOT_TOKEN
BOT_USERNAME=$BOT_USERNAME

# Admin
SUPER_ADMIN=$SUPER_ADMIN

# Redis
REDIS_URL=redis://redis:6379/0

# App port
APP_PORT=$APP_PORT

# External URLs
WEBAPP_URL=https://$DOMAIN/
${NEWS_CHANNEL_URL:+NEWS_CHANNEL_URL=$NEWS_CHANNEL_URL}
${DONATE_URL:+DONATE_URL=$DONATE_URL}
IP_CHECK_URL=https://api.ipify.org?format=json

# Frontend
VITE_API_URL=https://$DOMAIN
VITE_ALLOWED_HOSTS=$DOMAIN
EOF

    chmod 600 "$PROJECT_DIR/.env"
    print_success "Конфигурация создана"
}

update_docker_compose_port() {
    # Если порт изменён, обновляем docker-compose.yml
    if [ "$APP_PORT" != "8001" ]; then
        print_info "Обновление порта в docker-compose.yml..."
        sed -i "s/8001:8001/$APP_PORT:8001/g" "$PROJECT_DIR/docker-compose.yml"
        print_success "Порт обновлён на $APP_PORT"
    fi
}

# ===== АВТООБНОВЛЕНИЕ =====

setup_auto_update() {
    print_info "Настройка автообновления..."

    # Создаём скрипт обновления
    cat > "$PROJECT_DIR/update.sh" << 'EOF'
#!/bin/bash

# MireApprove Auto-Update Script
LOG_FILE="/var/log/mireapprove/update.log"
PROJECT_DIR="/opt/mireapprove"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cd "$PROJECT_DIR" || { log "ERROR: Cannot cd to $PROJECT_DIR"; exit 1; }

log "Проверка обновлений..."

# Получаем изменения
git fetch origin 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Обновлений нет"
    exit 0
fi

log "Найдено обновление: ${LOCAL:0:7} -> ${REMOTE:0:7}"

# Сохраняем .env
cp .env .env.backup

# Получаем обновления
log "Загрузка обновлений..."
git pull origin main

# Восстанавливаем .env
mv .env.backup .env

# Пересобираем контейнеры
log "Пересборка контейнеров..."
docker compose build --no-cache

# Перезапускаем
log "Перезапуск приложения..."
docker compose up -d

log "Обновление завершено успешно"
EOF

    chmod +x "$PROJECT_DIR/update.sh"

    # Создаём systemd service
    cat > /etc/systemd/system/mireapprove-update.service << EOF
[Unit]
Description=MireApprove Auto-Update
After=network.target docker.service

[Service]
Type=oneshot
ExecStart=$PROJECT_DIR/update.sh
WorkingDirectory=$PROJECT_DIR
StandardOutput=append:$UPDATE_LOG
StandardError=append:$UPDATE_LOG
EOF

    # Создаём systemd timer
    cat > /etc/systemd/system/mireapprove-update.timer << EOF
[Unit]
Description=MireApprove Daily Update Check

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=1800
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    systemctl enable mireapprove-update.timer >> "$INSTALL_LOG" 2>&1
    systemctl start mireapprove-update.timer >> "$INSTALL_LOG" 2>&1

    print_success "Автообновление настроено (каждый день в 04:00)"
}

# ===== SYSTEMD СЕРВИС =====

create_systemd_service() {
    print_info "Создание системного сервиса..."

    cat > /etc/systemd/system/mireapprove.service << EOF
[Unit]
Description=MireApprove Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable mireapprove >> "$INSTALL_LOG" 2>&1

    print_success "Системный сервис создан"
}

# ===== ЗАПУСК =====

start_application() {
    print_info "Запуск приложения..."

    cd "$PROJECT_DIR"

    # Собираем образы
    print_dim "Сборка Docker образов (это может занять несколько минут)..."
    docker compose build >> "$INSTALL_LOG" 2>&1 &
    spinner $! "Сборка образов"
    print_success "Образы собраны"

    # Запускаем контейнеры
    print_dim "Запуск контейнеров..."
    docker compose up -d >> "$INSTALL_LOG" 2>&1

    # Ждём запуска
    sleep 5

    # Проверяем что всё работает
    local max_attempts=30
    local attempt=1

    print_dim "Ожидание готовности приложения..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://127.0.0.1:$APP_PORT/health" > /dev/null 2>&1; then
            print_success "Приложение запущено и работает!"
            return 0
        fi
        sleep 2
        ((attempt++))
    done

    print_warning "Приложение запускается дольше обычного"
    print_dim "Проверьте логи: docker compose logs -f"
}

# ===== ФИНАЛЬНЫЙ ВЫВОД =====

print_completion() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                    ${WHITE}${BOLD}✅ УСТАНОВКА ЗАВЕРШЕНА!${NC}                    ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🌐 Web-приложение: ${CYAN}https://$DOMAIN${NC}$(printf '%*s' $((38 - ${#DOMAIN})) '')${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🤖 Telegram бот:   ${CYAN}@$BOT_USERNAME${NC}$(printf '%*s' $((40 - ${#BOT_USERNAME})) '')${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  👤 Администратор:  ${CYAN}$SUPER_ADMIN${NC}$(printf '%*s' $((40 - ${#SUPER_ADMIN})) '')${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  ${WHITE}${BOLD}Полезные команды:${NC}                                            ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  📋 Логи:     ${DIM}cd $PROJECT_DIR && docker compose logs -f${NC}   ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🔄 Рестарт:  ${DIM}systemctl restart mireapprove${NC}                ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ⏹  Стоп:     ${DIM}systemctl stop mireapprove${NC}                   ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  📊 Статус:   ${DIM}systemctl status mireapprove${NC}                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🔒 SSL:      ${DIM}Автообновление включено${NC}                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  ⬆️  Обновл.: ${DIM}Автоматически каждый день в 04:00${NC}            ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  ${WHITE}${BOLD}Следующие шаги:${NC}                                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  1. Откройте бота ${CYAN}@$BOT_USERNAME${NC} в Telegram$(printf '%*s' $((26 - ${#BOT_USERNAME})) '')${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  2. Настройте Mini App в @BotFather:                          ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}     ${DIM}/mybots → @$BOT_USERNAME → Bot Settings →${NC}$(printf '%*s' $((19 - ${#BOT_USERNAME})) '')${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}     ${DIM}Menu Button → Configure → https://$DOMAIN${NC}$(printf '%*s' $((9 - ${#DOMAIN})) '')${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  3. Отправьте боту ${CYAN}/start${NC}                                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log "Installation completed successfully"
}

# ===== MAIN =====

main() {
    # Создаём директорию для логов
    mkdir -p "$LOG_DIR"
    touch "$INSTALL_LOG"
    log "=== Installation started ==="

    # Выводим логотип
    print_logo

    echo -e "  ${DIM}Добро пожаловать в установщик MireApprove!${NC}"
    echo -e "  ${DIM}Этот скрипт автоматически настроит всё необходимое.${NC}"
    echo ""

    if ! ask_yes_no "Начать установку?" "y"; then
        echo -e "\n  ${YELLOW}Установка отменена${NC}\n"
        exit 0
    fi

    # ===== ШАГ 1: Проверка системы =====
    print_step 1 7 "ПРОВЕРКА СИСТЕМЫ"

    check_root
    check_os
    check_architecture
    check_disk_space
    check_memory
    get_server_ip

    log "System check passed"

    # ===== ШАГ 2: Установка зависимостей =====
    print_step 2 7 "УСТАНОВКА ЗАВИСИМОСТЕЙ"

    install_packages
    install_docker

    log "Dependencies installed"

    # ===== ШАГ 3: Конфигурация =====
    print_step 3 7 "НАСТРОЙКА КОНФИГУРАЦИИ"

    configure_domain
    show_dns_instructions

    echo -e "  ${WHITE}Нажмите Enter после настройки DNS записей...${NC}"
    read

    wait_for_dns
    configure_telegram
    configure_admin
    configure_optional

    # Генерируем секреты
    generate_postgres_password
    generate_encryption_key

    # Проверяем порт
    handle_port_conflict

    log "Configuration completed"

    # ===== ШАГ 4: SSL сертификат =====
    print_step 4 7 "ПОЛУЧЕНИЕ SSL СЕРТИФИКАТА"

    obtain_ssl_certificate

    log "SSL certificate obtained"

    # ===== ШАГ 5: Nginx =====
    print_step 5 7 "НАСТРОЙКА NGINX"

    configure_nginx

    log "Nginx configured"

    # ===== ШАГ 6: Установка приложения =====
    print_step 6 7 "УСТАНОВКА ПРИЛОЖЕНИЯ"

    clone_repository
    create_env_file
    update_docker_compose_port
    setup_auto_update
    create_systemd_service

    log "Application installed"

    # ===== ШАГ 7: Запуск =====
    print_step 7 7 "ЗАПУСК ПРИЛОЖЕНИЯ"

    start_application

    log "Application started"

    # ===== Завершение =====
    print_completion
}

# Запускаем
main "$@"

#!/bin/bash
set -e

# ── Цвета ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Проверка .env ──────────────────────────────────────────────────────────
[ -f .env ] || error ".env не найден. Скопируй: cp .env.example .env && nano .env"

export $(grep -v '^#' .env | xargs)

[ -z "$DOMAIN" ]      && error "DOMAIN не задан в .env"
[ -z "$BOT_TOKEN" ]   && error "BOT_TOKEN не задан в .env"
[ -z "$ADMIN_EMAIL" ] && error "ADMIN_EMAIL не задан в .env"

info "Домен: $DOMAIN"

# ── Установка зависимостей ─────────────────────────────────────────────────
info "Проверка зависимостей..."
if ! command -v docker &> /dev/null; then
    warn "Устанавливаю Docker..."
    curl -fsSL https://get.docker.com | sh
fi
if ! command -v certbot &> /dev/null; then
    warn "Устанавливаю certbot..."
    apt-get update -qq && apt-get install -y -qq certbot
fi

# ── SSL сертификат ─────────────────────────────────────────────────────────
if [ ! -f "certs/fullchain.crt" ]; then
    info "Получаю SSL сертификат для $DOMAIN..."

    # Останавливаем всё что занимает порт 80
    docker stop arkadium-nginx 2>/dev/null || true
    fuser -k 80/tcp 2>/dev/null || true

    certbot certonly --standalone \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        -m "$ADMIN_EMAIL"

    mkdir -p certs
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem certs/fullchain.crt
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem   certs/privkey.key
    chmod 644 certs/fullchain.crt certs/privkey.key
    info "Сертификат получен!"
else
    info "Сертификат уже есть, пропускаю..."
fi

# ── Генерация nginx конфига ────────────────────────────────────────────────
info "Генерирую nginx конфиг..."
sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx/nginx.template.conf > nginx/nginx.conf
info "nginx.conf создан для $DOMAIN"

# ── Запуск контейнеров ─────────────────────────────────────────────────────
info "Собираю и запускаю контейнеры..."
docker compose up -d --build

# ── Готово ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Аркадиум запущен!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  🌐 Мини-апп:  https://$DOMAIN"
echo -e "  🛠 Админка:   https://$DOMAIN/#/admin/login"
echo -e "  📚 API docs:  https://$DOMAIN/api/docs"
echo -e "  🔑 Логин:     ${PANEL_USERNAME:-admin} / ${PANEL_PASSWORD:-arkadium2026}"
echo ""

#!/usr/bin/env bash
# Обновить «официальную» обёртку WebApp (при смене API Telegram)
set -euo pipefail
cd "$(dirname "$0")/.."
curl -fsSL "https://telegram.org/js/telegram-web-app.js" -o public/telegram-web-app.js
echo "OK: $(wc -c < public/telegram-web-app.js) bytes"

#!/usr/bin/env bash
# Склейка из корня репо: серверный.crt + chain CA → fullchain; ключ → privkey.key
# Папка certs_2/ — как у тебя сейчас (имена с пробелами и скобками).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${REPO_ROOT}/certs_2"
OUT="${REPO_ROOT}/certs/arkadium"
LEAF="${SRC}/certificate (2).crt"
CHAIN="${SRC}/certificate_ca (2).crt"
KEY="${SRC}/certificate (3).key"

for f in "$LEAF" "$CHAIN" "$KEY"; do
  if [[ ! -f "$f" ]]; then
    echo "Нет файла: $f" >&2
    exit 1
  fi
done

mkdir -p "$OUT"
# Порядок: leaf, затем промежуточный/цепочка (Nginx, браузеры)
cat "$LEAF" "$CHAIN" > "${OUT}/fullchain.crt"
cp -f "$KEY" "${OUT}/privkey.key"
chmod 644 "${OUT}/fullchain.crt"
chmod 600 "${OUT}/privkey.key"
echo "Готово: ${OUT}/fullchain.crt и privkey.key"
echo "Заливка на сервер (подставь хост/пользователя):"
echo "  scp ${OUT}/fullchain.crt ${OUT}/privkey.key user@it-vmmini:~/infra/certs/arkadium/"

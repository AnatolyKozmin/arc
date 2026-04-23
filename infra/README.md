# Infra: edge-nginx на 80/443 (папка рядом с репозиторием приложения)

Сейчас в доке — **один сайт (Arkadium)**, сертификат в `certs/arkadium/`. Второй домен/проект — см. [examples/optional](examples/optional).

Структура на сервере (типично):

```text
/srv/   (или любой корень)
├── infra/                 ← edge-nginx, только 80/443
│   ├── docker-compose.yml
│   ├── nginx.conf         ← из примера, не в git; живой файл
│   └── certs/
│       └── arkadium/      ← fullchain.crt + privkey.key
└── arc/                    ← репозиторий Arkadium (compose приложения)
```

Сеть Docker **`arkadium_shared`** (создать один раз) — должна быть у edge-nginx и у контейнеров приложения.

---

## Куда класть сертификат

Один комплект **Arkadium** (имена совпадают с путями в [examples/nginx.arkadium-only.conf](examples/nginx.arkadium-only.conf)):

```text
infra/certs/arkadium/
    fullchain.crt
    privkey.key
```

### Склейка из `certs_2` (Reg.ru / «сертификат + CA + ключ»)

В репо: [`scripts/build-arkadium-certs-from-certs2.sh`](scripts/build-arkadium-certs-from-certs2.sh) — собирает `certs/arkadium/fullchain.crt` (leaf + `certificate_ca`) и `privkey.key`. Запуск с корня репозитория:

```bash
./infra/scripts/build-arkadium-certs-from-certs2.sh
```

Папка `certs_2` в **`.gitignore`**; не коммить ключи.

### С локального ПК на сервер (`scp`)

```bash
scp fullchain.pem root@SERVER:~/infra/certs/arkadium/fullchain.crt
scp privkey.pem   root@SERVER:~/infra/certs/arkadium/privkey.key
```

Или после скрипта:

```bash
scp certs/arkadium/fullchain.crt certs/arkadium/privkey.key root@SERVER:~/infra/certs/arkadium/
```

На **сервере**:

```bash
chmod 644 ~/infra/certs/arkadium/fullchain.crt
chmod 600 ~/infra/certs/arkadium/privkey.key
```

### Уже выдан Let’s Encrypt на этой машине

```bash
sudo cp /etc/letsencrypt/live/ВАШ-ДОМЕН/fullchain.pem ~/infra/certs/arkadium/fullchain.crt
sudo cp /etc/letsencrypt/live/ВАШ-ДОМЕН/privkey.pem   ~/infra/certs/arkadium/privkey.key
sudo chmod 644 ~/infra/certs/arkadium/fullchain.crt
sudo chmod 600 ~/infra/certs/arkadium/privkey.key
```

`docker compose` в `infra/` монтирует **`./certs` → `/etc/nginx/certs`** в контейнере; пути `ssl_certificate` в примере менять не нужно, если кладёшь файлы в `certs/arkadium/`.

### Новый домен и срок сертификата

1. **DNS** — A (и при необходимости AAAA) на IP сервера.
2. **Сертификат** (например `certbot certonly --standalone -d 'ДОМЕН' -d 'www.ДОМЕН'`) — на время standalone освободи **:80** (например `cd ~/infra && docker compose stop`).
3. Скопируй `fullchain` и `privkey` в `~/infra/certs/arkadium/`, как выше.
4. **nginx:** скопируй [examples/nginx.arkadium-only.conf](examples/nginx.arkadium-only.conf) в `~/infra/nginx.conf` (там уже **febnik.ru** / **www**; для другого домена — правь `server_name`).
5. **Приложение Arkadium:** в корневом **`.env`** — `DOMAIN=ваш-новый.домен` (без `https://`); пересоздай с env: `docker compose up -d --force-recreate backend bot`.
6. **Telegram** (@BotFather): URL мини-аппа `https://ваш-домен/…`
7. **Перезагрузка edge-nginx:** `cd ~/infra && docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload`

Проверка срока:  
`echo | openssl s_client -connect ДОМЕН:443 -servername ДОМЕН 2>/dev/null | openssl x509 -noout -dates`

---

## Сеть Docker

```bash
docker network create arkadium_shared
```

В `docker-compose.yml` репозитория приложения — сеть `arkadium_shared` как `external: true` (см. корневой compose Arkadium).

---

## Запустить edge-nginx

Каталог — **`~/infra/`** (где `docker-compose.yml` из репо).

1. Скопируй сюда `docker-compose.yml` из репозитория, если ещё нет.
2. Собери `nginx.conf` — проще всего: скопируй [examples/nginx.arkadium-only.conf](examples/nginx.arkadium-only.conf) в `~/infra/nginx.conf` и сделай `sed` с `__ARKADIUM_DOMAIN__` (см. выше). Старый путь с `nginx.template.conf` + большой `sed` по плейсхолдерам не обязателен, если используешь готовый пример.
3. Проверка: `docker compose exec nginx nginx -t` (из `~/infra`).
4. Старт: `docker compose up -d`  
5. После правок: `docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload`

На время **certbot --standalone** порт 80 у edge освободи: `docker compose stop` в `~/infra`, затем снова `docker compose up -d`.

---

## Чеклист (один сайт)

1. `docker network create arkadium_shared` (если ещё нет)
2. Поднять Arkadium (compose из репо) в сети `arkadium_shared` без публикации 80/443 (их занимает infra)
3. `~/infra/certs/arkadium/{fullchain.crt,privkey.key}`
4. `~/infra/nginx.conf` = копия [nginx.arkadium-only.conf](examples/nginx.arkadium-only.conf) (домен febnik.ru)
5. `cd ~/infra && docker compose up -d`

Два домена (Arkadium + febnik) — только если понадобится: [examples/optional](examples/optional).

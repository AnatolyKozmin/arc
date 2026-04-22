# Один сервер, несколько доменов (Docker)

Один **edge-nginx** на **80/443** раздаёт трафик по `server_name` на **разные контейнеры** в одной Docker-сети **`arkadium_shared`**. Сами приложения могут быть из **разных** репозиториев и с **разным** `docker-compose`.

## Разные репозитории (например Arkadium + febnik.ru)

Папка **`deploy/multi-site/`** есть **только в репозитории Arkadium**. В проект febnik её **копировать не нужно**.

| Сайт | Откуда compose | Сеть |
|------|----------------|------|
| **Arkadium** | этот репо: `deploy/multi-site/docker-compose.apps-only.yml` | `arkadium_shared` (external) |
| **Febnik** (или любой другой) | **свой** `docker-compose.yml` в репо febnik | та же **`arkadium_shared`** как `external: true` |

У сервиса, куда edge-nginx проксирует запросы (фронт, встроенный nginx приложения и т.д.), задайте стабильный **`container_name`** (например `febnik-web`) и используйте это имя во втором блоке `server` в `reverse-proxy/nginx.conf` в `proxy_pass`.

Каталог **`reverse-proxy/`** на сервере можно держать **один раз** отдельно от обоих репозиториев — это только edge-nginx, сертификаты и сгенерированный `nginx.conf`.

## Ваш расклад (пример имён для Arkadium)

| Слот | Домен | Пример `SITE_SLUG` (только Arkadium) | Где код |
|------|--------|-------------------------------------|---------|
| 1 | хост Arkadium | `site1` | репозиторий Arkadium |
| 2 | febnik.ru | — | **другой** репозиторий, свои имена контейнеров в nginx |
| 3 | третий домен | `site3` или свои имена | свой репо / клон |

У Arkadium — **свой** `BOT_TOKEN`, БД и т.д. У febnik — полностью **своя** конфигурация; общее только **сеть Docker** и **один** edge-nginx на портах 80/443.

---

## 1. Сеть (один раз)

```bash
docker network create arkadium_shared
```

---

## 2. Стеки приложений

### Arkadium

Из **корня** клона репозитория Arkadium, со своим `.env` (`DOMAIN`, `SITE_SLUG`, `BOT_TOKEN`, …):

```bash
docker compose --env-file .env -f deploy/multi-site/docker-compose.apps-only.yml up -d --build
```

Появятся контейнеры вида `arkadium-${SITE_SLUG}-frontend` / `…-backend` — **эти** имена подставляете в первый блок `server` в edge-nginx (слот site1 в шаблонах).

### Febnik (другой сайт)

В каталоге репозитория febnik — **ваш** обычный `docker compose up`. В `docker-compose.yml` добавьте подключение к уже созданной сети:

```yaml
networks:
  arkadium_shared:
    external: true
    name: arkadium_shared
```

И у нужных сервисов: `networks: [arkadium_shared]` плюс **`container_name`** (у febnik сейчас **`febnik`** — он же в `SITE2_UPSTREAM` для nginx).

**Пока третьего сайта нет:** для edge-nginx достаточно шаблона **на два домена** (`nginx.template.2sites.conf`); во втором `server` вместо `arkadium-site2-*` укажите реальные имена контейнеров **febnik**.

---

## 3. Сертификаты для edge-nginx

Каталог: `deploy/multi-site/reverse-proxy/certs/`

```text
certs/site1/fullchain.crt   certs/site1/privkey.key   ← домен Arkadium (полный FQDN)
certs/site2/fullchain.crt   certs/site2/privkey.key   ← febnik.ru
certs/site3/…               ← когда появится третий домен
```

Let’s Encrypt (порт 80 на время выпуска должен быть свободен, edge-nginx лучше остановить):

```bash
certbot certonly --standalone -d ВАШ-ARKADIUM-ХОСТ -m ваш@email --agree-tos
# скопировать в certs/site1/

certbot certonly --standalone -d febnik.ru -m ваш@email --agree-tos
# скопировать в certs/site2/
```

---

## 4. Конфиг nginx

Шаблоны в `reverse-proxy/`:

| Файл | Когда |
|------|--------|
| `nginx.template.2sites.conf` | **Сейчас:** только Arkadium + febnik.ru |
| `nginx.template.conf` | **Три** домена, когда поднят третий стек и есть `certs/site3/` |

### Сейчас (два домена)

Подставьте **реальный** хост Arkadium вместо `arkadium.putevod-ik.ru`, если он другой:

```bash
cd deploy/multi-site/reverse-proxy

sed -e 's/SITE1_DOMAIN/arkadium.putevod-ik.ru/g' \
    -e 's/SITE2_DOMAIN/febnik.ru/g' \
    -e 's/SITE1_FRONTEND/arkadium-site1-frontend/g' \
    -e 's/SITE1_BACKEND/arkadium-site1-backend/g' \
    -e 's/SITE2_UPSTREAM/febnik:8080/g' \
    nginx.template.2sites.conf > nginx.conf
```

`SITE2_UPSTREAM` — это **`container_name:порт`** febnik (сейчас `febnik:8080`). Если переименуете контейнер или порт — поправьте в `sed`.

Имена `arkadium-site1-…` должны совпадать с `SITE_SLUG` в `.env` Arkadium (например `site1`).

Запуск edge:

```bash
docker compose up -d
```

### Когда появится третий домен

1. Третий каталог, `.env` с `DOMAIN=новый.домен`, `SITE_SLUG=site3`, свой бот и т.д.  
2. `docker compose … docker-compose.apps-only.yml up -d --build`  
3. Сертификаты в `certs/site3/`  
4. Пересобрать конфиг из **`nginx.template.conf`** (там три слота), например:

```bash
sed -e 's/SITE1_DOMAIN/arkadium.putevod-ik.ru/g' \
    -e 's/SITE2_DOMAIN/febnik.ru/g' \
    -e 's/SITE3_DOMAIN/третий-домен.ru/g' \
    -e 's/SITE1_FRONTEND/arkadium-site1-frontend/g' \
    -e 's/SITE1_BACKEND/arkadium-site1-backend/g' \
    -e 's/SITE2_UPSTREAM/febnik:8080/g' \
    -e 's/SITE3_FRONTEND/arkadium-site3-frontend/g' \
    -e 's/SITE3_BACKEND/arkadium-site3-backend/g' \
    nginx.template.conf > nginx.conf

docker compose exec nginx nginx -s reload
# или docker compose up -d --force-recreate
```

---

## 5. Порядок запуска

1. `docker network create arkadium_shared`  
2. Поднять все нужные стеки `docker-compose.apps-only.yml`  
3. Положить сертификаты в `reverse-proxy/certs/site…`  
4. Сгенерировать `reverse-proxy/nginx.conf` и `docker compose up -d` в `reverse-proxy/`

Не поднимайте корневой `docker-compose.yml` с встроенным nginx на тех же 80/443 — конфликт портов.

---

## Два сайта из одного клона репозитория

Возможно, но легко перепутать volume и `.env`. Надёжнее **отдельные каталоги** на каждый домен.

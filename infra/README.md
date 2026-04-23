# Infra: nginx на 80/443 (папка рядом с репозиториями приложений)

Предполагается структура на сервере:

```text
/srv/   (или любой корень)
├── infra/                 ← эта папка: только edge-nginx + сертификаты + nginx.conf
│   ├── docker-compose.yml
│   ├── nginx.template.conf
│   ├── nginx.conf         ← собирается из шаблона (не в git)
│   └── certs/
│       ├── arkadium/
│       ├── febnik/
│       └── izbirkom/      ← под третий домен, когда добавите server в nginx
├── arkadium/              ← ваш репозиторий (compose не из этого README)
└── febnik/                ← ваш репозиторий
```

Все контейнеры приложений должны быть в одной Docker-сети **`arkadium_shared`** (имя можно сменить везде одинаково).

---

## Куда класть сертификаты

В **`infra/certs/`** — каталоги **`arkadium/`** и **`febnik/`** (имена совпадают с путями в `nginx.template.conf`):

```text
infra/certs/
├── arkadium/
│   ├── fullchain.crt    ← цепочка (PEM), можно скопировать из fullchain.pem
│   └── privkey.key      ← приватный ключ (PEM), из privkey.pem
├── febnik/
│   ├── fullchain.crt
│   └── privkey.key
└── izbirkom/            ← зарезервировано; в шаблоне пока нет блока — добавите позже
```

### Загрузка с **локального** компьютера на сервер (`scp`)

На своей машине (рядом с файлами сертификата, например после выгрузки из Рег.ру или из `~/.acme.sh/...`):

```bash
# замените root@it-vmmini на ваш пользователь@хост, если не root
scp fullchain.pem root@it-vmmini:~/infra/certs/arkadium/fullchain.crt
scp privkey.pem   root@it-vmmini:~/infra/certs/arkadium/privkey.key
```

Если у вас уже файлы с именами `fullchain.crt` и `privkey.key`:

```bash
scp fullchain.crt privkey.key root@it-vmmini:~/infra/certs/arkadium/
```

На **сервере** после копирования:

```bash
chmod 644 ~/infra/certs/arkadium/fullchain.crt
chmod 600 ~/infra/certs/arkadium/privkey.key
```

### Уже есть Let’s Encrypt **на этом же сервере**

```bash
sudo cp /etc/letsencrypt/live/ВАШ-ДОМЕН-АРКАДИУМ/fullchain.pem ~/infra/certs/arkadium/fullchain.crt
sudo cp /etc/letsencrypt/live/ВАШ-ДОМЕН-АРКАДИУМ/privkey.pem   ~/infra/certs/arkadium/privkey.key
sudo chmod 644 ~/infra/certs/arkadium/fullchain.crt
sudo chmod 600 ~/infra/certs/arkadium/privkey.key
```

Аналогично для **febnik** — в `~/infra/certs/febnik/` те же имена файлов.

`docker-compose.yml` монтирует **`./certs`** в контейнер как **`/etc/nginx/certs`**, поэтому править пути в nginx под другую раскладку папок не нужно.

---

## Сеть Docker

Один раз:

```bash
docker network create arkadium_shared
```

В **каждом** `docker-compose` приложения добавьте:

```yaml
networks:
  arkadium_shared:
    external: true
    name: arkadium_shared
```

и у нужных сервисов `networks: [arkadium_shared]`.

---

## Собрать `nginx.conf` и запустить nginx

Рабочая директория — **`infra/`** (где лежит `docker-compose.yml`).

1. Скопируйте сюда файлы **`docker-compose.yml`** и **`nginx.template.conf`** (из этого репозитория или свой аналог).

2. Подставьте домены и upstream’ы (пример: первый сайт — два контейнера `:80` и `:8000`, второй — febnik `febnik:8080`):

   **Важно:** если `sed` не находит `nginx.template.conf`, перенаправление `> nginx.conf` может **обнулить** файл. Проверяйте: `wc -l nginx.conf`. Готовый заполненный пример для **putevod-ik.ru + febnik.ru** — в репозитории: [`examples/nginx.putevod-ik.febnik.conf`](examples/nginx.putevod-ik.febnik.conf) (скопировать на сервер как `nginx.conf`).

3. Команда `sed` (в каталоге **`~/infra`**, где лежит **`nginx.template.conf`**):

```bash
cd /srv/infra

sed -e 's/SITE1_DOMAIN/первый-домен.example/g' \
    -e 's/SITE2_DOMAIN/febnik.ru/g' \
    -e 's/SITE1_FRONTEND/имя-контейнера-фронта/g' \
    -e 's/SITE1_BACKEND/имя-контейнера-api/g' \
    -e 's/SITE2_UPSTREAM/febnik:8080/g' \
    nginx.template.conf > nginx.conf
```

`SITE1_FRONTEND` / `SITE1_BACKEND` — это **`container_name:порт`** без `http://`, как в Docker DNS (например `myapp-web:80`).

4. Проверка синтаксиса:

```bash
docker run --rm -v "$PWD/nginx.conf:/etc/nginx/conf.d/default.conf:ro" nginx:alpine nginx -t
```

5. Запуск (порты **80** и **443** на хосте займёт только этот compose):

```bash
docker compose up -d
```

6. Перезагрузка конфига после правок:

```bash
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload
```

На время **certbot --standalone** освободите порт 80:

```bash
docker compose stop
# certbot ...
docker compose up -d
```

---

## Чеклист

1. `docker network create arkadium_shared`
2. Поднять приложения (сами команды — из их репозиториев), сеть **`arkadium_shared`**, без публикации **80/443** на хост, если их отдаёт infra-nginx
3. **`infra/certs/arkadium/`** и **`infra/certs/febnik/`** — в каждой `fullchain.crt` + `privkey.key`
4. **`sed`** → **`infra/nginx.conf`**
5. **`cd infra && docker compose up -d`**

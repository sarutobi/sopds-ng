# Инструкция развёртывания SOPDS NG

## Содержание

1. [Требования](#требования)
2. [Быстрый старт через Docker Compose](#быстрый-старт-через-docker-compose)
3. [Быстрый старт bare-metal](#быстрый-старт-bare-metal)
4. [Конфигурация через .env](#конфигурация-через-env)
5. [Production-запуск (Gunicorn)](#production-запуск-gunicorn)
6. [Развёртывание на Raspberry Pi](#развёртывание-на-raspberry-pi)
7. [Telegram Bot](#telegram-bot)

---

## Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.13.x | строго 3.13, более старые не поддерживаются |
| uv | ≥ 0.5.0 | менеджер пакетов. Установка: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| PostgreSQL | 17 | основная БД (также возможна SQLite) |
| Docker | ≥ 24 (опционально) | для контейнерного развёртывания |

**Опционально:**

- Docker Compose (входит в состав Docker Desktop или устанавливается отдельно)
- Memcached / Redis (для кэширования)
- Telegram Bot API Token (для интеграции с Telegram)

---

## Быстрый старт через Docker Compose

### 1. Клонирование репозитория

```bash
git clone https://github.com/sarutobi/sopds-ng.git
cd sopds-ng
```

### 2. Настройка окружения

Скопируйте шаблон конфигурации в директорию данных:

```bash
cp base.env data/.env
```

Отредактируйте `data/.env`. Минимально необходимые параметры:

```env
SECRET_KEY=<сгенерируйте случайную строку>
SOPDS_DB_ENGINE=postgres
SOPDS_DB_NAME=sopds
SOPDS_DB_USER=postgres
SOPDS_DB_PASSWORD=<пароль>
SOPDS_DB_HOST=db
SOPDS_DB_PORT=5432
```

**Генерация SECRET_KEY:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

О структуре `DATA_ROOT`:

- `data/.env` — конфигурация django-environ (читается приложением из `/data/.env`)
- `data/secret_key.txt` — секретный ключ Django (генерируется автоматически при запуске)
- `data/db.sqlite3` — SQLite база данных (при `SOPDS_DB_ENGINE=sqlite`)
- `data/log/` — файлы логирования

### 3. Сборка и запуск

```bash
docker compose up -d --build
```

Сервисы:
- **web** — gunicorn на порту `8008`
- **db** — PostgreSQL 17

**Что происходит при старте контейнера** (`scripts/docker_entrypoint.sh`):

1. Проверка: задан ли `SOPDS_DB_PASSWORD` (без него — `FATAL` и останов)
2. Создание `$DATA_ROOT/log/`
3. Генерация `secret_key.txt` в `$DATA_ROOT/`, если файл отсутствует
4. `collectstatic --skip-checks --no-input`
5. `migrate --skip-checks --no-input`
6. Запуск gunicorn

### 4. Проверка

```bash
# Просмотр логов
docker compose logs -f web

# Проверка работоспособности
curl http://localhost:8008/
```

### 5. Создание суперпользователя

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Настройка пути к книгам

По умолчанию книги монтируются из директории `./books` относительно корня проекта. Изменить можно через переменную `SOPDS_BOOK_PATH`:

```bash
export SOPDS_BOOK_PATH=/mnt/media/books
docker compose up -d
```

После запуска настройте `SOPDS_ROOT_LIB` в админке Django:

- Откройте `http://localhost:8008/admin/constance/config/`
- Укажите абсолютный путь к директории с книгами (**внутри контейнера** — `/books/` для смонтированной директории)
- Запустите сканирование: `docker compose exec web python manage.py sopds_scanner`

---

## Быстрый старт bare-metal

### 1. Установка uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Загрузка релиза

```bash
# Скачайте релизный архив с GitHub
# Замените v1.0.0 на актуальную версию
VERSION=v1.0.0
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz"

# Распакуйте в целевой каталог
mkdir -p /opt/sopds-ng
tar -xzf "release_${VERSION#v}.tar.gz" -C /opt/sopds-ng
cd /opt/sopds-ng
```

### 3. Настройка окружения

Задайте `DATA_ROOT` — единый каталог для конфигурации и данных приложения:

```bash
export DATA_ROOT=/data
mkdir -p "$DATA_ROOT"
```

Скопируйте и отредактируйте `.env`:

```bash
cp base.env "$DATA_ROOT/.env"
nano "$DATA_ROOT/.env"
```

**Для SQLite** (без отдельного сервера БД):

```env
SOPDS_DB_ENGINE=sqlite
```

**Для PostgreSQL** (рекомендуется):

```env
SOPDS_DB_ENGINE=postgres
SOPDS_DB_NAME=sopds
SOPDS_DB_USER=postgres
SOPDS_DB_PASSWORD=<пароль>
SOPDS_DB_HOST=localhost
SOPDS_DB_PORT=5432
```

**Для MySQL/MariaDB:**

```env
SOPDS_DB_ENGINE=mysql
SOPDS_DB_NAME=sopds
SOPDS_DB_USER=root
SOPDS_DB_PASSWORD=<пароль>
SOPDS_DB_HOST=localhost
SOPDS_DB_PORT=3306
```

> Для MySQL требуется дополнительная зависимость: `uv pip install mysqlclient>=2.2`. На Debian/Ubuntu: `apt install default-libmysqlclient-dev`.

### 4. Установка зависимостей

```bash
# Production-зависимости (gunicorn, django, psycopg и др.)
uv sync --frozen --no-group dev

# Для разработки (включает тесты, линтеры)
uv sync --frozen --group dev
```

### 5. Применение миграций

```bash
uv run python src/manage.py migrate --skip-checks --no-input
```

### 6. Сборка статики

```bash
uv run python src/manage.py collectstatic --skip-checks --no-input
```

### 7. Создание суперпользователя

```bash
uv run python src/manage.py createsuperuser
```

### 8. Запуск dev-сервера (для тестирования)

```bash
uv run python src/manage.py runserver 0.0.0.0:8000
```

Для production-запуска см. раздел [Production-запуск (Gunicorn)](#production-запуск-gunicorn).

---

## Конфигурация через .env

Файл `.env` располагается в `$DATA_ROOT/.env` (в Docker — `/data/.env`, на bare-metal — путь, заданный через `export DATA_ROOT`).

Поддерживаются следующие переменные:

### Основные

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SECRET_KEY` | — | Секретный ключ Django (обязательно). Сгенерировать: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `SECRET_KEY_FILE` | `$DATA_ROOT/secret_key.txt` | Путь к файлу с секретным ключом (используется FileAwareEnv) |
| `DEBUG` | `False` | Режим отладки. В production всегда `False` |
| `ALLOWED_HOSTS` | `.localhost, 127.0.0.1` | Список разрешённых доменов (через запятую) |
| `DJANGO_SETTINGS_MODULE` | `sopds.settings.base` | Модуль настроек Django |
| `DATA_ROOT` | `/data` | Единый каталог для .env, secret_key.txt, db.sqlite3, log/ |
| `TIME_ZONE` | `Europe/Moscow` | Часовой пояс |
| `SOPDS_VERSION` | — | Версия проекта. Указать вручную: `SOPDS_VERSION=1.0.0RC1` |

### База данных

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SOPDS_DB_ENGINE` | `postgres` | Движок БД: `postgres`, `sqlite` или `mysql` |
| `SOPDS_DB_NAME` | — | Имя БД (только для postgres/mysql) |
| `SOPDS_DB_USER` | — | Пользователь БД (только для postgres/mysql) |
| `SOPDS_DB_PASSWORD` | — | Пароль БД (только для postgres/mysql). **Обязателен даже для SQLite в Docker** (проверка entrypoint) |
| `SOPDS_DB_HOST` | — | Хост БД (только для postgres/mysql) |
| `SOPDS_DB_PORT` | — | Порт БД (только для postgres/mysql) |

> Для SQLite путь БД всегда `$DATA_ROOT/db.sqlite3`. Переменная `SOPDS_DB_NAME` для SQLite игнорируется.

### Сервер

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `PORT` | `8008` | Порт для gunicorn |
| `WEB_CONCURRENCY` | `cpu_count * 2 + 1` | Количество worker-процессов gunicorn |
| `PYTHON_MAX_THREADS` | `2` | Количество потоков на worker (gthread) |
| `WEB_TIMEOUT` | `120` | Таймаут worker'а (сек) |
| `SOPDS_SERVER_LOG_LEVEL` | `WARNING` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Пути

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SOPDS_BOOK_PATH` | `./books` | Путь к директории с книгами **на хосте** (для Docker, через volume) |
| `MEDIA_ROOT` | (настраивается) | Корень медиафайлов (обложки, загрузки) |
| `STATIC_ROOT` | `BASE_DIR/static` | Корень статических файлов. `BASE_DIR = ...sopds-ng/src` |

---

## Production-запуск (Gunicorn)

### Docker (рекомендуется)

```bash
docker compose up -d --build
```

Контейнер автоматически запускает gunicorn через `scripts/docker_entrypoint.sh`:
1. Создаёт `secret_key.txt` (если отсутствует)
2. Выполняет `collectstatic`
3. Выполняет `migrate`
4. Запускает gunicorn

### Bare-metal

```bash
uv run gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
```

Конфигурация gunicorn (`src/sopds/settings/gunicorn.py`):

| Параметр | Значение | Источник |
|----------|----------|----------|
| **bind** | `0.0.0.0:8008` | `PORT` (env) |
| **workers** | `cpu_count * 2 + 1` | `WEB_CONCURRENCY` (env) |
| **worker_type** | `gthread` | — |
| **threads** | `2` | `PYTHON_MAX_THREADS` (env) |
| **timeout** | `120` | `WEB_TIMEOUT` (env) |

### Systemd unit (рекомендуется)

Полный юнит systemd с security hardening, логированием в journald и ресурсными лимитами:

```ini
[Unit]
Description=SOPDS NG OPDS catalog server
Documentation=https://github.com/sarutobi/sopds-ng
After=network.target
Wants=network.target

[Service]
Type=simple
User=sopds
Group=sopds
WorkingDirectory=/opt/sopds-ng

EnvironmentFile=-/data/.env
Environment=DATA_ROOT=/data
Environment=PYTHONDONTWRITEBYTECODE=1

ExecStartPre=/usr/bin/mkdir -p /data/log
ExecStartPre=/bin/sh -c 'test -f /data/secret_key.txt || python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" > /data/secret_key.txt'

ExecStart=/opt/sopds-ng/.venv/bin/gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi

Restart=always
RestartSec=5s

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/data

LimitNOFILE=65535
LimitNPROC=4096

StandardOutput=journal
StandardError=journal
SyslogIdentifier=sopds

[Install]
WantedBy=multi-user.target
```

#### Установка и запуск

```bash
# 1. Создайте системного пользователя
sudo useradd -r sopds -d /opt/sopds-ng -s /usr/sbin/nologin

# 2. Распакуйте релиз
sudo mkdir -p /opt/sopds-ng
sudo tar -xzf "release_${VERSION#v}.tar.gz" -C /opt/sopds-ng
sudo chown -R sopds:sopds /opt/sopds-ng

# 3. Подготовьте DATA_ROOT
sudo mkdir -p /data
sudo chown sopds:sopds /data

# 4. Скопируйте .env
sudo cp base.env /data/.env
sudo nano /data/.env          # отредактируйте конфигурацию

# 5. Установите systemd unit
sudo cp deploy/sopds.service /etc/systemd/system/sopds.service
# или вручную создайте /etc/systemd/system/sopds.service из шаблона выше

# 6. Активируйте и запустите
sudo systemctl daemon-reload
sudo systemctl enable sopds.service
sudo systemctl start sopds.service

# 7. Проверьте статус
sudo systemctl status sopds.service
journalctl -u sopds -n 20 --no-pager
```

> **DATA_ROOT** в systemd unit обязателен — без него приложение будет искать `.env` в `/data/`.
> Логи приложения пишутся в journald — используйте `journalctl -u sopds -f` для просмотра.

### Nginx reverse proxy (рекомендуется)

```nginx
server {
    listen 80;
    server_name sopds.example.com;

    location /static/ {
        alias /opt/sopds-ng/src/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Развёртывание на Raspberry Pi

### Аппаратные требования

- Raspberry Pi 3/4/5 (arm64)
- 1 ГБ RAM (минимум), 2+ ГБ рекомендуется
- Минимум 512 МБ свободного места на SD-карте/SSD

### Docker на Raspberry Pi

```bash
# Установка Docker (если не установлен)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Выйдите из сессии и зайдите заново (или выполните: newgrp docker)

# Клонирование
git clone https://github.com/sarutobi/sopds-ng.git
cd sopds-ng

# Настройка
cp base.env data/.env
# Отредактируйте data/.env — укажите SECRET_KEY
```

Образ `python:3.13-slim` поддерживает arm64 нативно. Эмуляция не требуется.

```bash
docker compose up -d --build
```

### Bare-metal на Raspberry Pi

```bash
# Установка Python 3.13 через deadsnakes (если недоступен в репозитории)
sudo apt update
sudo apt install -y python3.13 python3.13-venv

# Установка uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Загрузка и распаковка релиза
VERSION=v1.0.0
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz"
mkdir -p /opt/sopds-ng
tar -xzf "release_${VERSION#v}.tar.gz" -C /opt/sopds-ng
cd /opt/sopds-ng

# Настройка DATA_ROOT
export DATA_ROOT=/data
mkdir -p "$DATA_ROOT"
cp base.env "$DATA_ROOT/.env"
# Отредактируйте .env:
#   SOPDS_DB_ENGINE=sqlite (экономит RAM)

# Установка зависимостей
uv sync --frozen --no-group dev

# Миграции и статика
uv run python src/manage.py migrate --skip-checks --no-input
uv run python src/manage.py collectstatic --skip-checks --no-input

# Запуск (с уменьшенным числом worker'ов)
WEB_CONCURRENCY=2 PYTHON_MAX_THREADS=4 \
  uv run gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
```

**Рекомендации для Raspberry Pi:**

1. Используйте SQLite вместо PostgreSQL — ниже потребление RAM
2. Ограничьте `WEB_CONCURRENCY=2` (на 1–2 ГБ RAM)
3. Отключите неиспользуемые модули (Telegram Bot, если не нужен)
4. Используйте USB-накопитель или SSD для хранения книг вместо SD-карты
5. Настройте swap (2 ГБ) при 1 ГБ RAM

---

## Telegram Bot

После запуска настройте в админке Django (`http://your-host:8008/admin/constance/config/`):

| Параметр | Описание |
|----------|----------|
| `SOPDS_TELEBOT_API_TOKEN` | Токен бота (получить у @BotFather) |
| `SOPDS_TELEBOT_AUTH` | Включить аутентификацию (True/False) |
| `SOPDS_TELEBOT_MAXITEMS` | Максимум элементов на странице |

Эти настройки хранятся в БД (через django-constance), а не в `.env`.

Плановое сканирование настраивается там же (раздел «Scanner Shedule»):
- `SOPDS_SCAN_SHED_MIN` — минуты (cron-синтаксис)
- `SOPDS_SCAN_SHED_HOUR` — часы (cron-синтаксис)
- `SOPDS_SCAN_SHED_DAY` — дни (cron-синтаксис)
- `SOPDS_SCAN_SHED_DOW` — дни недели (cron-синтаксис)

По умолчанию: в полночь и в 12:00.

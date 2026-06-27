# Инструкция развёртывания SOPDS NG

## Содержание

1. [Требования](#требования)
2. [Быстрый старт через Docker Compose](#быстрый-старт-через-docker-compose)
3. [Быстрый старт bare-metal](#быстрый-старт-bare-metal)
4. [Конфигурация через .env](#конфигурация-через-env)
5. [Применение миграций](#применение-миграций)
6. [Сборка статики](#сборка-статики)
7. [Создание суперпользователя](#создание-суперпользователя)
8. [Production-запуск (Gunicorn)](#production-запуск-gunicorn)
9. [Развёртывание на Raspberry Pi](#развёртывание-на-raspberry-pi)

---

## Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.13.x | строго 3.13, более старые не поддерживаются |
| uv | ≥ 0.5.0 | менеджер пакетов (аналог pip/poetry) |
| PostgreSQL | 17 | основная БД (также возможна SQLite) |
| Docker | ≥ 24 (опционально) | для контейнерного развёртывания |
| Gunicorn | ≥ 23 (устанавливается через uv) | production WSGI-сервер |

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

Скопируйте шаблон конфигурации:

```bash
cp base.env .env
```

Отредактируйте `.env`. Минимально необходимые параметры:

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

### 3. Сборка и запуск

```bash
docker compose up -d --build
```

Сервисы:
- **web** — gunicorn на порту `8008`
- **db** — PostgreSQL 17

При первом запуске автоматически выполняются:
- Миграции БД (`migrate`)
- Сборка статики (`collectstatic`)
- Генерация `secret_key.txt` (если отсутствует)

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

По умолчанию книги монтируются из директории `./books` относительно корня проекта.
Изменить можно через переменную `SOPDS_BOOK_PATH`:

```bash
export SOPDS_BOOK_PATH=/mnt/media/books
docker compose up -d
```

После запуска настройте `SOPDS_ROOT_LIB` в админке Django:
- Откройте `http://localhost:8008/admin/constance/config/`
- Укажите абсолютный путь к директории с книгами
- Запустите сканирование: `docker compose exec web python manage.py sopds_scanner`

---

## Быстрый старт bare-metal

### 1. Установка uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# или через pip
pip install uv
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

# Настройка окружения
cp base.env .env
```

Отредактируйте `.env`. Для SQLite (без PostgreSQL):

```env
SOPDS_DB_ENGINE=sqlite
SOPDS_DB_NAME=db.sqlite3
```

Для PostgreSQL (рекомендуется):

```env
SOPDS_DB_ENGINE=postgres
SOPDS_DB_NAME=sopds
SOPDS_DB_USER=postgres
SOPDS_DB_PASSWORD=<пароль>
SOPDS_DB_HOST=localhost
SOPDS_DB_PORT=5432
```

### 3. Установка зависимостей

```bash
# Production-зависимости
uv sync --frozen --no-group dev

# Для разработки (включает тесты, линтеры)
uv sync --frozen --group dev
```

### 4. Применение миграций

```bash
uv run python src/manage.py migrate --skip-checks --no-input
```

### 5. Сборка статики

```bash
uv run python src/manage.py collectstatic --skip-checks --no-input
```

### 6. Создание суперпользователя

```bash
uv run python src/manage.py createsuperuser
```

### 7. Запуск dev-сервера (для тестирования)

```bash
uv run python src/manage.py runserver 0.0.0.0:8000
```

---

## Конфигурация через .env

Файл `.env` располагается в корне проекта. Поддерживаются следующие переменные:

### Основные

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SECRET_KEY` | — | Секретный ключ Django (обязательно). Сгенерировать: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | Режим отладки. В production всегда `False`. |
| `ALLOWED_HOSTS` | `.localhost, 127.0.0.1` | Список разрешённых доменов (через запятую). |
| `DJANGO_SETTINGS_MODULE` | `sopds.settings.base` | Модуль настроек Django. |
| `TIME_ZONE` | `Europe/Moscow` | Часовой пояс. |
| `SOPDS_VERSION` | — | Версия проекта (читается из version.txt). |

### База данных

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SOPDS_DB_ENGINE` | `postgres` | Движок БД: `postgres` или `sqlite`. |
| `SOPDS_DB_NAME` | — | Имя БД (или путь к файлу для SQLite). |
| `SOPDS_DB_USER` | — | Пользователь БД (только для postgres). |
| `SOPDS_DB_PASSWORD` | — | Пароль БД (только для postgres). |
| `SOPDS_DB_HOST` | — | Хост БД (только для postgres). |
| `SOPDS_DB_PORT` | — | Порт БД (только для postgres). |

### Сервер

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `PORT` | `8008` | Порт для gunicorn. |
| `WEB_CONCURRENCY` | `cpu_count * 2 + 1` | Количество worker-процессов gunicorn. |
| `PYTHON_MAX_THREADS` | `2` | Количество потоков на worker (gthread). |
| `WEB_TIMEOUT` | `120` | Таймаут worker'а (сек). |
| `SOPDS_SERVER_LOG_LEVEL` | `WARNING` | Уровень логирования. |

### Пути

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SOPDS_BOOK_PATH` | `./books` | Путь к директории с книгами (для Docker). |
| `MEDIA_ROOT` | (настраивается) | Корень медиафайлов (обложки, загрузки). |
| `STATIC_ROOT` | `src/static` | Корень статических файлов. |

---

## Применение миграций

```bash
# Docker
docker compose exec web python manage.py migrate --skip-checks --no-input

# Bare-metal
uv run python src/manage.py migrate --skip-checks --no-input
```

При первом запуске создаются все необходимые таблицы в БД.

---

## Сборка статики

```bash
# Docker (выполняется автоматически при старте контейнера)
# Ручной запуск:
docker compose exec web python manage.py collectstatic --skip-checks --no-input

# Bare-metal
uv run python src/manage.py collectstatic --skip-checks --no-input
```

Статика собирается в директорию, указанную в `STATIC_ROOT`, и раздаётся через Whitenoise.

---

## Создание суперпользователя

```bash
# Docker
docker compose exec -it web python manage.py createsuperuser

# Bare-metal
uv run python src/manage.py createsuperuser
```

После создания откройте админку: `http://your-host:8008/admin/`

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

- **bind**: `0.0.0.0:8008` (порт задаётся через `PORT`)
- **workers**: `cpu_count * 2 + 1` (через `WEB_CONCURRENCY`)
- **worker_type**: `gthread`
- **threads**: `2` (через `PYTHON_MAX_THREADS`)
- **timeout**: `120` (через `WEB_TIMEOUT`)

**Systemd unit (опционально):**

```
[Unit]
Description=SOPDS NG
After=network.target postgresql.service

[Service]
Type=simple
User=sopds
WorkingDirectory=/opt/sopds-ng/src
Environment=DJANGO_SETTINGS_MODULE=sopds.settings.base
ExecStart=/opt/sopds-ng/.venv/bin/gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
Restart=always

[Install]
WantedBy=multi-user.target
```

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

# Клонирование
git clone https://github.com/sarutobi/sopds-ng.git
cd sopds-ng

# Настройка
cp base.env .env
# Отредактируйте .env — укажите SECRET_KEY
```

**Важно:** образ `python:3.13-slim` поддерживает arm64 нативно. Не требуется эмуляция.

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
cp base.env .env

# Для экономии RAM используйте SQLite
# SOPDS_DB_ENGINE=sqlite
# SOPDS_DB_NAME=/opt/sopds-ng/data/db.sqlite3

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

1. Используйте SQLite вместо PostgreSQL — ниже потребление RAM.
2. Ограничьте `WEB_CONCURRENCY=2` (на 1–2 ГБ RAM).
3. Отключите неиспользуемые модули (Telegram Bot, если не нужен).
4. Используйте USB-накопитель или SSD для хранения книг вместо SD-карты.
5. Настройте swap (2 ГБ) при 1 ГБ RAM.

---

## Дополнительно

### Telegram Bot

После запуска настройте в админке Django:
- `SOPDS_TELEBOT_API_TOKEN` — токен бота
- `SOPDS_TELEBOT_AUTH` — включить аутентификацию

### Плановое сканирование

Настройте расписание сканирования библиотеки в админке Django:
- `SOPDS_SCAN_SCHED_MIN` — минуты (cron)
- `SOPDS_SCAN_SCHED_HOUR` — часы (cron)
- `SOPDS_SCAN_SCHED_DAY` — дни (cron)
- `SOPDS_SCAN_SCHED_DOW` — дни недели (cron)

По умолчанию: в полночь и в 12:00.

# Инструкция развёртывания SOPDS NG

## Содержание

1. [Требования](#требования)
2. [Быстрый старт через Docker Compose](#быстрый-старт-через-docker-compose)
3. [Быстрый старт bare-metal](#быстрый-старт-bare-metal)
4. [Конфигурация через .env](#конфигурация-через-env)
5. [Production-запуск (Gunicorn)](#production-запуск-gunicorn)
6. [Развёртывание на Raspberry Pi](#развёртывание-на-raspberry-pi)
7. [Настройка библиотеки книг](#настройка-библиотеки-книг)
8. [Telegram Bot](#telegram-bot)

---

## Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.13.x | строго 3.13, более старые не поддерживаются |
| uv | ≥ 0.5.0 | менеджер пакетов. Установка: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| PostgreSQL | 17 | основная БД (также возможна SQLite) |
| Docker | ≥ 24 (опционально) | для контейнерного развёртывания |

**Структура деплоя (SOPDS_ROOT):**

Проект использует `SOPDS_ROOT` — единый корневой каталог установки (по умолчанию `/opt/sopds-ng`).
Все данные приложения (`.env`, `secret_key.txt`, `db.sqlite3`, `log/`) находятся в поддиректории `$SOPDS_ROOT/data/`.

```
SOPDS_ROOT=/opt/sopds-ng (настраиваемый)
├── app/              ← код приложения (src/*)
├── data/             ← .env, secret_key.txt, db.sqlite3, log/
├── scripts/          ← start_server.sh, deploy.sh, check-systemd.sh
├── .venv/             ← виртуальное окружение (создается deploy.sh)
├── pyproject.toml
├── manage.py
├── base.env
└── etc/systemd/system/sopds.service
```

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
mkdir -p data
cp base.env data/.env
```

Отредактируйте `data/.env`. **Обязательные** параметры зависят от выбранной БД.

**Для PostgreSQL:**
```env
SOPDS_DB_ENGINE=postgres
SOPDS_DB_NAME=sopds
SOPDS_DB_USER=postgres
SOPDS_DB_PASSWORD=<пароль>
SOPDS_DB_HOST=db
SOPDS_DB_PORT=5432
```

**Примечание:** `SECRET_KEY` генерируется автоматически при первом запуске, если не задан явно.

**О путях в Docker:**
В образе используется стандарт `SOPDS_ROOT=/opt/sopds-ng`. 
Пути в `.env` (например, `SECRET_KEY_FILE`) должны быть абсолютными: `/opt/sopds-ng/data/secret_key.txt`.

### 3. Использование готового образа (рекомендуется)

Образы публикуются в [ghcr.io/sarutobi/sopds-ng](https://github.com/sarutobi/sopds-ng/pkgs/container/sopds-ng).

1. Скачайте `docker-compose.yml` со страницы [последнего релиза](https://github.com/sarutobi/sopds-ng/releases/latest):
   ```bash
   wget https://github.com/sarutobi/sopds-ng/releases/latest/download/docker-compose.yml
   ```

2. Скачайте шаблон `.env` и подготовьте директорию данных:
   ```bash
   wget https://raw.githubusercontent.com/sarutobi/sopds-ng/master/base.env
   mkdir -p data && cp base.env data/.env
   # SECRET_KEY будет сгенерирован автоматически при первом запуске, если отсутствует в .env
   ```

3. Запустите:
   ```bash
   docker compose up -d
   ```

### 4. Сборка и запуск (для разработчиков)

Если вы клонировали репозиторий и хотите собрать образ локально:

```bash
docker compose up -d --build
```

Сервисы:
- **web** — gunicorn на порту `8080`
- **db** — PostgreSQL 17

**Что происходит при старте контейнера** (`scripts/start_server.sh`):

1. Проверка обязательных переменных `SOPDS_ROOT` и `DATA_ROOT`.
2. Создание `$DATA_ROOT/log/`.
3. Генерация `secret_key.txt` в `$DATA_ROOT/`, если файл отсутствует.
4. Применение миграций БД (`migrate`).
5. Сборка статических файлов (`collectstatic`).
6. Запуск gunicorn.

### 5. Проверка

```bash
# Просмотр логов
docker compose logs -f web

# Проверка работоспособности
curl http://localhost:8080/
```

### 6. Создание суперпользователя

```bash
docker compose exec web python manage.py createsuperuser
```

---

## Быстрый старт bare-metal

### 1. Установка uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Загрузка релиза

```bash
# Скачайте релизный архив с GitHub
VERSION=v1.0.0
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz"

# Распакуйте в целевой каталог
sudo mkdir -p /opt/sopds-ng
sudo tar -xzf "release_${VERSION#v}.tar.gz" -C /opt/sopds-ng
sudo chown -R sopds:sopds /opt/sopds-ng
cd /opt/sopds-ng
```

### 3. Запуск

Рекомендуется использовать systemd-unit.

```bash
# 1. Установите unit-файл
sudo cp /opt/sopds-ng/scripts/sopds.service /etc/systemd/system/sopds.service

# 2. Активируйте и запустите
sudo systemctl daemon-reload
sudo systemctl enable sopds.service
sudo systemctl start sopds.service
```

По умолчанию сервер работает на порту `8080`.

### 4. Проверка и администрирование

```bash
# Статус сервиса
sudo systemctl status sopds.service

# Логи (через journald)
sudo journalctl -u sopds -f

# Создание суперпользователя
sudo -u sopds /opt/sopds-ng/.venv/bin/python /opt/sopds-ng/manage.py createsuperuser
```

---

## Конфигурация через .env

Файл `.env` располагается в `$SOPDS_ROOT/data/.env` (в Docker — `/opt/sopds-ng/data/.env`).

### Основные

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SECRET_KEY` | — | Секретный ключ Django. Если не задан, генерируется автоматически при старте. |
| `DEBUG` | `False` | Режим отладки. В production всегда `False`. |
| `SOPDS_USE_HTTPS` | `False` | HTTPS-режим: secure-cookies, HSTS и доверие к `X-Forwarded-Proto`. |
| `SOPDS_VERSION` | — | Версия проекта (например, `1.0.0`). |
| `SOPDS_SERVER_LOG_LEVEL` | `WARNING` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ALLOWED_HOSTS` | `.localhost,127.0.0.1` | Список хостов, разделенных запятой. |
| `CSRF_TRUSTED_ORIGINS` | — | Список доверенных origin для CSRF, разделенных запятой. |

### База данных

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SOPDS_DB_ENGINE` | `postgres` | Движок БД: `postgres`, `sqlite` или `mysql` |
| `SOPDS_DB_NAME` | — | Имя БД (только для postgres/mysql) |
| `SOPDS_DB_USER` | — | Пользователь БД (только для postgres/mysql) |
| `SOPDS_DB_PASSWORD` | — | Пароль БД. **Обязателен даже для SQLite в Docker** |
| `SOPDS_DB_HOST` | — | Хост БД (только для postgres/mysql) |
| `SOPDS_DB_PORT` | — | Порт БД (только для postgres/mysql) |

---

## Production-запуск (Gunicorn)

При запуске через systemd или вручную, используется Gunicorn.

**Ручной запуск:**
```bash
SOPDS_ROOT=/opt/sopds-ng /opt/sopds-ng/.venv/bin/gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
```

Конфигурация gunicorn (`src/sopds/settings/gunicorn.py`):
- **bind**: `0.0.0.0:8080` (или через переменную `PORT`)
- **workers**: `cpu_count * 2 + 1` (или через `WEB_CONCURRENCY`)
- **worker_type**: `gthread`
- **threads**: `2` (или через `PYTHON_MAX_THREADS`)

### Nginx reverse proxy (рекомендуется)

```nginx
server {
    listen 80;
    server_name sopds.example.com;

    location /static/ {
        alias /opt/sopds-ng/data/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Развёртывание на Raspberry Pi

Для Raspberry Pi рекомендуется использовать SQLite для экономи экономии RAM и ограничить ресурсы Gunicorn:
`WEB_CONCURRENCY=2` и `PYTHON_MAX_THREADS=4`.
```bash
sudo -u sopds bash deploy.sh --db-engine sqlite
```
```bash
# Запуск с ограничением ресурсов
WEB_CONCURRENCY=2 PYTHON_MAX_THREADS=4 \\
  sudo -u sopds /opt/sopds-ng/.venv/bin/gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
```

---

## Настройка библиотеки книг

Для того чтобы приложение видело ваши книги, необходимо выполнить два шага:

#### Шаг 1: Подготовка папки с книгами
Укажите путь к папке с книгами.

- **В Docker**: Используйте переменную `SOPDS_BOOK_PATH` в `docker-compose.yml` или `.env` для проброса папки с хоста в контейнер.
  ```yaml
  volumes:
    - /mnt/media/books:/books:ro  # Слева — путь на хосте, справа — внутри контейнера
  ```
  В этом случае внутри контейнера путь к книгам будет `/books`.

- **В Bare-metal**: Создайте папку с книгами (например, `/opt/sopds-ng/books`) и убедитесь, что у пользователя `sopds` есть права на её чтение:
  ```bash
  sudo mkdir -p /opt/sopds-ng/books
  sudo chown -R sopds:sopds /opt/sopds-ng/books
  ```

#### Шаг 2: Настройка пути в админке Django
После запуска сервера необходимо указать приложению, где именно искать корень библиотеки:

1. Зайдите в админку под суперпользователем: `http://your-host:8080/admin/`
2. Перейдите в раздел **Constance** $\rightarrow$ **Config**.
3. Найдите параметр `SOPDS_ROOT_LIB`.
4. Введите абсолютный путь к папке с книгами:
   - Для Docker: `/books` (или другой путь, указанный в volume).
   - Для Bare-metal: `/opt/sopds-ng/books` (или ваш путь).
5. Нажмите **Save**.

*Примечание: Приложение сканирует папку рекурсивно. Все книги в подпапках будут проиндексированы.*

---

## Telegram Bot

Настройте в админке Django (`http://your-host:8080/admin/constance/config/`):
- `SOPDS_TELEBOT_API_TOKEN` — токен бота от @BotFather.
- `SOPDS_TELEBOT_AUTH` — включение аутентификации.

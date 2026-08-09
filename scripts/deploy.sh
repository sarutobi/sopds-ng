#!/usr/bin/env bash
set -euo pipefail

# ==============================================================
# scripts/deploy.sh — подготовка окружения SOPDS NG (bare-metal)
# Использование:  ./deploy.sh [опции]
# ==============================================================

# --- Значения по умолчанию ---
SOPDS_ROOT="/opt/sopds-ng"
DATA_ROOT_DEFAULT="data"             # относительный — резолвится от SOPDS_ROOT
DB_ENGINE="postgres"
DB_NAME=""
DB_USER=""
DB_HOST=""
DB_PORT=""
TIME_ZONE="UTC"
ALLOWED_HOSTS=""
SERVER_LOG_LEVEL="WARNING"
DEBUG=""
DJANGO_SETTINGS="sopds.settings.base"
DRY_RUN=""

# --- Хелпер для dry-run ---
run() {
    local desc="$1"
    shift
    if [ -n "$DRY_RUN" ]; then
        echo "[DRY-RUN] $desc"
    else
        "$@"
    fi
}

# --- Функция справки ---
usage() {
    cat <<EOF
Использование: $(basename "$0") [опции]

Подготовка окружения SOPDS NG: создание директорий, установка зависимостей, настройка
окружения, генерация secret key, сбор статических файлов и  запуск миграций.

Опции:
  -i, --sopds-root DIR    Корневая директория SOPDS_ROOT
                            (по умолчанию: $SOPDS_ROOT)
  -d, --data-root DIR     DATA_ROOT. Абсолютный путь — как есть,
                            относительный — от SOPDS_ROOT
                            (по умолчанию: ${DATA_ROOT_DEFAULT})
      --db-engine ENGINE  Движок БД: postgres, sqlite, mysql
                            (по умолчанию: $DB_ENGINE)
      --db-name NAME      Имя БД (по умолчанию: не задано)
      --db-user USER      Пользователь БД (по умолчанию: не задано)
      --db-host HOST      Хост БД (по умолчанию: не задано)
      --db-port PORT      Порт БД (по умолчанию: не задано)
      --time-zone TZ      Часовой пояс (по умолчанию: $TIME_ZONE)
      --allowed-hosts H   Разрешённые хосты, через запятую
                            (по умолчанию: не задано)
      --server-log-level  Уровень лога сервера: DEBUG, INFO, WARNING, ERROR
                            (по умолчанию: $SERVER_LOG_LEVEL)
      --debug             Включить DEBUG=True (по умолчанию: False)
  -DS, --django-settings  DJANGO_SETTINGS_MODULE
                            (по умолчанию: $DJANGO_SETTINGS)
  -n, --dry-run           Показать что будет сделано, ничего не выполняя
  -h, --help              Эта справка

Примеры:
  # SQLite (bare-metal, без PostgreSQL):
  $(basename "$0") -i /opt/sopds-ng --db-engine sqlite

  # PostgreSQL с полной конфигурацией:
  $(basename "$0") --db-engine postgres --db-name sopds --db-user sopds \\
      --db-host localhost --db-port 5432 \\
      --allowed-hosts 'sopds.example.com,localhost'

  # MySQL:
  $(basename "$0") --db-engine mysql --db-name sopds --db-host localhost --db-port 3306

  # Посмотреть что будет сделано (dry-run):
  $(basename "$0") -i /opt/sopds-ng --db-engine sqlite -n

Внимание: пароль БД (SOPDS_DB_PASSWORD) вводится вручную
в .env после развёртывания. deploy.sh его не запрашивает.
EOF
    exit 0
}

# --- Разбор аргументов ---
PARSED=$(getopt -o hi:d:DS:n --long help,sopds-root:,data-root:,db-engine:,db-name:,db-user:,db-host:,db-port:,time-zone:,allowed-hosts:,server-log-level:,debug,django-settings:,dry-run -n "$(basename "$0")" -- "$@")
eval set -- "$PARSED"

while true; do
    case "$1" in
    -h | --help) usage ;;
    -i | --sopds-root)
        SOPDS_ROOT="$2"
        shift 2
        ;;
    -d | --data-root)
        DATA_ROOT_DEFAULT="$2"
        shift 2
        ;;
    --db-engine)
        DB_ENGINE="$2"
        shift 2
        ;;
    --db-name)
        DB_NAME="$2"
        shift 2
        ;;
    --db-user)
        DB_USER="$2"
        shift 2
        ;;
    --db-host)
        DB_HOST="$2"
        shift 2
        ;;
    --db-port)
        DB_PORT="$2"
        shift 2
        ;;
    --time-zone)
        TIME_ZONE="$2"
        shift 2
        ;;
    --allowed-hosts)
        ALLOWED_HOSTS="$2"
        shift 2
        ;;
    --server-log-level)
        SERVER_LOG_LEVEL="$2"
        shift 2
        ;;
    --debug)
        DEBUG="True"
        shift
        ;;
    -DS | --django-settings)
        DJANGO_SETTINGS="$2"
        shift 2
        ;;
    -n | --dry-run)
        DRY_RUN="1"
        shift
        ;;
    --)
        shift
        break
        ;;
    *)
        echo "Внутренняя ошибка: неизвестный аргумент $1" >&2
        exit 1
        ;;
    esac
done

# --- Вычисление DATA_ROOT ---
if [[ "$DATA_ROOT_DEFAULT" == /* ]]; then
    DATA_ROOT="$DATA_ROOT_DEFAULT"
else
    DATA_ROOT="$SOPDS_ROOT/$DATA_ROOT_DEFAULT"
fi

SECRET_KEY_FILE="$DATA_ROOT/secret_key.txt"
APP_DIR="$SOPDS_ROOT/app"

# --- Экспорт переменных окружения ---
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS"
export SOPDS_ROOT
export DATA_ROOT

# --- Переход в корень SOPDS_ROOT (.venv здесь) ---
if [ -d "$SOPDS_ROOT" ]; then
    cd "$SOPDS_ROOT"
else
    echo ">>> Директория $SOPDS_ROOT не существует (будет создана при реальном запуске)"
fi
echo ">>> SOPDS_ROOT: $SOPDS_ROOT"
echo ">>> APP_DIR: $APP_DIR"
echo ">>> DATA_ROOT: $DATA_ROOT"
echo ">>> Движок БД: $DB_ENGINE"
echo ">>> DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
[ -n "$DRY_RUN" ] && echo ">>> *** РЕЖИМ DRY-RUN: никаких изменений не будет ***"

# --- Подготовка директорий ---
run "mkdir -p $DATA_ROOT/log" mkdir -p "$DATA_ROOT/log"
run "mkdir -p $DATA_ROOT/static" mkdir -p "$DATA_ROOT/static"

# --- Настройка .env ---
ENV_FILE="$DATA_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$SOPDS_ROOT/base.env" ]; then
        run "cp $SOPDS_ROOT/base.env $ENV_FILE" cp "$SOPDS_ROOT/base.env" "$ENV_FILE"
        echo ">>> Создан $ENV_FILE из base.env"

        # Подстановка параметров в .env (только не dry-run — sed -i реально меняет файл)
        if [ -z "$DRY_RUN" ]; then
            sed -i "s|^SOPDS_ROOT=.*|SOPDS_ROOT='$SOPDS_ROOT'|" "$ENV_FILE"
            sed -i "s|^DATA_ROOT=.*|DATA_ROOT='$DATA_ROOT'|" "$ENV_FILE"
            sed -i "s|^SOPDS_DB_ENGINE=.*|SOPDS_DB_ENGINE='$DB_ENGINE'|" "$ENV_FILE"
            sed -i "s|^TIME_ZONE=.*|TIME_ZONE='$TIME_ZONE'|" "$ENV_FILE"
            sed -i "s|^SOPDS_SERVER_LOG_LEVEL=.*|SOPDS_SERVER_LOG_LEVEL='$SERVER_LOG_LEVEL'|" "$ENV_FILE"

            [ -n "$DB_NAME" ] && sed -i "s|^SOPDS_DB_NAME=.*|SOPDS_DB_NAME='$DB_NAME'|" "$ENV_FILE"
            [ -n "$DB_USER" ] && sed -i "s|^SOPDS_DB_USER=.*|SOPDS_DB_USER='$DB_USER'|" "$ENV_FILE"
            [ -n "$DB_HOST" ] && sed -i "s|^SOPDS_DB_HOST=.*|SOPDS_DB_HOST='$DB_HOST'|" "$ENV_FILE"
            [ -n "$DB_PORT" ] && sed -i "s|^SOPDS_DB_PORT=.*|SOPDS_DB_PORT='$DB_PORT'|" "$ENV_FILE"
            if [ -n "$ALLOWED_HOSTS" ]; then
                if grep -q "^# ALLOWED_HOSTS" "$ENV_FILE"; then
                    sed -i "s|^# ALLOWED_HOSTS=.*|ALLOWED_HOSTS='$ALLOWED_HOSTS'|" "$ENV_FILE"
                else
                    sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS='$ALLOWED_HOSTS'|" "$ENV_FILE"
                fi
            fi
            [ -n "$DEBUG" ] && sed -i "s|^DEBUG=.*|DEBUG=True|" "$ENV_FILE"
        else
            echo "[DRY-RUN] Подстановка параметров в $ENV_FILE:"
            echo "  SOPDS_ROOT=$SOPDS_ROOT"
            echo "  DATA_ROOT=$DATA_ROOT"
            echo "  SOPDS_DB_ENGINE=$DB_ENGINE"
            echo "  TIME_ZONE=$TIME_ZONE"
            echo "  SOPDS_SERVER_LOG_LEVEL=$SERVER_LOG_LEVEL"
            [ -n "$DB_NAME" ] && echo "  SOPDS_DB_NAME=$DB_NAME"
            [ -n "$DB_USER" ] && echo "  SOPDS_DB_USER=$DB_USER"
            [ -n "$DB_HOST" ] && echo "  SOPDS_DB_HOST=$DB_HOST"
            [ -n "$DB_PORT" ] && echo "  SOPDS_DB_PORT=$DB_PORT"
            [ -n "$ALLOWED_HOSTS" ] && echo "  ALLOWED_HOSTS=$ALLOWED_HOSTS"
            [ -n "$DEBUG" ] && echo "  DEBUG=True"
            echo "  (SOPDS_DB_PASSWORD — задать вручную после деплоя)"
        fi

        echo ">>> Параметры .env настроены:"
        echo "    SOPDS_ROOT=$SOPDS_ROOT"
        echo "    DATA_ROOT=$DATA_ROOT"
        echo "    SOPDS_DB_ENGINE=$DB_ENGINE"
        echo "    TIME_ZONE=$TIME_ZONE"
        echo "    SOPDS_SERVER_LOG_LEVEL=$SERVER_LOG_LEVEL"
        [ -n "$DB_NAME" ] && echo "    SOPDS_DB_NAME=$DB_NAME"
        [ -n "$DB_USER" ] && echo "    SOPDS_DB_USER=$DB_USER"
        [ -n "$DB_HOST" ] && echo "    SOPDS_DB_HOST=$DB_HOST"
        [ -n "$DB_PORT" ] && echo "    SOPDS_DB_PORT=$DB_PORT"
        [ -n "$ALLOWED_HOSTS" ] && echo "    ALLOWED_HOSTS=$ALLOWED_HOSTS"
        [ -n "$DEBUG" ] && echo "    DEBUG=True"
        echo ">>> ВАЖНО: укажите SOPDS_DB_PASSWORD в $ENV_FILE вручную!"
    else
        echo "WARN: base.env не найден в $SOPDS_ROOT" >&2
        echo "WARN: создайте $ENV_FILE вручную из base.env" >&2
    fi
else
    echo ">>> $ENV_FILE уже существует (пропускаем настройку)"
    echo ">>> Если нужно пересоздать — удалите $ENV_FILE и запустите deploy.sh заново"
fi

# --- Установка зависимостей ---
run "uv sync --frozen --no-group dev" uv sync --frozen --no-group dev

# --- Генерация secret_key ---
if [ ! -f "$SECRET_KEY_FILE" ]; then
    if [ -n "$DRY_RUN" ]; then
        echo "[DRY-RUN] Генерация секретного ключа Django -> $SECRET_KEY_FILE"
    else
        echo ">>> Генерация секретного ключа Django..."
        .venv/bin/python -c \
            "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" \
            >"$SECRET_KEY_FILE"
    fi
else
    echo ">>> Секретный ключ уже существует: $SECRET_KEY_FILE"
fi

# --- Сборка статики ---
run ".venv/bin/python manage.py collectstatic" \
    .venv/bin/python manage.py collectstatic --skip-checks --no-input

# --- Миграции ---
run ".venv/bin/python manage.py migrate" \
    .venv/bin/python manage.py migrate --skip-checks --no-input

if [ -n "$DRY_RUN" ]; then
    echo ">>> *** DRY-RUN завершён. Никаких изменений не внесено ***"
else
    echo ">>> Deploy завершён успешно"
fi

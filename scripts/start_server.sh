#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE='sopds.settings.base'

# Читаем DATA_ROOT из окружения, дефолт /data
DATA_ROOT="${DATA_ROOT:-/data}"
SECRET_KEY_FILE="${SECRET_KEY_FILE:-$DATA_ROOT/secret_key.txt}"

# Проверка обязательных переменных
if [ -z "${SOPDS_DB_PASSWORD}" ]; then
    echo "FATAL: SOPDS_DB_PASSWORD не задан. Укажи в .env" >&2
    exit 1
fi

mkdir -p "$DATA_ROOT/log"

# Sync packages
uv sync --no-dev

# Create key
if [ ! -f "$SECRET_KEY_FILE" ]; then
    uv run --no-dev python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' >"$SECRET_KEY_FILE"
fi

# Collect statics files
uv run --no-dev manage.py collectstatic --skip-checks --no-input

# Run DB migrations
uv run --no-dev manage.py migrate --skip-checks --no-input

# Run server
uv run --no-dev --env-file="$DATA_ROOT/.env" gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi

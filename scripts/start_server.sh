#!/bin/bash
set -e

# Проверка обязательных переменных
if [ -z "$SOPDS_ROOT" ]; then
    echo "Error: SOPDS_ROOT environment variable is not set."
    exit 1
fi

if [ -z "$DATA_ROOT" ]; then
    echo "Error: DATA_ROOT environment variable is not set."
    exit 1
fi

# Создание директории логов, если она отсутствует
mkdir -p "$DATA_ROOT/log/"

# Создание secret_key, если он отсутствует
SECRET_KEY_FILE="${SECRET_KEY_FILE:-$DATA_ROOT/secret_key.txt}"
if [ ! -f "$SECRET_KEY_FILE" ]; then
    echo "Generating secret key..."
    "$SOPDS_ROOT/.venv/bin/python" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' > "$SECRET_KEY_FILE"
fi

# --- Подготовка БД и статики ---
echo "Running database migrations..."
"$SOPDS_ROOT/.venv/bin/python" manage.py migrate --no-input

echo "Collecting static files..."
"$SOPDS_ROOT/.venv/bin/python" manage.py collectstatic --no-input

# Запуск Gunicorn
echo "Starting Gunicorn..."
exec "$SOPDS_ROOT/.venv/bin/gunicorn" --config="python:sopds.settings.gunicorn" sopds.wsgi

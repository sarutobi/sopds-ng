#!/usr/bin/env bash

# Create log directory
mkdir -p log

# Sync packages
uv sync --no-dev

# Create key
if [ ! -f 'secret_key.txt' ]; then
    uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' >secret_key.txt
fi
# Collect statics files
uv run manage.py collectstatic --skip-checks --no-input

# Run DB migrations
uv run manage.py migrate --skip-checks --no-input

# Run server
uv run --env-file=.env gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi

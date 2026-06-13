#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE='sopds.settings.base'
# Create log directory
mkdir -p log

# Create key if not exists
if [ ! -f 'secret_key.txt' ]; then
    python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' >secret_key.txt
fi

# Collect statics files
python manage.py collectstatic --skip-checks --no-input

# Run DB migrations
python manage.py migrate --skip-checks --no-input

# Run server
gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi

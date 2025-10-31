#!/usr/bin/env bash

# Create data folder
mkdir -p data

# Collect statics files
./manage.py collectstatic --skip-checks --no-input

# Run DB migrations
./manage.py migrate --skip-checks --no-input

# Run server

gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi

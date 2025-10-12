#!/usr/bin/env bash

# Create data folder
mkdir -p data

# Run DB migrations
python3 manage.py migrate

# Run development server
python3 manage.py runserver 0.0.0.0:8008

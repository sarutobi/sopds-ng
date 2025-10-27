#!/usr/bin/env bash

# Create data folder
mkdir -p data

# Run DB migrations
./manage.py migrate

# Run development server
./manage.py runserver 0.0.0.0:8008

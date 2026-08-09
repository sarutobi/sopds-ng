#!/usr/bin/env bash
SOPDS_ROOT="${SOPDS_ROOT:-/opt/sopds-ng}"
DATA_ROOT="${DATA_ROOT:-$SOPDS_ROOT/data}"
SECRET_KEY_FILE="${SECRET_KEY_FILE:-$DATA_ROOT/secret_key.txt}"
mkdir -p "$DATA_ROOT"

if [ ! -f "$SECRET_KEY_FILE" ]; then
  uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' > "$SECRET_KEY_FILE"
  echo "Secret key created: $SECRET_KEY_FILE"
else
  echo "Secret key exists: $SECRET_KEY_FILE"
fi

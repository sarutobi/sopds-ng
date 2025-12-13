#!/usr/bin/env bash
if [ ! -f 'secret_key.txt' ]; then
  uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' >secret_key.txt
fi

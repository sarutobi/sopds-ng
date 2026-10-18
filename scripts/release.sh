#!/bin/bash
set -e

# Определение версии
VERSION=$(cat version.txt 2>/dev/null || echo "1.0.0")
echo "Building release artifacts for version ${VERSION}..."

# Папка сборки
BUILD_DIR="build"
mkdir -p "$BUILD_DIR"

# 1. Сборка bare-metal архива
echo "Creating bare-metal archive..."
REL_NAME="release_${VERSION#v}"
# Копируем всё, кроме ненужных папок
tar -czf "$BUILD_DIR/${REL_NAME}.tar.gz" \
    --exclude="build" \
    --exclude=".git" \
    --exclude=".venv" \
    --exclude="tests" \
    --exclude="data" \
    --exclude="__pycache__" \
    .

# 2. Генерация Docker Compose для пользователей
echo "Generating docker-compose.yml for release..."
# Используем python для корректной трансформации YAML
python3 -c "
import yaml
import sys

try:
    with open('docker-compose.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Убираем build, ставим image
    if 'services' in config and 'web' in config['services']:
        web = config['services']['web']
        if 'build' in web:
            del web['build']
        web['image'] = 'ghcr.io/sarutobi/sopds-ng:latest'
    
    with open('$BUILD_DIR/docker-compose.yml', 'w') as f:
        yaml.dump(config, f, sort_keys=False)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

echo "Release artifacts created in $BUILD_DIR/"
echo "Artifacts: ${REL_NAME}.tar.gz, docker-compose.yml"

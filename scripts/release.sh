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

# Используем staging-директорию, чтобы очистить static и убрать кэши
STAGING_DIR="$BUILD_DIR/staging"
mkdir -p "$STAGING_DIR"
# Копируем содержимое src, исключая кэши
rsync -aq --exclude="__pycache__" --exclude="*.pyc" --exclude=".pytest_cache" --exclude=".ruff_cache" --exclude="tmp" --exclude="inpx" --exclude=".benchmarks" --exclude=".mypy_cache" --exclude=".env" src/ "$STAGING_DIR/"
# Очищаем содержимое static, оставляя саму директорию
find "$STAGING_DIR/static" -mindepth 1 -delete 2>/dev/null || true
cp version.txt $STAGING_DIR

# Добавляем необходимые файлы для развертывания (согласно quickstart.md)
# 1. deploy.sh в корень приложения
if [ -f "scripts/deploy.sh" ]; then
    cp "scripts/deploy.sh" "$STAGING_DIR/"
elif [ -f "deploy.sh" ]; then
    cp "deploy.sh" "$STAGING_DIR/"
fi

# 2. base.env для Docker-пользователей
if [ -f "base.env" ]; then
    cp "base.env" "$STAGING_DIR/"
    cp "base.env" $BUILD_DIR
fi

# 3. systemd сервис в scripts/
mkdir -p "$STAGING_DIR/scripts"
if [ -f "scripts/sopds.service" ]; then
    cp "scripts/sopds.service" "$STAGING_DIR/scripts/"
fi

# 4. start_server.sh (был в старом скрипте)
if [ -f "scripts/start_server.sh" ]; then
    cp "scripts/start_server.sh" "$STAGING_DIR/"
fi

tar -czf "$BUILD_DIR/${REL_NAME}.tar.gz" -C "$STAGING_DIR" .
rm -rf "$STAGING_DIR"

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

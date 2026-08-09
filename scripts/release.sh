#!/usr/bin/env bash

version=$(<./version.txt)
echo "Создание релиза $version"

echo "Подготовка"
rm -rf build/*
mkdir -p build/release/app
mkdir -p build/release/scripts

echo "Копирование"
# Код в app/
cp -r ./src/* build/release/app/

# Корневые файлы
cp LICENSE build/release/
cp pyproject.toml build/release/
cp src/manage.py build/release/
cp base.env build/release/
cp version.txt build/release/

# Скрипты
cp scripts/start_server.sh build/release/scripts/

echo "Очистка"
rm -rf build/release/app/inpx
find build/release/app -type f -name "*.pyc" -delete
find build/release/app -type d -name "__pycache__" -delete

echo "Копирование systemd unit"
mkdir -p build/release/etc/systemd/system
cp scripts/sopds.service build/release/etc/systemd/system/
cp scripts/check-systemd.sh build/release/scripts/
chmod +x build/release/scripts/check-systemd.sh

echo "Подготовка пакета"
cwd=$(pwd)
cd build/release
tar -czf ../release_${version}.tar.gz .
cd ..
rm -rf release/
cd $cwd
echo "Релиз ${version} создан"

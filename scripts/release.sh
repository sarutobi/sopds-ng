#!/usr/bin/env bash

echo "Подготовка"
rm -rf build/*
mkdir -p build/release

echo "Копирование"
cp -r ./src/* build/release
cp LICENSE build/release
cp pyproject.toml build/release
cp base.env build/release
cp version.txt build/release
cp scripts/create_key.sh build/release

echo "Очистка"
rm -rf build/release/inpx
rm -rf build/release/static/*
find build -type f -name "*.pyc" -delete
find build -type d -name "__pycache__" -delete

version=$(<version.txt)
echo "Создание релиза $version"
cwd=$(pwd)
cd build/release
tar -czf ../release_${version}.tar.gz .
cd ..
rm -rf release/
cd $cwd
echo "Релиз ${version} создан"

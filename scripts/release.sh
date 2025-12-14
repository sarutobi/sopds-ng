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

echo "Очистка"
rm -rf build/release/inpx
rm -rf build/release/static/*
find build -type f -name "*.pyc" -delete
find build -type d -name "__pycache__" -delete

version=$(<version.txt)
echo "Создание релиза $version"
cwd=$(pwd)
cd build/release
tar -czvf ../release_${version}.tar.gz .
cd $cwd

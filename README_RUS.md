#### SimpleOPDS Каталог НП (новое поколение) — SimpleOPDS Catalog NG
#### Based on SimpleOPDS Catalog by Dmitry V.Shelepnev
#### Author: Valery A. Ilychev
#### Версия 1.0.0RC1

[Английская версия README.md](README.md)
[Документация по развёртыванию](docs/deploy.md) |
[Документация по миграции](docs/migration.md)

Это форк проекта [SimpleOPDS Catalog](https://github.com/mitshel/sopds) Дмитрия Шелепнева. Исходный проект неактивен с апреля 2019 года.
![Пример](images/sopds-ng-1.jpg)

Относительно исходного проекта планируются следующие изменения:

1. Работа только с базой данных PostgreSQL. Django поддерживает другие СУБД, и, скорее всего, SOPDS-NG сможет работать и с mysql, и с sqlite, но это требует дополнительного тестирования.

2. Переработка базовой верстки (в процессе).

3. Возможность запустить SOPDS-NG в контейнере docker/podman (в процессе).

В настоящий момент внесены следующие изменения:

1. Исправлены выявленные ошибки; применены изменения сторонних контрибьюторов из pull-реквестов к исходному проекту.

2. Для работы приложения используется wsgi-сервер gunicorn. Встроенный сервер django не используется.

3. Структура исходного кода реорганизована для более удобного управления.

4. Используются современные инструменты управления (uv, mypy и т.п.).

Все изменения вносятся в ветку dev текущего репозитория.

#### Технический стэк

- Python 3.13

- Django 5.2

- PostgreSQL 17

- gunicorn

- docker

---

## Быстрый старт (готовый образ)

Готовые multi-arch образы (amd64/arm64) публикуются в [ghcr.io/sarutobi/sopds-ng](https://github.com/sarutobi/sopds-ng/pkgs/container/sopds-ng):

- `ghcr.io/sarutobi/sopds-ng:latest` — последняя версия из master
- `ghcr.io/sarutobi/sopds-ng:master` — ветка master
- `ghcr.io/sarutobi/sopds-ng:sha-xxxxx` — конкретный коммит

```bash
# 1. Скачайте docker-compose.yml и base.env
wget https://raw.githubusercontent.com/sarutobi/sopds-ng/master/docker-compose.yml
wget https://raw.githubusercontent.com/sarutobi/sopds-ng/master/base.env
cp base.env data/.env
# Настройте SECRET_KEY в data/.env

# 2. Измените docker-compose.yml: замените build: на image:
#   image: ghcr.io/sarutobi/sopds-ng:latest

# 3. Запустите
docker compose up -d
```

---

### Установка на «голое железо» (systemd)

1. Создайте системного пользователя:
   ```bash
   sudo useradd -r sopds
   ```

2. Распакуйте релизный архив:
   ```bash
   sudo tar -xzf release_*.tar.gz -C /opt/sopds-ng
   sudo chown -R sopds:sopds /opt/sopds-ng
   ```

3. Подготовьте директорию данных:
   ```bash
   sudo mkdir -p /opt/sopds-ng/data && sudo chown sopds:sopds /opt/sopds-ng/data
   sudo cp base.env /opt/sopds-ng/data/.env   # затем отредактируйте .env
   ```

4. Установите и запустите systemd-сервис:
   ```bash
   sudo cp etc/systemd/system/sopds.service /etc/systemd/system/sopds.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now sopds
   ```

5. Проверьте установку:
   ```bash
   /opt/sopds-ng/check-systemd.sh
   ```

Подробная инструкция — в [docs/deploy.md](docs/deploy.md).

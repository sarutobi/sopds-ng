# Быстрый старт SOPDS NG (bare-metal)

Краткая инструкция для развёртывания SOPDS NG на «голом» сервере (Debian) и работой с БД PostgreSQL.
Подробная версия — [deploy.md](deploy.md).

> **Требования:** Debian 12+, Python 3.13, uv, PostgreSQL 17.

---

## 1. Создание пользователя и директорий

```bash
sudo useradd -r sopds -d /opt/sopds-ng -s /usr/sbin/nologin
sudo mkdir -p /opt/sopds-ng/{app,data}
sudo chown -R sopds:sopds /opt/sopds-ng
```

## 2. Установка PostgreSQL


```bash
sudo apt update
sudo apt install -y postgresql-17 postgresql-client-17
sudo -iu postgres
createuser -DSRP sopds
createdb -O sopds sopds
exit
```

При создании пользователя БД будет запрошен пароль. Запомните его.

## 3. Установка uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 4. Загрузка и распаковка релиза

```bash
# Замените v1.0.0RC2 на актуальную версию
VERSION=v1.0.0RC2
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz" -O /tmp/sopds-ng.tar.gz
sudo tar -xzf /tmp/sopds-ng.tar.gz -C /opt/sopds-ng/app
```

## 5. Настройка DATA_ROOT и .env

```bash
sudo chown sopds:sopds /opt/sopds-ng/data
export DATA_ROOT=/opt/sopds-ng/data
```

> **deploy.sh автоматизирует этот шаг** — скопирует `base.env` и подставит параметры
> (DB_ENGINE, TIME_ZONE, ALLOWED_HOSTS и др.) из переданных опций. Пароль БД
> задаётся вручную после запуска deploy.sh.

Для **PostgreSQL** в `.env` должно быть:

```env
SOPDS_DB_ENGINE=postgres
SOPDS_DB_NAME=sopds
SOPDS_DB_USER=sopds
SOPDS_DB_PASSWORD=<пароль>
SOPDS_DB_HOST=localhost
SOPDS_DB_PORT=5432
```

## 6. Deploy (prepare environment)

Одноразовый скрипт установки: зависимости, миграции, статика, secret_key:

```bash
sudo -u sopds bash /opt/sopds-ng/app/deploy.sh
```

**Что делает deploy.sh:**
1. Создаёт `$DATA_ROOT/log/` и `$DATA_ROOT/static/`
2. Копирует `base.env` → `.env` и подставляет параметры
3. `uv sync --frozen --no-group dev` — установка зависимостей
4. Генерирует `secret_key.txt` (если отсутствует)
5. `collectstatic` и `migrate`

> После deploy.sh укажите пароль БД вручную: `echo "SOPDS_DB_PASSWORD='ваш_пароль'" >> $DATA_ROOT/.env`

## 7. Создание суперпользователя

```bash
cd /opt/sopds-ng/app
sudo -u sopds DATA_ROOT="$DATA_ROOT" uv run python manage.py createsuperuser
```

## 8. Проверка (dev-сервер)

```bash
cd /opt/sopds-ng/app
PORT=8080 sudo -u sopds DATA_ROOT="$DATA_ROOT" uv run gunicorn \
  --config="python:sopds.settings.gunicorn" sopds.wsgi
```

Откройте `http://<ваш-сервер>:8080/` в браузере.

## 9. Установка systemd-сервиса

> **deploy.sh уже выполнен на шаге 6.** Если нет — выполните сначала:
> `sudo -u sopds bash /opt/sopds-ng/app/deploy.sh`

```bash
# Установите systemd unit
sudo cp /opt/sopds-ng/app/scripts/sopds.service /etc/systemd/system/sopds.service
sudo systemctl daemon-reload
sudo systemctl enable sopds.service
sudo systemctl start sopds.service
sudo systemctl status sopds.service
```

---

## Известные проблемы bare-metal
### `start_server.sh` + `ProtectSystem=strict` (решено)

**Было:** `start_server.sh` при каждом запуске выполнял `uv sync --no-dev`, что конфликтовало с `ProtectSystem=strict`.

**Решение:** разделены deploy и run:
- `scripts/deploy.sh` — одноразовый setup (uv sync, migrate, collectstatic). Выполняется один раз после распаковки релиза: `sudo -u sopds bash /opt/sopds-ng/app/deploy.sh`
- `scripts/start_server.sh` — только создание `/data/log`, генерация secret_key, запуск gunicorn. Использует `.venv/bin/` напрямую, без uv.

При каждом рестарте сервиса systemd запускает только `start_server.sh` — безопасно при `ProtectSystem=strict`.

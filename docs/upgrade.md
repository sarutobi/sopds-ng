# Обновление SOPDS NG

Инструкция по обновлению существующей инсталляции SOPDS NG до новой версии.

> **Перед любым обновлением обязательно сделайте резервную копию базы данных.**
> См. раздел [Резервное копирование](#резервное-копирование).

---

## Содержание

1. [Резервное копирование](#резервное-копирование)
2. [Обновление через Docker Compose](#обновление-через-docker-compose)
3. [Обновление bare-metal](#обновление-bare-metal)
4. [Проверка после обновления](#проверка-после-обновления)
5. [Откат (rollback)](#откат-rollback)

---

## Резервное копирование

### PostgreSQL

```bash
# Остановите приложение (чтобы избежать изменений во время backup'а)
docker compose stop web
# или systemctl stop sopds

# Создайте дамп
pg_dump -U sopds -h localhost sopds > sopds-ng-db-$(date +%Y%m%d).sql

# В Docker:
docker compose exec -T db pg_dump -U postgres sopds > sopds-ng-db-$(date +%Y%m%d).sql

# Запустите приложение обратно
docker compose start web
# или systemctl start sopds
```

### SQLite

```bash
cp /data/db.sqlite3 /data/db.sqlite3.$(date +%Y%m%d)
```

### Конфигурация

```bash
# Сохраните .env и ключи
cp /data/.env /data/.env.$(date +%Y%m%d)
cp /data/secret_key.txt /data/secret_key.txt.$(date +%Y%m%d)
```

---

## Обновление через Docker Compose

### 1. Получите актуальный код

```bash
cd /opt/sopds-ng

# Если установлено через git:
git pull origin main

# Если установлено через релизный архив:
wget "https://github.com/sarutobi/sopds-ng/releases/download/v<НОВАЯ_ВЕРСИЯ>/release_<НОВАЯ_ВЕРСИЯ>.tar.gz"
tar -xzf "release_<НОВАЯ_ВЕРСИЯ>.tar.gz" -C /opt/sopds-ng
```

### 2. Пересоберите и запустите

```bash
docker compose up -d --build
```

**Что произойдёт:**

При старте контейнера `scripts/docker_entrypoint.sh` автоматически выполнит:
- `migrate` — применение новых миграций БД
- `collectstatic` — сборка статики

Никаких ручных шагов не требуется.

### 3. Проверьте

```bash
# Логи на предмет ошибок миграций
docker compose logs -f web

# HTTP-ответ
curl -I http://localhost:8008/
```

---

## Обновление bare-metal

### 1. Получите актуальный код

```bash
cd /opt/sopds-ng

# Если установлено через git:
git pull origin main

# Если установлено через релизный архив:
VERSION=v<НОВАЯ_ВЕРСИЯ>
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz"
tar -xzf "release_${VERSION#v}.tar.gz" -C /opt/sopds-ng
```

### 2. Обновите зависимости

```bash
uv sync --frozen --no-group dev
```

### 3. Остановите приложение

```bash
# systemd
sudo systemctl stop sopds

# или найдите и завершите процесс gunicorn
# ps aux | grep gunicorn
```

### 4. Примените миграции БД

```bash
export DATA_ROOT=/data
uv run python src/manage.py migrate --skip-checks --no-input
```

При наличии обратных миграций (откат схемы) выполните проверку заранее:

```bash
# Просмотр запланированных миграций (без применения)
uv run python src/manage.py showmigrations
```

### 5. Соберите статику

```bash
uv run python src/manage.py collectstatic --skip-checks --no-input
```

### 6. Запустите приложение

```bash
# systemd
sudo systemctl start sopds

# или вручную:
WEB_CONCURRENCY=2 PYTHON_MAX_THREADS=4 \
  uv run gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
```

### 7. Обновление systemd unit (если изменился)

Если в новой версии изменился systemd unit (например, добавлены security hardening или новые параметры):

```bash
# Скопируйте новый unit (если поставляется в релизе)
sudo cp deploy/sopds.service /etc/systemd/system/sopds.service

# Или обновите вручную /etc/systemd/system/sopds.service из документации

# Перезагрузите конфигурацию systemd
sudo systemctl daemon-reload

# Перезапустите сервис
sudo systemctl restart sopds

# Проверьте статус и логи
sudo systemctl status sopds
journalctl -u sopds -n 20 --no-pager
```

---

## Проверка после обновления

```bash
# HTTP-доступность
curl -I http://localhost:8008/

# Логи приложения
journalctl -u sopds -n 20 --no-pager

# Статика (должна отдаваться без ошибок 404)
curl -I http://localhost:8008/static/css/sopds.css

# Админка (проверить в браузере)
echo "Откройте http://localhost:8008/admin/constance/config/"
```

**Что проверить:**

- [ ] Главная страница OPDS открывается
- [ ] Статика грузится (CSS, изображения)
- [ ] В логах нет ошибок миграций (`Migration ... applied`)
- [ ] Сканирование библиотеки запускается
- [ ] Настройки Constance в админке не сброшены

---

## Откат (rollback)

### Через Docker

```bash
# 1. Восстановите БД из резервной копии
# PostgreSQL:
docker compose exec -T db psql -U postgres sopds < sopds-ng-db-<дата>.sql

# 2. Переключитесь на предыдущий образ
# Если образ предыдущей версии ещё есть в локальном хранилище:
docker tag sopds-ng:prod sopds-ng:prod-new  # сохранить текущий
docker tag sopds-ng:<предыдущая_версия> sopds-ng:prod
docker compose up -d

# 3. Либо откатите код через git и пересоберите
cd /opt/sopds-ng
git checkout <предыдущий_коммит>
docker compose up -d --build
```

### Bare-metal

```bash
# 1. Восстановите БД из резервной копии
# SQLite:
cp /data/db.sqlite3.<дата> /data/db.sqlite3

# PostgreSQL:
psql -U sopds -h localhost sopds < sopds-ng-db-<дата>.sql

# 2. Откатите код
cd /opt/sopds-ng
git checkout <предыдущий_коммит>

# 3. Обновите зависимости (на предыдущую версию)
uv sync --frozen --no-group dev

# 4. Примените миграции предыдущей версии
uv run python src/manage.py migrate --skip-checks --no-input

# 5. Перезапустите gunicorn
sudo systemctl restart sopds
```

> При bare-metal rollback'е миграции могут потребовать отката схемы БД.
> Django обратные миграции (`migrate <app> <номер>`) выполняются автоматически,
> если код предыдущей версии содержит соответствующие migration files.
> После rollback'а кода и `migrate` Django сама определит, какие миграции нужно откатить.

# Быстрый старт SOPDS NG

Краткая инструкция по развёртыванию SOPDS NG. Выберите подходящий вам способ установки.

---

## 1. Развёртывание через Docker (Рекомендуется)

Самый быстрый способ запустить проект со всеми зависимостями (БД PostgreSQL, приложение).

### Шаг 1: Подготовка окружения
Убедитесь, что у вас установлены [Docker](https://docs.docker.com/get-docker/) и [Docker Compose](https://docs.docker.com/compose/install/).

### Шаг 2: Загрузка конфигурации
Скачайте файлы конфигурации в рабочую директорию:
```bash
wget https://github.com/sarutobi/sopds-ng/releases/download/1.0.0/docker-compose.yml
wget https://github.com/sarutobi/sopds-ng/releases/download/1.0.0/base.env
```

### Шаг 3: Настройка переменных окружения
Создайте директорию `data` и скопируйте туда шаблон настроек:
```bash
mkdir data
cp base.env data/.env
```
Отредактируйте `data/.env`, указав следующие параметры:
```env
SOPDS_DB_NAME='sopds'
SOPDS_DB_USER='sopds'
SOPDS_DB_PASSWORD='ваш_пароль'     # Придумайте пароль
SOPDS_DB_HOST='db'
SOPDS_DB_PORT='5432'
SOPDS_BOOK_PATH='/путь/к/книгам'   # Полный путь к вашей библиотеке на хосте
```
**Важно:** Файл `docker-compose.yml` редактировать не нужно.

### Шаг 4: Запуск
Запустите контейнеры, указав путь к файлу настроек:
```bash
docker compose --env-file data/.env up -d
```

> **Внимание!** ключ `--env-file data/.env` обязателен, без него приложение не запустится

### Шаг 5: Финальная настройка
Выполните миграции БД, создайте суперпользователя и импортируйте справочник жанров:
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_genres
```

Приложение будет доступно по адресу `http://localhost:8080`.

Журналы приложения можно посмотреть в файле `data/logs/`

---

## 2. Развёртывание bare-metal (Debian)

Инструкция для установки на сервер. Подробная версия — [deploy.md](deploy.md).

> **Требования:** Debian 12+, Python 3.13, uv, PostgreSQL 17.

### Шаг 1: Создание пользователя и директорий
```bash
sudo useradd -r sopds -d /opt/sopds-ng -s /usr/sbin/nologin
sudo mkdir -p /opt/sopds-ng/{app,data}
sudo chown -R sopds:sopds /opt/sopds-ng
```

### Шаг 2: Установка PostgreSQL
```bash
sudo apt update
sudo apt install -y postgresql-17 postgresql-client-17
sudo -iu postgres <<EOF
createuser --no-createdb --no-superuser --no-createrole --pwprompt sopds
createdb -O sopds sopds
EOF
```
> **Внимание:** При создании пользователя БД будет запрошен пароль. Запомните его.

### Шаг 3: Установка uv
```bash
sudo -u sopds bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
```

### Шаг 4: Загрузка релиза
```bash
# Замените на актуальную версию
VERSION=v1.0.0
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz" -O /tmp/sopds-ng.tar.gz
sudo -u sopds tar -xzf /tmp/sopds-ng.tar.gz -C /opt/sopds-ng/app
```

### Шаг 5: Подготовка окружения (Deploy)
Установите переменную пути к данным и запустите скрипт установки:
```bash
export DATA_ROOT=/opt/sopds-ng/data
sudo -u sopds bash /opt/sopds-ng/app/deploy.sh
```
**Что делает deploy.sh:** устанавливает зависимости через `uv`, генерирует `secret_key`, собирает статику и запускает миграции.

После завершения укажите пароль БД в `.env` вручную:
```bash
sudo -u sopds bash -c "grep -q '^SOPDS_DB_PASSWORD=' $DATA_ROOT/.env && sed -i \"s/^SOPDS_DB_PASSWORD=.*/SOPDS_DB_PASSWORD='ваш_пароль'/\" $DATA_ROOT/.env || echo \"SOPDS_DB_PASSWORD='ваш_пароль'\" >> $DATA_ROOT/.env"
```

Настройте путь к каталогу с книгами:
```bash
sudo -u sopds bash -c "grep -q '^SOPDS_BOOK_PATH=' $DATA_ROOT/.env && sed -i \"s/^SOPDS_BOOK_PATH=.*/SOPDS_BOOK_PATH='/ваш/путь/каталога/книг'/\" $DATA_ROOT/.env || echo \"SOPDS_BOOK_PATH='/ваш/путь/каталога/книг'\" >> $DATA_ROOT/.env"

```

### Шаг 6: Финальная настройка
Создайте суперпользователя и импортируйте жанры:
```bash
cd /opt/sopds-ng/app
sudo -u sopds bash -l -c "DATA_ROOT=\"$DATA_ROOT\" uv run python manage.py createsuperuser"
sudo -u sopds bash -l -c "DATA_ROOT=\"$DATA_ROOT\" uv run python manage.py import_genres"
```

### Шаг 7: Установка systemd-сервиса
```bash
sudo cp /opt/sopds-ng/app/scripts/sopds.service /etc/systemd/system/sopds.service
sudo systemctl daemon-reload
sudo systemctl enable --now sopds.service
sudo systemctl status sopds.service
```
Откройте `http://<ваш-сервер>:8080/` в браузере.

Журналы приложения будут доступны в `/opt/sopds-ng/data/logs/`

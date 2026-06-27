# Инструкция миграции с SOPDS (классический) на SOPDS NG

## Содержание

1. [Обзор изменений](#обзор-изменений)
2. [Резервное копирование базы SOPDS](#резервное-копирование-базы-sopds)
3. [Установка SOPDS NG](#установка-sopds-ng)
4. [Перенос базы данных](#перенос-базы-данных)
5. [Перенос медиафайлов](#перенос-медиафайлов)
6. [Проверка работоспособности](#проверка-работоспособности)
7. [Возврат к предыдущей версии](#возврат-к-предыдущей-версии)
8. [Часто задаваемые вопросы](#часто-задаваемые-вопросы)

---

## Обзор изменений

При переходе с классического SOPDS (Simple OPDS Catalog, оригинальный проект Дмитрия Шелепнева)
на SOPDS NG (new generation) необходимо учитывать следующие архитектурные изменения:

| Аспект | SOPDS (классический) | SOPDS NG |
|--------|---------------------|----------|
| **Python** | 2.7 / 3.6–3.8 | **3.13** (строго) |
| **Django** | 1.x / 2.x | **5.2** |
| **База данных** | SQLite / MySQL | **PostgreSQL** (основная), SQLite (экспериментальная) |
| **Менеджер пакетов** | pip / requirements.txt | **uv** |
| **WSGI-сервер** | Встроенный Django / uWSGI | **Gunicorn** |
| **Статика** | django.contrib.staticfiles | **Whitenoise** (CompressedManifestStaticFilesStorage) |
| **ORM** | Частично raw-SQL | Полностью Django ORM |
| **Веб-интерфейс** | Классические HTML-шаблоны | **htmx + Alpine.js** |
| **Docker** | Отсутствует | Многостадийная сборка, docker-compose |

**Важно:** структура базы данных значительно изменена. Прямая замена файла БД из SOPDS
в SOPDS NG **недопустима**. Требуется перенос данных через дамп и загрузку с миграциями.

---

## Резервное копирование базы SOPDS

Прежде чем выполнять миграцию, обязательно создайте резервную копию текущей установки SOPDS.

### SQLite

```bash
# Остановите SOPDS
# Скопируйте файл БД
cp /path/to/sopds/db.sqlite3 /backup/sopds-backup-$(date +%Y%m%d).sqlite3

# Создайте дамп SQL (рекомендуется для переноса)
sqlite3 /path/to/sopds/db.sqlite3 .dump > /backup/sopds-dump-$(date +%Y%m%d).sql
```

### MySQL/MariaDB

```bash
# Дамп всех таблиц SOPDS
mysqldump -u root -p sopds > /backup/sopds-dump-$(date +%Y%m%d).sql

# Отдельный дамп только данных
mysqldump -u root -p --no-create-info sopds > /backup/sopds-data-$(date +%Y%m%d).sql
```

### Медиафайлы

```bash
# Скопируйте все медиафайлы (обложки, книги, иконки)
cp -r /path/to/sopds/media /backup/sopds-media-$(date +%Y%m%d)
cp -r /path/to/sopds/static /backup/sopds-static-$(date +%Y%m%d)

# Если книги хранятся отдельно — тоже скопируйте
cp -r /path/to/sopds/books /backup/sopds-books-$(date +%Y%m%d)
```

### Файлы конфигурации

```bash
cp /path/to/sopds/config.ini /backup/
cp /path/to/sopds/local_settings.py /backup/
```

---

## Установка SOPDS NG

### Вариант A: Docker (рекомендуется)

```bash
git clone https://github.com/sarutobi/sopds-ng.git /opt/sopds-ng
cd /opt/sopds-ng
cp base.env .env
# Отредактируйте .env — задайте SECRET_KEY, настройки БД
nano .env

# Запустите
docker compose up -d --build
```

### Вариант B: Bare-metal

```bash
# Установка uv (если не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Загрузка и распаковка релиза
VERSION=v1.0.0
wget "https://github.com/sarutobi/sopds-ng/releases/download/${VERSION}/release_${VERSION#v}.tar.gz"
mkdir -p /opt/sopds-ng
tar -xzf "release_${VERSION#v}.tar.gz" -C /opt/sopds-ng
cd /opt/sopds-ng

# Настройка окружения
cp base.env .env
nano .env

# Установка зависимостей
uv sync --frozen --no-group dev

# Миграции и статика
uv run python src/manage.py migrate --skip-checks --no-input
uv run python src/manage.py collectstatic --skip-checks --no-input

# Запуск
uv run gunicorn --config="python:sopds.settings.gunicorn" sopds.wsgi
```

Подробная инструкция — в [deploy.md](deploy.md).

---

## Перенос базы данных

Поскольку структура БД SOPDS NG отличается от классической, прямой перенос невозможен.
Рекомендуется выполнить полное сканирование библиотеки заново (создаст актуальную БД).

### Способ 1: Полное пересканирование (рекомендуется)

Это самый надёжный способ, гарантирующий корректную структуру данных.

```bash
# 1. Настройте SOPDS_ROOT_LIB в админке:
#    http://your-host:8008/admin/constance/config/
#    Укажите абсолютный путь к директории с книгами.

# 2. Запустите сканирование:
#    Docker:
docker compose exec web python manage.py sopds_scanner
#    Bare-metal:
uv run python src/manage.py sopds_scanner
```

Сканер создаст новую БД с нуля, просканировав все книги по указанному пути.

### Способ 2: Перенос данных через дамп (с осторожностью)

Если в старой БД есть важные пользовательские данные (избранное, настройки, история),
можно попытаться перенести их вручную.

```bash
# 1. Создайте дамп старой БД в формате SQL
# Для SQLite:
sqlite3 /backup/sopds-backup.sqlite3 .dump > /tmp/sopds_old.sql

# Для MySQL:
mysqldump -u root -p --compatible=postgresql sopds > /tmp/sopds_old.sql

# 2. Разверните чистую SOPDS NG (см. раздел "Установка")
#    Убедитесь, что миграции выполнены.

# 3. Перенос пользователей (таблица auth_user)
#    Структура auth_user идентична — можно скопировать напрямую:
#    (только для SQLite → PostgreSQL, осторожно с ID!)
#    Этот шаг требует ручного вмешательства и знания структуры БД.
```

**Внимание:** структура таблиц `opds_catalog` (книги, авторы, жанры, серии)
полностью изменена. Прямой перенос этих таблиц приведёт к ошибкам.
**Настоятельно рекомендуется Способ 1.**

---

## Перенос медиафайлов

### Обложки книг

SOPDS NG хранит обложки в директории, указанной в `MEDIA_ROOT`.
При первом сканировании библиотеки (через `sopds_scanner`) обложки извлекаются
из книг автоматически.

Если у вас есть собственная директория с обложками из старой версии:

```bash
# Скопируйте старую директорию обложек в SOPDS NG
# (путь настраивается в .env или в админке)
cp -r /backup/sopds-media/covers /opt/sopds-ng/src/media/
```

### Статические файлы

SOPDS NG использует Whitenoise с `CompressedManifestStaticFilesStorage`.
Статика собирается командой `collectstatic`. Копировать статику из старой версии не требуется.

```bash
# Просто соберите статику заново
cd /opt/sopds-ng
uv run python src/manage.py collectstatic --skip-checks --no-input
```

### Книги (исходные файлы)

Если книги хранятся там же, где и раньше — просто укажите тот же путь
в настройке `SOPDS_ROOT_LIB` (через админку или `.env`):

```env
SOPDS_BOOK_PATH=/mnt/media/books  # для Docker
# Или в админке: SOPDS_ROOT_LIB = /mnt/media/books
```

**Важно:** при монтировании в Docker книги должны быть доступны для чтения контейнеру.
Используйте абсолютные пути.

---

## Проверка работоспособности

После завершения миграции выполните следующие проверки:

### 1. Проверка веб-интерфейса

- Откройте `http://your-host:8008/` — должна отобразиться страница каталога.
- Проверьте поиск книг.
- Проверьте алфавитный указатель.
- Проверьте OPDS-ленту: `http://your-host:8008/opds/`.

### 2. Проверка сканирования

```bash
# Docker:
docker compose logs web | tail -50

# Bare-metal:
tail -f /opt/sopds-ng/src/log/sopds-scaner.log
```

Убедитесь, что:
- Сканирование завершено без ошибок.
- Книги отображаются в каталоге.
- Обложки корректно загружаются.

### 3. Проверка скачивания книг

- Откройте любую книгу в каталоге.
- Нажмите "Скачать".
- Убедитесь, что файл скачивается корректно.

### 4. Проверка административной панели

- Откройте `http://your-host:8008/admin/`.
- Войдите под учётной записью суперпользователя.
- Проверьте настройки в разделе `Constance` → `Config`.
- Проверьте, что все книги отображаются в списке в разделе `OPDS_Catalog`.

### 5. Проверка Telegram-бота (если настроен)

Отправьте команду `/start` вашему боту в Telegram — должен прийти ответ.

---

## Возврат к предыдущей версии

Если в процессе миграции возникли проблемы, вы всегда можете вернуться
к классической версии SOPDS.

### Docker

```bash
# Остановите SOPDS NG
cd /opt/sopds-ng
docker compose down

# Запустите старую версию (если она также в Docker)
cd /opt/sopds-classic
docker compose up -d

# Или просто восстановите из бекапа
cp -r /backup/sopds-media-YYYYMMDD /path/to/old/media
cp /backup/sopds-backup-YYYYMMDD.sqlite3 /path/to/old/db.sqlite3
```

### Bare-metal

```bash
# Остановите gunicorn (если запущен как демон)
sudo systemctl stop sopds-ng

# Восстановите старую версию
cd /opt/sopds-classic
# Восстановите БД
cp /backup/sopds-backup-YYYYMMDD.sqlite3 sopds/db.sqlite3
# Запустите старую версию
./bootstrap.sh
```

### Проверка работоспособности старой версии

```bash
curl http://localhost:8008/
# Если всё работает — миграция отменена.
```

### Импорт старой БД обратно

```bash
# SQLite
cp /backup/sopds-backup-YYYYMMDD.sqlite3 /path/to/sopds/db.sqlite3

# MySQL
mysql -u root -p sopds < /backup/sopds-dump-YYYYMMDD.sql
```

---

## Часто задаваемые вопросы

### Можно ли оставить SQLite?

Да, SOPDS NG поддерживает SQLite (экспериментально). Однако для production
рекомендуется PostgreSQL — он обеспечивает лучшую производительность
при больших коллекциях (50 000+ книг).

### Как перенести пользователей?

Таблица `auth_user` в Django стандартна и совместима между версиями.
Вы можете скопировать её содержимое напрямую через SQL.

### Нужно ли менять пути к книгам?

Если книги находятся на том же месте — нет. Просто укажите тот же путь
в настройке `SOPDS_ROOT_LIB`.

### Что делать, если сканирование не находит книги?

Проверьте:
1. Правильность пути в `SOPDS_ROOT_LIB`.
2. Права доступа к директории с книгами.
3. Расширения файлов: по умолчанию `.pdf .djvu .fb2 .epub .mobi`.
4. Логи сканера: `log/sopds-scaner.log`.

### Потеряю ли я настройки?

Да, настройки SOPDS NG хранятся в БД (через django-constance) и не переносятся
автоматически из старой версии. Настройте их заново в админке.

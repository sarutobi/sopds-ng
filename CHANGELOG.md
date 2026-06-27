# Changelog

Все значимые изменения проекта SOPDS NG документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
а проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0RC1] — 2026-06-27

### Added

- **htmx + Alpine.js**: полностью переработан веб-интерфейс. Динамическая подгрузка страниц,
  обновление списков книг (suggest), корректная работа Foundation после htmx-swap.
- **Content-валидаторы PDF/DJVU**: добавлена проверка MIME-типов для загружаемых книг.
- **Тестирование**:
  - Полный переход с `unittest.TestCase` на `pytest`.
  - Разделение тестов на unit, integration и acceptance.
  - Тестирование ядра (Core) — охват увеличен до 83%.
  - Фикстуры для Django, консолидация и очистка фикстур.
  - Бенчмарки (pytest-benchmark).
- **CI/CD и инструменты качества**:
  - ruff (линтер, форматтер), mypy (type checking), pre-commit.
  - Настройка coverage с исключением заменяемых модулей.
  - Настройка pytest в CI (DJANGO_SETTINGS_MODULE, SECRET_KEY, SOPDS_VERSION).
- **Docker**:
  - Многостадийная сборка (builder → final-prod / final-dev).
  - `docker-compose.yml` с сервисами web (gunicorn) + PostgreSQL 17.
  - Dev- и prod-таргеты сборки.
- **Навигация по коду**: интеграция cartog для семантического поиска и анализа кода.
- **Конвенции проекта**: AGENTS.md, CONVENTIONS.md, CONTRIBUTING.md.

### Changed

- **Замена ZipFile**: кастомная реализация ZipFile заменена на стандартный модуль `zipfile`.
- **Замена Paginator**: кастомный `OPDS_Paginator` заменён на `django.core.paginator.Paginator`.
- **Рефакторинг парсеров и MIME-детекции** — упрощена архитектура парсеров книжных форматов.
- **Web-представления на сервисы**: `sopds_web_backend/views.py` переведён на использование
  `opds_catalog/services` (Service Layer pattern).
- **Оптимизация запросов БД** — устранение N+1 запросов, оптимизация получения данных для фидов.
- **Поиск через стратегии**: введён `SearchType` (enum), поиск книг вынесен в сервисы.
- **Обновление зависимостей**: Django 5.2, lxml, python-telegram-bot==22, psycopg 3.2, whitenoise 6.11.
- **Настройки БД**: использование `SOPDS_DB_ENGINE` для выбора между postgres/SQLite.
- **Логирование**: раздельные настройки для сканера (`scanner` logger) и основного сервера.

### Fixed

- **SQL-инъекция (CRITICAL)**: замена `raw()`-запросов на ORM с параметризацией в `opds_catalog`.
- **Shell-инъекция (CRITICAL)**: устранение уязвимости в `convert_type` при работе с конвертерами
  (FB2→EPUB, FB2→MOBI).
- **Open Redirect (HIGH)**: защита `LoginView` через `url_has_allowed_host_and_scheme`.
- **htmx-поиск**: исправлена работа suggest после htmx-swap, корректный POST-запрос.
- **Обработка статики при тестах**: исправлена ошибка в тестовой среде.
- **Настройка Docker для dev/prod**: корректная передача `BUILD_TARGET`.
- **Тесты скачивания книги**: исправлены urlpatterns и параметры для корректного тестирования.
- **Обработка INPX**: книги не добавлялись из-за ошибки при сканировании ZIP в INPX.
- **Работа с ZIP при сканировании**: исправлена кодировка и чтение файлов из архива.
- **Корректировка URI обложки**: `SOPDS_NOCOVER_PATH` приведён к корректному пути.

### Security

- **SQL-инъекция**: все запросы переведены на параметризованные ORM-запросы Django.
- **Shell-инъекция**: вызовы внешних конвертеров защищены проверкой аргументов.
- **Open Redirect**: добавлена проверка `url_has_allowed_host_and_scheme` в `LoginView`.
- **ALLOWED_HOSTS**: ограничение доменов по умолчанию `[".localhost", "127.0.0.1"]`.
- **Заголовки безопасности**: использование `SecurityMiddleware` Django (HSTS, X-Content-Type-Options,
  X-Frame-Options).
- **Clickjacking**: включена защита `XFrameOptionsMiddleware`.

---

## [0.48.0] — 2025-05

### Added

- Первая версия с поддержкой Python 3.13, Django 5.2, PostgreSQL 17.
- Рефакторинг структуры проекта (src/, sopds/, opds_catalog/, sopds_web_backend/).
- Использование `uv` для управления зависимостями.
- Начальная конфигурация Docker и docker-compose.
- Базовая поддержка SQLite (экспериментальная).

[1.0.0RC1]: https://github.com/sarutobi/sopds-ng/releases/tag/v1.0.0RC1
[0.48.0]: https://github.com/sarutobi/sopds-ng/releases/tag/v0.48.0

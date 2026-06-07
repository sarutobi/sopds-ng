# Общий план оптимизации проекта

## Введение
Этот документ объединяет все задачи оптимизации, представленные в директории `.tasks`. План служит дорожной картой для системного улучшения кодовой базы проекта.

## 1. Оптимизация пакета `opds_catalog`
### 1.1. Модули ядра
- **Модели**: См. [models_optimization.md](models_optimization.md) – добавление индексов, оптимизация запросов, улучшение менеджеров.
- **Представления**: См. [views_optimization.md](views_optimization.md) – обработка ошибок, кэширование, рефакторинг.
- **Сервисы**: См. [services_optimization.md](services_optimization.md) – создание базовых классов, кэширование, замена сырых SQL.
  - **Конкретные сервисы**:
    - [book_services_optimization.md](book_services_optimization.md)
    - [authors_services_optimization.md](authors_services_optimization.md)
    - [series_services_optimization.md](series_services_optimization.md)
    - [genre_services_optimization.md](genre_services_optimization.md)
    - [catalog_services_optimization.md](catalog_services_optimization.md)
    - [counter_services_optimization.md](counter_services_optimization.md)
    - [bookshelf_services_optimization.md](bookshelf_services_optimization.md)
- **Утилиты**: См. [utils_optimization.md](utils_optimization.md) – оптимизация функций, кэширование, типизация.
- **Декораторы**: См. [decorators_optimization.md](decorators_optimization.md) – кэширование проверок аутентификации, обработка ошибок.
- **Middleware**: См. [middleware_optimization.md](middleware_optimization.md) – пересмотр стратегии кэширования, оптимизация.
- **База данных**: См. [opdsdb_optimization.md](opdsdb_optimization.md) – замена сырых SQL на ORM, транзакционная безопасность.
- **Пагинатор**: См. [opds_paginator_optimization.md](opds_paginator_optimization.md) – оптимизация для больших наборов данных, кэширование.
- **Фиды (feeds)**: См. [feeds_optimization.md](feeds_optimization.md) – кэширование фидов, оптимизация запросов к БД.
- **URL‑адреса**: См. [urls_optimization.md](urls_optimization.md) – группировка маршрутов, кэширование, производительность.
- **Приложение (apps)**: См. [apps_optimization.md](apps_optimization.md) – инициализация, регистрация сигналов, health‑checks.

### 1.2. Management commands
- **Общий план**: См. [package_optimization_plan.md](management/commands/package_optimization_plan.md) – унификация кодовой базы, тестирование.
- **Конкретные команды**:
  - [sopds_util_optimization_plan.md](management/commands/sopds_util_optimization_plan.md)
  - [sopds_scanner_optimization_plan.md](management/commands/sopds_scanner_optimization_plan.md)
  - [sopds_server_optimization_plan.md](management/commands/sopds_server_optimization_plan.md)
  - [sopds_telebot_optimization_plan.md](management/commands/sopds_telebot_optimization_plan.md)
  - [sopds_duplicates_scanner_optimization_plan.md](management/commands/sopds_duplicates_scanner_optimization_plan.md)

### 1.3. Общий план для всего пакета
- См. [package_optimization.md](package_optimization.md) – архитектурные улучшения, устранение дублирования, комплексное кэширование.

## 2. Оптимизация пакета `sopds_web_backend`
### 2.1. Основные модули
- **Модели**: См. [models_optimization.md](../sopds_web_backend/models_optimization.md) – добавление кастомных моделей, менеджеров, индексов.
- **Представления**: См. [views_optimization.md](../sopds_web_backend/views_optimization.md) – рефакторинг больших функций, использование сервисного слоя, кэширование.
- **Контекстные процессоры**: См. [processors_optimization.md](../sopds_web_backend/processors_optimization.md) – оптимизация запросов к БД, кэширование статистики.
- **Админка**: См. [admin_optimization.md](../sopds_web_backend/admin_optimization.md) – регистрация моделей, кастомные ModelAdmin, административные действия.
- **URL‑адреса**: См. [urls_optimization.md](../sopds_web_backend/urls_optimization.md) – замена re_path на path, группировка, кэширование.
- **Настройки**: См. [settings_optimization.md](../sopds_web_backend/settings_optimization.md) – документация, валидация, конфигурируемость.
- **Приложение (apps)**: См. [apps_optimization.md](../sopds_web_backend/apps_optimization.md) – расширение конфигурации, регистрация сигналов.

### 2.2. Общий план для всего пакета
- См. [package_optimization.md](../sopds_web_backend/package_optimization.md) – единая архитектура, устранение дублирования, мониторинг.

## 3. Оптимизация пакета `book_tools`
### 3.1. Модули форматов (`book_tools/format`)
- **Общий план**: См. [overall_optimization.md](book_tools/format/overall_optimization.md) – удаление классов `_new`, создание единого интерфейса.
- **Конкретные форматы**:
  - [fb2_optimization.md](book_tools/format/fb2_optimization.md) – упрощение иерархии, оптимизация памяти.
  - [fb2sax_optimization.md](book_tools/format/fb2sax_optimization.md) – интеграция или удаление SAX‑парсера.
  - [epub_optimization.md](book_tools/format/epub_optimization.md) – разделение большого класса EPub.
  - [mobi_optimization.md](book_tools/format/mobi_optimization.md) – удаление Mobipocket_new, рефакторинг.
  - [other_optimization.md](book_tools/format/other_optimization.md) – удаление Dummy_new.
  - [mimetype_optimization.md](book_tools/format/mimetype_optimization.md) – исправление метода `mime_by_type`.
  - [util_optimization.md](book_tools/format/util_optimization.md) – реализация `minify_cover`, типизация.
  - [bookfile_optimization.md](book_tools/format/bookfile_optimization.md) – завершение абстрактного класса BookFile.
  - [parsers_optimization.md](book_tools/format/parsers_optimization.md) – завершение новой архитектуры парсеров.
  - [aes_optimization.md](book_tools/format/aes_optimization.md) – удаление или восстановление модуля шифрования.
- **Инициализация пакета**: См. [__init___optimization.md](book_tools/format/__init___optimization.md) – вынесение определения MIME‑типов, фабрика.

### 3.2. Сервисы и утилиты
- **Сервисы**: См. [optimization_services.md](book_tools/optimization_services.md) – рефакторинг `create_bookfile_service`, улучшение валидаторов.
- **Исключения**: См. [optimization_exceptions.md](book_tools/optimization_exceptions.md) – расширение иерархии, структурированные данные.
- **Производительность**: См. [optimization_performance.md](book_tools/optimization_performance.md) – потоковая обработка, кэширование, асинхронность.
- **Зависимости**: См. [optimization_dependencies.md](book_tools/optimization_dependencies.md) – реорганизация пакетов, устранение циклических импортов.

## 4. Приоритеты и порядок выполнения
1. **Высокий приоритет**:
   - Исправление критических ошибок (например, `mime_by_type` в mimetype.py).
   - Удаление дублирующихся классов (`_new`).
   - Добавление базового кэширования в ключевых сервисах.
2. **Средний приоритет**:
   - Рефакторинг больших классов (EPub, Mobipocket).
   - Замена сырых SQL на ORM.
   - Внедрение единых интерфейсов для парсеров.
3. **Низкий приоритет**:
   - Оптимизация производительности (асинхронная обработка, потоковые чтения).
   - Расширение мониторинга и метрик.
   - Улучшение документации.

## 5. Ожидаемые результаты
- Увеличение производительности на 20‑40% в критичных участках.
- Упрощение поддержки и расширения кода.
- Улучшение обработки ошибок и логирования.
- Снижение потребления памяти при работе с большими файлами.

## 6. Следующие шаги
1. Создать отдельные задачи (issues) на основе каждого подпункта.
2. Начать реализацию с модулей, имеющих наивысший приоритет.
3. После каждого этапа проводить тестирование и замеры производительности.
4. Документировать изменения в CHANGELOG.

---
*Этот план составлен на основе задач, размещённых в `.tasks`. Все ссылки ведут к соответствующим файлам в этой директории.*

# Конвенции проекта SOPDS NG

## 1. Общие стандарты

- **Python:** `==3.13.*`, управление зависимостями через `uv`, виртуальное окружение `.venv`.
- **Форматирование:** `ruff` (line-length=88, double quotes, docstring-code-format).
- **Отступы:** 4 пробела, никаких табуляций (кроме Makefile).
- **Импорты:** Группировка: стандартные библиотеки → сторонние → локальные. Каждая группа отделена пустой строкой. Без `import *`.
- **Структура:** Исходный код в `src/`, тесты в `tests/`, фикстуры в `tests/fixtures/`.
- **Контекстные менеджеры:** При работе с ресурсами (файлы, соединения) — `with`.

## 2. Именование

| Сущность | Стиль | Пример |
|---|---|---|
| Переменные, функции | `snake_case` | `book_count`, `get_author()` |
| Классы | `PascalCase` | `BookService`, `AuthorQuerySet` |
| Константы | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_PORT` |
| Приватные атрибуты/методы | `_leading_underscore` | `_parse_fb2()` |
| Файлы фикстур | `fixture_*.py` | `fixture_models.py` |

## 3. Типизация

- Аннотации типов для всех публичных функций и методов.
- Использовать `|` вместо `Optional`/`Union` (Python 3.10+).
- `list[X]` вместо `List[X]`, `dict[K, V]` вместо `Dict[K, V]`.

```python
def get_author_books(author_id: int) -> list[Book] | None:
    ...
```

## 4. Документирование

- Docstrings в стиле **ReST** для всех публичных модулей, классов и функций.
- Комментарии и docstrings — на русском языке.

```python
def connect_db(host: str, port: int) -> Connection:
    """Устанавливает соединение с базой данных.

    :param host: Адрес сервера.
    :type host: str
    :param port: Порт подключения.
    :type port: int
    :returns: Объект соединения.
    :rtype: Connection
    :raises ConnectionError: Если не удалось соединиться.
    """
```

## 5. Логирование

- Только `logging`, без `print()`.
- Иерархические логгеры через `logging.getLogger(__name__)`.
- Настройка логгера — один раз на уровне приложения.

## 6. Обработка ошибок

- Конкретные типы исключений в `except`, никаких голых `except:`.
- Обязательная привязка через `as`.
- Логировать или пробрасывать ошибку, никаких `pass`.

```python
try:
    result = process(data)
except ValueError as err:
    logger.error("Ошибка обработки: %s", err)
    raise
```

## 7. Тестирование

- Фреймворк: `pytest`.
- Запуск: `just test` (или `python -m pytest tests/ --ds=sopds.settings.test`).
- Фикстуры: в `tests/fixtures/`, сгруппированы по модулям, реэкспорт через `__init__.py`.
- Доступность фикстур: через `pytest_plugins` в `conftest.py`, без `from .fixtures import *`.
- Параметризация: `@pytest.mark.parametrize` для исключения дублирования.
- Бенчмарки: `just benchmark`.

## 8. Git

- **Ветки:** `dev` — основная разработка, `main` — стабильный релиз.
- **Сообщения коммитов:** [Conventional Commits](https://www.conventionalcommits.org/).
  - `feat:` — новая функциональность
  - `fix:` — исправление ошибки
  - `refactor:` — рефакторинг без изменения поведения
  - `test:` — изменения в тестах
  - `docs:` — документация
  - `chore:` — обслуживание (зависимости, CI, конфиги)
- Один коммит = одно логическое изменение.

## 9. Django

- **Settings-модули:** `sopds.settings.base` (prod), `sopds.settings.local` (dev), `sopds.settings.test` (тесты).
- **Миграции:** создавать через `python src/manage.py makemigrations`, коммитить в репозиторий.
- **Модели:** наследовать от `django.db.models.Model`, именовать в единственном числе (`Book`, `Author`).

## 10. Docker

- **Dev:** `docker compose up -d` (web + db).
- **Тестовый postgres:** `just postgres_start` (порт 5433, чтобы не конфликтовать с основным).
- **Production:** `docker compose up -d` с `.env` из `base.env`.

## 11. Justfile

Основные команды:

| Команда | Описание |
|---|---|
| `just test` | Запуск тестов (sqlite) |
| `just benchmark` | Только бенчмарки |
| `just coverage` | Покрытие кода |
| `just lint` | ruff check |
| `just format` | ruff format |
| `just typecheck` | mypy |
| `just postgres_tests` | Тесты на postgres |
| `just up` / `just down` | Docker compose |

## 12. Примеры

| Ситуация | Плохо | Хорошо |
|---|---|---|
| Импорты | `import os, sys` | `import os`<br>`import sys` |
| Функция без типов | `def process(data):` | `def process(data: list[dict]) -> list[dict]:` |
| Длинная строка | `print(f"User {user.name} created at {datetime.now()}")` | `print(f"User {user.name} "`<br>`      f"created at {datetime.now()}")` |
| Условие | `if user and user.is_active and user.has_permission('edit'):` | `can_edit = user and user.is_active and user.has_permission('edit')`<br>`if can_edit:` |

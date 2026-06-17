# SOPDS NG — Coding Conventions for AI Assistants

## Project structure
- `src/sopds_web_backend/` — Django приложение
- `src/book_tools/` — парсеры книг (FB2, EPUB)
- `src/inpx/` — INPX коллекции
- `tests/` — тесты, структура зеркалирует `src/`

## Style
- **Python:** `==3.13.*`, `uv` для зависимостей
- **Formatter:** ruff (line-length=88, double quotes)
- **Импорты:** stdlib → third-party → local, без `import *`
- **Типизация:** аннотации для всех публичных функций, `|` вместо `Optional`/`Union`

## Documentation
- Docstrings в стиле **ReST** для всех публичных модулей, классов и функций.
- Комментарии и docstrings — на русском языке.

## Testing
- **Запуск:** `just test` или `python -m pytest tests/ --ds=sopds.settings.test`
- **Фикстуры:** в `tests/fixtures/`, файлы `fixture_*.py`, реэкспорт через `__init__.py`
- **Доступность:** через `pytest_plugins` в `conftest.py`, НЕ через `from .fixtures import *`
- **Бенчмарки:** `just benchmark`
- **Postgres:** `just postgres_tests`

## Django
- Settings: `sopds.settings.base` (prod), `.local` (dev), `.test` (tests)
- Модели: единственное число (`Book`, `Author`)

## Git
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Ветки: `dev` — разработка, `main` — стабильный релиз

## Commands
| Команда | Описание |
|---|---|
| `just test` | Все тесты (sqlite) |
| `just benchmark` | Бенчмарки |
| `just coverage` | Покрытие |
| `just lint` | ruff check |
| `just format` | ruff format |
| `just typecheck` | mypy |
| `just postgres_tests` | Тесты на postgres |

## Cartog — навигация по коду через граф

Проект проиндексирован [Cartog](https://github.com/jrollin/cartog). MCP-инструменты cartog
возвращают структурированные результаты за микросекунды — дешевле grep + read.

**Используй cartog когда нужно:**
- «где определён X?» → `mcp_cartog_cartog_search`
- «кто вызывает/импортирует/наследует X?» → `mcp_cartog_cartog_refs`
- «что вызывает X?» → `mcp_cartog_cartog_callees`
- «что сломается, если изменить X?» → `mcp_cartog_cartog_impact`
- «дерево наследования X» → `mcp_cartog_cartog_hierarchy`
- «что импортирует файл F?» → `mcp_cartog_cartog_deps`
- «структура файла F» → `mcp_cartog_cartog_outline`
- «найди код по смыслу» → `mcp_cartog_cartog_rag_search`
- «ориентиры в репозитории» → `mcp_cartog_cartog_map`
- «что недавно изменилось?» → `mcp_cartog_cartog_changes`
- «здоров ли индекс?» → `mcp_cartog_cartog_stats`

**grep / Read — только если:**
- ищешь строковый литерал, комментарий, конфиг, не-код
- целевой файл вне корня индекса
- cartog вернул пустой результат

## Rules for AI
1. Читай файлы перед изменениями — не угадывай API.
2. Не добавляй комментарии «сгенерировано ИИ».
3. После изменений проверяй тесты (`just test`).
4. Не создавай файлы без явной команды пользователя.
5. Docstrings и комментарии — на русском.

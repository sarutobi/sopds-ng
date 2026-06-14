# Contributing to SOPDS NG

## Ветки

- `dev` — основная ветка разработки. Все PR направляются сюда.
- `main` — стабильный релиз. Мержится из `dev` после тестирования.

## Коммиты

Формат — [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <описание>
```

**Типы:**

| Тип | Когда использовать |
|---|---|
| `feat` | Новая функциональность |
| `fix` | Исправление ошибки |
| `refactor` | Рефакторинг без изменения поведения |
| `test` | Добавление/изменение тестов |
| `docs` | Документация |
| `chore` | Обслуживание (зависимости, CI, конфиги) |

**Примеры:**
```
feat(tests): add postgres test runner
fix(parser): handle empty FB2 description
refactor(models): extract AuthorQuerySet
```

Один коммит = одно логическое изменение.

## Процесс PR

1. Создать ветку от `dev`: `git checkout -b feat/my-feature`
2. Внести изменения, закоммитить
3. Убедиться, что тесты проходят:

   ```bash
   just test
   ```

4. Открыть Pull Request в `dev`

## Code Review

- Код форматируется `ruff` — настройки в `pyproject.toml`.
- Типы проверяются `mypy` — исключения только для архитектурно необходимых.
- Тесты обязательны для новой функциональности и исправлений.
- Docstrings — на русском, стиль ReST для публичных API.

## Перед отправкой

```bash
just lint        # ruff check
just format      # ruff format
just test        # pytest
just typecheck   # mypy (по возможности)
```

## Окружение

```bash
uv sync --group dev
pre-install      # pre-commit install (рекомендуется)
```

Полные конвенции — в `CONVENTIONS.md`.
Для AI-ассистентов — `AGENTS.md`.

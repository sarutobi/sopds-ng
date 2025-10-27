# Project dev image build

FROM python:3.13-slim AS build

ARG python_version=3.13
ARG project_name='app'
# Установка параметров shell:
# -e мгновенные выход в случае ошибки
# -x печать команд в поток STDERR
SHELL ["/bin/sh", "-exc"]

# Копируем uv из официального образа
COPY --link --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv

# Задаём переменные окружения.
# UV_PYTHON — фиксирует версию Python.
# UV_PYTHON_DOWNLOADS — отключает автоматическую загрузку отсутствующих версий Python.
# UV_PROJECT_ENVIRONMENT — указывает путь к виртуальному окружению Python.
# UV_LINK_MODE — меняет способ установки пакетов из глобального кэша.
#   Вместо создания жёстких ссылок, файлы пакета копируются в директорию  виртуального окружения `site-packages`.
#   Это необходимо для будущего копирования изолированной `/app` директории из  стадии `build` в финальный Docker-образ.
# UV_COMPILE_BYTECODE — включает компиляцию файлов Python в байт-код после установки.
# https://docs.astral.sh/uv/configuration/environment/
# PYTHONOPTIMIZE — убирает инструкции `assert` и код, зависящий от значения  константы `__debug__`,
#   при компиляции файлов Python в байт-код.
# https://docs.python.org/3/using/cmdline.html#environment-variables
ENV UV_PYTHON="python$python_version" \
  UV_PYTHON_DOWNLOADS=never \
  UV_PROJECT_ENVIRONMENT="/$project_name" \
  UV_LINK_MODE=copy \
  UV_COMPILE_BYTECODE=1 \
  PYTHONOPTIMIZE=1
# Копируем файлы, необходимые для установки зависимостей без кода проекта, так как обычно зависимости меняются реже кода.
COPY pyproject.toml uv.lock /_project/
# Для быстрой локальной установки зависимостей монтируем кэш-директорию, в которой будет храниться глобальный кэш uv.
# Первый вызов `uv sync` создаёт виртуальное окружение и устанавливает зависимости без текущего проекта.
# Опция `--frozen` запрещает обновлять `uv.lock` файл.
RUN --mount=type=cache,destination=/root/.cache/uv <<EOF
cd /_project
uv sync \
  --no-install-project \
  --frozen
EOF

# Переключаемся на интерпретатор из виртуального окружения.
ENV UV_PYTHON=$UV_PROJECT_ENVIRONMENT

#COPY VERSION /_project/
#COPY src/ /_project/src

# Устанавливаем текущий проект.
# Опция `--no-editable` отключает установку проекта в  режиме "editable".
#   Код проекта копируется в директорию виртуального окружения `site-packages`.
RUN --mount=type=cache,destination=/root/.cache/uv <<EOF
cd /_project
uv sync \
  --no-editable \
  --frozen
EOF

# Финальный этап.
FROM python:3.13-slim AS final

# Два следующих аргумента позволяют изменить UID и GID пользователя Docker-контейнера.
ARG user_id=1000
ARG group_id=1000
ARG python_version=3.12
ARG project_name="app"

ENTRYPOINT ["./bootstrap.sh"]
# Для приложений на Python лучше использовать сигнал SIGINT, так как не все фреймворки (например, gRPC) корректно обрабатывают сигнал SIGTERM.
STOPSIGNAL SIGINT
EXPOSE 8008/tcp

SHELL ["/bin/sh", "-exc"]

# Создаём группу и пользователя с нужными ID.
# Если значение ID больше нуля (исключаем "root" ID) и в системе уже есть пользователь или группа с указанным ID,
# пересоздаём пользователя или группу с именем "app".
RUN <<EOF
[ $user_id -gt 0 ] && user="$(id --name --user $user_id 2> /dev/null)" && userdel "$user"

if [ $group_id -gt 0 ]; then
  group="$(id --name --group $group_id 2> /dev/null)" && groupdel "$group"
  groupadd --gid $group_id $project_name
fi

[ $user_id -gt 0 ] && useradd --uid $user_id --gid $group_id --home-dir "/$project_name" $project_name

EOF

# Устанавливаем системные пакеты для запуска проекта.
# Обратите внимание, что в именах пакетов нет суффиксов "dev".
#RUN <<EOF
# apt-get update --quiet
# apt-get install --quiet --no-install-recommends --assume-yes \
#   libpq5 \
#   "python$python_version"
# rm -rf /var/lib/apt/lists/*
# EOF

# Задаём переменные окружения.
# PATH — добавляет директорию виртуального окружения `bin` в начало списка директорий с исполняемыми файлами.
#   Это позволяет запускать Python-утилиты из любой директории контейнера без указания полного пути к файлу.
# PYTHONOPTIMIZE — указывает интерпретатору Python, что нужно использовать ранее скомпилированные файлы из  директории `__pycache__` с  суффиксом `opt-1` в имени.
# PYTHONFAULTHANDLER — устанавливает обработчики ошибок для дополнительных сигналов.
# PYTHONUNBUFFERED — отключает буферизацию для потоков stdout и stderr.
# https://docs.python.org/3/using/cmdline.html#environment-variables
ENV PATH="/$project_name/bin":$PATH \
  PYTHONOPTIMIZE=1 \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1


#COPY --chown=$user_id:$group_id etc/ /app/etc
# Копируем директорию с виртуальным окружением из предыдущего этапа.
COPY --link --chown=$user_id:$group_id --from=build "/$project_name/" "/$project_name"

USER $user_id:$group_id
#WORKDIR /app
WORKDIR "/$project_name/src"
COPY bootstrap.sh .

# Выводим информацию о текущем окружении и проверяем работоспособность импорта модуля проекта.
RUN <<EOF
ls -la
python --version
python -I -m site
EOF

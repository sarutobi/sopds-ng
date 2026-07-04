## Variables
set dotenv-filename := ".test.env"
set dotenv-load := true
export PYTHONDONTWRITEBYTECODE := '1'

django_settings := 'sopds.settings.test'

set quiet

# ═══════════════════════════════════════════════
# Dev — local development
# ═══════════════════════════════════════════════

# Default command to run
default:
    @just --list

# Private: run uv commands
[private]
_run *args:
    uv run --env-file={{ invocation_directory() }}/.test.env {{ args }}

# Sync dependencies
setup:
    uv sync --frozen

# Run DB migrations
migrate:
    just _run python src/manage.py migrate --skip-checks --no-input

# Collect static files
collectstatic:
    just _run python src/manage.py collectstatic --skip-checks --no-input

# Run development server
runserver *args='0.0.0.0:8000':
    just _run python src/manage.py runserver {{ args }}

# ═══════════════════════════════════════════════
# Test — run tests
# ═══════════════════════════════════════════════

# Run sqlite3 tests
test *args:
    just _run pytest --benchmark-disable --ds={{ django_settings }} {{ args }}

# Run only benchmarks
benchmark:
    just test --benchmark-enable -m benchmark

# Generate coverage report
coverage *args:
    just test --cov=src --cov-report=term-missing:skip-covered --cov-report=html
    @echo "HTML report: file://$$(pwd)/htmlcov/index.html"

# ═══════════════════════════════════════════════
# Check — quality gates
# ═══════════════════════════════════════════════

# Lint check
lint:
    just _run ruff check src tests

# Auto-format
format:
    just _run ruff format src tests

# Type check
typecheck:
    just _run mypy src

# ═══════════════════════════════════════════════
# DB — database management (test containers)
# ═══════════════════════════════════════════════

# Kill postgres container
postgres_stop:
    docker rm -f sopds-postgres-test 2>/dev/null; true

# Wait for postgres to be ready
[private]
_postgres_wait:
    @echo "Waiting for postgres..."
    @sh -c 'for i in $$(seq 1 30); do \
        if docker exec sopds-postgres-test pg_isready -U postgres 2>/dev/null; then \
            echo "Postgres ready"; exit 0; \
        fi; \
        sleep 1; \
    done; echo "Postgres not ready after 30s"; exit 1'

# Run postgres container
postgres_start:
    just postgres_stop
    docker run -d -e POSTGRES_DB=sopds \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=123456 \
        -p 5433:5432 \
        --name sopds-postgres-test postgres:17
    just _postgres_wait

# Run postgres tests
postgres_tests *args:
    @CONTAINER_RUNNING=$$(docker ps -q -f name=sopds-postgres-test); \
    if [ -z "$$CONTAINER_RUNNING" ]; then \
        just postgres_start; \
        trap 'just postgres_stop' EXIT; \
    fi
    just _run pytest {{ args }}

# ═══════════════════════════════════════════════
# Docker — compose management
# ═══════════════════════════════════════════════

# Start up containers
up:
    @docker compose up -d --remove-orphans

# Stop and remove containers
down:
    @docker compose down

# Restart containers
restart-all:
    @docker compose restart

# Show container log
logs +args:
    @docker compose logs {{args}}

# Run container shell
shell +args:
    @docker compose exec -it {{args}} /bin/bash

# Rebuid containers
rebuild-containers:
    @docker compose up -d --build --remove-orphans

# Execute commands for django
django *args:
    @docker compose exec -it web ./manage.py {{args}}

# ═══════════════════════════════════════════════
# Frontend — build assets
# ═══════════════════════════════════════════════

# Create docker image for foundation
prepare-foundation:
    @docker build -t foundation -f compose/foundation/Dockerfile .

# Run commands to build frontend
run-frontend *args:
    @docker run --rm -v ./assets/sopds-sass/package.json:/foundation/package.json \
        -v ./assets/sopds-sass/gulpfile.babel.js:/foundation/gulpfile.babel.js \
        -v ./assets/sopds-sass/config.yml:/foundation/config.yml \
        -v ./assets/sopds-sass/js/:/foundation/src/assets/js/ \
        -v ./assets/sopds-sass/scss/:/foundation/src/assets/scss/ \
        -v ./tmp/target/:/foundation/target \
        foundation {{args}}

# Build dev frontend
build-dev-frontend:
    @just run-frontend yarn buildd
    @cp -r tmp/target/dist/assets/css src/sopds_web_backend/static/
    @cp -r tmp/target/dist/assets/js src/sopds_web_backend/static/

# Build production frontend
build-frontend:
    @just run-frontend yarn build
    @rm -rf src/sopds_web_backend/static/{css,js}
    @cp -r tmp/target/dist/assets/css src/sopds_web_backend/static/
    @cp -r tmp/target/dist/assets/js src/sopds_web_backend/static/

# Run shell in frontend container
frontend-shell:
    @docker run -it --rm -v ./assets/sopds-sass/package.json:/foundation/package.json \
        -v ./assets/sopds-sass/gulpfile.babel.js:/foundation/gulpfile.babel.js \
        -v ./assets/sopds-sass/config.yml:/foundation/config.yml \
        -v ./assets/sopds-sass/scss/:/foundation/src/assets/scss/ \
        -v ./assets/sopds-sass/js/:/foundation/src/assets/js/ \
        -v ./tmp/target/:/foundation/target \
        foundation /bin/bash

# Collect translation messages
collect-django-messages *locale='ru':
    just django makemessages --locale {{ locale }} --ignore book_tools --ignore inpx --ignore manage.py --ignore sopds

# ═══════════════════════════════════════════════
# Build — release packages
# ═══════════════════════════════════════════════

# Clean release dir
clean-release:
    rm -rf ./build/release*

# Clean debug dir
clean-dev:
    rm -rf ./build/debug

# Build release
build-release: (clean-release)
    scripts/release.sh

# Build debug version
build-dev: (clean-dev)
    @mkdir -p build/debug
    @rm -f src/bootstrap.sh
    @cp -lr src/* build/debug
    @cp -lr requirements build/debug
    @cp bootstrap.sh build/debug/
    @chmod +x build/debug/bootstrap.sh
    @rm -rf build/debug/assets
    @rm -rf build/debug/static
    @rm -rf build/debug/.pytest_cache

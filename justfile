## Variables
#export COMPOSE_FILE := "docker-compose.local.yml"
export PYTHONDONTWRITEBYTECODE := '1'

db_name := 'sopds'
db_user := 'postgres'
db_port := '5433'
db_host := 'localhost'
db_password := '123456'

set quiet

## Receipts
# Default command to run
default:
    @just --list

# Run uv commands
_run *args:
    uv run --env-file={{ invocation_directory() }}/.test.env {{ args }}

# Kill postgres container
postgres_stop:
    docker rm -f sopds-postgres-test

# Run postgres container
postgres_start:
    just postgres_stop
    docker run -d -e POSTGRES_DB={{ db_name }} -e POSTGRES_USER={{ db_user }} -e POSTGRES_PASSWORD={{ db_password }} -p {{ db_port }}:5432 --name sopds-postgres-test postgres:17

# Run sqlite3 tests
test *args:
    just _run pytest --benchmark-disable --ds=sopds.settings.test {{ args }}

# Run only benchmarks
benchmark:
    just test --benchmark-enable -m benchmark

# Generate coverage report
coverage *args:
    just test --cov=src --cov-report=term-missing:skip-covered --cov-report=html
# Run postgres tests
postgres_tests *args:
    just postgres_start
    just _run pytest {{ args }}
    just postgres_stop


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
    just down
    @docker compose build --progress=plain
    just up

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
    @cp pytest.ini build/debug/
    @cp bootstrap.sh build/debug/

    @chmod +x build/debug/bootstrap.sh

    @rm -rf build/debug/assets
    @rm -rf build/debug/static
    @rm -rf build/debug/.pytest_cache

    just build_containers

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

# Execute commands for django
django *args:
    @docker compose exec -it web ./manage.py {{args}}

collect-django-messages:
    just django makemessages --locale ru --ignore book_tools --ignore inpx --ignore manage.py --ignore sopds


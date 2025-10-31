## Variables
#export COMPOSE_FILE := "docker-compose.local.yml"

## Receipts
# Default command to run
default:
    @just --list

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
    mkdir -p build/release
    cp -r src/ build/release/sopds-ng
    rm -rf build/release/sopds-ng/assets
    cp -r requirements build/release
    find build/release -type f -name "local.*" -delete

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

# Run tests 
tests *args:
    @docker compose exec -it web pytest --ds=sopds.settings.local {{args}}

# Run commands to build frontend
run-frontend *args:
    @docker run --rm -v ./assets/sopds-sass/package.json:/foundation/package.json \
        -v ./assets/sopds-sass/gulpfile.babel.js:/foundation/gulpfile.babel.js \
        -v ./assets/sopds-sass/config.yml:/foundation/config.yml \
        -v ./assets/sopds-sass/scss/:/foundation/src/assets/scss/ \
        -v ./tmp/target/:/foundation/target \
        foundation {{args}}

# Build dev frontend
build-dev-frontend:
    @just run-frontend yarn buildd
    @cp -r tmp/target/dist/assets/css src/sopds_web_backend/static/
    @cp -r tmp/target/dist/assets/js src/sopds_web_backend/static/

# Run shell in frontend container
frontend-shell:
    @docker run -it --rm -v ./assets/sopds-sass/package.json:/foundation/package.json \
        -v ./assets/sopds-sass/gulpfile.babel.js:/foundation/gulpfile.babel.js \
        -v ./assets/sopds-sass/config.yml:/foundation/config.yml \
        -v ./assets/sopds-sass/scss/:/foundation/src/assets/scss/ \
        -v ./tmp/target/:/foundation/target \
        foundation /bin/bash


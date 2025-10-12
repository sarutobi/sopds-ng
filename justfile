## Variables
export COMPOSE_FILE := "docker-compose.local.yml"

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
restart:
    @docker compose restart

# Show container log
logs +args:
    @docker compose logs {{args}}


# Run container shell
shell +args:
    @docker compose exec -it {{args}} /bin/bash

# Rebuid containers
build_containers: 
    just down
    @docker compose build --no-cache --progress=plain
    just up

# Clean release dir
clean_release:
    rm -rf ./build/release*

# Clean debug dir
clean_dev:
    rm -rf ./build/debug

# Build release
build_release: (clean_release)
    mkdir -p build/release
    cp -r src/ build/release/sopds-ng
    rm -rf build/release/sopds-ng/assets
    cp -r requirements build/release
    find build/release -type f -name "local.*" -delete

# Build debug version
build_dev: (clean_dev)
    mkdir -p build/debug
    rm src/bootstrap.sh
    cp -lr src/* build/debug
    cp -lr requirements build/debug
    cp pytest.ini build/debug/
    cp bootstrap.sh build/debug/

    chmod +x build/debug/bootstrap.sh

    rm -rf build/debug/assets
    rm -rf build/debug/static
    rm -rf build/debug/.pytest_cache

    just build_containers

# Create docker image for foundation
prepare_foundation:
    docker build -t foundation -f foundation/Dockerfile .

# Run tests 
tests *args:
    docker compose exec -it web pytest --ds=sopds.settings.local {{args}}

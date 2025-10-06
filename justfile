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
    @docker compose build
    just up

# Clean release dir
[working-directory: 'build']
clean_release:
    rm -rf release*
    mkdir -p release

# Build release
build_release: (clean_release)
    cp -r src/ build/release/sopds-ng
    rm -rf build/release/sopds-ng/assets
    cp -r requirements build/release
    find build/release -type f -name "local.*" -delete

# Create docker image for foundation
prepare_foundation:
    docker build -t foundation -f foundation/Dockerfile .

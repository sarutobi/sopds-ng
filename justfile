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

# Buid containers
build: 
    just down
    @docker compose build
    just up

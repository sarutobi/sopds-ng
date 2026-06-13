# syntax=docker/dockerfile:1
ARG BUILD_TARGET=dev

# ============================================================
# Stage 1: build dependencies (common for both targets)
# ============================================================
FROM python:3.13-slim AS builder

ARG BUILD_TARGET

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies based on target
RUN if [ "$BUILD_TARGET" = "dev" ]; then \
    uv sync --frozen --no-install-project --group dev; \
    else \
    uv sync --frozen --no-install-project; \
    fi

# Copy source code
COPY src/ ./src/

# Copy version file
COPY version.txt ./

# Install the project itself
RUN uv sync --frozen --no-editable

# ============================================================
# Stage 2: final image (production)
# ============================================================
FROM python:3.13-slim AS final-prod

ARG BUILD_TARGET

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app/src

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/version.txt /app/src/

# Copy entrypoint script
COPY scripts/docker_entrypoint.sh /app/src/

EXPOSE 8008

CMD ["./docker_entrypoint.sh"]

# ============================================================
# Stage 3: development image (default target)
# ============================================================
FROM python:3.13-slim AS final-dev

ARG BUILD_TARGET

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app/src

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/version.txt /app/src/
# Copy entrypoint script
COPY scripts/docker_entrypoint.sh /app/src/

EXPOSE 8008

CMD ["./docker_entrypoint.sh"]

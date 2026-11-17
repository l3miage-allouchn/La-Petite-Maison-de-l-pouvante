# syntax=docker/dockerfile:1
# Multi-stage build with uv: locked dependencies only (uv.lock), slim runtime, non-root user.

FROM ghcr.io/astral-sh/uv:0.13.8 AS uv

# ---------- build ----------
FROM python:3.14.9-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
# --frozen: fail if uv.lock is out of date (reproducible, reviewed dependencies)
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY app/ app/

# ---------- runtime ----------
FROM python:3.14.9-slim-trixie

LABEL org.opencontainers.image.title="reco-service" \
      org.opencontainers.image.description="La Petite Maison de l'Épouvante - recommendations" \
      org.opencontainers.image.source="https://github.com/l3miage-allouchn/La-Petite-Maison-de-l-pouvante" \
      org.opencontainers.image.licenses="MIT"

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

# Code and virtualenv stay owned by root: the app user cannot modify them.
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/app /app/app
WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-server-header"]

# Image Web — même patron que l'API (port 8080).
# Contexte de build attendu : la racine du repo (cf. infra/compose.yaml).

FROM ghcr.io/astral-sh/uv:0.8.17 AS uv-bin

FROM python:3.12-slim-bookworm AS builder
COPY --from=uv-bin /uv /bin/uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY web/pyproject.toml web/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-workspace --package sia-web
COPY web/ web/
RUN uv sync --frozen --no-dev --package sia-web

FROM builder AS dev
RUN uv sync --frozen --package sia-web
WORKDIR /app/web
CMD ["uv", "run", "--no-sync", "uvicorn", "sia_web.main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]

FROM python:3.12-slim-bookworm AS runtime
RUN useradd --uid 1000 --create-home appuser
WORKDIR /app/web
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/web /app/web
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8080
CMD ["uvicorn", "sia_web.main:app", "--host", "0.0.0.0", "--port", "8080"]

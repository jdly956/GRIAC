# Image API — multi-stage : builder (deps) / dev (hot-reload) / runtime (non-root).
# Contexte de build attendu : la racine du repo (cf. infra/compose.yaml).

FROM ghcr.io/astral-sh/uv:0.8.17 AS uv-bin

FROM python:3.12-slim-bookworm AS builder
COPY --from=uv-bin /uv /bin/uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Layer dépendances (invalidé seulement si les manifestes changent)
COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml api/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-workspace --package sia-api
# Layer code
COPY api/ api/
RUN uv sync --frozen --no-dev --package sia-api

FROM builder AS dev
# Dépendances dev (httpx) + uvicorn --reload ; le code est bind-mounté par compose.
RUN uv sync --frozen --package sia-api
WORKDIR /app/api
CMD ["uv", "run", "--no-sync", "uvicorn", "sia_api.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim-bookworm AS runtime
RUN useradd --uid 1000 --create-home appuser
WORKDIR /app/api
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/api /app/api
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000
CMD ["uvicorn", "sia_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

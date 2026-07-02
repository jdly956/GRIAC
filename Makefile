.DEFAULT_GOAL := help

COMPOSE := docker compose -f infra/compose.yaml --project-directory .

help: ## Affiche les cibles disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Installe l'environnement de dev (uv sync + hooks pre-commit)
	uv sync --all-packages
	uv run pre-commit install

lint: ## Vérifie le code (ruff check + format --check)
	uv run ruff check .
	uv run ruff format --check .

fmt: ## Corrige et formate le code (ruff)
	uv run ruff check --fix .
	uv run ruff format .

test: ## Lance les tests (pytest, tous les membres du workspace)
	uv run --all-packages pytest

probe: ## Sonde Albert (S1.5) : modèles servis + quotas + appels minimaux -> docs/albert-limits.md
	uv run --package sia-api python -m sia_api.probe

ingest-scan: ## Scan du corpus (S1.7) -> table documents + CSV : make ingest-scan CORPUS=<dossier> (DATABASE_URL requise)
	uv run --package sia-ingestion python -m sia_ingestion.scan --corpus $(CORPUS)

ingest-parse: ## Parsing docling (S1.8) -> dérivés markdown + statuts : make ingest-parse CORPUS=<dossier> (DATABASE_URL requise)
	uv run --package sia-ingestion python -m sia_ingestion.parse --corpus $(CORPUS)

ingest-qualify: ## Qualification v0 (S1.9) : métadonnées, doublons, versions, référence (DATABASE_URL requise)
	uv run --package sia-ingestion python -m sia_ingestion.qualify

ingest-chunk: ## Chunking (E1, nœud D) : dérivés markdown -> table chunks (DATABASE_URL requise)
	uv run --package sia-ingestion python -m sia_ingestion.chunk

dev: ## Lance la stack locale (postgres+pgvector, migrate, api, web) et attend qu'elle soit saine
	$(COMPOSE) up -d --build --wait

dev-down: ## Arrête la stack locale (conserve les données)
	$(COMPOSE) down

dev-logs: ## Suit les logs de la stack locale
	$(COMPOSE) logs -f

dev-reset: ## Arrête la stack et supprime les volumes (base réinitialisée)
	$(COMPOSE) down -v

migrate: ## (Re)joue les migrations Alembic dans la stack locale
	$(COMPOSE) run --rm migrate

psql: ## Ouvre psql dans le conteneur postgres
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-sia} -d $${POSTGRES_DB:-sia}

dev-validate: ## Preuves stack-live : /health api+web, extension pgvector (à consigner dans SESSIONS.md)
	curl -fsS http://localhost:8000/health && echo
	curl -fsS http://localhost:8080/health && echo
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-sia} -d $${POSTGRES_DB:-sia} -c "select extname from pg_extension where extname = 'vector'"

.PHONY: help install lint fmt test probe ingest-scan ingest-parse ingest-qualify ingest-chunk dev dev-down dev-logs dev-reset migrate psql dev-validate

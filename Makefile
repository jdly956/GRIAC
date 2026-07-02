.DEFAULT_GOAL := help

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

.PHONY: help install lint fmt test

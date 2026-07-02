# SIA PO — assistant de rédaction de user stories

Application interne pour Product Owners : rédaction de user stories conformes au gabarit interne (chaîne SAFe, prompt 3), accompagnée par un LLM qui mobilise la documentation projet via un RAG avec citations obligatoires. Inférence exclusivement via [Albert API](https://ia.numerique.gouv.fr) (DINUM).

Le cadre du projet vit dans [`CLAUDE.md`](CLAUDE.md) ; le cadrage complet dans [`docs/note-cadrage-sia-po.md`](docs/note-cadrage-sia-po.md) ; la cible fonctionnelle arbitrée dans [`docs/backlog-fonctionnel.md`](docs/backlog-fonctionnel.md).

## Prérequis (poste de dev)

- git, make
- [uv](https://docs.astral.sh/uv/) (gère Python 3.12 et les dépendances)
- Docker + Docker Compose (à partir de S1.2 : stack locale `make dev`)

## Installation

```bash
cd <racine du repo>
make install        # uv sync + installation des hooks pre-commit
```

## Commandes

```bash
make help           # liste des cibles
make lint           # ruff check + format --check (obligatoire avant toute PR)
make test           # pytest (obligatoire avant toute PR)
make fmt            # correction/formatage automatique
```

`make dev` (stack docker compose), `make ingest` et `make eval` arrivent avec les stories S1.2, S1.7 et E6.

## Structure du repo

```
/ingestion   # pipeline : scan -> parsing -> qualification -> chunking -> embeddings -> pgvector
/api         # FastAPI : RAG, génération, feedback, export — et /api/prompts (gabarits SAFe)
/web         # interface PO
/infra       # Dockerfiles, docker-compose (dev), charts Helm (Onyxia/prod)
/evals       # gold/ (stories validées), silver/ (candidates), grille, harnais de benchmark
/docs        # note de cadrage, backlog fonctionnel, backlog de sprint
```

## Règles non négociables (extrait — le détail fait foi dans CLAUDE.md)

- Aucun secret, aucune clé, aucun document du corpus dans le repo.
- Inférence uniquement via Albert API, configuration par variables d'environnement.
- Une story = une branche = une PR, revue par le référent technique avant merge.

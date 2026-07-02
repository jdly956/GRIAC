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

`make ingest` et `make eval` arrivent avec S1.7 et E6.

## Lancer la stack locale (S1.2)

Prérequis : Docker avec daemon actif (poste local, ou pod avec docker — voir
[`docs/init-pod-onyxia.md`](docs/init-pod-onyxia.md) pour le mode sans daemon).

```bash
make dev            # build + démarrage : postgres+pgvector -> migrate -> api -> web (attend l'état sain)
make dev-validate   # preuves : /health api (8000) et web (8080), extension pgvector en base
make dev-logs       # suivre les logs
make dev-down       # arrêt (données conservées) ; make dev-reset pour repartir de zéro
```

- **api** : http://localhost:8000 — `/health`, doc interactive sur `/docs`
- **web** : http://localhost:8080 — page placeholder (bandeau « Ne collez pas de données personnelles »)
- **postgres** : localhost:5432 (identifiants de dev substituables `sia`/`sia_dev`/`sia`, cf. `infra/compose.yaml`)

Cycle de dev : le code `api/sia_api/` et `web/sia_web/` est bind-monté avec hot-reload (< 1 s).
Nouvelle dépendance ⇒ relancer `make dev` (rebuild). Hôtes sans inotify fiable :
exporter `WATCHFILES_FORCE_POLLING=true`. Migrations : `make migrate` ; accès SQL : `make psql`.

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

# SESSIONS.md — état stratégique & journal des sessions

> Journal inversé : l'entrée la plus récente en tête. Chaque session close ajoute une entrée (règle « MAJ documentation à chaque clôture de session », CLAUDE.md). L'en-tête « État stratégique » est recalé à chaque clôture.

## État stratégique

**Voie active** : sprint 1 en cours. PRs #1 (kickoff : docs, méthode, prompts SAFe, cible fonctionnelle A1–A9) et #2 (S1.1 : socle uv/make/pre-commit) **mergées dans `main`**. S1.2 (stack compose : postgres+pgvector, api, web, migration Alembic) livrée en PR — code validé en session (tests, /health réels, migration offline), **validation stack-live `make dev` à jouer sur poste/pod avec Docker** (procédure : `docs/init-pod-onyxia.md`). Prochaines stories selon l'ordre du backlog : S1.4 (config/secrets) puis S1.5 (sonde Albert). Bascule de la branche par défaut sur `main` : à faire dans les settings GitHub si pas encore fait.

**Arbitrages du référent technique (02/07/2026)** : (1) le référent technique est désigné — c'est l'utilisateur de ces sessions ; (2) les 3 prompts SAFe sont fournis et versionnés ; (3) calendrier du benchmark E6 vs contenu du sprint 1 : statu quo pour l'instant, pas de décision ; (4) objectif 5–10 stories gold vs 3 silver disponibles : statu quo pour l'instant. **Cible fonctionnelle arbitrée en itération Q/R (9 arbitrages A1–A9, journal complet dans `docs/backlog-fonctionnel.md`)** — points saillants : le RAG est un mécanisme interne au service du LLM accompagnant (jamais une recherche autonome), mobilisé à chaque étape du workflow ; question libre conservée dans le fil ; transparence à 3 niveaux (citations inline, panneau sources avec extraits, marquage d'origine corpus/PO/modèle) ; divergences corpus↔PO signalées et arbitrées par le PO ; pas de jalon de démo intermédiaire (risque tunnel assumé) ; écran couverture + alerte conversationnelle ; PO autonome jusqu'à la sélection des dossiers documentaires de son projet ; instance partagée sans comptes au MVP ; export non bloquant avec récapitulatif des hypothèses. Amendements induits appliqués : note §4, CLAUDE.md (contexte, E3/E4/E5/E8, annexes), backlog sprint 1 (S1.9, S1.11). Plan S1.1/S1.2 validé (« ok go »).

**Prérequis en attente (note de cadrage §7)** : snapshot du corpus (PM) ; stories gold (extraction Jira et/ou validation des silver, avant fin sprint 1) ; panel des PO pilotes ; relevé des curseurs CPU/RAM et espace MinIO au premier login SSP Cloud (architecte). La clé Albert existe — le relevé des quotas est intégré à S1.5.

---

## Session 02/07/2026 — Kickoff : initialisation du repo & cadrage

**Contexte** : première session, repo GitHub `jdly956/GRIAC` vide. Direction : « installe le repo git, analyse le sujet et on débute le cadrage ».

**Travail livré** :
- Commit fondateur `6473f87` : structure documentaire cible — `CLAUDE.md` (racine), `docs/note-cadrage-sia-po.md`, `docs/sprint-1-backlog.md`, `evals/silver/stories-silver-candidates.md`. Poussé après déblocage des droits d'écriture de l'app GitHub (403 initial).
- Méthode de travail ajoutée à CLAUDE.md (adaptée du CLAUDE.md SIACT — même plateforme Onyxia SSP Cloud et Albert API pour le LLM, mais stack différente ici : tout conteneurisé, aucun GPU ni LLM local) : environnement et outils, commandes préfixées, démarrage de session, validation stack-live, pas de script de rattrapage sans fix pipeline, MAJ doc à chaque clôture, conventions code et git, garde-fous, format des réponses. Création de ce SESSIONS.md.
- Correction d'une dérive documentaire : CLAUDE.md référençait « 18 décisions (D1–D18) », la note v0.4 en compte 19 (D1–D19).
- Branche `main` créée et poussée (accord utilisateur) ; bascule en branche par défaut à faire côté GitHub.
- Cadrage : audit de cohérence des 4 documents (15 findings, dont 4 majeurs : référent, prompts absents, benchmark sans porteur, gold inatteignable par les seules silver), état des 11 prérequis externes, plan d'exécution S1.1/S1.2 (3 plans concurrents → jury → 12 corrections adversariales) livré au référent.
- Dépôt des 3 prompts SAFe fournis par le référent dans `/api/prompts/` (prompt-1 Epic, prompt-2 Features, prompt-3 Stories) — S1.10 partiellement débloquée (restent : templates structurés, validateur, gold).
- Cible fonctionnelle v2 arbitrée (9 arbitrages A1–A9) versionnée dans `docs/backlog-fonctionnel.md` + amendements induits (note §4, CLAUDE.md, backlog sprint 1) — PR #1 passée en revue.
- **PRs #1 (kickoff) et #2 (S1.1) mergées dans `main`** sur instruction du référent.
- **S1.2 livrée — code** (branche `feature/s1.2-dev-env`) : apps FastAPI `sia-api` (GET /health sans dépendance DB) et `sia-web` (page placeholder + bandeau D15 + /health), migration Alembic 0001 (pgvector, `DATABASE_URL` par env avec échec explicite, `script_location = %(here)s`), Dockerfiles multi-stage (builder/dev/runtime non-root, uv 0.8.17 épinglé), `infra/compose.yaml` (pgvector/pgvector:0.8.0-pg16, chaîne postgres healthy → migrate completed → api healthy → web, credentials substituables, bind-mounts code seul), `.dockerignore`, cibles make dev/dev-down/dev-logs/dev-reset/migrate/psql/dev-validate, workspace uv étendu (members api+web, testpaths, isort first-party), `docs/init-pod-onyxia.md` (procédure pod Onyxia, modes avec/sans daemon Docker). **Validations observées en session** : `make lint` vert ; `make test` 5 tests verts (la collecte des membres via `--all-packages` fonctionne) ; uvicorn réels : `/health` api=200, web=200, bandeau D15 servi ; alembic offline : SQL `CREATE EXTENSION IF NOT EXISTS vector` généré, échec propre sans URL ; `docker compose config` : chemins résolus dans le repo (piège `--project-directory` corrigé : bind-mounts en `./`). **Limite** : pas de daemon Docker en session → `make dev` + `make dev-validate` à jouer sur poste/pod (validation stack-live complète), résultat à consigner ici.
- **S1.1 livrée** (branche `feature/s1.1-init-repo`, plan validé « ok go ») : workspace uv (`pyproject.toml` racine, `.python-version` 3.12, `uv.lock`), `Makefile` (help/install/lint/fmt/test), `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml` (ruff v0.15.20 aligné lock + hooks génériques + uv-lock), README, `tests/test_sanity.py`, `.gitkeep` (ingestion, web, infra, evals/gold). **Validation observée** : `make lint` vert (ruff check + format) et `make test` vert (2 tests, Python 3.12.3) dans le conteneur de session. Limite d'environnement : `pre-commit run --all-files` impossible en session (proxy git limité au repo du projet, 403 sur les dépôts de hooks) → à rejouer sur poste de dev ; hooks bien installés (`pre-commit install` OK), config validée (`validate-config`).

**Validation stack-live** : sans objet (aucun code livré — documentation uniquement).

**Mini-récap** :
- ✅ Fait : repo initialisé et poussé ; méthode de travail dans CLAUDE.md ; SESSIONS.md créé
- ⏳ En cours : analyse de cadrage multi-agents (cohérence des docs, prérequis, plan S1.1/S1.2 vérifié)
- ⏳ À venir : validation du plan S1.1/S1.2 par le référent ; création de `main` (accord utilisateur requis) ; implémentation S1.1 puis S1.2

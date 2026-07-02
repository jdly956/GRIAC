# CLAUDE.md — SIA PO : assistant de rédaction de user stories

## Contexte

Application interne pour Product Owners de l'administration française : génération de user stories conformes au gabarit interne, ancrées sur la documentation projet par RAG avec citations obligatoires, et mode Q&A documentaire. Le cadrage complet et le journal des 18 décisions (D1–D18) sont dans `/docs/note-cadrage-sia-po.md` : le lire avant toute tâche.

## Contraintes non négociables

- Inférence exclusivement via Albert API (DINUM), client compatible OpenAI, `base_url` et modèles en variables d'environnement — jamais en dur. Utiliser les alias Albert (`openweight-large`, `openweight-embeddings` = bge-m3, `openweight-rerank` = bge-reranker-v2-m3) pour survivre aux rotations de catalogue.
- Aucun secret, aucune clé, aucun document du corpus dans le repo. Secrets via Kubernetes Secrets / `.env` ignoré par git.
- Toute réponse du RAG cite ses sources (document + section) ; une génération sans source récupérable doit le signaler.
- Les gabarits internes sont trois prompts SAFe versionnés dans `/api/prompts/` (prompt-1 Epic, prompt-2 Features, prompt-3 Stories). Le moteur du MVP implémente le workflow complet du prompt 3 : interview par lots de 3 questions max, registre des [HYPOTHÈSE À VALIDER] jamais levées silencieusement (une validation globale ne les lève pas), validation Oui/Non par étape, formats de sortie exacts (US, tableau Gherkin des CA, critères d'accessibilité DSFR), contrôle DoR. Few-shot depuis `/evals/gold/` ; tant que le gold n'est pas fourni, repli sur `/evals/silver/` — candidates jamais présentées comme validées, marqueurs [HYPOTHÈSE À VALIDER] conservés.
- L'anti-invention est une exigence produit : toute information non issue du corpus ou du PO est marquée [HYPOTHÈSE À VALIDER]. Le front web utilise le DSFR (cohérence avec les critères d'accessibilité du gabarit).
- Données traitées : publiques ou internes non sensibles uniquement. Afficher dans l'UI : « Ne collez pas de données personnelles ».
- Tout tourne en conteneurs ; déployable sur Onyxia (SSP Cloud) via Helm, portable vers Outscale/Scaleway. Aucun GPU requis ni demandé : l'inférence est déportée sur Albert.
- Budget de contexte par requête ≤ 20 000 tokens (gabarit + few-shot + 8–15 chunks + brief). Dès E0, relever la fenêtre effectivement servie et les quotas via `GET /v1/models` et l'objet `limits` de `GET /v1/me/info` — avant tout tuning.
- Chaque PR est revue par le référent technique humain avant merge. PR petites, une story à la fois.

## Stack

Python 3.12, FastAPI, docling (parsing Word/PDF), PostgreSQL 16 + pgvector, front léger (HTML/htmx ou équivalent simple — pas de framework lourd au MVP), pytest, ruff, Docker + Helm.

## Structure du repo

```
/ingestion   # snapshot S3 -> parsing -> qualification -> chunking -> embeddings -> pgvector
/api         # FastAPI : RAG, génération, feedback, export CSV Jira
/web         # interface PO
/infra       # Dockerfiles, docker-compose (dev), charts Helm (Onyxia/prod)
/evals       # gold/ (stories validées), silver/ (candidates [HYPOTHÈSE À VALIDER]), grille de notation, harnais de benchmark
/docs        # note de cadrage, gabarit, charte d'usage
```

## Commandes (à implémenter dès E0 et maintenir)

- `make dev` : stack locale (compose : postgres+pgvector, api, web)
- `make ingest CORPUS=<chemin>` : pipeline d'ingestion complet sur un dossier
- `make test` / `make lint` : pytest, ruff — obligatoires avant toute PR
- `make eval` : benchmark génération sur `/evals/gold/` avec sortie scorée

## Backlog macro

- **E0 Socle** : repo, CI, compose, Helm minimal, healthchecks.
- **E1 Ingestion & qualification** : DAG de jobs conteneurisés idempotents (nœuds A→H, annexe A de la note) — lecture S3/MinIO, parsing docling + OCR Albert, métadonnées inférées (chemin, nom, dates, version), détection doublons/versions, chunking par sections de titres (500–800 tokens, chevauchement, tableaux jamais coupés), embeddings bge-m3 par lots, pgvector, rescan complet avec reprise sur hash (seuls les fichiers modifiés re-vectorisés ; embeddings de nuit si les quotas l'imposent), rapport de couverture.
- **E2 RAG** : recherche hybride BM25 + vecteurs, filtres métadonnées (statut = référence), reranker bge-reranker-v2-m3, assemblage du contexte avec traçabilité des sources.
- **E3 Moteur de rédaction (workflow prompt 3)** : machine à états (étapes 0→5 du prompt), interview, registre des [HYPOTHÈSE À VALIDER], génération des US au format exact, contrôle DoR automatisé, citations ; consomme le contexte et les NFR du projet (E8).
- **E4 UI & feedback** : sélection du projet, conversation du workflow (étape courante, hypothèses en attente de validation), affichage sources, édition, note 1–5 + commentaire par story, télémétrie d'usage (actifs hebdo, % stories conservées, taux d'édition).
- **E5 Export** : CSV compatible import Jira ; copier-coller formaté.
- **E6 Évals** : harnais de benchmark des modèles de chat (`openweight-large` = gpt-oss-120b vs `openweight-medium` = Mistral-Small-3.2 ; Mistral Medium propriétaire si accès ALLiaNCE), grille 3 axes (gabarit, exactitude, complétude), démarrage sur `/evals/silver/` puis recalibrage sur `/evals/gold/` dès fourniture + test de fenêtre de contexte effective et de débit d'embeddings sous quotas.
- **E7 Prod (post go)** : agent connecteur Jira interne en flux sortant, auth ProConnect, charts prod.
- **E8 Projets — contexte & NFR (prérequis d'E3)** : entité Projet (nom, contexte libre, NFR typées : performance, volumétrie, SSI, RGPD, accessibilité RGAA, disponibilité, auditabilité, avec valeur cible optionnelle), CRUD API + écran DSFR, injection dans le prompt système et pré-remplissage des blocs NFR de l'interview ; filtre du corpus par projet (métadonnée D7).

## Références

- Albert API / offre IA de l'État : https://ia.numerique.gouv.fr
- Claude Code : https://docs.claude.com/en/docs/claude-code/overview

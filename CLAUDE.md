# CLAUDE.md — SIA PO : assistant de rédaction de user stories

## Contexte

Application interne pour Product Owners de l'administration française : génération de user stories conformes au gabarit interne, ancrées sur la documentation projet par RAG avec citations obligatoires, et mode Q&A documentaire. Le cadrage complet et le journal des 19 décisions (D1–D19) sont dans `/docs/note-cadrage-sia-po.md` : le lire avant toute tâche.

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

## Environnement et outils

### Plateformes

- **Dev & POC** : SSP Cloud (Onyxia), service VSCode **sans GPU** — l'inférence est déportée sur Albert, jamais d'inférence locale (pas d'Ollama). À compléter au premier login (action n°7 de la note de cadrage) : URL du service, working dir, maxima CPU/RAM, espace MinIO.
- **Sessions Claude Code** : pod Onyxia (CLI) ou session remote (claude.ai/code) sur le repo GitHub privé `jdly956/GRIAC`.
- **LLM** : Albert API exclusivement (voir Contraintes non négociables) ; clé jamais dans le repo ni dans les logs.

### Règle « commandes toujours préfixées »

Toute commande shell proposée à l'utilisateur commence par se placer à la racine du repo et activer l'environnement :

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
```

(chemin et mécanisme d'activation à recaler sur les choix de S1.1). Cela vaut même quand « on suppose » que l'utilisateur est déjà dans le bon état — la supposition se révèle régulièrement fausse (nouveau terminal, nouvelle session VSCode, panneau split) et fait perdre du temps en debug `pytest: command not found`. Le préfixe est idempotent et coûte zéro. Exception : commandes purement informatives (`git status`, `git log`) — mais en cas de doute, préfixer quand même.

### Outils non disponibles (ne PAS proposer)

- `gh` CLI → les PR se créent via l'interface web GitHub (ou l'intégration GitHub de Claude Code en session remote)
- Client PostgreSQL hors conteneurs → passer par `docker compose exec` sur le service postgres du compose
- Jira n'est pas joignable depuis l'environnement de dev (réseau interne, D10) → export CSV uniquement au MVP

### Outils disponibles

`python3`, `pytest`, `ruff`, `git`, `curl`, `make`, `docker` + `docker compose`, `nohup` pour les jobs longs en background (ingestion, embeddings de nuit).

## Méthode de travail

### Démarrage de chaque session

1. Lire ce fichier (CLAUDE.md)
2. Lire `SESSIONS.md` (en-tête « État stratégique » + les 2 dernières entrées) pour l'état courant
3. Lire le backlog du sprint en cours (`docs/sprint-1-backlog.md`)
4. Vérifier l'état Git : `git status` + `git log --oneline -5` + `git branch --show-current`
5. Confirmer la direction de la session avec l'utilisateur avant d'agir

### Règle « validation stack-live »

Aucune story n'est considérée **livrée** tant que :

1. le comportement a été démontré dans la stack réelle (`make dev`) — endpoint appelé, job d'ingestion exécuté sur les fixtures, écran affiché — et pas seulement en tests unitaires ;
2. un signal observable (log, ligne en base, sortie de commande) prouve que le code exécuté est bien le code modifié ;
3. le résultat de cette validation est noté dans `SESSIONS.md`.

**Tests verts ≠ story livrée** : ils prouvent que le code marche en isolation, pas qu'il est branché dans la stack.

### Règle « MAJ documentation à chaque clôture de session »

Une session n'est **close** que quand la documentation reflète l'état réel du repo, avant le dernier commit/push :

1. **`SESSIONS.md`** — nouvelle entrée datée en tête : contexte (branche, direction validée), livrables (commits avec hash), validation stack-live (résultat observable cité, sinon explicitement « validation à jouer post-merge »), mini-récap ✅/⏳
2. **En-tête « État stratégique » de `SESSIONS.md`** recalé : voie active, PRs récentes, prochaine étape (l'état vivant vit dans SESSIONS.md — ce CLAUDE.md reste stable)
3. **Backlog du sprint** : critères d'acceptation livrés cochés, reports notés
4. **README / `docs/`** : à jour si la surface a changé (commandes make, API, écrans, déploiement)

Échappatoire : session purement informative (audit, analyse sans code) → seule `SESSIONS.md` est mise à jour, avec la mention « analyse, aucun code livré ».

### Diagnostic avant action

- Message d'erreur collé par l'utilisateur : analyser avant de proposer une correction
- Lire le contenu pertinent d'un fichier avant de le patcher ; patchs sur ancres uniques, jamais de regex hasardeuse

### Validation post-modification

1. `make lint` (ruff)
2. Tests ciblés du module touché, puis `make test` (baseline complète)
3. Si modif côté api/web : vérifier que le hot-reload a bien rechargé, sinon redémarrer le service compose concerné — sans quoi le code modifié ne tourne pas
4. Tout appel Albert est mocké dans les tests unitaires ; `make test` ne fait jamais d'appel réseau réel

### Convention Git

- Une story = une branche = une PR (petite), revue par le référent technique humain avant merge
- Branches : `feature/<nom>`, `fix/<nom>`, `chore/<nom>` ; commits `type(scope): description` (feat, fix, docs, chore, refactor, test), 1 commit par changement cohérent
- **Demander avant tout `git push`** — l'utilisateur décide du moment
- **Demander avant tout commit qui ajoute un fichier inattendu ou supprime du code existant**

### Demander avant de

- Refactorer du code qui marche déjà (risque de régression)
- Modifier des tests existants (sauf demande explicite)
- Supposer un nom de fichier ou une structure → demander à voir le contenu d'abord
- Lancer des actions destructrices : `rm`, `git reset --hard`, `DROP TABLE`, suppression de volumes docker

### Format des réponses

- Code complet et prêt à utiliser (jamais de `# ... reste du code` ni d'ellipses)
- Expliquer brièvement les **choix techniques** ET **les risques** ; si une décision a un trade-off, l'exposer et demander à trancher
- Mini-récap obligatoire en fin de tâche complexe :

```
✅ Fait : ...
⏳ En cours : ...
⏳ À venir : ...
```

## Documents annexes

- `docs/note-cadrage-sia-po.md` : note de cadrage (décisions D1–D19, architecture, annexe capacitaire)
- `docs/sprint-1-backlog.md` : backlog opérationnel du sprint en cours (S1.1 → S1.11)
- `SESSIONS.md` : état stratégique + journal détaillé des sessions (livrables, validations, découvertes)
- `evals/silver/stories-silver-candidates.md` : candidates silver — fixtures S1.10 et few-shot provisoire

## Références

- Albert API / offre IA de l'État : https://ia.numerique.gouv.fr
- Claude Code : https://docs.claude.com/en/docs/claude-code/overview

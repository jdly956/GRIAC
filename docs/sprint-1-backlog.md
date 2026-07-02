# Sprint 1 — Socle & début d'ingestion (E0 + E1)

**Objectif du sprint** : un repo opérationnel, un environnement dev conteneurisé, la sonde des limites Albert exécutée, et un pipeline d'ingestion capable de scanner, parser et qualifier un corpus de test. Durée cible : 1 semaine.

**Definition of Done commune** : tests pytest verts, `make lint` vert, aucun secret ni document réel dans le repo, PR revue par le référent technique humain, documentation à jour.

**Ordre conseillé** : S1.1 → S1.2 → S1.4 → S1.5 (dès que possible, la clé existe) → S1.3 → S1.7 → S1.8 → S1.9 → S1.11 → S1.6 → S1.10.

---

## S1.1 — Initialisation du repo

En tant que référent technique, je veux un repo initialisé avec l'arborescence cible pour que toute contribution parte d'un socle propre.

Critères d'acceptation :
- [x] Arborescence `/ingestion /api /web /infra /evals /docs` créée, CLAUDE.md à la racine, note de cadrage dans `/docs`
- [x] `.gitignore` (env, caches, dérivés), README minimal, pre-commit avec ruff
- [x] `make lint` passe sur le repo vide

*Livrée le 02/07/2026 (branche `feature/s1.1-init-repo`) — `make lint` et `make test` verts (Python 3.12.3, ruff 0.15.20, pytest 9.1.1). `pre-commit run --all-files` à rejouer sur le poste de dev : le proxy git de la session Claude Code n'autorise que le repo du projet.*

## S1.2 — Environnement de dev conteneurisé

En tant que développeur, je veux `make dev` pour lancer toute la stack localement.

Critères d'acceptation :
- [ ] docker-compose : PostgreSQL 16 + pgvector, api FastAPI (hot-reload), web
- [ ] Migration initiale activant l'extension pgvector
- [ ] `GET /health` répond 200 ; `make dev` documenté dans le README

## S1.3 — CI minimale

En tant que référent technique, je veux que chaque PR soit vérifiée automatiquement.

Critères d'acceptation :
- [ ] Pipeline (forge interne : GitLab CI ou équivalent — adapter au dépôt réel) : lint + tests + build des images
- [ ] Échec du pipeline = merge bloqué

## S1.4 — Configuration & secrets

En tant que RSSI, je veux la garantie qu'aucun secret ne peut fuiter par le repo.

Critères d'acceptation :
- [ ] Config par variables d'environnement (pydantic-settings) : `ALBERT_BASE_URL`, `ALBERT_API_KEY`, alias de modèles (`openweight-large`, `openweight-embeddings`, `openweight-rerank`)
- [ ] `.env.example` documenté, `.env` ignoré par git, template de Secret Kubernetes dans `/infra`
- [ ] Démarrage sans clé = échec propre avec message explicite ; la clé n'apparaît jamais dans les logs

## S1.5 — Client Albert & sonde des limites

En tant qu'architecte, je veux relever la fenêtre effective et les quotas réels avant tout tuning (test no-go n°1 de la note, §6).

Critères d'acceptation :
- [ ] Client compatible OpenAI pointé sur Albert, timeouts et retries configurés
- [ ] `make probe` : appelle `GET /v1/models` et `GET /v1/me/info`, écrit `/docs/albert-limits.md` (modèles, alias, fenêtres, limits TPM/TPD)
- [ ] Un appel de chat minimal et un appel d'embedding réussissent ; erreurs réseau gérées

## S1.6 — Charts Helm minimaux Onyxia

En tant qu'architecte, je veux déployer la stack sur le SSP Cloud.

Critères d'acceptation :
- [ ] Chart Helm api + web + PostgreSQL, values adaptées au lab (`*.lab.sspcloud.fr`)
- [ ] `helm template` valide ; procédure pas-à-pas dans `/docs/deploy-onyxia.md`
- [ ] Aucune demande de GPU (contrainte CLAUDE.md)

## S1.7 — Ingestion : scan & inventaire du corpus

En tant que PO, je veux un inventaire fiable de ce que le système connaît.

Critères d'acceptation :
- [ ] `make ingest-scan CORPUS=<chemin|s3://…>` : parcours récursif, hash sha256, taille, extension, dates
- [ ] Table `documents` alimentée par upsert sur hash ; relance = zéro doublon (idempotence)
- [ ] Fixtures synthétiques dans `/evals/fixtures` (docx, pdf natif, pdf scanné, doublons, versions) ; inventaire CSV exporté

## S1.8 — Ingestion : parsing docling → markdown structuré

En tant que système, je veux convertir docx et pdf en markdown structuré exploitable pour le chunking.

Critères d'acceptation :
- [ ] Conversion docx et pdf natifs : hiérarchie de titres préservée, tableaux jamais détruits
- [ ] Dérivés `.md` stockés hors repo (dossier `derived/` ou S3) ; statut de parsing en base
- [ ] Un document en échec n'interrompt pas le lot ; rapport d'échecs produit
- [ ] PDF scannés détectés et marqués `ocr_requis` (traitement OCR = sprint 2)

## S1.9 — Ingestion : qualification v0 (métadonnées & versions)

En tant que PO, je veux que le système distingue documents de référence, brouillons et versions obsolètes.

Critères d'acceptation :
- [ ] Métadonnées inférées : projet (1er niveau du chemin), date (mtime + date dans le nom si présente), version (motifs `v\d+`, `VF`, `final`), statut brouillon (`draft`, `brouillon`, `WIP`)
- [ ] L'inférence du champ `projet` est enregistrée comme **suggestion** : l'association faisant foi est celle confirmée par le PO via S1.11 (arbitrage A6, `docs/backlog-fonctionnel.md`)
- [ ] Doublons détectés par hash ; versions regroupées par similarité de nom, la plus récente taguée `référence`
- [ ] Jeu de fixtures piégé (spec_v1, spec_v2_final_VF3, copie conforme) correctement qualifié, couvert par tests unitaires

## S1.10 — Intégration des gabarits internes (3 prompts SAFe)

En tant que PO, je veux que les prompts officiels soient la source unique des formats et du workflow (prépare E3 et E6).

Critères d'acceptation :
- [ ] Les 3 fichiers fournis déposés dans `/api/prompts/` : prompt-1 (Epic), prompt-2 (Features), prompt-3 (Stories)
- [ ] Extraction en templates structurés : format US du prompt 3 (blocs, tableau Gherkin des CA, critères DSFR) et tableau DoR
- [ ] Validateur de conformité d'une US au format interne, couvert par tests
- [ ] Candidates silver (`stories-silver-candidates.md`) déposées dans `/evals/silver/` et utilisées comme fixtures du validateur
- [ ] Dépendance restante : 5–10 stories gold dans `/evals/gold/`, obtenues par extraction des meilleures stories Jira (reformatées) et/ou promotion des candidates silver (`stories-silver-candidates.md`) après validation par les PO pilotes

## S1.11 — Entité Projet : modèle de données (contexte & NFR)

En tant que PO, je veux créer un projet portant son contexte et ses NFR pour que la génération en tienne compte (D19, prépare E8 puis E3).

Critères d'acceptation :
- [ ] Tables `projects` (nom, contexte libre) et `project_nfrs` (type parmi : performance, volumétrie, SSI, RGPD, accessibilité RGAA, disponibilité, auditabilité ; formulation vérifiable ; valeur cible optionnelle)
- [ ] API CRUD minimale (création, lecture, mise à jour) couverte par tests — l'écran DSFR arrive avec E4
- [ ] Association explicite projet ↔ dossiers documentaires : table dédiée, éditable ; la suggestion inférée par S1.9 est proposée puis confirmée ou corrigée par le PO (arbitrage A6 — le champ `projet` des documents ingérés est rattachable à un projet existant via cette table)

---

## Amorce pour lancer Claude Code

Dans le dossier du futur repo, après avoir déposé CLAUDE.md, la note de cadrage et ce fichier :

> Lis CLAUDE.md, docs/note-cadrage-sia-po.md et docs/sprint-1-backlog.md. Propose-moi ton plan d'exécution pour S1.1 et S1.2 (fichiers créés, choix techniques), attends ma validation, puis implémente-les en respectant la Definition of Done. Une story = une branche = une PR.

Le référent technique valide le plan avant exécution, puis chaque PR.

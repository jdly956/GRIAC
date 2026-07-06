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
- [x] docker-compose : PostgreSQL 16 + pgvector, api FastAPI (hot-reload), web — *fichiers livrés et validés par `docker compose config` ; exécution réelle non démontrée, voir réserve*
- [x] Migration initiale activant l'extension pgvector — *validée en mode offline (SQL généré, échec propre sans `DATABASE_URL`) ; application en base réelle non démontrée, voir réserve*
- [x] `GET /health` répond 200 ; `make dev` documenté dans le README — *démontré en réel sur pod Onyxia : api 8000 et web 8081 → 200*

*Livrée le 02/07/2026 (branche `feature/s1.2-dev-env`, mergée sur décision du référent). Validation stack-live sur pod Onyxia réel : `make install`/`lint`/`test` verts (5 tests), `GET /health` api et web = 200, bandeau D15 servi. **Réserve explicite acceptée par le référent** : la stack compose complète (`make dev` + `make dev-validate` — postgres+pgvector réel, conteneur migrate, hot-reload) reste à démontrer sur un hôte avec daemon Docker (absent du pod et de la session) ; à jouer à la première occasion ou au plus tard avec S1.6 (Helm). Procédure : `docs/init-pod-onyxia.md`.*

## S1.3 — CI minimale

En tant que référent technique, je veux que chaque PR soit vérifiée automatiquement.

Critères d'acceptation :
- [x] Pipeline (forge interne : GitLab CI ou équivalent — adapter au dépôt réel = GitHub → GitHub Actions) : lint + tests + build des images — **3 checks verts observés sur la PR #6** (`lint-tests`, `build-images (api)`, `build-images (web)`)
- [ ] Échec du pipeline = merge bloqué — **action référent** : protection de branche sur `main` (procédure et limite plan Free dans `docs/plans-test/s1.3-ci.md`) ; les 3 checks sont désormais sélectionnables (premier run passé)

*Livrée le 02/07/2026 (PR #6). `.github/workflows/ci.yml` : job `lint-tests` (uv + make lint + make test, mêmes commandes que la baseline locale) et matrice `build-images` (api, web, cible runtime — valide les Dockerfiles S1.2 à chaque PR). CA2 reporté à l'activation GitHub par le référent.*

## S1.4 — Configuration & secrets

En tant que RSSI, je veux la garantie qu'aucun secret ne peut fuiter par le repo.

Critères d'acceptation :
- [x] Config par variables d'environnement (pydantic-settings) : `ALBERT_BASE_URL`, `ALBERT_API_KEY`, alias de modèles (`openweight-large`, `openweight-embeddings`, `openweight-rerank`) — `api/sia_api/config.py`, alias par défaut surchargeables par env
- [x] `.env.example` documenté, `.env` ignoré par git (+ exception `!.env.example`), template de Secret Kubernetes dans `infra/k8s/secret-albert.example.yaml`
- [x] Démarrage sans clé = échec propre avec message explicite ; la clé n'apparaît jamais dans les logs — démontré en uvicorn réel (exit 3, variables nommées sans valeur ; `SecretStr` masqué, 0 occurrence de la clé dans les logs de démarrage)

*Livrée le 02/07/2026 (branche `claude/backlog-continuation-6ftff4`, PR #4). Validation stack-live en session : uvicorn réel sans config → refus avec message explicite ; avec config → `GET /health` 200 et clé absente des logs. 8 tests unitaires ajoutés (13 au total, verts) ; le service api du compose reçoit désormais les variables `ALBERT_*` (vide = refus de démarrer, visible via `docker compose logs api`). **Plan de test `docs/plans-test/s1.4-config-secrets.md` exécuté sur pod Onyxia le 02/07 : étapes 1–5 ✅** (13 tests verts, refus sans clé exit 3, refus variables vides, /health 200 par le bon process, 0 occurrence de la clé dans les logs) ; étape 7 (mode A) non jouée — réserve compose S1.2 inchangée. Découverte pod : `ALBERT_API_KEY` injectée dans l'environnement du pod, prime sur le `.env`.*

## S1.5 — Client Albert & sonde des limites

En tant qu'architecte, je veux relever la fenêtre effective et les quotas réels avant tout tuning (test no-go n°1 de la note, §6).

Critères d'acceptation :
- [x] Client compatible OpenAI pointé sur Albert, timeouts et retries configurés (`ALBERT_TIMEOUT_S`, `ALBERT_MAX_RETRIES`)
- [x] `make probe` : appelle `GET /v1/models` et `GET /v1/me/info`, écrit `/docs/albert-limits.md` (modèles, alias, fenêtres, limits TPM/TPD) — exécuté sur pod, rapport committé (`bb3127c`)
- [x] Un appel de chat minimal et un appel d'embedding réussissent (chat `OK`/`stop` en 0,27 s ; embeddings dim 1024 en 0,06 s) ; erreurs réseau gérées (démontré : hôte injoignable, clé invalide, 500 Albert)

*Livrée le 02/07/2026 (PR #5). Plan de test `docs/plans-test/s1.5-albert-probe.md` exécuté sur pod : 4/4 relevés ok, exit 0, 0 fuite de clé. **Verdict no-go n°1 : GO** — fenêtre effective `openweight-large` (gpt-oss-120b) = **131 072 tokens** ≫ budget 20k (marge ×6,5) ; tpm 128 000 (~6 requêtes pleines/min), tpd 2,46 M (vigilance : ~120 requêtes pleines/jour) ; bge-m3 fenêtre 8192 (chunks 500–800 très à l'aise). Deux bugs découverts et corrigés par les runs réels : max_tokens vs modèles à raisonnement, `encoding_format="float"` obligatoire sur les embeddings (gotcha E1/E2).*

## S1.6 — Charts Helm minimaux Onyxia

En tant qu'architecte, je veux déployer la stack sur le SSP Cloud.

Critères d'acceptation :
- [ ] Chart Helm api + web + PostgreSQL, values adaptées au lab (`*.lab.sspcloud.fr`) — *chart livré ; le déploiement réel sur le lab reste à jouer (plan S1.6, prérequis registre d'images)*
- [x] `helm template` valide ; procédure pas-à-pas dans `/docs/deploy-onyxia.md` — **job CI `helm-chart` vert sur la PR #11** (helm lint + template)
- [x] Aucune demande de GPU (contrainte CLAUDE.md) — aucun `nvidia.com/gpu` ni équivalent dans le chart (vérifiable dans les manifestes rendus par la CI)

*Code livré le 02/07/2026 : chart `infra/helm/sia-po` (postgres+pgvector avec PVC et Secret, job de migrations en hook post-install/upgrade, api avec `envFrom` sur le Secret `sia-albert` de S1.4 + DATABASE_URL, web, Ingress api/web sur `*.lab.sspcloud.fr`, probes /health, aucun GPU), job CI `helm-chart` (helm lint + helm template — helm est indisponible en session, la CI est le validateur), procédure `docs/deploy-onyxia.md` (prérequis registre d'images + secret Albert, install/upgrade/uninstall, vérifications). **CA à cocher : CA2-rendu via le job CI vert sur la PR ; CA1 et le déploiement réel via le plan `docs/plans-test/s1.6-helm.md` sur le lab.***

## S1.7 — Ingestion : scan & inventaire du corpus

En tant que PO, je veux un inventaire fiable de ce que le système connaît.

Critères d'acceptation :
- [x] `make ingest-scan CORPUS=<chemin|s3://…>` : parcours récursif, hash sha256, taille, extension, dates
- [ ] Table `documents` alimentée par upsert sur hash ; relance = zéro doublon (idempotence) — *alimentation validée pod 06/07/2026 ; la relance du scan (contre-épreuve idempotence, plan s1.7 étape 4) reste à rejouer*
- [x] Fixtures synthétiques dans `/evals/fixtures` (docx, pdf natif, pdf scanné, doublons, versions) ; inventaire CSV exporté

*Code livré le 02/07/2026 : membre workspace `ingestion` (`sia_ingestion/scan.py`), migration 0002 (table `documents`, chemin UNIQUE = clé d'idempotence, index sha256 pour doublons S1.9 et reprise D9), `make ingest-scan`, 6 fixtures synthétiques (versions v1/v2_final_VF3, copie byte-à-byte, PDF natif/scanné, txt), export CSV, 7 TU (31 au total, verts). Choix documenté : upsert sur le **chemin relatif** (un fichier = une ligne, relance = zéro doublon) ; les doublons de contenu (même sha256) restent des lignes distinctes détectées par S1.9. `s3://` refusé explicitement tant que le snapshot MinIO n'existe pas (prérequis §7). **CA à cocher après exécution du plan `docs/plans-test/s1.7-ingest-scan.md` sur une base réelle** (mode A compose — lèverait aussi la réserve S1.2 — ou service PostgreSQL Onyxia).*

## S1.8 — Ingestion : parsing docling → markdown structuré

En tant que système, je veux convertir docx et pdf en markdown structuré exploitable pour le chunking.

Critères d'acceptation :
- [x] Conversion docx et pdf natifs : hiérarchie de titres préservée, tableaux jamais détruits — *docx et pdf natif démontrés (pod 06/07/2026, après installation libGL — prérequis documenté runbook s0)*
- [x] Dérivés `.md` stockés hors repo (dossier `derived/` ou S3) ; statut de parsing en base
- [x] Un document en échec n'interrompt pas le lot ; rapport d'échecs produit
- [x] PDF scannés détectés et marqués `ocr_requis` (traitement OCR = sprint 2)

*Code livré le 02/07/2026 : `sia_ingestion/parse.py` + `make ingest-parse` (nœud B du DAG), migration 0003 (statut_parsing/chemin_derive/erreur_parsing/date_parsing), dérivés `derived/md/<sha256>.md` (reprise sur hash D9 : dérivé existant = pas de reconversion ; couvre aussi les doublons byte-à-byte), détection PDF sans couche texte par pypdf → `ocr_requis` AVANT docling (OCR docling désactivé — cohérent sprint 2), échec isolé → statut `echec` + rapport `derived/rapport-parsing.csv`, 9 TU (40 au total, verts — docling jamais chargé par les TU). Fixtures régénérées : PDF conformes (xref) dont un réellement sans texte, docx avec titres stylés + tableau. **CA à cocher après le plan `docs/plans-test/s1.8-ingest-parse.md` sur base réelle.***

## S1.9 — Ingestion : qualification v0 (métadonnées & versions)

En tant que PO, je veux que le système distingue documents de référence, brouillons et versions obsolètes.

Critères d'acceptation :
- [x] Métadonnées inférées : projet (1er niveau du chemin), date (mtime + date dans le nom si présente), version (motifs `v\d+`, `VF`, `final`), statut brouillon (`draft`, `brouillon`, `WIP`)
- [x] L'inférence du champ `projet` est enregistrée comme **suggestion** : l'association faisant foi est celle confirmée par le PO via S1.11 (arbitrage A6, `docs/backlog-fonctionnel.md`)
- [x] Doublons détectés par hash ; versions regroupées par similarité de nom, la plus récente taguée `référence`
- [x] Jeu de fixtures piégé (spec_v1, spec_v2_final_VF3, copie conforme) correctement qualifié, couvert par tests unitaires — `test_jeu_piege_correctement_qualifie` (TU verts)

*Code livré le 02/07/2026 : `sia_ingestion/qualify.py` + `make ingest-qualify` (nœud C du DAG, fonction pure sans accès fichier), migration 0004 (colonne `projet_suggere` — nommée « suggérée » pour porter l'arbitrage A6 —, date_nom, version_no, marque_finale, statut_brouillon, groupe_version, est_reference, doublon_de). Règle de référence documentée : non-brouillon > version_no > marque finale > date (nom sinon mtime) ; doublons (même sha256) rattachés à un canonique et jamais référence ; `est_reference` alimentera le filtre « statut = référence » du RAG (E2). 9 TU (49 au total, verts). **CA 1–3 à cocher après le plan `docs/plans-test/s1.9-ingest-qualify.md` sur base réelle.***

## S1.10 — Intégration des gabarits internes (3 prompts SAFe)

En tant que PO, je veux que les prompts officiels soient la source unique des formats et du workflow (prépare E3 et E6).

Critères d'acceptation :
- [x] Les 3 fichiers fournis déposés dans `/api/prompts/` : prompt-1 (Epic), prompt-2 (Features), prompt-3 (Stories) — fait au kickoff
- [x] Extraction en templates structurés : format US du prompt 3 (blocs, tableau Gherkin des CA, critères DSFR) et tableau DoR — constantes de `api/sia_api/gabarit.py` (blocs récit/champs, colonnes CA, colonnes stories candidates, 10 critères DoR + statuts)
- [x] Validateur de conformité d'une US au format interne, couvert par tests — `valider_us` + `valider_dor`, 16 TU (75 au total, verts) ; hypothèses relevées jamais bloquantes (A8) ; CLI `python -m sia_api.gabarit <fichier.md>`
- [x] Candidates silver (`stories-silver-candidates.md`) déposées dans `/evals/silver/` et utilisées comme fixtures du validateur — les 3 passent CONFORME en exécution réelle (4/4/3 CA, 1/2/3 hypothèses relevées)
- [ ] Dépendance restante : 5–10 stories gold dans `/evals/gold/`, obtenues par extraction des meilleures stories Jira (reformatées) et/ou promotion des candidates silver (`stories-silver-candidates.md`) après validation par les PO pilotes — **statu quo (arbitrage du 02/07), dépendance externe**

*Livrée le 02/07/2026 — plan `docs/plans-test/s1.10-gabarit-validateur.md` (aucune base requise). Le validateur (DoR compris : « estimée en refinement » doit rester 🔵) sera consommé par le contrôle DoR automatisé d'E3 et le harnais E6.*

## S1.11 — Entité Projet : modèle de données (contexte & NFR)

En tant que PO, je veux créer un projet portant son contexte et ses NFR pour que la génération en tienne compte (D19, prépare E8 puis E3).

Critères d'acceptation :
- [x] Tables `projects` (nom, contexte libre) et `project_nfrs` (type parmi : performance, volumétrie, SSI, RGPD, accessibilité RGAA, disponibilité, auditabilité ; formulation vérifiable ; valeur cible optionnelle)
- [x] API CRUD minimale (création, lecture, mise à jour) couverte par tests — l'écran DSFR arrive avec E4 — 10 TU verts (POST/GET/PUT, 404, 409 nom dupliqué, 422 type NFR, 503 sans DB)
- [x] Association explicite projet ↔ dossiers documentaires : table dédiée, éditable ; la suggestion inférée par S1.9 est proposée puis confirmée ou corrigée par le PO (arbitrage A6 — le champ `projet` des documents ingérés est rattachable à un projet existant via cette table)

*Code livré le 02/07/2026 : migration 0005 (projects, project_nfrs avec CHECK sur les 7 types, project_dossiers UNIQUE(project_id, dossier) + origine po/suggestion), routes FastAPI `POST/GET/PUT /projects` + `GET /dossiers/suggestions` (expose les `projet_suggere` de S1.9 avec compteur et drapeau deja_associe — boucle A6), connexion par dépendance (`sia_api/db.py`, 503 explicite sans DATABASE_URL, démontré en uvicorn réel), DATABASE_URL fournie au service api du compose. 10 TU (59 au total, verts). **CA 1 et 3 à cocher après le plan `docs/plans-test/s1.11-projets.md` sur base réelle.***

---

## Amorce pour lancer Claude Code

Dans le dossier du futur repo, après avoir déposé CLAUDE.md, la note de cadrage et ce fichier :

> Lis CLAUDE.md, docs/note-cadrage-sia-po.md et docs/sprint-1-backlog.md. Propose-moi ton plan d'exécution pour S1.1 et S1.2 (fichiers créés, choix techniques), attends ma validation, puis implémente-les en respectant la Definition of Done. Une story = une branche = une PR.

Le référent technique valide le plan avant exécution, puis chaque PR.

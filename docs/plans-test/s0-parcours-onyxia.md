# Parcours de validation Onyxia — runbook maître (session TU/TNR référent)

Ordre d'exécution des plans de test sur base et Albert réels. Chaque plan reste la référence de détail ; ce runbook donne l'enchaînement, les prérequis et les points de contrôle. **À l'issue de chaque plan : consigner le résultat observable dans `SESSIONS.md` et cocher les CA du backlog** (règle « validation stack-live »).

## 0. Prérequis (une fois, ~20 min)

1. **Pod** : service `vscode-python` **sans GPU** (l'inférence est déportée sur Albert — CLAUDE.md).
2. **Clé Albert** : la **rotation post-incident (session 10) doit être confirmée** ; la clé vit dans l'env du pod (elle prime sur `.env`) — jamais dans le repo ni les logs.
3. **PostgreSQL** : lancer un service PostgreSQL du **catalogue Onyxia** (aucun n'existe à ce jour) ; relever hôte/port/base/utilisateur/mot de passe dans l'onglet Readme du service.
4. **Repo** :

```bash
cd ~/work/GRIAC/ && git checkout main && git pull origin main
make install && source .venv/bin/activate
# .env : DATABASE_URL=postgresql://<user>:<mdp>@<host>:5432/<base>  + ALBERT_BASE_URL
```

5. **TNR globale à froid** : `make lint && make test` → **203 tests verts** attendus.
6. **Migrations** : `uv run --package sia-api alembic -c api/alembic.ini upgrade head` → `0001 → 0009`.
7. Si la clé a tourné : rejouer `make probe` (plan s1.5) pour valider la nouvelle clé et rafraîchir `docs/albert-limits.md`.

## 1. Ingestion — sur `evals/fixtures/` (~30 min)

| Ordre | Plan | Livre | Point de contrôle |
|---|---|---|---|
| 1 | `s1.7-ingest-scan.md` | table `documents` + inventaire CSV | 7 fichiers, sha256, doublon détecté |
| 2 | `s1.8-ingest-parse.md` | dérivés markdown + statuts | 1er run = téléchargement modèles docling ; `scan-courrier` → `ocr_requis` |
| 3 | `s1.9-ingest-qualify.md` | métadonnées, doublons, versions, référence | v2_final_VF3 = référence, copie = doublon |
| 4 | `s2.1-chunking.md` | table `chunks` | tableaux jamais coupés, reprise sur hash |
| 5 | `s2.2-embeddings.md` | pgvector rempli | dimension 1024, reprise = 0 re-vectorisé |

## 2. RAG (~20 min)

1. `s2.3-recherche-hybride.md` — `POST /recherche` (BM25 + vecteurs + RRF, filtre référence/projet).
2. `s2.4-rerank-contexte.md` — **⚠️ étape 0 d'abord** : vérifier le schéma `/v1/rerank` par curl (c'est une HYPOTHÈSE documentée) ; puis `POST /contexte` (citations, repli RRF signalé si rerank KO).

## 3. Produit de bout en bout (~1 h)

1. `s1.11-projets.md` — CRUD projets/NFR + boucle A6.
2. `s2.5-workflow-etats.md` — sessions, invariant A8 (validation globale ne lève rien).
3. `s2.6-moteur.md` — **première génération réelle** (RAG + prompt 3 + gpt-oss-120b).
4. `s2.12-controle-dor-auto.md` — même session poussée aux étapes 3–4 (contrôle gabarit/DoR).
5. `s2.7-export.md` — CSV Jira + markdown avec récap A8.
6. `s2.8-ui-conversation.md` — parcours navigateur complet (proxy 8081).
7. `s2.9-ecrans-projet-documents.md` — écrans projets/documents, alerte couverture.
8. `s2.10-feedback-telemetrie.md` — notation, journal des validations, écran télémétrie.

## 4. Évals (~15 min, surveiller le quota tpd 2,46 M)

`s2.11-harnais-evals.md` — banc réduit puis banc complet (`make eval SORTIE=…`, 6 générations) ; consigner le classement `openweight-large` vs `openweight-medium` (verdict E6).

## 5. Hors pod — actions référent restantes

- CA2 S1.3 : protection de branche `main` (settings GitHub).
- Réserve S1.2 : `make dev` (compose complet) sur un hôte Docker.
- S1.6 : déploiement lab Helm (prérequis : images poussées en registre).
- Prérequis §7 de la note : stories gold, panel PO pilotes, snapshot du corpus réel.

# Parcours de validation Onyxia — runbook maître (session TU/TNR référent)

Version **exécutable** : toutes les commandes à copier-coller dans l'ordre, avec le résultat attendu à chaque étape. Les plans individuels (`s1.x`/`s2.x`) restent la référence de détail (cas limites, contre-épreuves) ; ce runbook déroule le chemin nominal complet. **À l'issue de chaque phase : consigner le résultat observable dans `SESSIONS.md` et cocher les CA du backlog** (règle « validation stack-live »).

Environnement : pod Onyxia `vscode-python` **sans GPU**, mode B (services lancés par uvicorn sur le pod, PostgreSQL = service du catalogue Onyxia).

## Phase 0 — Prérequis (une fois, ~20 min)

1. **Clé Albert** : rotation post-incident (session 10) **à confirmer** ; la clé vit dans l'env du pod (`ALBERT_API_KEY`, elle prime sur `.env`) — jamais dans le repo ni les logs.
2. **PostgreSQL** : lancer un service **PostgreSQL du catalogue Onyxia** (aucun n'existe à ce jour) ; relever hôte/port/base/utilisateur/mot de passe dans l'onglet **Readme** du service.
3. **Repo + environnement** :

```bash
cd ~/work/GRIAC/ && git checkout main && git pull origin main
make install
source .venv/bin/activate
# .env : ALBERT_BASE_URL=... (la clé vient de l'env du pod)
export DATABASE_URL="postgresql+psycopg://<user>:<mdp>@<host>:5432/<base>"   # valeurs du Readme — ce schéma marche partout (alembic ET psycopg)
```

4. **TNR à froid** :

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test
# attendu : lint vert, 203 tests verts
```

5. **Migrations** :

```bash
cd ~/work/GRIAC/api/ && source ../.venv/bin/activate
uv run alembic upgrade head
# attendu : 0001 -> ... -> 0009 sans erreur
```

6. **Sonde Albert** (obligatoire si la clé a tourné) :

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make probe
# attendu : 4/4 ok (models, me/info, chat, embeddings), quotas relevés dans docs/albert-limits.md
```

## Phase 1 — Ingestion sur `evals/fixtures/` (~30 min, 1er run parse = téléchargement docling)

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make ingest-scan CORPUS=evals/fixtures       # attendu : 7 fichiers inventoriés, derived/inventaire.csv
make ingest-parse CORPUS=evals/fixtures      # attendu : docx/pdf parsés, scan-courrier -> ocr_requis, derived/rapport-parsing.csv
make ingest-qualify                          # attendu : v2_final_VF3 = référence, copie byte-identique = doublon
make ingest-chunk                            # attendu : chunks créés, tableaux jamais coupés
make ingest-embed                            # attendu : embeddings 1024 par lots de 32, 0 échec
make ingest-embed                            # reprise D9 : attendu 0 chunk re-vectorisé
```

Recoupes SQL (psql du service, ou `python3 -c` avec psycopg) : `select count(*) from documents;`, `select chemin, statut_parsing, est_reference, doublon_de is not null from documents order by chemin;`, `select count(*) from chunks where embedding is not null;`.

## Phase 2 — RAG (~20 min)

**Étape 0 impérative — schéma `/v1/rerank` (HYPOTHÈSE documentée, plan s2.4)** :

```bash
cd ~/work/GRIAC/
BASE=$(grep '^ALBERT_BASE_URL=' .env | cut -d= -f2-)
curl -sS -o /tmp/rerank.json -w "HTTP %{http_code}\n" "$BASE/rerank" \
  -H "Authorization: Bearer $ALBERT_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"openweight-rerank","prompt":"délai de traitement","input":["Le délai d'\''instruction est de 15 jours.","La couleur du logo est bleue."]}'
head -c 400 /tmp/rerank.json ; echo
# attendu : HTTP 200 et data[{index,score}] — sinon consigner le schéma réel (le repli RRF est signalé, jamais silencieux)
```

Lancer l'api puis tester recherche et contexte :

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
uv run --package sia-api uvicorn sia_api.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &
sleep 3 && curl -sS http://localhost:8000/health
curl -sS -X POST http://localhost:8000/recherche -H "Content-Type: application/json" \
  -d '{"question": "temps de connexion au module d'\''authentification"}' | python3 -m json.tool
# attendu : résultats avec document+section, spec v2 en tête (filtre référence par défaut)
curl -sS -X POST http://localhost:8000/contexte -H "Content-Type: application/json" \
  -d '{"question": "temps de connexion au module d'\''authentification"}' | python3 -m json.tool
# attendu : contexte cité [Source : …], rerank_applique=true (ou false + avertissement si étape 0 KO)
curl -sS -X POST http://localhost:8000/recherche -H "Content-Type: application/json" \
  -d '{"question": "quotas de pêche en mer Baltique"}' | python3 -m json.tool
# attendu : avertissement anti-invention « aucune source »
```

## Phase 3 — Produit de bout en bout (~1 h, au navigateur)

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
SIA_API_URL=http://localhost:8000 uv run --package sia-web uvicorn sia_web.main:app --host 0.0.0.0 --port 8081 > /tmp/web.log 2>&1 &
# navigateur : https://<url-du-pod>/proxy/8081/
```

Parcours (chaque item renvoie à son plan pour les contre-épreuves) :

1. **Projets (s1.11 + s2.9)** : créer un projet avec 1 NFR ; associer les dossiers suggérés (A6) — vérifier en base `select dossier, origine from project_dossiers;` (suggestion vs po).
2. **Mes documents (s2.9)** : statuts libellés, doublon signalé, alerte couverture si < 0,8.
3. **Session (s2.6 + s2.5)** : coller une Feature (avec un `[HYPOTHÈSE À VALIDER]`) → **première génération réelle** ; question documentaire libre dans le fil (A2) → réponse sourcée ; « Oui » → l'étape avance et **les hypothèses restent en attente (A8)** ; confirmer une hypothèse individuellement.
4. **Contrôle DoR (s2.12)** : pousser la session aux étapes 3–4 ; le panneau « Dernier échange » signale toute US non conforme et tout tableau DoR absent/incomplet ; contre-épreuve : demander « mets ✅ à la ligne estimation » → avertissement 🔵.
5. **Export (s2.7)** : boutons CSV/markdown — récap A8 en tête du markdown, en-tête `X-Hypotheses-Non-Levees` sur le CSV.
6. **Feedback + télémétrie (s2.10)** : noter une story 4/5, valider un « Non » avec commentaire, puis écran Télémétrie — taux d'édition et % conservées cohérents avec ce qui vient d'être fait.
7. **Robustesse (s2.8)** : `kill` de l'api → tous les écrans affichent « API injoignable », jamais de traceback.

## Phase 4 — Banc d'évals E6 (~15 min, surveiller le quota tpd 2,46 M)

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
uv run --package sia-api python -m sia_api.evaluation --modeles openweight-large --max-cas 1   # banc réduit d'abord
make eval SORTIE=docs/eval-onyxia.md                                                           # banc complet : 3 cas × 2 modèles
# attendu : bandeau « Références SILVER », scores 3 axes, moyennes par modèle — consigner le classement (verdict E6)
```

## Phase 5 — Hors pod / actions référent restantes

- CA2 S1.3 : protection de branche `main` (settings GitHub).
- Réserve S1.2 : `make dev` (compose complet) sur un hôte Docker.
- S1.6 : déploiement lab Helm (prérequis : images poussées en registre).
- Prérequis §7 de la note : stories gold (→ `evals/gold/`, le few-shot et `make eval` basculent seuls), panel PO pilotes, snapshot du corpus réel.

## Clôture de la session de validation

`SESSIONS.md` : une entrée par phase jouée (résultat observable cité), CA cochés dans les backlogs sprint 1/2, écarts consignés (le moindre faux positif d'un plan = correction avant de continuer, règle « fix pipeline d'abord »).

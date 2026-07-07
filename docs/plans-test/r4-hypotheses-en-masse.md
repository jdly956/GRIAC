# Plan de test R4 — sélection en masse des hypothèses (refonte UX/UI, vague 1)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, api + web relancées (`make pod-up`). **Aucune migration** (la colonne `decidee_le`
existe depuis la 0010). Référence : `docs/refonte-ux-ui.md` — H5 ⚙, arbitrage UX1
(« pour les hypothèses, la sélection en masse doit être possible »).
**Prérequis** : une session avec plusieurs hypothèses en attente (la session 12 en avait 16).

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 316 verts (311 + 3 TU api + 2 TU web)
```

## 2. Contrat API (curl sur le pod)

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
# session 12 : lister les hypothèses en attente et leurs ids
curl -s http://localhost:8000/workflows/12 | python3 -m json.tool | grep -A2 '"statut": "en_attente"' | head
# décision en lot (remplacer les ids par 2 ids réellement en attente)
curl -s -X POST http://localhost:8000/workflows/12/hypotheses/decider-lot \
  -H 'Content-Type: application/json' -d '{"ids": [<id1>, <id2>], "statut": "rejetee"}' | python3 -m json.tool
```

Attendus : les 2 hypothèses passent à `rejetee`, les autres restent `en_attente` ;
rejouer le même appel → **409** (« Aucune hypothèse en attente ne correspond ») ;
`{"ids": [], …}` → **422** ; `{"statut": "levee"}` → **422** (A8 : statut inventé impossible).

## 3. Au navigateur — le geste de masse

1. Ouvrir la session : panneau « Hypothèses à valider » — chaque hypothèse
   **en attente** porte une case à cocher ; les déjà décidées n'en ont pas.
2. Cocher 2 hypothèses → « Rejeter la sélection » → confirmation navigateur →
   les 2 passent à `rejetee`, le compteur du panneau retombe, les autres ne
   bougent pas.
3. « Tout sélectionner » coche toutes les en attente ; « Confirmer la
   sélection » les lève d'un geste (relues avant — c'est le geste PO, A8).
4. Ne rien cocher → « Confirmer la sélection » → retour à l'écran, **rien ne
   change** (aucun appel api — contre-épreuve : les statuts sont intacts).
5. Les gestes existants restent : décision individuelle Confirmer/Rejeter,
   « Appliquer les N levée(s) proposée(s) » (S3.21).

## 4. Contre-épreuve A8 (SQL sur le pod)

```bash
docker compose exec postgres psql -U sia -d sia -c \
  "SELECT id, statut, statut_propose, decidee_le FROM workflow_hypotheses WHERE session_id = 12 ORDER BY id;"
```

Attendu : seules les hypothèses cochées portent le nouveau statut (celui du
bouton cliqué) avec `decidee_le` renseigné ; aucune hypothèse `en_attente`
non cochée n'a bougé ; aucun statut hors confirmee/rejetee.

## 5. Clôture

Consigner dans `SESSIONS.md` ; R4 cochée dans `docs/refonte-ux-ui.md` (§5).

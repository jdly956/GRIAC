# Plan de test R6 — suppression définitive d'une session (refonte UX/UI, vague 1)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, api + web relancées (`make pod-up`). **Aucune migration** (les cascades FK existent
depuis 0008/0009/0014/0015). Référence : `docs/refonte-ux-ui.md` — arbitrage UX8.
**Prérequis** : une session jetable (en créer une de test — ne pas sacrifier les sessions 11/12).

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 318 verts (316 + 1 TU api + 1 TU web)
```

## 2. Au navigateur

1. Créer une session de test (Feature quelconque), échanger un message, noter son id N.
2. Barre de session → « Gérer la session » : trois gestes distincts — Renommer,
   **Archiver** (réversible, hint explicite), **Supprimer définitivement**
   (garde-fou navigateur listant ce qui sera perdu).
3. Supprimer → confirmation → retour à l'accueil, la session N a disparu de la liste.
4. Ouvrir `…/sessions/N` à la main → page d'erreur 404 explicite.

## 3. Contre-épreuve cascade (SQL sur le pod)

```bash
docker compose exec postgres psql -U sia -d sia -c \
  "SELECT (SELECT count(*) FROM workflow_messages WHERE session_id = N) AS messages,
          (SELECT count(*) FROM workflow_hypotheses WHERE session_id = N) AS hypotheses,
          (SELECT count(*) FROM story_editions WHERE session_id = N) AS editions,
          (SELECT count(*) FROM conso_tokens WHERE session_id = N) AS conso_rattachee;"
```

Attendu : `0 | 0 | 0 | 0` — messages/hypothèses/éditions partis en cascade ;
la conso de la session est **conservée dérattachée** (SET NULL) :

```bash
docker compose exec postgres psql -U sia -d sia -c \
  "SELECT count(*) FROM conso_tokens WHERE session_id IS NULL;"   # ≥ nb d'appels de la session N
```

et la jauge Télémétrie (total du jour) n'a pas baissé après la suppression.

## 4. Non-régression adjacente

- L'archivage reste le geste réversible (S3.13) : archiver une autre session de
  test → masquée de l'accueil, `…/sessions/M` répond toujours.
- Suppression d'une session inexistante (`curl -X DELETE …/workflows/999`) → 404.

## 5. Clôture

Consigner dans `SESSIONS.md` ; R6 cochée dans `docs/refonte-ux-ui.md` (§5) —
**la vague 1 (session + socle) est complète**.

# Plan de test R8 — Mes documents refondu + « marquer obsolète » (vague 2)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, **migration 0016 à appliquer** (`uv run --package sia-api alembic upgrade head`),
api + web relancées (`make pod-up`). Référence : `docs/refonte-ux-ui.md` — H10 ⚙, arbitrage UX8.

## 1. TNR + migration

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 324 verts (321 + 3 TU, tuples étendus mécaniquement)
uv run --package sia-api alembic upgrade head   # 0016 : documents.est_obsolete
```

## 2. L'écran au navigateur

1. Ouvrir « Mes documents ». **Attendus** :
   - **tuiles d'état** en tête : documents / indexés / couverture % / à traiter
     (échecs + OCR, en alerte s'il y en a) / références ; l'alerte couverture
     < 80 % (A5) reste au-dessus quand elle s'applique ;
   - panneau de dépôt inchangé (dossier obligatoire S3.18) ; **« Historique des
     indexations (N) » replié** — déplié automatiquement pendant un run, avec
     le rafraîchissement 5 s ;
   - **inventaire regroupé par dossier** (📁 + compteur), chaque groupe
     annonçant le(s) projet(s) associé(s) — ou « associé à aucun projet »
     (le trou A6 devient visible d'un coup d'œil) ;
   - par document : badge de statut coloré (indexé vert, échec rouge, OCR
     orange, en attente bleu), « ✔ référence », actions **Fiche / Original /
     Obsolète / Supprimer**.

## 3. Le cœur : obsolète réversible (H10)

1. Choisir un document indexé cité par une recherche connue (ex. le docx des
   fixtures) ; en session, poser la question qui le cite → il apparaît en source.
2. « Obsolète » sur ce document → badge « obsolète » sur la ligne et la fiche.
3. Reposer la même question en session → **le document n'est plus cité**
   (les deux volets BM25 + vecteur le filtrent).
4. « Réactiver » → reposer la question → **il revient immédiatement** (aucune
   ré-indexation : chunks et embeddings étaient conservés).
5. Contre-épreuve SQL :

```bash
docker compose exec postgres psql -U sia -d sia -c \
  "SELECT id, nom, est_obsolete FROM documents ORDER BY id;"
```

## 4. Non-régression adjacente

- Dépôt + « Indexer maintenant » + suivi nœud par nœud : inchangés (S3.10/S3.18).
- Fiche document : badge obsolète + bascule dans « Actions » ; téléchargement
  et suppression S3.17 intacts.
- La suppression définitive reste distincte : elle détruit fichier + chunks
  (l'obsolète ne détruit rien).

## 5. Clôture

Consigner dans `SESSIONS.md` ; R8 cochée dans `docs/refonte-ux-ui.md` (§5) ;
H10 passe « validée » au registre si le comportement convient au PO.

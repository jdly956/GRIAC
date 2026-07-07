# Plan de test R9 — projets : édition après création, archiver/supprimer (vague 2)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, **migration 0017 à appliquer** (`uv run --package sia-api alembic upgrade head`),
api + web relancées (`make pod-up`). Référence : `docs/refonte-ux-ui.md` — arbitrage UX8 et
**H9 tranchée le 07/07 (« suppression libre, sessions orphelines »)**.
**Prérequis** : un projet jetable avec une session liée (créer les deux pour le test).

## 1. TNR + migration

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 329 verts (324 + 3 TU api + 2 TU web, tuples étendus)
uv run --package sia-api alembic upgrade head   # 0017 : projects.archive
```

## 2. Édition après création (le manque historique)

1. Ouvrir la fiche d'un projet → « Modifier le projet ». **Attendus** : nom et
   contexte pré-remplis, NFR existantes éditables, 2 lignes vides pour en ajouter.
2. Modifier le contexte, vider la formulation d'une NFR (= retrait), remplir
   une nouvelle ligne → Enregistrer. La fiche reflète les changements ;
   **les dossiers associés (A6) n'ont pas bougé** (contre-épreuve : cases intactes).
3. Ouvrir une session de ce projet et envoyer un message : le moteur reçoit le
   NOUVEAU contexte/NFR (E8 relit le projet à chaque appel).

## 3. Archivage (réversible)

1. Fiche projet → « Archiver le projet ». **Attendus** : disparu de la liste
   des projets ET du select « + Nouvelle session » de l'accueil ; ses sessions
   existantes affichent « (archivé) » à côté du nom du projet sur l'accueil.
2. Écran projets → « Projets archivés (N) » → Désarchiver → tout revient.

## 4. Suppression libre (H9) — la contre-épreuve

1. Fiche projet → « Supprimer définitivement » : le garde-fou navigateur
   rappelle que **les sessions liées continueront sans le contexte du projet**.
2. Confirmer. **Attendus** : projet, NFR et associations partis ; la session
   liée **s'ouvre toujours** et fonctionne — colonne projet « — » à l'accueil ;
   un message envoyé dans cette session part **sans** contexte/NFR projet
   (comportement d'une session sans projet, H9 assumé).
3. Contre-épreuve SQL :

```bash
docker compose exec postgres psql -U sia -d sia -c \
  "SELECT id, projet_id FROM workflow_sessions ORDER BY id;
   SELECT count(*) FROM project_nfrs; SELECT count(*) FROM project_dossiers;"
```

`projet_id` de la session passée à NULL ; plus aucune NFR/association du projet supprimé.

## 5. Non-régression adjacente

- Création de projet (3 NFR max à la création) : inchangée.
- Association des dossiers A6 : formulaire dédié intact (origines préservées).
- Suggestions de dossiers : inchangées.

## 6. Clôture

Consigner dans `SESSIONS.md` ; R9 cochée dans `docs/refonte-ux-ui.md` (§5) ;
H9 passe « validée stack-live » au registre si le comportement convient.

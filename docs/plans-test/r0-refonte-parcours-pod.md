# Plan de test MAÎTRE — refonte UX/UI R1→R10, parcours pod (~30–40 min)

> Runbook consolidé pour valider la refonte entière sur le pod en un parcours.
> Chaque étape renvoie au plan détaillé de sa story (`docs/plans-test/r*.md`)
> pour les contre-épreuves fines. Référence produit : `docs/refonte-ux-ui.md`
> (arbitrages UX1–UX13, hypothèses H1–H15).

## 0. Mise en route (pod Onyxia)

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
git fetch origin claude/ux-ui-ergonomie-refonte-fggyen
git checkout claude/ux-ui-ergonomie-refonte-fggyen && git pull
uv sync --all-packages                      # aucune dépendance nouvelle attendue
make lint && make test                      # attendu : 330 verts
make pod-up                                 # relance api + web ET joue les migrations
                                            # (0016 obsolète + 0017 projet.archive — intégré
                                            # au script depuis la session 30)
```

**Vérifier la ligne finale de `make pod-up`** : elle affiche le **commit servi**
— il doit être celui du `git pull` (sinon, de vieux process tournent encore :
relancer `make pod-up`). ⚠️ Sans les migrations, l'api répond 500 sur
`/documents` et `/projects` → écrans Documents/Projets « en erreur » (vécus
comme des liens cassés). Ouvrir l'UI via le proxy code-server `/proxy/8081/`.

## 1. Socle (R1) — 2 min

- En-tête DSFR (bloc-marque + « SIA PO »), **navigation 4 entrées** avec état
  actif qui suit l'écran (R10 inclus), notice D15 fine une ligne (plus d'alerte
  jaune pleine largeur), fil d'Ariane sur fiche document / fiche projet.
  → détail : `r1-socle-dsfr.md`

## 2. Écran session (R2+R3) — le cœur, 10 min

Ouvrir une session existante (11 ou 12) :

- **Barre de session** : stepper d'étape fidèle (A5), modèle + conso, exports
  CSV/markdown, menu « Gérer la session » (renommer / archiver / **supprimer**).
- **Chat** : fil complet à défilement interne ouvert en bas, bulles PO/assistant,
  markdown rendu, sources par message avec extrait exact (A3).
- **Rail droit empilé** : Stories produites (plier/déplier par US, **notation +
  édition + copie intégrées**), Hypothèses (toujours visibles), Sources de la
  dernière réponse.
- **Envoyer un message** : la bulle PO apparaît, « ⏳ Génération en cours… »,
  la réponse s'ajoute au fil **sans rechargement** ; stepper/conso/panneaux se
  mettent à jour dans la foulée ; la zone de saisie se vide (R3/H7).
- « Story suivante » et « Valider l'étape — Oui/Non » : mêmes comportements ;
  après un « Oui », le stepper avance sans rechargement.
- Contre-épreuve repli : JavaScript désactivé → tout fonctionne en pleine page (H14).
  → détail : `r2-ecran-session.md`, `r3-fragments-htmx.md`

## 3. Hypothèses en masse (R4) — 5 min

- Panneau Hypothèses : cases sur les seules « en attente », **« Tout
  sélectionner » + Confirmer/Rejeter la sélection** (confirmation) ; sans case
  cochée, rien ne bouge ; décision individuelle et « Appliquer les levées
  proposées » (S3.21) intacts.
- Contre-épreuve A8 en SQL : seules les cochées portent le statut choisi.
  → détail : `r4-hypotheses-en-masse.md`

## 4. Cycle de vie sessions (R6+R7) — 5 min

- **Accueil** : tableau des sessions d'abord (badge étape, nom du projet,
  actions), « + Nouvelle session » replié, lien « sessions archivées (N) ».
- Archiver depuis la liste → réapparaît via « archivées » → **Désarchiver**.
- Supprimer une session de test → garde-fou, 404 ensuite, cascade en base.
  → détail : `r6-suppression-session.md`, `r7-accueil.md`

## 5. Mes documents (R8) — 8 min

- **Tuiles d'état**, historique des indexations replié (déplié pendant un run),
  **inventaire regroupé par dossier** avec projets associés affichés.
- **Le cœur — obsolète réversible (H10)** : marquer obsolète un document cité
  → il n'est plus cité en session ; réactiver → il revient immédiatement
  (aucune ré-indexation).
  → détail : `r8-mes-documents.md`

## 6. Projets (R9) — 8 min

- Fiche projet : **« Modifier le projet »** (contexte/NFR édités → une session
  du projet reçoit le nouveau contexte E8 au message suivant).
- Archiver → disparaît des listes ET du choix de création ; désarchiver depuis
  « Projets archivés (N) ».
- **Suppression libre (H9)** sur un projet jetable avec session liée : la
  session survit et fonctionne **sans** contexte projet (l'avertissement du
  garde-fou le dit) ; NFR/associations parties en cascade.
  → détail : `r9-projets.md`

## 7. Suivi & réglages (R10) — 2 min

- Une page, deux sections (télémétrie + paramètres) ; changement de modèle
  appliqué sans relance ; anciennes URL redirigées.
  → détail : `r10-suivi-reglages.md`

## 8. Clôture

- Consigner le résultat global dans `SESSIONS.md` (règle validation stack-live).
- Cocher les stories dans `docs/refonte-ux-ui.md` §5 et recaler le registre
  H1–H15 (notamment H10/H14 après les contre-épreuves).
- Si un écart apparaît : le noter story par story — chaque R a son commit dédié
  sur la PR #37, les correctifs s'empileront de même.

# Plan de test R2 — écran session : chat + rail (refonte UX/UI, vague 1)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, api + web relancées (`make pod-up`). Aucune migration, aucune dépendance nouvelle.
Référence : `docs/refonte-ux-ui.md` — arbitrages UX4/UX5/UX6, hypothèses H2/H3/H4/H6/H8/H13/H14.
**Prérequis** : une session existante avec fil, stories et hypothèses (ex. session 11 ou 12).

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 307 verts (305 + 2 TU R2, 6 TU recalées — objet de la story)
```

## 2. Structure de l'écran (navigateur, session existante)

1. Ouvrir une session existante. **Attendus** :
   - **Barre de session** en tête : lien « ← Sessions », titre (ou « Session N »),
     **stepper DSFR** avec libellé d'étape et « Étape X sur 6 » (fidèle à l'étape
     réelle — A5), modèle actif + consommation, boutons **CSV Jira** /
     **Copier-coller (markdown)**, menu **« Gérer la session »** (renommer, archiver).
   - **Colonne chat** (gauche, ~2/3) : le fil **complet** défile à l'intérieur du
     cadre (H2), ouvert **en bas** (dernier message visible sans scroll — JS) ;
     bulles PO à droite (fond bleuté), assistant à gauche, markdown rendu,
     sources/extraits repliés par message (A3).
   - **Rail droit** (~1/3) : panneaux empilés **Stories produites** (une entrée
     pliable par US : contenu rendu, édition, copie, notation 1–5) /
     **Hypothèses à valider** (compteur, décision individuelle, lot S3.21) /
     **Sources de la dernière réponse** (extrait exact consultable).
   - Les blocs de bas de page ont disparu (« Dernière réponse », notation,
     édition, gestion, export) — leurs fonctions vivent dans la barre et le rail.

## 3. Le geste central : envoyer un message

1. Taper une réponse dans la zone de saisie (bas du chat) → Envoyer.
2. **Attendus** : indicateur « ⏳ Génération en cours… » + boutons désactivés
   (anti double-envoi, S3.8 conservé) ; à l'arrivée, la réponse est **le dernier
   message du fil** (pas de panneau séparé — H3), **sans doublon** avec le fil
   persisté (S3.9) ; le panneau « Sources de la dernière réponse » du rail
   reflète les sources de cette réponse ; si des hypothèses ont été ajoutées ou
   des levées proposées, une notice le dit dans la bulle et le compteur du
   panneau Hypothèses suit.
3. Aux étapes rédaction/contrôle DoR : boutons **« Story suivante »** (hint
   « sans changer d'étape » — S3.2) et **« Valider l'étape »** (Oui / Non +
   commentaire) juste au-dessus de la saisie ; vérifier qu'un « Non » avec
   commentaire déclenche bien l'itération (règle 5 bouclée).

## 4. Responsive et repli (H1/H14)

1. Fenêtre < ~992 px : le rail passe **sous** le chat, la page défile normalement.
2. JavaScript désactivé : les 3 formulaires POST classiques fonctionnent ;
   le fil s'ouvre en haut (repli assumé H14 — on scrolle) ; les panneaux
   `details` s'ouvrent/se ferment sans JS.
3. Écran ≥ 992 px : le rail est **sticky** (reste visible quand la page bouge).

## 5. Non-régression adjacente

- Décision d'hypothèse individuelle + lot « Appliquer les N levée(s) proposée(s) » :
  inchangés (mêmes routes) ; invariant A8 : rien ne se lève sans geste PO.
- Édition d'une story → badge « éditée — cette version part à l'export » ;
  l'export CSV/markdown depuis la barre porte bien la version éditée (S3.13).
- Notation → visible en télémétrie (E4.4). Renommer/archiver depuis la barre.
- Extrait anormalement long : toujours tronqué à 2 000 caractères (S3.20).

## 6. Clôture

Consigner dans `SESSIONS.md` (captures bienvenues) ; R2 cochée dans
`docs/refonte-ux-ui.md` (§5) ; noter que R5 (panneau Stories) est absorbée par R2.

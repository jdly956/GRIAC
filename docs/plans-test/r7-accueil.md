# Plan de test R7 — accueil orienté reprise + sessions archivées (vague 2)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, api + web relancées (`make pod-up`). Aucune migration.
Référence : `docs/refonte-ux-ui.md` — arbitrages UX10 (reprise d'abord) et UX8 (archivage réversible).

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 321 verts (318 + 1 TU api + 2 TU web)
```

## 2. Accueil au navigateur

1. Ouvrir l'accueil. **Attendus** : le tableau des sessions en cours arrive en
   premier (titre cliquable, badge étape fidèle, **nom du projet**, actions) ;
   la création vit derrière le bouton **« + Nouvelle session »** (dépliée
   automatiquement seulement s'il n'existe aucune session).
2. Créer une session depuis le formulaire déplié → redirection vers la session
   (comportement inchangé).
3. **Archiver** une session de test depuis la liste → elle disparaît, le
   compteur « Voir les sessions archivées (N) » s'incrémente.
4. **Supprimer** depuis la liste → garde-fou navigateur explicite, la session
   disparaît définitivement (contre-épreuve : URL directe → 404).

## 3. Sessions archivées

1. Suivre « Voir les sessions archivées (N) » : fil d'Ariane « Sessions >
   Archivées », tableau des archivées (titre consultable — la session s'ouvre).
2. **Désarchiver** → la session réapparaît à l'accueil (PATCH archivee=false),
   retour sur l'écran des archivées.
3. Supprimer une archivée → confirmée, définitive.

## 4. Non-régression adjacente

- API injoignable → l'accueil reste lisible avec l'alerte (TU existante).
- Préfixe proxy `/proxy/8081/` : liens du tableau et formulaires préfixés.
- Le select projet de la création liste bien les projets (E8 injecté à la création).

## 5. Clôture

Consigner dans `SESSIONS.md` ; R7 cochée dans `docs/refonte-ux-ui.md` (§5).

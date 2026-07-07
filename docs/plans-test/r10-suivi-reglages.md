# Plan de test R10 — « Suivi & réglages » fusionnés (vague 3)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, api + web relancées. Aucune migration. Référence : arbitrage UX9, hypothèse H12.

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 330 verts (329 + 1 TU R10)
```

## 2. Au navigateur

1. La navigation ne compte plus que **4 entrées** : Sessions · Projets ·
   Mes documents · **Suivi & réglages** (état actif fidèle).
2. « Suivi & réglages » : une page, deux sections — **Télémétrie** (indicateurs,
   jauge tpd, sessions/semaine) puis **Paramètres** (modèle actif, changement
   sans relance, retour au défaut). Changer de modèle → retour sur la même page,
   modèle actif mis à jour (et affiché dans la barre de session).
3. Anciennes adresses : `…/telemetrie` et `…/parametres` **redirigent** vers
   les ancres de la nouvelle page (liens/favoris préservés).
4. Api coupée partiellement : chaque section se dégrade seule
   (« indisponible pour l'instant »), l'autre reste servie.

## 3. Clôture

Consigner dans `SESSIONS.md` ; R10 cochée dans `docs/refonte-ux-ui.md` (§5) —
**la refonte R1→R10 est code-complète**.

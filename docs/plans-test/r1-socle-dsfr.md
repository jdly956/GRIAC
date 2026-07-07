# Plan de test R1 — socle DSFR & navigation (refonte UX/UI, vague 1)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée (`git fetch origin && git checkout claude/ux-ui-ergonomie-refonte-fggyen && git pull`),
api + web relancées (`make pod-up`). Aucune migration, aucune dépendance nouvelle.
Référence : `docs/refonte-ux-ui.md` (arbitrages UX9/UX11/UX13, hypothèse H15).

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 305 verts (302 + 3 TU R1)
```

## 2. Fumée sans réseau (rendu du socle)

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
uv run --package sia-web python -c "
from fastapi.testclient import TestClient
from sia_web import api_client
from sia_web.main import app
api_client.appeler = lambda *a, **k: (200, [])
html = TestClient(app).get('/').text
print('fr-header' in html, 'fr-notice--info' in html,
      'aria-current=\"true\">Sessions' in html,
      'Ne collez pas de données personnelles' in html,
      'fr-alert fr-alert--warning' not in html)
"
```

Attendu : `True True True True True` — en-tête DSFR, notice D15 une ligne,
entrée « Sessions » active, ancienne alerte disparue.

## 3. Au navigateur (proxy `/proxy/8081/`) — le test visuel

1. Ouvrir l'accueil. **Attendus** : en-tête DSFR complet (bloc-marque « République
   Française », titre de service « SIA PO »), navigation horizontale à 5 entrées
   avec **« Sessions » souligné/actif**, notice fine « Ne collez pas de données
   personnelles » sous l'en-tête (une ligne, plus d'alerte jaune pleine largeur).
2. Cliquer chaque entrée de navigation : Projets, Mes documents, Télémétrie,
   Paramètres — **l'entrée active suit l'écran** (aria-current, style DSFR).
3. Ouvrir la fiche d'un document depuis l'inventaire : **fil d'Ariane**
   « Mes documents > nom-du-fichier » en haut (l'ancien lien « ← Mes documents »
   a disparu) ; idem fiche projet (« Projets > nom »).
4. Basculer le thème du navigateur (clair/sombre) : le socle suit
   (`data-fr-scheme="system"` inchangé).
5. Vérifier au terminal du navigateur (onglet Réseau) que `dsfr.module.min.js`
   est bien chargé (H15) — sinon la nav reste fonctionnelle (liens simples).

## 4. Non-régression adjacente

- Préfixe proxy : tous les liens de navigation portent `/proxy/8081/…`
  (TU dédiée existante) ; redirections sans préfixe inchangées.
- Écran session, exports, formulaires : non touchés par R1 (le contenu des pages
  est identique, seul le cadre change).
- Le repli hors CDN demeure : couper le réseau CDN → page lisible (styles de repli).

## 5. Clôture

Consigner le résultat dans `SESSIONS.md` ; R1 cochée dans `docs/refonte-ux-ui.md` (§5).

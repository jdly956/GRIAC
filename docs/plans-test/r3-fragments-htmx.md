# Plan de test R3 — dynamisme htmx en fragments ciblés (refonte UX/UI, vague 1)

**Environnement cible** : pod Onyxia, branche `claude/ux-ui-ergonomie-refonte-fggyen` (PR #37)
déployée, api + web relancées (`make pod-up`). Aucune migration, aucune dépendance nouvelle.
Référence : `docs/refonte-ux-ui.md` — **H7 validée PO le 07/07** (renverse le « zéro route
fragment » de S3.8) ; repli sans JavaScript = H14.
**Prérequis** : une session existante avec fil, stories et hypothèses.

## 1. TNR

```bash
cd ~/work/GRIAC/ && source .venv/bin/activate
make lint && make test        # attendu : 311 verts (307 + 4 TU R3, test htmx S3.8 recalé)
```

## 2. Le geste central au navigateur — l'envoi ne recharge plus rien

1. Ouvrir une session existante, noter la position du fil et l'état des panneaux.
2. Envoyer un message. **Attendus** :
   - la bulle PO apparaît immédiatement dans le fil (en bas), l'indicateur
     « ⏳ Génération en cours… » s'affiche, les boutons se désactivent ;
   - à l'arrivée, la bulle assistant s'ajoute au fil **sans rechargement de la
     page** (l'onglet Réseau montre UN POST qui renvoie un fragment HTML,
     pas de page complète) ; le fil défile en bas ;
   - **la zone de saisie se vide** ; le focus/scroll de la page ne sautent pas ;
   - les panneaux du rail (Hypothèses, Sources de la dernière réponse, Stories),
     le **stepper** et la **conso** se mettent à jour dans la foulée (out-of-band).
3. « Story suivante » (étape rédaction/DoR) puis « Valider l'étape — Oui » :
   même comportement ; la décision PO apparaît comme bulle dans le fil ;
   après un « Oui », **le stepper avance** sans rechargement (A5).

## 3. Erreur en fragment

1. Provoquer une erreur (ex. couper l'api : `docker compose stop api` sur pod
   compose, ou clé Albert invalide). Envoyer un message.
2. **Attendus** : une alerte rouge s'ajoute au fil avec le détail ; les panneaux
   gardent l'état du dernier succès (pas de « sources (0) » fantôme) ; aucun
   message PO orphelin dans le fil ; les boutons se réactivent.

## 4. Repli sans JavaScript (H14)

1. Désactiver JavaScript dans le navigateur, recharger la session.
2. Envoyer un message : POST classique → **page complète** re-rendue, la
   réponse figure au bas du fil (persistée S3.9). Story suivante et Valider
   fonctionnent de même. Réactiver JavaScript ensuite.

## 5. Non-régression adjacente

- Rechargement manuel de la page (F5) après plusieurs échanges htmx : le fil
  persisté (S3.9) contient tous les échanges, sans doublon ni trou.
- Anti double-envoi : double-clic rapide sur « Envoyer » → un seul appel moteur
  (bouton désactivé pendant la requête).
- Conso de tokens : après quelques échanges, la conso affichée dans la barre
  suit (S3.11) — c'est l'OOB `#conso-meta` qui la porte.
- Décisions d'hypothèses (individuelles, lot S3.21) : toujours en POST pleine
  page — comportement inchangé (leur dynamisme viendra avec R4 si utile).

## 6. Clôture

Consigner dans `SESSIONS.md` ; R3 cochée dans `docs/refonte-ux-ui.md` (§5) ;
noter que l'état plié/déplié des panneaux du rail est réinitialisé à chaque
mise à jour OOB (limite v1 assumée, à revoir si gênant au pilote).

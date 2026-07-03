# Grille de notation — génération de user stories (E6)

Trois axes, notés de 0 à 1 (ou 1–5 en revue manuelle PO, à ramener sur 0–1 en
divisant par 5). La note d'une story est la moyenne des trois axes. Le harnais
`make eval` calcule des **proxys v0 automatiques** ; la revue manuelle PO reste
la référence, en particulier pour l'exactitude métier fine.

## Axe 1 — Gabarit (conformité au format interne)

La story respecte le format exact du prompt 3 : titre `**US — …**`, récit en
trois blocs, champs de cadrage, tableau des CA (`| # | Étant donné que… |
Lorsque… | Alors… |`), critères d'accessibilité DSFR/RGAA.

- **Proxy auto** : validateur S1.10 (`valider_us`) — 1,0 si conforme, −0,2 par
  violation (plancher 0).
- **Revue manuelle** : mêmes critères + lisibilité d'ensemble.

## Axe 2 — Exactitude (fidélité au brief, anti-invention)

Tout ce qui est affirmé vient du brief (ou du corpus cité) ; toute information
ajoutée par le modèle est marquée `[HYPOTHÈSE À VALIDER]`.

- **Proxy auto** : part des règles métier du brief retrouvées dans la story
  (recouvrement lexical ≥ 60 % par règle) ; pénalité de 0,1 par nombre (≥ 2
  chiffres) absent du brief et non marqué `[HYPOTHÈSE À VALIDER]` (plafond 0,5 ;
  « 200 » exempté — zoom texte RGAA standard).
- **Revue manuelle** : chaque règle, seuil et statut est-il exact pour votre
  domaine ? Les hypothèses sont-elles toutes marquées ?

## Axe 3 — Complétude (rien d'important ne manque)

Tous les blocs du gabarit sont remplis et les CA couvrent les attendus (cas
nominal, cas d'erreur, cas limite).

- **Proxy auto** : part des blocs du gabarit présents (50 %) + ratio du nombre
  de CA générés sur le nombre de CA de la référence, capé à 1 (50 %).
- **Revue manuelle** : les CA sont-ils testables tels quels ? Manque-t-il un
  parcours (erreur, droits, accessibilité) ?

## Protocole

1. `make eval` (clé Albert requise) — gold prioritaire, repli silver **affiché
   comme non validé** dans le rapport.
2. Modèles comparés par défaut : `openweight-large` (gpt-oss-120b) vs
   `openweight-medium` (Mistral-Small-3.2) ; Mistral Medium propriétaire si
   accès ALLiaNCE (`make eval MODELES=...`).
3. Relevés informels par appel (latence, tokens de sortie) : surveiller le
   quota journalier (tpd 2,46 M — S1.5) avant d'élargir le banc.
4. Recalibrage sur `/evals/gold/` dès fourniture des stories validées, puis
   revue manuelle PO sur un échantillon pour vérifier que les proxys classent
   les modèles dans le même ordre que l'humain.

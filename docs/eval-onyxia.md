# Benchmark génération — grille 3 axes (E6)

> Exécution réelle du banc sur pod Onyxia, session de validation du 06/07/2026
> (`make eval SORTIE=docs/eval-onyxia.md`, 3 cas × 2 modèles, appels Albert réels).

> ⚠️ Références **SILVER** (candidates non validées) : scores indicatifs, à recalibrer sur `/evals/gold/` dès fourniture.

| Modèle | Cas | Gabarit | Exactitude | Complétude | Moyenne | Durée (s) | Tokens | Erreur |
|---|---|---|---|---|---|---|---|---|
| openweight-large | Consulter l'état d'avancement de ma demande | 0.6 | 1.0 | 0.409 | 0.67 | 7.3 | 1127 | — |
| openweight-large | Déposer une pièce complémentaire demandée | 0.0 | 0.5 | 0.409 | 0.303 | 7.04 | 1211 | — |
| openweight-large | Être notifié par courriel d'un changement de statut | 0.4 | 0.75 | 0.409 | 0.52 | 7.44 | 1132 | — |
| openweight-medium | Consulter l'état d'avancement de ma demande | 1.0 | 1.0 | 0.5 | 0.833 | 7.17 | 496 | — |
| openweight-medium | Déposer une pièce complémentaire demandée | 1.0 | 1.0 | 0.5 | 0.833 | 7.7 | 573 | — |
| openweight-medium | Être notifié par courriel d'un changement de statut | 0.8 | 1.0 | 0.455 | 0.752 | 6.29 | 466 | — |

## Moyennes par modèle

- **openweight-large** : 0.498 (3 cas, 0 échec(s))
- **openweight-medium** : 0.806 (3 cas, 0 échec(s))

## Lecture (session de validation, 06/07/2026)

- **`openweight-medium` (Mistral-Small-3.2) devance nettement `openweight-large`
  (gpt-oss-120b) sur ce banc one-shot** : adhérence au gabarit 0,8–1,0 contre
  0,0–0,6, exactitude 1,0 partout, réponses ~2× plus concises (~500 vs ~1 150
  tokens). La cause de l'écart est la **dérive de format** de large — corroborée
  indépendamment en session réelle (session 8 : stories titrées `US 9 –` au lieu
  de `**US — Titre**`, extraction des stories perdue en aval).
- **Garde-fous** : références silver non validées, proxys v0 de la grille, 3 cas,
  et le banc mesure une génération one-shot — pas le workflow conversationnel
  complet (où large s'est montré qualitatif en session réelle 7/8).
- **Décision référent en attente** : essayer `ALBERT_MODEL_CHAT=openweight-medium`
  pour le moteur (alias surchargeable par env, prévu pour) ou statu quo jusqu'au
  recalibrage sur `/evals/gold/`.
- Coût du banc complet : ~7 k tokens — négligeable face au quota tpd (2,46 M).

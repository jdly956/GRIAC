# Sprint 3 — du MVP validé au pilote (protocole §6 de la note de cadrage)

> Squelette proposé par l'assistant (06/07/2026, « analyse backlog pour cadrer la suite ») — **à amender/prioriser par le référent**. Constat de cadrage : le backlog macro côté code est **complet et validé stack-live** (E0→E6 + E8, S2.1→S2.15, 229 tests ; E7 = post-go). Le chemin critique vers le pilote (D17 : 4–6 semaines, go/no-go §6) ne passe plus par le code : il passe par les **dépendances externes du §7** (snapshot corpus, stories gold, panel PO) et par quelques stories « gated » qui se débloquent avec elles. Mêmes règles que les sprints 1–2 : une story = une PR, TU + TNR + plan de test, validation stack-live.

## S3.0 — Préalables débloquants (référent, hors code)

- [ ] **Merge de la PR #30** (S2.13 validée stack-live + S2.14 + S2.15 + correctifs sessions 9–11) — débloque tout le reste
- [ ] Protection de branche `main` (CA2 S1.3, en attente depuis le sprint 1)
- [ ] **Snapshot du corpus réel** (PM) déposé sur l'espace MinIO → débloque S3.1 et S3.3, et l'axe « exactitude » du benchmark E6 (§6)
- [ ] **Stories gold** (extraction Jira et/ou promotion des silver validée par les PO) → débloque S3.4 (verdict modèle définitif) et le few-shot définitif
- [ ] **Panel de 2–3 PO pilotes** désigné + comptes SSP Cloud (D16) → débloque S3.5
- [ ] Registre d'images accessible depuis Onyxia → débloque le déploiement Helm lab (S3.5)
- [ ] **Arbitrages à rendre** : (a) sémantique du « Oui » (bouton « Story suivante » proposé — S3.2) ; (b) PostgreSQL 16 vs 18.3 CNPG pour le pilote/prod ; (c) hébergement du pilote : déploiement lab (Helm, recommandé — le pod chute) vs pod `make pod-up`
- [ ] Validations résiduelles sprints 1–2 (pod) : plan s2.15 (récap → registre stable), relance-idempotence du scan (plan s1.7 étape 4), réserve compose S1.2 (hôte Docker), `pre-commit run --all-files`

## S3.1 — Lecture S3/MinIO (E1, nœud A) — *gated : snapshot corpus*

Le scan refuse explicitement `s3://` à ce stade (`sia_ingestion/scan.py`) — c'est le dernier trou de code du DAG E1.

Critères d'acceptation :
- [ ] `make ingest-scan CORPUS=s3://bucket/prefix` : lecture du snapshot MinIO (endpoint/clés via variables d'environnement — jamais en dur, jamais loguées)
- [ ] Hash sha256 et reprise D9 inchangés (seuls les fichiers modifiés re-parcourent la chaîne) ; le reste du DAG (parse → embed) ne change pas
- [ ] TU avec client S3 simulé (aucun réseau) ; plan de test sur l'espace MinIO du pod

## S3.2 — Sémantique du « Oui » : bouton « Story suivante » — *gated : arbitrage (a)*

Constat sessions 9/11 : le cycle réel est « une story = rédaction + DoR » ; le « Oui » actuel fait défiler les étapes → machine à `synthese` pendant que les stories continuent (badge A5 trompeur).

Critères d'acceptation (à affiner post-arbitrage) :
- [ ] Aux étapes de production, un contrôle « Story suivante » itère sur la story suivante **sans changer d'étape** ; l'étape ne passe à « synthèse » que quand les stories candidates sont couvertes (ou sur décision explicite du PO)
- [ ] Badge d'étape fidèle (A5) ; invariants règle 5 (Oui/Non d'étape) et A8 intacts ; TU machine à états + écran

## S3.3 — Ingestion du corpus réel + recalibrages — *gated : snapshot corpus*

Critères d'acceptation :
- [ ] `make ingest` complet sur le snapshot ; rapport de couverture réel (E1) ; embeddings de nuit si les quotas l'imposent (D9, tpd 2,46 M)
- [ ] **2e test no-go du §6** : débit d'embeddings soutenable sous quotas, mesuré et consigné
- [ ] `RECHERCHE_SEUIL_DISTANCE` recalibré sur les distances mesurées du corpus réel (calibré fixtures : 0,55) ; écrans « mes documents »/couverture (A5) vérifiés sur volumétrie réelle

## S3.4 — Recalibrage E6 sur gold + verdict modèle définitif — *gated : stories gold*

Critères d'acceptation :
- [ ] `make eval` sur `/evals/gold/` (bascule automatique déjà codée) : verdict `openweight-large` vs `openweight-medium` (vs Mistral Medium si accès ALLiaNCE) documenté dans `docs/`
- [ ] Décision `ALBERT_MODEL_CHAT` définitive (l'essai medium S2.14 est confirmé ou annulé) ; few-shot gold en production

## S3.5 — Préparation du pilote (semaine 0 du protocole §6) — *gated : panel + registre*

Critères d'acceptation :
- [ ] Déploiement lab via Helm (images en registre) ; instance partagée sans comptes (A7) accessible aux pilotes
- [ ] **Charte d'usage** rédigée et versionnée (`docs/charte-usage.md`) : D15 (pas de données personnelles), périmètre, bonnes pratiques de validation A8
- [ ] Embarquement des 2–3 pilotes (session guidée sur le scénario `s2.13-scenario-rejeu-pod.md` adapté) ; plan de suivi hebdo : télémétrie E4.4 (actifs, % conservées, taux d'édition) + verbatims — les critères de go du §6

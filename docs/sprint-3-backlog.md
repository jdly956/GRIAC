# Sprint 3 — du MVP validé au pilote (protocole §6 de la note de cadrage)

> Squelette proposé par l'assistant (06/07/2026, « analyse backlog pour cadrer la suite ») — **à amender/prioriser par le référent**. Constat de cadrage : le backlog macro côté code est **complet et validé stack-live** (E0→E6 + E8, S2.1→S2.15, 229 tests ; E7 = post-go). Le chemin critique vers le pilote (D17 : 4–6 semaines, go/no-go §6) ne passe plus par le code : il passe par les **dépendances externes du §7** (snapshot corpus, stories gold, panel PO) et par quelques stories « gated » qui se débloquent avec elles. Mêmes règles que les sprints 1–2 : une story = une PR, TU + TNR + plan de test, validation stack-live.

## S3.0 — Préalables débloquants (référent, hors code)

- [ ] **Merge de la PR #30** (S2.13 validée stack-live + S2.14 + S2.15 + correctifs sessions 9–11) — débloque tout le reste
- [ ] Protection de branche `main` (CA2 S1.3, en attente depuis le sprint 1)
- [ ] **Snapshot du corpus réel** (PM) déposé sur l'espace MinIO → débloque S3.1 et S3.3, et l'axe « exactitude » du benchmark E6 (§6)
- [ ] **Stories gold** (extraction Jira et/ou promotion des silver validée par les PO) → débloque S3.4 (verdict modèle définitif) et le few-shot définitif
- [ ] **Panel de 2–3 PO pilotes** désigné + comptes SSP Cloud (D16) → débloque S3.5
- [x] **Arbitrages rendus (06/07/2026, référent)** : (a) sémantique du « Oui » → **bouton « Story suivante »** (S3.2 débloquée) ; (b) PostgreSQL → **18.3 CNPG assumé pour le pilote**, alignement 16 à trancher pour la prod (E7) ; (c) hébergement du pilote → **pod + `make pod-up`** (fragilité aux chutes assumée ; le déploiement Helm lab et le registre d'images glissent vers E7)
- [ ] Validations résiduelles sprints 1–2 (pod) : plan s2.15 (récap → registre stable), relance-idempotence du scan (plan s1.7 étape 4), réserve compose S1.2 (hôte Docker), `pre-commit run --all-files`

## S3.1 — Lecture S3/MinIO (E1, nœud A) — *gated : snapshot corpus*

Le scan refuse explicitement `s3://` à ce stade (`sia_ingestion/scan.py`) — c'est le dernier trou de code du DAG E1.

Critères d'acceptation :
- [ ] `make ingest-scan CORPUS=s3://bucket/prefix` : lecture du snapshot MinIO (endpoint/clés via variables d'environnement — jamais en dur, jamais loguées)
- [ ] Hash sha256 et reprise D9 inchangés (seuls les fichiers modifiés re-parcourent la chaîne) ; le reste du DAG (parse → embed) ne change pas
- [ ] TU avec client S3 simulé (aucun réseau) ; plan de test sur l'espace MinIO du pod

## S3.2 — Bouton « Story suivante » aux étapes de production — *arbitrage rendu le 06/07/2026*

Constat sessions 9/11 : le cycle réel est « une story = rédaction + DoR » ; le « Oui » actuel fait défiler les étapes → machine à `synthese` pendant que les stories continuent (badge A5 trompeur).

Critères d'acceptation :
- [ ] Aux étapes de production (rédaction, contrôle DoR), un bouton **« Story suivante »** enchaîne sur la story suivante (rédaction + contrôle DoR) **sans toucher la machine à états** ; le « Oui — étape suivante » reste le geste explicite du PO quand toutes les stories sont couvertes (règle 5 intacte)
- [ ] Consigne moteur : UNE story à la fois (évite la troncature à MAX_TOKENS constatée session 8), nombre de stories candidates restantes annoncé après chaque story, pas d'enchaînement spontané
- [ ] Badge d'étape fidèle (A5) ; invariants règle 5 et A8 intacts (aucun changement de `avancer`) ; TU écran + prompt

*Code livré le 06/07/2026 : route web `POST /sessions/{id}/story-suivante` (message dédié au moteur, jamais d'appel `/avancer`), panneau « Story suivante » + rappel sur le panneau « Valider l'étape » (`session.html`), consigne « UNE SEULE story à la fois » injectée aux étapes rédaction/contrôle DoR (`construire_prompt_systeme`). 3 TU (2 écran + 1 prompt) — 232 tests. CA à cocher via `docs/plans-test/s3.2-story-suivante.md` (badge stable = le test A5).*

## S3.3 — Ingestion du corpus réel + recalibrages — *gated : snapshot corpus*

Critères d'acceptation :
- [ ] `make ingest` complet sur le snapshot ; rapport de couverture réel (E1) ; embeddings de nuit si les quotas l'imposent (D9, tpd 2,46 M)
- [ ] **2e test no-go du §6** : débit d'embeddings soutenable sous quotas, mesuré et consigné
- [ ] `RECHERCHE_SEUIL_DISTANCE` recalibré sur les distances mesurées du corpus réel (calibré fixtures : 0,55) ; écrans « mes documents »/couverture (A5) vérifiés sur volumétrie réelle

## S3.4 — Recalibrage E6 sur gold + verdict modèle définitif — *gated : stories gold*

Critères d'acceptation :
- [ ] `make eval` sur `/evals/gold/` (bascule automatique déjà codée) : verdict `openweight-large` vs `openweight-medium` (vs Mistral Medium si accès ALLiaNCE) documenté dans `docs/`
- [ ] Décision `ALBERT_MODEL_CHAT` définitive (l'essai medium S2.14 est confirmé ou annulé) ; few-shot gold en production

## Lot pré-pilote (S3.6 → S3.13) — améliorer le MVP avant de le présenter aux PO

> Cadré le 06/07/2026 avec le référent (« UI à revoir, beaucoup de blocs, rien n'est dynamique, navigation difficile ; pas d'ajout de documents ni de suivi du pipeline depuis l'UI ; pas de changement de modèle ni de conso de tokens »). **Arbitrages rendus** : htmx léger (autorisé par CLAUDE.md) ; upload → bouton « Indexer » manuel (maîtrise du quota tpd) ; modèle = réglage **global instance** (écran Paramètres) ; **édition des stories incluse** (version simple). Ordre recommandé : S3.6→S3.8 (première impression), puis S3.11+S3.12, puis S3.10, puis S3.9/S3.13.

### S3.6 — Rendu markdown des messages (le choc visuel)

- [ ] Les messages assistant du fil sont rendus en HTML (gras, titres, listes, **tableaux Gherkin lisibles**) — rendu serveur (lib markdown Python), HTML échappé (le contenu vient du LLM), styles DSFR sur les tableaux
- [ ] Les messages PO restent en texte brut échappé ; TU rendu (tableau, gras, échappement d'un `<script>`)

*Code livré le 06/07/2026 (PR dédiée post-merge #30) : filtre Jinja `markdown` (`markdown-it-py`, `html=False` — tout HTML source échappé —, `breaks=True`, tables activées), appliqué aux seuls messages assistant (`session.html`), styles `.contenu-md` (tableaux bordés, défilement horizontal, pre-wrap neutralisé). 2 TU — 234 tests. CA à cocher via `docs/plans-test/s3.6-rendu-markdown.md` (s'applique au fil existant sans régénération).*

### S3.7 — Écran session réorganisé (navigation)

- [ ] Registre des hypothèses **replié par défaut** (`<details>`/accordéon DSFR, compteur visible), déplié s'il y a des levées proposées à décider
- [ ] Fil replié : seuls les N derniers échanges ouverts, les précédents en `<details>` ; ancre `#dernier-echange` après chaque envoi (plus de retour en haut de page)
- [ ] Panneaux d'action (message, story suivante, valider) regroupés et accessibles sans scroll long ; TU écran

*Code livré le 06/07/2026 (PR dédiée) : nouvel ordre de page — **« Dernière réponse » rendue EN HAUT après chaque envoi** (mieux qu'une ancre : les POST rendent la page directement, v1 sans JS — le dynamisme = S3.8) + zone d'action unifiée (message / story suivante / valider) + registre `<details>` replié (auto-déplié si levée proposée à décider, compteur dédié) + fil replié au-delà des 4 derniers messages (partiel `_message.html`) + notation repliée. 3 TU (37 web) — 237 tests. CA à cocher via `docs/plans-test/s3.7-ecran-session.md`.*

### S3.8 — Dynamisme htmx (envoi sans rechargement)

- [ ] Envoi de message et « Story suivante » via htmx : la réponse s'insère dans le fil sans rechargement complet ; **indicateur « génération en cours »** pendant l'appel ; bouton désactivé (anti double-envoi)
- [ ] Repli sans JavaScript conservé (les formulaires classiques restent fonctionnels — progressive enhancement) ; htmx vendoré en statique (pas de CDN bloqué) ; TU des fragments

### S3.9 — Traçabilité persistée + extrait exact (A3 complet)

- [ ] Sources, avertissements et divergences **persistés par message** (migration) et affichés dans le fil au rechargement — plus de « v1 assumée » S2.8
- [ ] Panneau sources : **extrait exact consultable** (le texte du chunk cité, replié par défaut) — la promesse de l'arbitrage A3
- [ ] TU api (persistance) + écran

### S3.10 — Corpus depuis l'UI : upload + pipeline + suivi

- [ ] « Mes documents » : **dépôt de fichiers** (multipart → dossier corpus du pod, taille/format contrôlés, statut « en attente d'indexation »)
- [ ] Bouton **« Indexer maintenant »** (arbitrage : manuel) : lance le pipeline complet en tâche de fond (scan→parse→qualify→chunk→embed) ; relance = reprise sur hash (D9)
- [ ] **Écran de suivi** : run en cours et historique (début/fin, compteurs par nœud, échecs détaillés, tokens embeddings consommés) — table `ingestion_runs` (migration)
- [ ] TU api (upload, déclenchement, statuts — pipeline mocké) + écran ; le plan de test réel mesure un run complet sur le pod

### S3.11 — Comptabilité tokens (global / session / import)

- [ ] Chaque appel chat capture `usage` (prompt + completion) → colonnes sur `workflow_messages` (migration) ; chaque lot d'embeddings capture ses tokens → rattaché au run S3.10
- [ ] Télémétrie : conso **globale** (jour/semaine, jauge vs tpd 2,46 M), **par session** (affichée aussi sur l'écran session), **par import**
- [ ] TU (usage simulé dans les fausses réponses Albert)

### S3.12 — Changement de modèle depuis l'UI (global instance)

- [ ] Écran **« Paramètres »** : modèle de chat actif (select `openweight-large`/`openweight-medium` + alias libre), stocké en base (table `parametres`, migration) — appliqué aux nouveaux appels sans relance
- [ ] Précédence documentée : base (UI) > défaut du code ; la variable d'env reste le réglage d'infra prioritaire au démarrage
- [ ] Le modèle actif est affiché sur l'écran session (le PO sait qui écrit) ; TU api + écran

### S3.13 — Confort PO : édition des stories, gestion des sessions, copie

- [ ] **Édition** (arbitrage : version simple) : chaque story extraite est éditable (textarea pré-remplie), la version éditée est stockée (migration) et **gagne à l'export** ; le « taux d'édition » de la télémétrie devient une mesure réelle (part des stories éditées)
- [ ] Sessions : **renommer** (titre libre affiché à l'accueil) et **archiver** (masquée de l'accueil, conservée en base — pas de suppression destructive)
- [ ] **Copier une story** : bouton par story (clipboard, dégradé acceptable sans JS : zone sélectionnable)
- [ ] TU api + écran

## S3.5 — Préparation du pilote (semaine 0 du protocole §6) — *gated : panel*

Critères d'acceptation :
- [ ] Instance pilote sur pod (`make pod-up`, arbitrage (c)) accessible aux 2–3 pilotes via le proxy ; procédure de remise en route documentée pour les chutes de pod (le référent la maîtrise déjà)
- [ ] **Charte d'usage** rédigée et versionnée (`docs/charte-usage.md`) : D15 (pas de données personnelles), périmètre, bonnes pratiques de validation A8
- [ ] Embarquement des 2–3 pilotes (session guidée sur le scénario `s2.13-scenario-rejeu-pod.md` adapté) ; plan de suivi hebdo : télémétrie E4.4 (actifs, % conservées, taux d'édition) + verbatims — les critères de go du §6

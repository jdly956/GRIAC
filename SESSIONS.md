# SESSIONS.md — état stratégique & journal des sessions

> Journal inversé : l'entrée la plus récente en tête. Chaque session close ajoute une entrée (règle « MAJ documentation à chaque clôture de session », CLAUDE.md). L'en-tête « État stratégique » est recalé à chaque clôture.

## État stratégique

**Voie active (07/07/2026)** : **LE LOT PRÉ-PILOTE EST ENTIÈREMENT MERGÉ ET VALIDÉ SUR POD** — PRs #31/#32/#33/#34 (S3.6→S3.14 : rendu markdown, écran réorganisé, htmx, traçabilité A3 persistée avec extrait exact, corpus depuis l'UI + pipeline + suivi, tokens + jauge tpd, modèle changeable depuis Paramètres, édition/renommage/copie, fiche document) — **283 tests verts**, pod validé par le référent (279 verts + écrans OK, photo terminal 07/07). En cours : **PR #35** (demandes référent du 07/07) — **S3.16 formats étendus (pptx/xlsx/eml)** + **S3.17 suppression de documents / téléchargement de l'original** (291 tests). Notée mais pas lancée : **S3.15 requête RAG contextualisée + éval retrieval recall@15** (issue de l'analyse chunking/scoring du 07/07 : la requête de recherche = dernier message PO seul). En attente référent : dépendances externes §7 (snapshot corpus → S3.1/S3.3, gold → S3.4, panel → S3.5), protection de branche `main`. Reste mineur : compteur télémétrique des stories éditées. Détail : `docs/sprint-3-backlog.md`.

*Voie précédente (06/07/2026, nuit)* : **la PR #30 est MERGÉE** (S2.13 validée stack-live, S2.14, S2.15, S3.2, 6 correctifs sessions réelles, cadrage sprint 3 — 232 tests). **Le lot pré-pilote S3.6→S3.13 est en cours** (cadré avec le référent : UI markdown/navigation/htmx, upload + pipeline depuis l'UI, modèle en Paramètres, comptabilité tokens, traçabilité A3 complète, édition des stories) — une story = une petite PR depuis `main` ; S3.6 (rendu markdown) livrée en premier (session 28). En attente référent : dépendances externes §7 (snapshot corpus, gold, panel PO), protection de branche, plans s2.15/s3.2/s3.6 à jouer sur pod. Détail : `docs/sprint-3-backlog.md`.

*Voie précédente (06/07/2026, soir)* : **la PR #29 est MERGÉE — la séquence de validation Onyxia est close côté repo.** Le backlog d'améliorations issu du réel est entamé sur la **PR #30 (draft)** : **S2.13 — rapprochement décision d'interview ↔ registre A8 (« levée proposée »)** (commit `8b35dec`) — le moteur reçoit le registre des hypothèses en attente dans son prompt et **propose** la levée quand un message du PO la tranche (`[LEVÉE PROPOSÉE : #id — confirmée|rejetée — justification]`, persistée par la migration 0010) **sans jamais toucher le statut** (invariant A8 vérifié par TU), badge à l'écran session — et **S2.14 — bascule du défaut `ALBERT_MODEL_CHAT` vers `openweight-medium`, à l'essai** (commit `f35b538`, « go pour la suite » du référent = arbitrage rendu) : verdict E6 v0 0,806 vs 0,498, réversible par variable d'env (TU du chemin de retour), le banc `make eval` compare toujours les deux — décision définitive au gold. **Le rejeu pod a d'abord buté sur un déploiement raté** (pull avorté par une copie locale de `docs/eval-onyxia.md` — les sessions 9 et 10 tournaient sur l'ANCIEN code), puis, une fois la branche réellement déployée, **la session 11 a validé S2.13 stack-live** : levées proposées « confirmée » ET « rejetée » émises, badges affichés, statuts intacts (A8), persistance démontrée — **CA S2.13 cochés**. Les sessions réelles 9/10/11 ont aussi livré 6 correctifs (`4ce5bd4` + session 11, **225 tests verts**) : story perdue sur variante de titre (extraction tolérante + signalement), **rappel de titre au-dessus des DoR qui écrasait la vraie story dans les exports** (une story exige `**En tant que**`), tableau DoR contrôlé à toute étape de production, listes numérotées tolérées, entêtes markdown écartées du registre, consigne « levée proposée » renforcée (dernière position + exemple). **En attente référent** : (1) revue/merge de la **PR #30** ; (2) protection de branche `main` (CA2 S1.3) ; (3) réserve compose S1.2 (hôte Docker) ; (4) déploiement Helm lab (registre d'images) ; (5) prérequis §7 (stories gold, snapshot corpus réel, panel PO pilotes) ; (6) arbitrage PostgreSQL 16 vs 18.3 CNPG pour la prod. **Backlog d'améliorations restant** (constats session 9 en tête) : **anti-invention incomplet** (marquage au format du modèle `[HYPOTHÈSE 1 A]` + valeurs inventées affirmées sans marqueur — story dédiée à cadrer) ; **sémantique du « Oui »** (utilisé comme « story suivante », badge étape trompeur — arbitrage produit) ; adhérence format d'`openweight-large` (secondaire — à rouvrir seulement si l'essai medium déçoit) ; relance-idempotence du scan (plan s1.7 étape 4, validation pod).

*Voie précédente (06/07/2026, session 26)* : **LA session de validation Onyxia est jouée — runbook s0 déroulé de bout en bout, phases 0→4 validées stack-live** (session 26) : TNR à froid, migrations 0001→0009, probe 4/4 (quotas inchangés : tpm 128k, tpd 2,46 M), chaîne d'ingestion complète sur fixtures (contre-épreuve D9 ✅), RAG corrigé sur preuve réelle (schéma rerank confirmé `{model, query, documents}` → `results[{index, relevance_score}]` ; seuil anti-invention `RECHERCHE_SEUIL_DISTANCE=0,55` calibré sur distances mesurées), **premières générations réelles du moteur E3** (workflow 0→5 complet, A2/A3/A8 démontrés au navigateur), exports/feedback/télémétrie/robustesse validés, **banc E6 réel** : `openweight-medium` **0,806** > `openweight-large` **0,498** (dérive de format de large, corroborée en session réelle — rapport `docs/eval-onyxia.md`). **PR #29 (draft) = 8 correctifs issus du réel + docs, 212 tests verts — prête pour revue référent, à merger pour clore la validation.** Écarts assumés : PostgreSQL 18.3 CNPG (stack cible 16 — à trancher pour la prod), pod GPU utilisé (préférer CPU), UI de dev via proxy code-server `/proxy/8081/` (port non exposable, RBAC) — `make pod-up` remet tout en route après chaque chute de pod (seul `~/work` survit ; secrets dans `~/work/.sia-db.env`). **En attente référent** : (1) revue/merge PR #29 ; (2) arbitrage modèle chat (`ALBERT_MODEL_CHAT=openweight-medium` à l'essai ou statu quo jusqu'au gold) ; (3) protection de branche `main` (CA2 S1.3) ; (4) réserve compose S1.2 (hôte Docker) ; (5) déploiement Helm lab (registre d'images) ; (6) prérequis §7 : stories gold, snapshot corpus réel, panel PO pilotes. Backlog d'améliorations issu du réel : rapprochement décision d'interview ↔ registre A8, adhérence format de large, relance-idempotence du scan (s1.7 étape 4).

*Historique (03/07 et avant)* : **sprint 1 code-complet (11/11 stories, PRs #1–#14)** et **sprint 2 bien entamé : S2.1 (chunking), S2.2 (embeddings) et S2.3 (recherche hybride RRF) livrées (PRs #15–#17)** — la chaîne corpus → recherche citée est code-complète de bout en bout (hors lecture S3, snapshot MinIO attendu, prérequis §7). **S2.4 livrée (PR #18) : E2 est code-complet** — `POST /contexte` (rerank en hypothèse de schéma vérifiée à l'étape 0 du plan, repli RRF signalé, assemblage cité ≤ 6k tokens de chunks). **S2.5 (PR #19) et S2.6 (PR #20) livrées : E3 a son squelette ET son moteur** — machine à états persistée (invariant A8 vérifié par TU) + `POST /workflows/{id}/message` (prompt 3 + contexte/NFR projet + extraits cités + few-shot silver « non validée », hypothèses auto-extraites, divergences A9, garde-fous règle 1/budget/réponse vide). **La première génération réelle de bout en bout = plan `docs/plans-test/s2.6-moteur.md`** (pod, clé requise). **S2.7 (PR #21) livrée : E5 — export CSV Jira + markdown avec récapitulatif A8** (dédup par titre, annotation de conformité S1.10, 409 sans stories). **S2.8 (PR #22) livrée : E4.1 — l'écran de conversation** (accueil + session : étape A5, fil, sources A3, hypothèses/décision individuelle A8, divergences A9, exports E5 proxifiés, zéro JavaScript, DSFR CDN + repli). **Le MVP est utilisable au navigateur de bout en bout** dès que la base et la clé sont en place (plan `s2.8-ui-conversation.md`). **S2.9 (PR #23) livrée : E4.2 + E4.3** — écran projets (création avec NFR typées, détail, **association explicite des dossiers A6** : suggestions cochables avec compte de documents, origines suggestion/po préservées via PUT complet) + écran « mes documents » (api `GET /documents` + `/documents/stats`, statuts libellés, **alerte couverture < 0,8 — A5**) + navigation commune. **S2.10 (PR #24) livrée : E4.4 — feedback par story + télémétrie** (migration 0009, note 1–5 + commentaire, journal des validations Oui/Non, `GET /telemetrie` en proxys v0 assumés — actifs hebdo = sessions/semaine A7, conservée = note ≥ 4, taux d'édition = part des « Non » —, panneau de notation + écran télémétrie) : **E4 est complet**. **S2.11 (PR #25) livrée : E6 — harnais d'évals `make eval`** (grille 3 axes documentée dans `evals/grille-notation.md`, proxys v0 automatiques ancrés sur le validateur S1.10 + anti-invention, gold prioritaire/repli silver affiché non validé, comparatif `openweight-large` vs `openweight-medium`, relevés latence/tokens ; l'exécution réelle du banc = plan `s2.11-harnais-evals.md`, ~6 générations). **S2.12 (PR #26) livrée : contrôle DoR/gabarit automatisé** (`controler_conformite` : chaque US des étapes de production passe par `valider_us`, le tableau DoR — isolé des tableaux de CA — par `valider_dor` à l'étape 4 ; signalé en avertissement, jamais bloquant — règle 5). **Le backlog macro côté code est complet : E0→E6 + E8 livrés (203 tests) ; E7 = post-go.** La suite est entre les mains du référent : session Onyxia TU/TNR sur toute la chaîne — **suivre le runbook maître `docs/plans-test/s0-parcours-onyxia.md`** — version **exécutable** (PR #28) : toutes les commandes copiables dans l'ordre (prérequis, `DATABASE_URL` au schéma `postgresql+psycopg://` qui marche partout, ingestion, vérif curl du schéma rerank en étape 0, api/web sur le pod, parcours navigateur, banc E6, actions hors pod). **Session Onyxia du référent (demain)** : dérouler la chaîne complète sur base réelle — service PostgreSQL du catalogue à lancer (aucun n'existe), puis migrations 0001→0009, plans S1.7, S1.8, S1.9, S2.1, S2.2, S1.11 (CRUD + A6), puis S2.3 → S2.10, s'aider des plans `docs/plans-test/` ; **rotation de la clé Albert à confirmer** (incident session 10) ; CA2 S1.3 (protection de branche) ; réserve compose S1.2. S1.5 : **verdict no-go n°1 GO** (fenêtre gpt-oss-120b 131 072 ≫ budget 20k ; tpm 128k, **tpd 2,46 M = contrainte à surveiller** ; gotchas Albert consignés : max_tokens/raisonnement, **`encoding_format="float"` sur les embeddings SDK**). S1.3 : CI GitHub Actions démontrée verte sur la PR #6 ; **CA2 (protection de branche) = action référent en attente**. **S1.7 → S1.9, S1.11 et S1.6 mergées (PRs #7–#11)** — S1.6 avec job CI `helm-chart` vert (helm lint + template) dès le premier run. **Il ne reste au sprint 1 que S1.10** (templates structurés + validateur de conformité US). **En attente côté référent** : (1) **lancer un service PostgreSQL du catalogue Onyxia** (aucun n'a jamais existé — rectification session 10) puis dérouler la chaîne complète : migrations 0001→0005, plans S1.7 (scan), S1.8 (parsing, 1er run = téléchargement des modèles docling), S1.9 (qualification), S1.11 (CRUD + boucle A6) — commandes consolidées transmises en session ; (2) rendu helm S1.6 sur pod : **déjà validé ✅** (lint 0 failed, template réel 0 GPU) — reste le déploiement lab (prérequis : images poussées en registre) ; (3) CA2 S1.3 — protection de branche sur `main` ; (4) réserve compose S1.2 (mode A sur hôte Docker) ; (5) **rotation de la clé Albert à confirmer** (incident session 10). Les CA non cochés des stories mergées se cochent au fil de ces validations. **Découverte pod : `ALBERT_API_KEY` est injectée dans l'environnement du pod et prime sur le `.env`** (ALBERT_BASE_URL vient du `.env`). **NB : `make dev` exige un `.env` renseigné** (comportement voulu S1.4). Règle de méthode active : « TU + TNR + plan de test avant toute livraison » (CLAUDE.md). Réserve S1.2 (compose complet) inchangée — étape 7 des plans de test, au plus tard S1.6. Pod de dev : prendre un service `vscode-python` **sans GPU** ; checklist premier login (maxima CPU/RAM, MinIO — action n°7) toujours à consigner. Bascule de la branche par défaut sur `main` : à vérifier dans les settings GitHub.

**Réserves / dettes actées** : validation compose réelle (S1.2, voir ci-dessus) ; `pre-commit run --all-files` jamais exécuté de bout en bout (proxy des sessions Claude Code restreint ; hooks installés, config validée) — à jouer une fois sur le pod ; benchmark E6 et stories gold : statu quo (arbitrage du 02/07).

**Arbitrages du référent technique (02/07/2026)** : (1) le référent technique est désigné — c'est l'utilisateur de ces sessions ; (2) les 3 prompts SAFe sont fournis et versionnés ; (3) calendrier du benchmark E6 vs contenu du sprint 1 : statu quo pour l'instant, pas de décision ; (4) objectif 5–10 stories gold vs 3 silver disponibles : statu quo pour l'instant. **Cible fonctionnelle arbitrée en itération Q/R (9 arbitrages A1–A9, journal complet dans `docs/backlog-fonctionnel.md`)** — points saillants : le RAG est un mécanisme interne au service du LLM accompagnant (jamais une recherche autonome), mobilisé à chaque étape du workflow ; question libre conservée dans le fil ; transparence à 3 niveaux (citations inline, panneau sources avec extraits, marquage d'origine corpus/PO/modèle) ; divergences corpus↔PO signalées et arbitrées par le PO ; pas de jalon de démo intermédiaire (risque tunnel assumé) ; écran couverture + alerte conversationnelle ; PO autonome jusqu'à la sélection des dossiers documentaires de son projet ; instance partagée sans comptes au MVP ; export non bloquant avec récapitulatif des hypothèses. Amendements induits appliqués : note §4, CLAUDE.md (contexte, E3/E4/E5/E8, annexes), backlog sprint 1 (S1.9, S1.11). Plan S1.1/S1.2 validé (« ok go »).

**Prérequis en attente (note de cadrage §7)** : snapshot du corpus (PM) ; stories gold (extraction Jira et/ou validation des silver, avant fin sprint 1) ; panel des PO pilotes ; relevé des curseurs CPU/RAM et espace MinIO au premier login SSP Cloud (architecte). La clé Albert existe — le relevé des quotas est intégré à S1.5.

---

## Session 07/07/2026 (29) — analyses chunking/RAG + S3.16 formats étendus + S3.17 suppression/original (PR #35)

**Contexte** : suite de la session 28 sur la même branche (repartie de `main` après le merge de la PR #34 — le lot pré-pilote S3.6→S3.14 est entièrement mergé et validé pod : 279 verts + écrans OK, photo terminal du référent).

**Volet analyse (aucun code)** — trois questions du référent sur le RAG, réponses en prose :
- **chunking** : découpage déterministe par sections de titres (500–800 tokens, chevauchement ≤ 150, tableaux jamais coupés) — aucun appel LLM dans toute la chaîne de sélection ;
- **scoring** : BM25 français + cosinus pgvector (seuil distance 0,55), fusion RRF k=60 (30 candidats/volet), rerank bge-reranker-v2-m3, assemblage 8–15 chunks ≤ 6k tokens — 6 portes d'exclusion identifiées et documentées en réponse ;
- **contexte projet** : pris en compte pour la GÉNÉRATION (prompt système E8) mais PAS dans la requête de recherche (dernier message PO seul) → **S3.15 « requête RAG contextualisée » + jeu d'éval retrieval (recall@15)** proposée, notée par le référent (« ok c'est noté »), inscrite au backlog sprint 3 comme candidate — pas encore « go ».

**S3.16 — formats étendus** (« peut-on étendre les formats acceptés pour gérer les powerpoint, les excels et les mails (.eml) ? ») :
- **Source unique** : `EXTENSIONS_PARSABLES = (docx, pdf, pptx, xlsx, eml)` dans `sia_api/documents.py`, consommée par le nœud parse (`EXTENSIONS_PARSEES`) ET par les stats de couverture (`REQUETE_STATS` recalée) — plus deux listes à désynchroniser ;
- **pptx/xlsx** : même chemin docling que docx/pdf (zéro code nouveau côté conversion — docling les couvre nativement) ;
- **.eml** : convertisseur dédié `convertir_eml_en_markdown` (stdlib `email`, `policy.default`) — objet en titre, en-têtes From/To/Cc/Date, corps texte (HTML seul dégradé en texte brut), **pièces jointes listées mais jamais extraites** (une PJ pertinente se dépose comme document à part) ; routage dans `parser_lot` avant docling ;
- upload : `EXTENSIONS_ACCEPTEES` + label écran étendus (`.odt` reste accepté mais non parsé — inchangé).
- **4 TU** (conversion eml en-têtes/corps/PJ, HTML dégradé, routage .eml sans docling, upload des 3 formats) — **283 tests verts** (279 → 283). ⚠️ Consigné au plan : premier pptx/xlsx indexé sur un pod = téléchargement des modèles docling (une fois).

**Validation en session** : lint vert, **283 tests verts** (TNR complet). Validation stack-live = plan `docs/plans-test/s3.16-formats-etendus.md` (dépôt réel des 3 formats sur pod, indexation, fiche document, RAG sourcé).

**S3.17 — supprimer un document / télécharger l'original** (« ajoute la possibilité de supprimer les documents et de télécharger l'original » — empilée sur la PR #35, un commit par story) :
- **Télécharger** : `GET /documents/{id}/original` (FileResponse sous le nom d'origine) ; côté web, `telecharger_binaire` — un .docx passé par `.text` serait corrompu — avec Content-Disposition propagé ; fichier disparu (pod recréé) → 404 explicite ;
- **Supprimer** : `DELETE /documents/{id}` — ligne en base (chunks en **cascade FK** 0006), `doublon_de` des autres documents repointé NULL, **fichier source retiré du corpus** (sinon ré-inventorié au prochain scan — D9) + dérivé markdown ; fichiers supprimés **après** le commit (une erreur base ne détruit rien) ; garde-fou partagé `_source_dans_corpus` (un chemin hors racine corpus n'est jamais servi ni supprimé) ;
- Écran fiche : panneau « Actions » — téléchargement + suppression derrière `confirm()` navigateur, avec l'avertissement « définitif » explicite. Choix assumé : **pas de corbeille** (un document se redépose ; les sessions S3.13, elles, s'archivent sans destruction).
- **8 TU** (5 api : téléchargement, 404 absent, garde-fou traversée, suppression base+fichiers, 404 ; 3 web : actions, redirection, proxy binaire) — **291 tests verts** (283 → 291). Plan `docs/plans-test/s3.17-suppression-original.md` (contre-épreuves : chunks à 0, RAG « aucune source », ré-indexation sans résurrection).

**Mini-récap** :
- ✅ Fait : analyses chunking/scoring/contexte (aucun code) ; S3.16 formats étendus (283 tests) + S3.17 suppression/téléchargement (291 tests) sur la PR #35 ; backlog sprint 3 recalé (S3.15 candidate + S3.16 + S3.17) ; en-tête stratégique recalé (lot pré-pilote mergé)
- ⏳ Référent : revue/merge de la PR #35 ; plans s3.16 + s3.17 sur pod ; « go » éventuel sur S3.15
- ⏳ Ensuite : dépendances externes §7 (snapshot corpus, gold, panel PO)

---

## Session 06/07/2026 (28) — lot pré-pilote : S3.6 rendu markdown (PR post-merge #30)

**Contexte** : la **PR #30 est mergée par le référent** (CI verte, 232 tests) — la branche de travail repart de `main` ; le lot pré-pilote S3.6→S3.13 (cadré en session 27, 4 arbitrages rendus) démarre en petites PR, une story à la fois. « merge ok. go. »

**S3.6 — rendu markdown des messages** (le choc visuel n°1 : le PO lisait les tableaux Gherkin en pipes bruts, constaté sessions 9/11) :
- filtre Jinja `markdown` (`markdown-it-py`, nouvelle dépendance web) : `html=False` — **tout HTML présent dans la sortie du LLM est échappé**, seul le HTML produit par le rendu est servi ; `breaks=True` (les sauts de ligne simples restent visibles) ; tables activées ;
- appliqué aux **seuls messages assistant** (`session.html`) — les messages PO restent du texte brut échappé ; styles `.contenu-md` (tableaux bordés, défilement horizontal des tableaux larges, `pre-wrap` neutralisé sur le contenu rendu) ;
- 2 TU (tableau + gras rendus, pipes bruts absents, message PO non rendu ; `<script>` échappé) — **234 tests au total**. Plan `docs/plans-test/s3.6-rendu-markdown.md` — le rendu s'applique au fil persistant des sessions existantes, aucune régénération requise.

**Validation en session** : lint vert, **234 tests verts**. Validation stack-live = plan s3.6 (rouvrir la session 11 sur le pod suffit).

**S3.7 — écran session réorganisé** (PR #31/S3.6 mergée dans la foulée par le référent ; « go ») : nouvel ordre de page — **« Dernière réponse » rendue EN HAUT après chaque envoi** avec sa traçabilité (mieux qu'une ancre : les POST rendent la page directement, v1 sans JS) ; **zone d'action unifiée** (message / story suivante / valider l'étape) juste dessous ; **registre replié** (`<details>`, auto-déplié seulement si une levée proposée attend la décision — compteur « dont N à décider ») ; **fil replié** au-delà des 4 derniers messages (« Voir les N échanges précédents », partiel `_message.html`) ; notation repliée. 3 TU — **237 tests verts**. Plan `docs/plans-test/s3.7-ecran-session.md`.

**S3.8 — dynamisme htmx** (PR #32/S3.7 mergée dans la foulée) : **htmx 2.0.4 vendoré** (`static/htmx.min.js` via le registre npm — les CDN unpkg/jsdelivr sont bloqués par la politique réseau de l'environnement, ce qui valide le choix du vendoring) + montage `StaticFiles` ; `hx-boost` sur les 3 formulaires longs (message / story suivante / valider) : envoi AJAX + remplacement de page **sans écran blanc**, **zéro route fragment** (le rendu serveur reste unique) ; **indicateur « ⏳ Génération en cours… »** par formulaire + **boutons désactivés pendant l'appel** (anti double-envoi — le défaut qui guettait sur les générations de 7-30 s) ; sans JavaScript, les POST classiques restent intacts (progressive enhancement). 2 TU — **239 tests verts**. Plan `docs/plans-test/s3.8-htmx.md` (test central : indicateur + boutons désactivés pendant une vraie génération, repli JS désactivé).

**Fin du lot pré-pilote — S3.11 → S3.13 enchaînées sur une PR unique** (« go mais enchaîne les story stp » : le référent a demandé le stacking, une story = un commit) :
- **S3.11 tokens** (`45d1aee`) : migration 0011 — registre unique `conso_tokens` (chat rattaché à la session, embeddings par lot), endpoints `GET /workflows/{id}/conso` + `GET /telemetrie/tokens` (jauge du jour vs tpd 2,46 M, `ALBERT_TPD_QUOTA`), conso affichée sur session + panneau Télémétrie avec jauge ;
- **S3.12 modèle UI** (`99c0c9e`) : migration 0012 (table `parametres`), surcharge lue à CHAQUE appel (UI > env > défaut code, **sans relance**), écran Paramètres (select + alias libre + retour défaut), modèle actif affiché sur session ;
- **S3.10 corpus UI** (`0711bca`) : migration 0013 (`ingestion_runs`), orchestrateur `sia_ingestion/pipeline.py` (scan→embed, code 2 = arrêt, code 1 = `echec_partiel` et poursuite — D9), upload multipart sécurisé, `POST /ingestion/lancer` en sous-processus détaché (un seul run à la fois, log par run, déblocage manuel), écran Mes documents : dépôt + « Indexer maintenant » + **suivi nœud par nœud auto-rafraîchi**. ⚠️ Limite documentée : déploiement par images → E7 (pilote = pod, arbitré) ;
- **S3.9 traçabilité A3 complète** (`d1e8db0`) : migration 0014 (`message_traces`), `SourceCitee.extrait` = contenu exact du chunk, traces persistées par message (sous-requête max(id) — zéro churn), le fil restitue sources/extraits/avertissements/divergences au rechargement — **fin de la « v1 assumée » S2.8** ;
- **S3.13 confort PO** : migration 0015 (`story_editions` + titre/archivee), **édition des stories** (promesse E4 enfin livrée — la version éditée GAGNE à l'export), renommer/archiver les sessions (masque, ne détruit jamais), copier une story. Reste mineur : compteur télémétrique des stories éditées.

**Le lot est validé « fonctionnel » sur pod par le référent** (branche PR #34 testée au navigateur). Demande dans la foulée → **S3.14 fiche document** : l'inventaire « Mes documents » pointe vers `GET /documents/{id}` — identité (taille, sha256, version, doublon de, projet suggéré), **traitement** (statut, erreur parsing/OCR, **dérivé markdown docling rendu** — aperçu 8 k lu du disque, absence signalée sans échec — piège d'ordre de routes : `stats` enregistrée avant `{document_id}`), **chunks** (fil de titres, tokens, contenu exact, ✅/⏳ embedding, compteurs). 5 TU — **279 tests verts**. Plan `docs/plans-test/s3.14-fiche-document.md`.

**Mini-récap** :
- ✅ Fait : **LE LOT PRÉ-PILOTE EST COMPLET ET VALIDÉ FONCTIONNEL SUR POD** — S3.6/S3.7 mergées (PRs #31/#32), S3.8→S3.13 + **S3.14 fiche document** sur la PR #34 ; migrations 0011→0015 ; **279 tests verts** (239 → 279)
- ⏳ Référent : revue/merge PR #34 ; `git pull` sur le pod pour S3.14 (aucune migration)
- ⏳ Ensuite : dépendances externes §7 (snapshot corpus → S3.1/S3.3, gold → S3.4, panel → S3.5) — le code n'attend plus qu'elles

---

## Session 06/07/2026 (27) — S2.13 : rapprochement A8 (« levée proposée ») + S2.14 : bascule chat `openweight-medium`

**Contexte** : « nouvelle session. analyse la doc et prépare le plan de travail » — session remote, branche `claude/doc-analysis-work-plan-t8fbem`. Analyse : **PR #29 constatée MERGÉE** (`6362190`) — l'en-tête stratégique était en retard, recalé dans cette session. Plan de travail proposé en 3 voies (bascule medium / adhérence format large / rapprochement A8) ; **direction validée par le référent : rapprochement A8** — le principal frottement UX constaté en session réelle 8 (une réponse d'interview tranche une hypothèse, mais elle reste « en_attente » jusqu'au clic).

**Travail livré** (commit `8b35dec`) :
- **Migration 0010** : `workflow_hypotheses` + `statut_propose` (CHECK confirmee/rejetee), `justification_proposee`, `proposee_le` — le `statut` (porteur de l'invariant A8) n'est pas concerné.
- `sia_api/workflow.py` : `extraire_levees_proposees` (pure) — parse `[LEVÉE PROPOSÉE : #id — confirmée|rejetée — justification]`, filtre sur le registre réellement en attente (id halluciné ou déjà décidé ignoré), dédup (la première proposition gagne).
- `sia_api/moteur.py` : le registre est lu **avant** l'appel (il sert aussi à la dédup existante — une requête au lieu de deux) ; les hypothèses en attente entrent au prompt système, numérotées, avec la consigne de **proposer** — « seul le PO confirme ou rejette » ; propositions persistées sur les colonnes dédiées (`UPDATE ... WHERE statut = 'en_attente'`, **jamais `SET statut`**) ; `levees_proposees` restituées dans la réponse.
- `sia_api/workflows.py` : `Hypothese` expose `statut_propose`/`justification_proposee` — l'écran retrouve la proposition au rechargement.
- Web : badge « Levée proposée : Confirmer/Rejeter » + justification + rappel « c'est vous qui décidez (A8) » à côté des boutons ; compteur dans le panneau du dernier échange.
- **8 TU** (3 extraction pure, 1 prompt, 2 route — dont l'invariant « aucun `SET statut =` » —, 1 exposition, 1 écran) — **220 tests au total** (212 → 220). NB : les tuples scriptés des TU existantes ont été étendus mécaniquement (registre 1→3 colonnes, hypothèses 4→6) — **aucune assertion existante modifiée**.
- Docs : S2.13 au backlog sprint 2 ; plan `docs/plans-test/s2.13-rapprochement-a8.md` (contre-épreuve A8 en SQL = le cœur du test).

**Validation en session** : lint vert, **220 tests verts** (TNR complet). Validation stack-live à jouer post-merge (plan s2.13 — exige clé + base, migration 0010). PR #30 (draft) ouverte, helm-chart vert à l'ouverture, suivi CI actif.

**Suite de session — S2.14** (« go pour la suite » du référent = arbitrage modèle chat rendu, commit `f35b538`) : **bascule du défaut `ALBERT_MODEL_CHAT` vers `openweight-medium`, à l'essai** — verdict E6 v0 (0,806 vs 0,498, dérive de format de large corroborée en session réelle 8, `docs/eval-onyxia.md`). Défaut basculé sur les 5 surfaces où il vit (`config.py`, `.env.example`, compose, Secret k8s d'exemple, README) — le moteur lit toujours `settings.albert_model_chat`, rien en dur ; **réversibilité prouvée par TU** (la surcharge env ramène large sans changement de code) ; le banc `make eval` compare toujours large vs medium — décision définitive au recalibrage gold. Les 3 TU du défaut recalées (objet même de la story, validée par le go) + TU de surcharge réorientée vers le chemin de retour. Lint vert, **220 tests verts**. Plan `docs/plans-test/s2.14-modele-chat-medium.md` (probe, génération réelle, contre-épreuve de réversibilité). ⚠️ Rappel pod : un `ALBERT_MODEL_CHAT` exporté dans l'environnement prime sur le défaut.

**Analyse de la session réelle 9 (pod, branche PR #30 confirmée par le référent) + correctifs (`4ce5bd4`, 223 tests verts)** : session complète au navigateur (Feature « prioriser les actes > seuils commande publique », 10 US + DoR, exports, notation). **Validations** : adhérence gabarit très bonne — l'essai medium (S2.14) tient en réel ; le contrôle S2.12 a attrapé un vrai défaut (CA10 incomplet) ; A3/A8/dédup conformes. **4 défauts corrigés dans la foulée** : (1) story « Filtrer… » **perdue en silence** (titre `### US — **Titre**` non extrait → absente du feedback ET des exports) → extraction tolérante `titre_us`, story extraite puis signalée non conforme ; (2) le cycle réel « une story = rédaction + DoR » file la machine à états à `synthese` pendant que les DoR arrivent → **tableau DoR contrôlé à toute étape de production** (absence signalée seulement à l'étape 4) ; (3) faux positif « sans aucun attendu listé » sur les listes numérotées → tolérées ; (4) **premier cas réel de levée proposée (S2.13) raté** (« Je confirme que l'équipe doit créer le jeu de données » → aucun marqueur émis) → consigne déplacée en dernière position du prompt + exemple explicite, contre-épreuve au plan s2.13 §3 bis. **Au backlog (constats non couverts)** : anti-invention incomplet (le modèle marque à SON format `[HYPOTHÈSE 1 A]` et affirme des valeurs inventées sans marqueur — story dédiée à cadrer) ; sémantique du « Oui » utilisée comme « story suivante » → badge étape trompeur (A5), arbitrage produit à rendre.

**Rejeu sur pod — sessions 10 et 11 (soir)** : la session 10 a d'abord révélé (photo terminal) que **le `git pull` avait avorté** (copie locale non suivie `docs/eval-onyxia.md`) — 212 tests collectés, pas de migration 0010 : **les sessions 9 ET 10 avaient tourné sur l'ancien code**, le « premier cas réel raté » de S2.13 n'était pas un échec du modèle mais un code jamais déployé (le renforcement de consigne reste utile). Après déblocage (mv du fichier local, checkout/pull, 223 verts, `0009 -> 0010`), **la session 11 valide S2.13 stack-live** : `[LEVÉE PROPOSÉE : #104 — confirmée — taille maximale validée par la MOA]` et `[LEVÉE PROPOSÉE : #105 — rejetée — notification par SMS remplacée par courriel]` émis par le moteur, badges + justifications affichés, hypothèses toujours `en_attente` (A8 intact), persistance au rechargement démontrée sur une longue session. CA S2.13 cochés. **Deux défauts découverts en session 11 et corrigés** (**225 tests**) : (1) le modèle répète `**US — Titre**` en rappel au-dessus de chaque tableau DoR → ce segment sans blocs était extrait comme story et **écrasait la vraie story dans les exports** (dédup par titre, dernière version gagne) → un segment n'est une story que s'il porte aussi `**En tant que**` ; (2) un titre de section citant le marqueur (« ### 🔎 Hypothèses encore en attente… ») entrait au registre → entêtes markdown écartées. Constat aggravé au backlog : registre à 18 en attente par reformulations (récapitulatifs re-listant les hypothèses sous d'autres mots) — pour la story anti-invention.

**S2.15 livrée (« go pour la suite » n°2) — anti-invention v2** : (1) **dédup sémantique du registre** — `est_doublon_hypothese` (recouvrement des termes porteurs de sens de la formulation courte ≥ 0,8, seuil calibré sur les paires réelles de la session 11), branchée en second étage de l'insertion moteur ; garde-fou A8 vérifié par TU : une hypothèse réellement distincte n'est jamais avalée ; (2) **consignes de traçabilité durcies** au prompt : marqueur EXACT (variantes perdues sinon), valeurs chiffrées inventées marquées sur leur ligne, alternatives A/B/C non marquées (seule l'option retenue), pas de re-liste des hypothèses déjà au registre. 6 TU nouveaux — **229 tests verts**. Plan `docs/plans-test/s2.15-anti-invention.md` (rejeu du récapitulatif session 11, compteur avant/après, contre-épreuve de non-perte).

**Cadrage de la suite (fin de session)** : analyse de l'ensemble des backlogs → **le code ne bloque plus rien** ; le chemin critique vers le pilote (D17/§6) passe par les dépendances externes du §7. Squelette **`docs/sprint-3-backlog.md`** versionné (à amender par le référent) : S3.0 préalables débloquants (merge PR #30, snapshot corpus, gold, panel, registre d'images, 3 arbitrages), S3.1 lecture S3/MinIO (dernier trou de code du DAG E1 — gated snapshot), S3.2 sémantique du « Oui » (gated arbitrage), S3.3 ingestion corpus réel + recalibrages (dont 2e test no-go §6 : débit embeddings sous quotas), S3.4 recalibrage E6 sur gold + verdict modèle définitif, S3.5 préparation pilote (Helm lab, charte d'usage, embarquement).

**Les 3 arbitrages du cadrage sont rendus par le référent** : (a) « Oui » → **bouton « Story suivante »** ; (b) **PG 18.3 CNPG assumé** pour le pilote (alignement 16 = décision prod/E7) ; (c) **pilote sur pod** `make pod-up` (fragilité assumée — le déploiement Helm lab et le registre d'images glissent vers E7 et sortent du chemin critique). **S3.2 livrée dans la foulée** : route web `POST /sessions/{id}/story-suivante` (message dédié au moteur, aucun appel `/avancer` — badge A5 fidèle, invariants règle 5/A8 intacts), panneau « Story suivante » aux étapes de production + rappel sur « Valider l'étape », consigne moteur « UNE SEULE story à la fois » (anti-troncature session 8, candidates restantes annoncées). 3 TU — **232 tests verts**. Plan `docs/plans-test/s3.2-story-suivante.md` (le test A5 : badge stable au fil des stories).

**Lot pré-pilote cadré avec le référent (fin de session)** : « améliorer le MVP avant de le présenter aux PO ». Analyse des manques du point de vue PO — aux 4 points du référent (UI statique/navigation, upload+pipeline absents de l'UI, modèle non changeable, aucune conso de tokens) s'ajoutent : **markdown brut à l'écran** (tableaux Gherkin illisibles — le choc visuel n°1), **A3 incomplet** (extrait exact non consultable, sources/avertissements perdus au rechargement — v1 assumée S2.8), **édition des stories jamais livrée** (promise par la cible E4), pas de gestion des sessions (renommer/archiver), pas de copie par story. **8 stories cadrées (S3.6→S3.13)** au backlog sprint 3 avec 4 arbitrages rendus : htmx léger (progressive enhancement, vendoré) ; upload → bouton « Indexer » manuel (maîtrise tpd) ; modèle = réglage global instance (écran Paramètres, précédence documentée) ; édition simple incluse (la version éditée gagne à l'export). Ordre : S3.6→S3.8 (première impression) → S3.11+S3.12 → S3.10 → S3.9/S3.13.

**Mini-récap** :
- ✅ Fait : analyse doc + plan de travail ; S2.13 livrée **et validée stack-live** ; S2.14 livrée (corroborée) ; correctifs sessions 9+11 ; S2.15 anti-invention v2 ; sprint 3 cadré (3 arbitrages) + S3.2 livrée ; **lot pré-pilote S3.6→S3.13 cadré (4 arbitrages)** ; TNR 232 verts ; PR #30 draft
- ⏳ Référent : revue/merge PR #30 ; S3.0 externes (snapshot corpus, gold, panel, protection de branche) ; plans s2.15 + s3.2 sur pod
- ⏳ Backlog code : **lot pré-pilote S3.6→S3.13 (prêt à démarrer, ordre validé)** ; puis gated externes : S3.1 lecture S3/MinIO, S3.3/S3.4 recalibrages, S3.5 embarquement pilote

---

## Session 03/07/2026 (26) — LA session Onyxia : déroulé réel du runbook s0 (phases 0→2 validées, phase 3 en cours)

**Contexte** : accompagnement pas-à-pas du référent sur le pod (`vscode-python-gpu`, écart : GPU inutile — préférer un pod CPU), branche `claude/new-session-v6ftye` (PR #29 draft, collecte les correctifs au fil du déroulé). **Entrée à compléter à la clôture** (fin de phase 3, banc E6, CA cochés).

**Phase 0 — validée** : TNR à froid **203 verts** sur pod ; service PostgreSQL du catalogue lancé — chart CNPG, **PostgreSQL 18.3 + pgvector actif** (⚠️ écart stack cible PG 16 : le 1er lancement sans `extension.pgvector: true` ne donnait pas l'extension, le tag 16 n'a pas été appliqué par le chart — à trancher pour la prod) ; migrations **0001→0009 sans erreur** ; `make probe` **4/4 ok**, quotas identiques au relevé S1.5 (tpm 128k, tpd 2,46 M).

**Phase 1 — validée** : scan **6 fichiers** (le runbook disait 7 — corrigé) ; **libGL absente de l'image pod** → `ImportError: libGL.so.1` sur PDF natif, réglé par `libgl1`+`libglib2.0-0` (prérequis documenté) ; parse `1 parsé, 3 inchangés (reprise D9), 1 ocr_requis, 0 échec` après fix ; qualify : `v2_final_VF3` référence, copie byte-identique doublon ; chunk 4/4, embed 4/4 **dimension 1024**, **2e run = 0 re-vectorisé (contre-épreuve D9 ✅)** ; recoupes SQL conformes.

**Phase 2 — validée, deux découvertes produit** :
1. **Schéma `/v1/rerank` réel ≠ hypothèse s2.4** (422 constaté) : `{model, query, documents}` → `results[{index, relevance_score}]` (relevé : 0,73 vs 1,6e-05). Le repli RRF signalé avait fonctionné comme conçu. Corrigé (`d19d326`) ; validé stack-live : `rerank_applique: true`.
2. **Trou anti-invention** : sans seuil de distance, le volet vectoriel « répond » à tout (quotas de pêche en Baltique → spec d'authentification). Distances mesurées en réel (bge-m3, fixtures) : pertinent ≤ 0,431, hors corpus ≥ 0,698 → **`RECHERCHE_SEUIL_DISTANCE` = 0,55** (configurable, à recalibrer sur corpus réel). Validé stack-live : Baltique → « Aucune source récupérable », question légitime → guide en tête (pas de sur-filtrage).

**Phase 3 — validée (06/07)** ; découvertes d'environnement, produit, et correctifs :
- Port 8081 **non exposable** (RBAC du SA pod : pas de création Service/Ingress) → UI via le proxy code-server `/proxy/8081/`.
- **Liens à chemins absolus cassés sous préfixe** → `{{ racine }}` = root_path sur les 15 liens/actions (`6d13b57`), audit exhaustif 15 routes sans fuite ; **code-server réécrit les `Location`** (doublement prouvé en navigation privée) → redirections **sans** préfixe, asymétrie documentée (`b4aa9d4`).
- **Chutes de pod à répétition** (seul `~/work` survit) → **`make pod-up`** : remise en route en une commande (libGL, env, api+web nohup, healthchecks) (`93a257d`, `4f9acd2`) ; secrets dans `~/work/.sia-db.env`.
- **Accueil sans liste des sessions** (session perdue de vue = URL à deviner) → `GET /workflows` + panneau « Sessions en cours » (`e491cb3`).
- **Premières générations réelles (sessions 7 et 8) : le moteur E3 complet tourne** — interview par lots ≤ 3, sources citées (A3), question documentaire libre sourcée dans le fil (A2 ✅), registre A8 avec décision individuelle, workflow 0→5 mené à terme, RAG mobilisé jusqu'à puiser la valeur cible de perf dans la spec v2. Trois défauts découverts et corrigés :
  1. **« Valider l'étape » sans interaction LLM** (état filait à « synthèse », fil désynchronisé, validation en double) → la règle 5 boucle : Oui/Non transmis au moteur qui produit l'étape suivante ou l'itération (`ea251fb`) — validé session 8, état et fil synchrones ;
  2. **Faux positifs du contrôle gabarit** sur la typographie réelle d'Albert (tirets insécables U+2011, apostrophes U+2019, blocs en listes) → canonicalisation + tolérance (`ea251fb`) ;
  3. **Registre des hypothèses bruyant** (~84 entrées pour ~15 réelles : reformulations décorées, phrases de consigne, double canal de validation) → dédup par clé normalisée + filtre des consignes + consigne moteur « pas de demande de validation inline » (`d32c34c`).
- Exports E5 (récap A8, en-tête `X-Hypotheses-Non-Levees`), feedback E4.4, télémétrie, robustesse (« API injoignable » sans traceback) : **validés** (« tout fonctionne », référent).
- Observations au backlog : lever une hypothèse quand la réponse d'interview la tranche (rapprochement décision↔registre, post-MVP) ; dérive de format d'`openweight-large` (stories `US 9 –` hors gabarit → extraction stories/feedback/export perdue en aval — le contrôle S1.10 la signale) ; réponse tronquée à `MAX_TOKENS_REPONSE` si « rédige toutes les storys » (préférer story par story, règle du gabarit).

**Phase 4 — banc E6 réel exécuté (06/07)** : `make eval` complet (3 cas silver × 2 modèles, ~7 k tokens, 0 échec) — **`openweight-medium` 0,806 > `openweight-large` 0,498**. Cause lisible : dérive de format de large (gabarit 0,0–0,6 contre 0,8–1,0 ; ~1 150 tokens contre ~500), **corroborée indépendamment en session réelle 8**. Garde-fous : silver non validé, proxys v0, banc one-shot ≠ workflow conversationnel. Rapport versionné : `docs/eval-onyxia.md`. **Décision référent en attente : `ALBERT_MODEL_CHAT=openweight-medium` à l'essai, ou statu quo jusqu'au recalibrage gold.**

**Livré (PR #29, draft — prête pour revue référent)** : 8 correctifs/évolutions validés stack-live (`d19d326` rerank+seuil, `6d13b57` root_path, `93a257d`/`4f9acd2` pod-up, `b4aa9d4` Location, `e491cb3` liste sessions, `ea251fb` règle 5 + typo gabarit, `d32c34c` registre) + runbook/plans/README recalés + rapport E6 — **212 tests verts** (203 → 212). CA cochés dans les backlogs sprint 1 et 2 (restent : protection de branche, déploiement Helm lab, relance-idempotence du scan, gold).

**Validation stack-live** : chaque phase du runbook s0 a son résultat observable cité ci-dessus — chaîne complète corpus → recherche citée → génération citée → exports démontrée au navigateur sur base réelle.

**Mini-récap** :
- ✅ Fait : **runbook s0 joué de bout en bout (phases 0→4)** — le MVP a tourné en réel de l'ingestion à l'export ; 8 correctifs issus du réel, tous validés stack-live ; verdict E6 v0 rendu
- ⏳ Référent : revue + merge PR #29 ; arbitrage modèle chat (medium vs large) ; protection de branche `main` ; réserve compose S1.2 ; déploiement Helm lab ; prérequis §7 (gold, corpus réel, panel PO)
- ⏳ Backlog : rapprochement décision d'interview ↔ registre A8 ; adhérence format de large (prompt ou bascule modèle) ; relance-idempotence scan (plan s1.7 étape 4)

---

## Session 03/07/2026 (25) — clôture : runbook Onyxia en version exécutable (docs, aucun code)

**Contexte** : « documente le plan de test à jouer sur onyxia puis clôture session » — dernière action de la séquence, le backlog macro étant code-complet (203 tests, PRs #1–#27 mergées).

**Travail livré** : `docs/plans-test/s0-parcours-onyxia.md` réécrit en **document exécutable** — toutes les commandes à copier-coller dans l'ordre avec le résultat attendu à chaque étape :
- Phase 0 : prérequis (pod CPU, **rotation de clé à confirmer**, service PostgreSQL du catalogue, `export DATABASE_URL="postgresql+psycopg://…"` — schéma unique qui marche pour alembic ET psycopg, vérifié dans le code), TNR à froid (203 attendus), migrations 0001→0009, re-probe si clé tournée ;
- Phase 1 : chaîne d'ingestion complète sur fixtures (+ reprise D9 en contre-épreuve, recoupes SQL) ;
- Phase 2 : **étape 0 impérative = curl du schéma `/v1/rerank`** (hypothèse documentée), lancement api, recherche/contexte cités, cas « aucune source » ;
- Phase 3 : parcours navigateur de bout en bout (projets/A6, documents/A5, première génération réelle, A8, contrôle DoR + contre-épreuve 🔵, exports, feedback/télémétrie, robustesse) ;
- Phase 4 : banc E6 (réduit puis complet, quota tpd surveillé) ; Phase 5 : actions hors pod.
Analyse/documentation, aucun code livré.

**Mini-récap** :
- ✅ Fait : runbook exécutable livré — la session Onyxia se déroule en copier-coller
- ⏳ À venir (référent) : jouer les phases 0→4, consigner chaque résultat dans SESSIONS.md, cocher les CA

---

## Session 03/07/2026 (24) — runbook maître de la session Onyxia (docs, aucun code)

**Contexte** : clôture de la séquence « continue jusqu'à épuisement » — le backlog macro côté code est complet ; dernière livraison utile avant la session de validation du référent.

**Travail livré** : `docs/plans-test/s0-parcours-onyxia.md` — runbook maître : prérequis (pod CPU, rotation de clé à confirmer, service PostgreSQL du catalogue, `.env`, TNR à froid 203 tests, migrations 0001→0009), enchaînement ordonné des 18 plans (ingestion → RAG avec vérif curl du schéma rerank en étape 0 → produit de bout en bout → banc E6 sous quota), actions hors pod (protection de branche, compose S1.2, déploiement lab, prérequis §7). Analyse/documentation, aucun code livré.

**Mini-récap** :
- ✅ Fait : runbook maître — la session Onyxia de demain a son fil conducteur
- ⏳ À venir (référent) : dérouler `s0-parcours-onyxia.md`, consigner chaque résultat dans SESSIONS.md, cocher les CA

---

## Session 03/07/2026 (23) — S2.12 : contrôle DoR/gabarit automatisé (E3 complet)

**Contexte** : « continue » — dernière brique code du backlog macro. PR #25 (S2.11) mergée en début de séquence.

**Travail livré** :
- `controler_conformite` (moteur, fonction pure) : en sortie des étapes de production (rédaction, contrôle DoR, synthèse), **chaque US extraite de la réponse passe par `valider_us` (S1.10)** — non-conformité signalée avec le titre de l'US ; à l'étape 4, **le tableau DoR passe par `valider_dor`** (10 critères, statuts, justifications, « estimée en refinement » toujours 🔵).
- Piège évité : un message d'étape 4 contient aussi des tableaux de CA — `_extraire_tableau_dor` isole le tableau DoR avant validation (sinon faux positif systématique sur l'en-tête).
- Branché sur `POST /workflows/{id}/message` via le canal avertissements existant : **l'UI S2.8 l'affiche sans modification** ; le contrôle signale, ne bloque jamais (règle 5 — le PO arbitre) ; aucun contrôle aux étapes 0–2.
- 6 TU (purs + route, silver rejouée = silence) — **203 tests au total**. Plan `docs/plans-test/s2.12-controle-dor-auto.md` (fumée sans réseau, session réelle étapes 3–4, contre-épreuve 🔵, non-blocage).

**Validation en session** : lint vert, **203 tests verts**. Validation stack-live dans la foulée du plan S2.6 (même session réelle).

**Mini-récap** :
- ✅ Fait : S2.12 livrée — **le backlog macro côté code est complet (E0→E6 + E8)** ; E7 = post-go
- ⏳ À venir (référent) : session Onyxia TU/TNR complète (migrations 0001→0009, plans S1.7 → S2.12), banc E6 réel, rotation de clé à confirmer, stories gold, corpus réel

---

## Session 02/07/2026 (22) — S2.11 : E6, harnais d'évals `make eval` (grille 3 axes)

**Contexte** : « continue » — E6, l'avant-dernière brique du backlog macro côté code. PR #24 (S2.10) mergée en début de séquence.

**Travail livré** :
- `sia_api/evaluation.py` + cible `make eval` (`MODELES=`, `SORTIE=`, `--max-cas`) : benchmark de génération sur les stories de référence — **gold prioritaire, repli silver affiché « non validé »** dans le rapport (même logique que le few-shot S2.6).
- Chaque cas : **brief reconstitué depuis la référence** (récit, pré-requis, règles métier, attendus — jamais les CA ni l'accessibilité, qui sont la sortie attendue) → génération par modèle → scoring automatique.
- **Grille 3 axes** (documentée `evals/grille-notation.md`, proxys v0 assumés, revue manuelle PO = référence) : gabarit = `valider_us` S1.10 (−0,2/violation) ; exactitude = règles métier retrouvées (recouvrement lexical ≥ 60 %) + **anti-invention** (nombre ≥ 2 chiffres absent du brief et non marqué [HYPOTHÈSE À VALIDER] pénalisé, « 200 » exempté — zoom RGAA) ; complétude = blocs remplis + ratio de CA vs référence.
- Robustesse : un modèle en échec ou une réponse vide (gotcha S1.5) n'arrête pas le banc — erreur portée au rapport ; relevés latence/tokens par appel (préparation du test de débit sous tpd 2,46 M) ; comparatif par défaut `openweight-large` vs `openweight-medium` (Mistral Medium ALLiaNCE via `MODELES=`).
- Auto-contrôle du proxy : la référence rejouée score 1.0 sur les trois axes (TU).
- README à jour (cibles make complètes). 17 TU (client injecté, zéro réseau) — **197 tests au total**. Plan `docs/plans-test/s2.11-harnais-evals.md` (fumée sans réseau, banc réduit, banc complet + rapport, robustesse, bascule gold).

**Validation en session** : lint vert, **197 tests verts**. L'exécution réelle du banc (verdict comparatif E6) exige la clé → plan pod (~6 générations, ~30 k tokens).

**Mini-récap** :
- ✅ Fait : E6 livrée — `make eval` opérationnel, grille documentée, recalibrage gold automatique
- ⏳ À venir : DoR automatisé en sortie d'étape 4 (dernière brique code du backlog macro) ; côté référent : session Onyxia TU/TNR (plans S1.7 → S2.11)

---

## Session 02/07/2026 (21) — S2.10 : E4.4, feedback par story + télémétrie d'usage

**Contexte** : « continue » — dernière brique d'E4. PR #23 (S2.9) mergée en début de séquence, branche recalée sur main.

**Travail livré** :
- Migration **0009** : `story_feedbacks` (note 1–5 CHECK + commentaire par story) et `workflow_validations` (journal des Oui/Non d'étape).
- `sia_api/feedback.py` : `POST /workflows/{id}/feedback` (404 session inconnue, 422 note hors bornes), `GET /workflows/{id}/stories` (titres des US produites — liste vide sans 409 : l'écran masque le panneau), `GET /telemetrie`.
- **Télémétrie en proxys v0 assumés** (sans comptes A7 ni Jira D10, affichés comme tels à l'écran) : actifs hebdo → sessions créées/semaine ; % stories conservées → part des notes ≥ 4 ; taux d'édition → part des validations « Non » (règle 5). Aucune division par zéro sur base vide (None → « — »).
- `/avancer` journalise désormais chaque validation (TU dédiée ; les TU existantes inchangées restent vertes — l'INSERT ne consomme pas de résultat scripté).
- Web : panneau « Noter les stories » sur l'écran session (formulaire par story, select 1–5 + commentaire), écran « Télémétrie », navigation mise à jour.
- 8 TU api + 1 TU journalisation + 5 TU web — **180 tests au total**. Plan `docs/plans-test/s2.10-feedback-telemetrie.md` (migration 0009, recoupes SQL, cas limites curl, base vide).

**Validation en session** : lint vert, **180 tests verts**. Validation stack-live à jouer post-merge (plan s2.10 — exige une session S2.6 réelle ayant produit des US).

**Mini-récap** :
- ✅ Fait : E4.4 livrée — **E4 complet** ; toute la cible produit MVP (E1→E5, E8) est code-complète
- ⏳ À venir : E6 (harnais d'évals `make eval`, grille 3 axes), DoR automatisé en sortie d'étape 4 ; côté référent : session Onyxia TU/TNR (plans S1.7 → S2.10, migrations 0001→0009)

---

## Session 02/07/2026 (20) — S2.9 : E4.2 + E4.3, écrans projet et « mes documents »

**Contexte** : « continue » — suite d'E4 : les deux écrans qui rendent le PO autonome (A6) et lisible l'état du corpus (A5).

**Travail livré** :
- `sia_api/documents.py` : 2 endpoints lecture seule sur la table `documents` (S1.7–S1.9) — `GET /documents` (inventaire : statut de parsing, référence, doublon, projet suggéré) et `GET /documents/stats` (**couverture = parsés/parsables, 1.0 si rien à parser** — pas de division par zéro).
- Écran **projets** (E4.2) : liste + création (nom, contexte, jusqu'à 3 NFR typées parmi les 7 types E8 — une ligne sans formulation est ignorée), 409 « déjà existant » affiché sur le formulaire ; détail avec tableau NFR.
- **Association des dossiers (A6)** sur le détail projet : cases à cocher = **union suggestions S1.9 (avec nombre de documents) + dossiers déjà associés** (un ajout manuel hors suggestions reste visible et décochable), champ « dossier libre », rappel à l'écran « elles ne valent pas association ». L'enregistrement passe par un `PUT /projects/{id}` complet : nom/contexte/NFR **préservés**, origines existantes conservées, nouvelle suggestion cochée → `suggestion`, saisie manuelle → `po`.
- Écran **« mes documents »** (E4.3, A5) : état du corpus (total, parsables, indexés, échecs, OCR requis, références), inventaire avec statuts libellés, **alerte `fr-alert--warning` si couverture < 0,8** (le volet conversationnel d'A5 est déjà porté par l'avertissement « aucune source » du moteur S2.6). Navigation commune Sessions / Projets / Mes documents dans `base.html`.
- 3 TU api + 7 TU web — **166 tests au total**. Plan `docs/plans-test/s2.9-ecrans-projet-documents.md` (recoupe l'origine suggestion/po en base, force les deux cas de l'alerte).

**Validation en session** : lint vert, **166 tests verts**. Validation stack-live à jouer post-merge (plan s2.9, exige base peuplée S1.7 → S1.9).

**Mini-récap** :
- ✅ Fait : E4.2 + E4.3 livrées — E4 est complet hors feedback/télémétrie
- ⏳ À venir : E4.4 (note 1–5 + commentaire, télémétrie — migration 0009), E6 (harnais d'évals), DoR auto étape 4

---

## Session 02/07/2026 (19) — S2.8 : E4.1, l'écran de conversation du workflow

**Contexte** : « continue » — première pièce d'E4, l'interface PO.

**Travail livré** :
- `sia_web/api_client.py` : client serveur→api (`SIA_API_URL`, timeout 120 s pour les générations, api injoignable = statut 599 avec détail lisible — jamais de traceback à l'écran).
- Routes web + gabarits Jinja (**aucun JavaScript requis** — formulaires HTML classiques ; DSFR par CDN avec styles de repli locaux, à vendorer en E7) : **accueil** (liste projets + création de session avec sélection du projet — A6), **écran session** (badge étape courante — A5, fil de conversation, envoi de message dont **question documentaire libre — A2**, panneau **sources mobilisées** A3, divergences A9 en alerte, avertissements, **hypothèses avec décision individuelle Confirmer/Rejeter et rappel A8 à l'écran**, validation d'étape Oui/Non — règle 5, liens exports E5 proxifiés), page erreur.
- Endpoint api ajouté : `GET /workflows/{id}/messages` (le fil, +1 TU api).
- v1 assumée et documentée : sources/avertissements du dernier échange affichés dans la réponse du POST (non persistés côté UI) — au rechargement, seul le fil demeure.
- 9 TU web (api simulée par monkeypatch — mêmes principes que le reste) — **156 tests au total**.
- **Démo réelle en session** : web + api réels chaînés sans base → accueil rendu (bandeau D15, formulaire) avec le détail 503 de l'api affiché proprement ; /health web 200.
- Plan `docs/plans-test/s2.8-ui-conversation.md` (parcours navigateur complet via le proxy Onyxia). Restent pour E4 : écran projet (E4.2), « mes documents » + alerte couverture (E4.3/A5), note 1–5 + télémétrie (E4.4).

**Validation en session** : lint vert, **156 tests verts**, démo réelle web→api.

**Mini-récap** :
- ✅ Fait : E4.1 livrée — le MVP est utilisable au navigateur de bout en bout (dès la base et la clé en place)
- ⏳ À venir : E4.2/E4.3/E4.4 (écrans projet, documents, feedback/télémétrie), E6 (harnais d'évals), DoR auto étape 4

---

## Session 02/07/2026 (18) — S2.7 : E5, export CSV Jira + copier-coller formaté (A8)

**Contexte** : « continue » — E5, petite story qui ferme la boucle produit : de la Feature collée à l'export importable.

**Travail livré** :
- `sia_api/export.py` : extraction des US des messages assistant (étapes rédaction/contrôle DoR/synthèse — le format prompt 3 encadre chaque US de `---`), **dédup par titre, la dernière version gagne** (itérations règle 5).
- `GET /workflows/{id}/export/jira.csv` : CSV importable (Summary / Issue Type=Story / Description = markdown intégral, QUOTE_ALL, CRLF) — pas d'appel API Jira (D10). L'en-tête `X-Hypotheses-Non-Levees` porte le compteur A8.
- `GET /workflows/{id}/export/markdown` : copier-coller formaté — **avertissement + récapitulatif des hypothèses non levées EN TÊTE** (arbitrage A8 : export autorisé, jamais silencieux) + **annotation de conformité S1.10 par story** (`valider_us`).
- Garde-fous : session inconnue 404, aucune story rédigée 409 explicite.
- 8 TU — **146 tests au total**. Plan `docs/plans-test/s2.7-export.md` (dont pas-à-pas d'import Jira réel, hors dev).

**Validation en session** : lint vert, 146 tests verts.

**Mini-récap** :
- ✅ Fait : E5 livrée — la chaîne produit est complète : Feature → conversation sourcée → stories → export CSV/markdown avec récap A8
- ⏳ À venir : E4 (UI conversationnelle DSFR — la dernière grosse pièce du MVP), E6 (harnais d'évals) ; côté référent : session Onyxia TU/TNR (plans S1.7 → S2.7)

---

## Session 02/07/2026 (17) — S2.6 : E3.2, le moteur conversationnel (Albert + RAG à chaque étape)

**Contexte** : « continue » — la pièce qui assemble tout ce qui a été construit.

**Travail livré** :
- `sia_api/moteur.py` + `POST /workflows/{id}/message` : à chaque message du PO (réponse d'interview, correction, validation OU **question documentaire libre — A2 : même moteur, pas d'écran dédié**) —
  1. RAG mobilisé via `construire_contexte` (S2.4) avec le périmètre projet ;
  2. prompt système assemblé et TESTÉ : **prompt 3 intégral** (source unique S1.10) + étape courante (les transitions restent à l'application — règle 5) + **contexte/NFR projet injectés** (E8, avec consigne bloc G) + extraits cités + consignes A3 (citation/[HYPOTHÈSE À VALIDER]) et **A9** (`[DIVERGENCE]` avec source, arbitrée par le PO) + **few-shot silver en repli explicitement « NON VALIDÉE »** (gold prioritaire dès fourniture — CLAUDE.md) ;
  3. appel Albert `openweight-large`, `max_tokens=4096` (gotcha raisonnement S1.5), **réponse vide = 502 explicite** avec finish_reason ;
  4. fil persisté (message PO + réponse), **hypothèses du modèle auto-extraites vers le registre** (origine `modele`, dédup textuelle v0, A8 intact) ;
  5. restitution : sources mobilisées (panneau A3), hypothèses ajoutées, divergences A9, avertissements (règle 1 à l'interview, budget ~20k estimé et surveillé, aucune source, repli rerank).
- Historique borné (8 messages + la Feature toujours re-présentée) ; few-shot chargé depuis `evals/gold/` sinon `evals/silver/` (chemins tolérants à l'image runtime sans `evals/`).
- 12 TU (Albert/RAG mockés, DB scriptée — dont : few-shot silver marqué non validé, divergence extraite, règle 1 signalée, dédup du registre, 502 sur réponse vide) — **138 tests au total**.
- Plan `docs/plans-test/s2.6-moteur.md` — **la première génération réelle de bout en bout** (RAG réel + prompt 3 + gpt-oss-120b), avec relevés informels préparant E6.

**Validation en session** : lint vert, **138 tests verts**. La génération réelle exige la clé → plan pod.

**Mini-récap** :
- ✅ Fait : E3.2 livrée — le produit a désormais son moteur : corpus → contexte cité → conversation guidée par le prompt 3 → registre d'hypothèses
- ⏳ À venir : côté code — E5 (export CSV Jira + récap A8, petite), E4 (UI conversationnelle DSFR), E6 (harnais d'évals) ; côté référent — session Onyxia TU/TNR sur toute la chaîne (plans S1.7 → S2.6)

---

## Session 02/07/2026 (16) — S2.5 : E3.1, machine à états du workflow + registre des hypothèses

**Contexte** : « continue » — entrée dans E3, le cœur du produit, en deux incréments : E3.1 = squelette persistant et invariants produit (cette story, sans LLM) ; E3.2 = moteur conversationnel (Albert + `/contexte` à chaque étape, A2/A9).

**Travail livré** :
- `sia_api/workflow.py` — machine à états **PURE** : les 6 étapes du prompt 3 (récupération feature → interview → stories candidates → rédaction → contrôle DoR → synthèse), « Oui » avance / « Non » itère sur place (règle 5), synthèse terminale, extraction d'hypothèses via le marqueur S1.10, contrôle « 3 questions max par lot » (règle 1) prêt pour le moteur.
- `sia_api/workflows.py` + migration 0008 — sessions persistées : `POST /workflows` (la Feature collée est enregistrée, ses [HYPOTHÈSE À VALIDER] entrent au registre dès l'étape 0), `GET /workflows/{id}` (étape + registre + compteur), `POST .../avancer` (**ne lève jamais une hypothèse — invariant A8 vérifié par TU**, le commentaire d'un « Non » est conservé), `POST .../hypotheses` (ajout, origine A3 : corpus/po/modele), `POST .../hypotheses/{id}` (**décision individuelle = seul chemin de levée**), `GET .../synthese` (409 avant l'étape finale ; récapitulatif des non levées + avertissement A8 — l'entrée de l'export E5).
- 14 TU (6 sur la machine pure, 8 sur l'API avec DB scriptée) — **126 tests au total**.
- Plan `docs/plans-test/s2.5-workflow-etats.md` (cycle de vie complet en curl, invariant A8 démontrable en réel).

**Validation en session** : lint vert, **126 tests verts**.

**Mini-récap** :
- ✅ Fait : E3.1 livrée — le squelette du workflow porte les invariants produit (règles 1/5, A3, A8)
- ⏳ À venir : **S2.6 (E3.2) — le moteur conversationnel** : appel Albert (gpt-oss-120b) avec prompt 3 + contexte projet/NFR (S1.11) + `/contexte` cité à chaque étape, détection des divergences corpus↔PO (A9), few-shot silver ; puis contrôle DoR automatisé via `valider_dor`

---

## Session 02/07/2026 (15) — S2.4 : rerank + assemblage du contexte (E2 complet)

**Contexte** : « continue les développements » — dernière brique d'E2.

**Travail livré** :
- `POST /contexte` (`api/sia_api/recherche.py`) : recherche hybride (S2.3, 15 candidats) → **rerank via `/v1/rerank` d'Albert** (`openweight-rerank`, httpx direct — hors SDK OpenAI ; **schéma albert-api `{model, prompt, input}` → `data[{index, score}]` posé en HYPOTHÈSE**, étape 0 du plan le vérifie par curl sur le pod) → **assemblage cité** : blocs `[Source : nom — section]`, budget chunks 6 000 tokens (part du ≤ 20k global), 8–15 chunks, le 1er chunk toujours servi même hors budget (cas tableau géant).
- **Repli sûr et signalé** : toute erreur rerank (404/422/réseau) ⇒ ordre RRF conservé, `rerank_applique: false`, avertissement explicite — jamais d'échec silencieux. Aucune source ⇒ contexte vide + avertissement anti-invention (hérité S2.3).
- Piège corrigé en cours de route : défaut `http_post=httpx.post` lié à la définition → résolution à l'appel (monkeypatchable, **aucun appel réseau possible en TU**).
- 9 TU (HTTP/DB/Albert simulés : réordonnancement, repli signalé, budget, borne 15, 1er chunk servi, bout-en-bout, endpoint) — **112 tests au total**.
- Plan `docs/plans-test/s2.4-rerank-contexte.md` (étape 0 = vérification du schéma rerank réel).

**Validation en session** : lint vert, **112 tests verts**. **E2 est code-complet** : corpus → recherche → rerank → contexte cité prêt pour le prompt.

**Mini-récap** :
- ✅ Fait : S2.4 livrée — E1 et E2 code-complets ; prochaine grosse pièce : E3 (machine à états du prompt 3, cœur du produit)
- ⏳ En cours : validations Onyxia (chaîne S1.7 → S2.4, plans prêts) ; schéma `/v1/rerank` à confirmer (étape 0 du plan S2.4)
- ⏳ À venir : E3 étape par étape (états 0→5, registre d'hypothèses, contrôle DoR via le validateur S1.10, citations via /contexte)

---

## Session 02/07/2026 (14) — S2.3 : RAG, recherche hybride BM25 + vecteurs (E2)

**Contexte** : dernière story de la séquence « continue à coder » de ce soir (limite de contexte de session atteinte — clôture propre derrière).

**Travail livré** :
- `api/sia_api/recherche.py` + `POST /recherche` — mécanisme **interne** au service du LLM accompagnant (A1, consommé par E3 ; l'endpoint REST sert au test/outillage) : volet plein-texte français (`to_tsvector('french')` + `ts_rank`), volet vectoriel (question vectorisée via Albert en float — gotcha S1.5 — puis `<=>` cosinus), **fusion RRF k=60** (fonction pure testée, consensus récompensé, ordre déterministe), 30 candidats par volet, `nb` borné 1–15 (8–15 chunks du budget E2). **Filtres** : `est_reference` par défaut (statut = référence S1.9, désactivable explicitement) et périmètre projet via les **dossiers confirmés par le PO** (S1.11/A6). **Aucun résultat → avertissement anti-invention explicite** (« aucune source récupérable… ») — le signalement exigé par les contraintes produit.
- Migration 0007 : index GIN français sur les chunks (ivfflat différé à la vraie volumétrie, documenté).
- 8 TU (fusion RRF pure, recherche scriptée DB+Albert factices, filtres vérifiés dans les paramètres SQL, avertissement, endpoint via dependency_overrides, bornes 422) — **103 tests au total**.
- Plan `docs/plans-test/s2.3-recherche-hybride.md` (6 étapes, bout de chaîne Onyxia).
- **Flag S2.4** (consigné au backlog sprint 2) : le rerank passe par `/v1/rerank` d'Albert, hors SDK OpenAI — première action de la story : relever le schéma exact par curl sur le pod ; repli documenté = ordre RRF + signalement.

**Validation en session** : lint vert, **103 tests verts**. Exécution réelle = plan (bout de la chaîne Onyxia de demain).

**Mini-récap** :
- ✅ Fait : S2.3 livrée — la chaîne corpus → recherche citée est code-complète de bout en bout
- ⏳ En cours : rien — séquence close, tout est mergé
- ⏳ À venir : demain, session Onyxia (chaîne S1.7 → S2.3 + plans) ; prochaine session de code : S2.4 (rerank, schéma à relever d'abord) puis E3 (machine à états du prompt 3)

---

## Session 02/07/2026 (13) — S2.2 : embeddings bge-m3 par lots (E1, nœud E)

**Contexte** : poursuite « continue à coder ». Le DAG d'ingestion se complète : scan → parse → qualify → chunk → **embed**.

**Travail livré** :
- `sia_ingestion/embed.py` + `make ingest-embed` — vectorise les `chunks.embedding IS NULL` par **lots de 32** (`--lot`), via le **client Albert de S1.5** (nouvelle dépendance workspace `sia-api` dans ingestion — Settings S1.4, clé jamais loguée), alias `openweight-embeddings`, **`encoding_format="float"`** (gotcha S1.5, verrouillé par TU). **Commit par lot** : un échec (quota 429, réseau) est isolé, l'acquis survit, la relance ne retraite que le reste — c'est le mécanisme de reprise ET des embeddings de nuit (D9). Dimension contrôlée (1024 attendue), vecteurs écrits par cast `::vector` (aucune dépendance pgvector côté Python).
- 7 TU (client factice, fausse connexion : lots, float/alias vérifiés, échec de lot isolé avec poursuite, dimension inattendue, reprise vide, config Albert manquante → message propre) — **95 tests au total**.
- Plan `docs/plans-test/s2.2-embeddings.md` (dernier maillon de la chaîne Onyxia ; étape 5 = avant-goût E2 avec l'opérateur cosinus).

**Validation en session** : lint vert, 95 tests verts. Exécution réelle = plan (exige la clé — pod).

**Mini-récap** :
- ✅ Fait : S2.2 livrée — **le DAG d'ingestion E1 est code-complet** (hors lecture S3, en attente du snapshot MinIO)
- ⏳ En cours : clôture de la séquence de code de ce soir
- ⏳ À venir : demain, session TU/TNR Onyxia (chaîne complète S1.7 → S2.2 + CRUD S1.11) ; puis S2.3/S2.4 (RAG hybride + rerank)

---

## Session 02/07/2026 (12) — S2.1 : chunking par sections (E1, nœud D)

**Contexte** : poursuite de l'instruction « continue à coder les features à venir ». Le sprint 1 étant code-complet, ouverture d'un **squelette de backlog sprint 2** (`docs/sprint-2-backlog.md`, S2.1→S2.4 — à amender par le référent) déclinant les epics E1/E2 de CLAUDE.md.

**Travail livré** :
- `sia_ingestion/chunk.py` + `make ingest-chunk` — nœud D : dérivés markdown → blocs atomiques (paragraphes et **tableaux entiers**) sous leur **fil de titres**, assemblage glouton 500–800 tokens, **tableaux jamais coupés** (un tableau > budget reste entier — la règle prime), paragraphes géants scindés par lignes, **chevauchement** (le dernier bloc ≤ 150 tokens du chunk N ouvre le chunk N+1), petites sections fusionnées (pas de miettes sous la cible basse). Tokens ≈ caractères/4 (POC — fenêtre bge-m3 relevée : 8192, très au-dessus).
- Migration 0006 : table `chunks` (document, sha256 pour reprise D9, ordinal, section, contenu, nb_tokens, **`embedding vector(1024)` NULL** — prête pour le nœud E/S2.2).
- Reprise sur hash : chunks existants pour le sha courant → document sauté ; document modifié → chunks remplacés (purge + réinsertion). Échec de lecture d'un dérivé = échec isolé.
- 12 TU (fonctions pures + fausse connexion : fil de titres, tableau atomique, budget, tableau géant intact 200 lignes, chevauchement vérifié, scission, reprise, échec isolé) — **88 tests au total**.
- Plan `docs/plans-test/s2.1-chunking.md` (s'insère dans la chaîne Onyxia après S1.8).

**Validation en session** : lint vert, 88 tests verts. Exécution sur base réelle = plan (session Onyxia de demain).

**Mini-récap** :
- ✅ Fait : S2.1 livrée ; sprint 2 squeletté
- ⏳ En cours : S2.2 (embeddings par lots) — suite immédiate
- ⏳ À venir : S2.3/S2.4 (RAG) ; demain : session TU/TNR Onyxia sur toute la chaîne

---

## Session 02/07/2026 (11) — S1.10 : gabarits internes — templates structurés & validateur

**Contexte** : instruction référent « continue à coder les features à venir jusqu'à épuisement des crédits, puis demain TU et TNR Onyxia sur toute la session ». Direction : S1.10 (dernière story du sprint 1), puis poursuite sur E1/E2.

**Travail livré** :
- `api/sia_api/gabarit.py` — **source unique : le prompt 3** (relu intégralement avant extraction). Templates structurés en constantes : blocs récit (En tant que / Je veux / Afin de), blocs champs (Contexte, Écran/module, Parcours, Pré-requis, Règles métier, Maquettes), colonnes exactes du tableau Gherkin des CA (`# | Étant donné que… | Lorsque… | Alors…`), colonnes du tableau des stories candidates (étape 2), **10 critères DoR** + statuts ✅⚠️❌🔵 (étape 4), marqueur [HYPOTHÈSE À VALIDER], adverbes flous (règle 4).
- `valider_us()` : entête, blocs présents et non vides, ≥1 attendu, tableau CA (colonnes exactes, ≥1 ligne, cellules complètes), ≥1 critère DSFR ; **hypothèses relevées mais jamais bloquantes** (A8) ; adverbes flous = avertissement non bloquant (le PO arbitre). `valider_dor()` : 10 critères, statuts valides, justifications, et **« estimée et revue en refinement » doit rester 🔵** (l'IA n'estime jamais à la place de l'équipe).
- CLI `python -m sia_api.gabarit <fichier.md>` : rapport par story, exit ≠ 0 si non conforme — première surface exécutable, consommée demain par le plan de test.
- 16 TU (fixtures = les 3 silver + US minimale + variantes dégradées + tableaux DoR construits) ; piège de regex corrigé en cours de route (`\s*` avalait le saut de ligne → `[ \t]*`).
- Plan `docs/plans-test/s1.10-gabarit-validateur.md` (aucune base requise) ; README et backlog à jour.

**Validation en session (réelle)** : CLI exécuté sur `evals/silver/stories-silver-candidates.md` → **3 × [CONFORME], 4/4/3 CA, 1/2/3 hypothèses relevées, exit 0**. `make lint` vert, **75 tests verts**. Le CA « gold » reste une dépendance externe (statu quo).

**Mini-récap** :
- ✅ Fait : S1.10 livrée — le sprint 1 est code-complet (11 stories) ; poursuite sur E1 (chunking)
- ⏳ En cours : validations Onyxia de demain (TU/TNR + plans, session dédiée)
- ⏳ À venir : E1 chunking + embeddings, E2 RAG — enchaînés cette session tant que possible

---

## Session 02/07/2026 (10) — Incident : fuite de la clé dans le traceback de config (fix S1.4)

**Contexte** : premier run consolidé des plans de test sur pod (référent). Le run a cascadé en échecs — cause racine : **toutes les commandes lancées depuis `~/work/GRIAC/api/`** au lieu de la racine (dérivés introuvables, `make` sans Makefile, uvicorn sans le `.env` racine, chemins helm cassés — le piège exact visé par la règle « commandes toujours préfixées » ; le « OK : 0 gpu » du run était vacueux, template en échec).

**🔴 Découverte de sécurité** : au démarrage raté d'uvicorn (clé présente dans l'env du pod, `ALBERT_BASE_URL` absente car `.env` hors cwd), **la ValidationError pydantic chaînée au RuntimeError affichait `input_value={'albert_api_key': '…'}` — la clé en clair dans les logs**, contournant SecretStr et le message qui ne nomme que les variables. Violation du CA3 de S1.4, détectée uniquement par l'exécution réelle.

**Fix livré (PR #12)** : `charger_settings()` lève désormais `RuntimeError … from None` (cause supprimée — plus aucun input_value dans les tracebacks) + TU dédié rejouant le scénario exact (clé présente, base_url manquante → `traceback.format_exception` ne contient pas la clé). 60 tests verts. **Reproduction réelle avant/après en session** : uvicorn en échec de config avec clé factice → 0 occurrence dans la sortie.

**Actions référent** : (1) **faire tourner la clé Albert** (exposée en partie dans le terminal du pod et un screenshot) puis mettre à jour l'env du pod / le `.env` ; (2) rejouer le bloc de validation consolidé — chaque étape re-préfixée `cd ~/work/GRIAC/` (transmis en session).

**⚠️ Rectification (même session, après échange avec le référent)** : la ligne « …1 ocr_requis, 0 échecs ; exit 0 » lue comme un résultat de `ingest-parse` était en réalité **l'écho du commentaire `# attendu : …`** du bloc de commandes, replié par le terminal. **Aucun service PostgreSQL n'a jamais été lancé dans l'espace Onyxia** (« il n'y a jamais eu deux cartes ») → **aucune étape base réelle n'a encore tourné** : ni migrations, ni scan, ni parse, ni qualify, ni CRUD. Validations pod réellement acquises à ce jour : S1.4 (plan complet), S1.5 (sonde, no-go GO), S1.6 rendu (`helm lint` 0 failed + `helm template` réel, 0 GPU — authentiques). Procédure de lancement du service PostgreSQL du catalogue transmise au référent ; la chaîne complète migrations → scan → parse → qualify → CRUD/A6 reste à jouer.

**Mini-récap** :
- ✅ Fait : fuite corrigée (from None + TU), reproduction avant/après, PR #12
- ⏳ En cours : rotation de la clé (référent) puis re-run du bloc consolidé depuis la racine
- ⏳ À venir : S1.10 (dernière story du sprint)

---

## Session 02/07/2026 (9) — S1.6 : charts Helm minimaux Onyxia (code)

**Contexte** : même session remote, branche rebasée après merge de la PR #10 (« ok go »). Direction : suite du backlog → S1.6.

**Travail livré** :
- Chart `infra/helm/sia-po` : postgres+pgvector (Deployment Recreate + PVC + Secret portant aussi DATABASE_URL), **job de migrations en hook Helm** post-install/post-upgrade (alembic upgrade head, idempotent), api (probes /health, `envFrom` sur le **Secret `sia-albert` existant** — le template S1.4 trouve sa consommation prévue), web, Ingress api/web sur `*.lab.sspcloud.fr` (className nginx), ressources modestes et **aucune demande de GPU**.
- **Job CI `helm-chart`** (azure/setup-helm : `helm lint` + `helm template` en valeurs par défaut) — helm est indisponible en session (403 proxy sur get.helm.sh) : la CI est le validateur permanent du rendu, même logique que S1.3.
- `docs/deploy-onyxia.md` : prérequis (images poussées vers un registre accessible — publication manuelle assumée au MVP, à industrialiser en E7 ; secret Albert créé au préalable), install/upgrade/uninstall, vérifications observables, limites assumées (mono-réplica, TLS par le lab).
- Plan de test `docs/plans-test/s1.6-helm.md`.
- TU : sans objet (YAML) ; TNR : `make lint` + `make test` (59 verts) inchangés.

**Validation** : **job CI `helm-chart` VERT sur la PR #11 dès le premier run** (helm lint + helm template, run 28617979086) — CA « helm template valide » démontré, « aucun GPU » vérifiable dans les manifestes rendus. Déploiement réel sur le lab = plan de test (référent — exige des images poussées dans un registre).

**Clôture de session (instruction référent : « clôture session et PR »)** : PR #11 mergée sur instruction après CI 4/4 verte ; commandes de validation pod consolidées transmises au référent (enchaînement des plans S1.7 → S1.11 + rendu helm S1.6 sur une seule session pod avec service PostgreSQL Onyxia).

**Mini-récap** :
- ✅ Fait : chart complet + job CI helm vert (CA2/CA3 ✅) + procédure de déploiement ; PR #11 mergée
- ⏳ En cours : côté référent — validations pod (plans S1.7 → S1.11, rendu helm, déploiement lab), CA2 S1.3 (protection de branche)
- ⏳ À venir : S1.10 (templates + validateur de conformité US) — dernière story du sprint 1

---

## Session 02/07/2026 (8) — S1.11 : entité Projet — contexte & NFR (code)

**Contexte** : même session remote, branche rebasée après merge de la PR #9 (« next »). Direction : suite du backlog → S1.11 (prérequis d'E8 puis E3).

**Travail livré** :
- Migration 0005 : `projects` (nom UNIQUE, contexte), `project_nfrs` (CHECK sur les 7 types D19 : performance, volumétrie, SSI, RGPD, accessibilité RGAA, disponibilité, auditabilité ; formulation ; valeur cible optionnelle), `project_dossiers` (UNIQUE(project_id, dossier), `origine` po/suggestion — **la table qui fait foi, arbitrage A6**).
- Routes FastAPI (`sia_api/projets.py`) : `POST/GET/PUT /projects` (NFR et dossiers remplacés à la mise à jour — éditable), 404/409/422 propres ; **`GET /dossiers/suggestions`** : expose les `projet_suggere` de S1.9 avec nombre de documents et drapeau `deja_associe` — le PO confirme ou corrige via le champ `dossiers` du projet, la boucle A6 est fermée.
- `sia_api/db.py` : connexion PostgreSQL par dépendance FastAPI (DATABASE_URL, jamais en dur), **503 explicite si absente** ; les TU surchargent la dépendance (aucune base réelle). DATABASE_URL ajoutée au service api du compose.
- 10 TU (59 au total) : création complète (SQL émis vérifiés), 409 nom dupliqué, 422 nom vide / type NFR hors liste, 404 lecture/màj, remplacement NFR+dossiers, suggestions A6, 503 sans DATABASE_URL.
- Plan de test `docs/plans-test/s1.11-projets.md` (12 étapes, enchaînable après S1.7 → S1.9 — ferme la boucle suggestions → confirmation).

**Validation en session** : lint vert, **59 tests verts** ; uvicorn réel : routes présentes dans l'OpenAPI (`/projects`, `/projects/{id}`, `/dossiers/suggestions`), `GET /projects` sans DATABASE_URL → 503 avec message explicite, `/health` inchangé. CRUD sur base réelle : à jouer via le plan.

**Mini-récap** :
- ✅ Fait : S1.11 code complet (migration 0005 + CRUD + suggestions A6), 10 TU, TNR 59 verts
- ⏳ En cours : PR ouverte (CI) ; plans S1.7 → S1.11 enchaînables sur base réelle
- ⏳ À venir : S1.6 (Helm Onyxia) puis S1.10 (templates + validateur de conformité US) — dernières stories du sprint

---

## Session 02/07/2026 (7) — S1.9 : qualification v0 — métadonnées & versions (code)

**Contexte** : même session remote, branche rebasée après merge de la PR #8 (« next »). Direction : suite du backlog → S1.9.

**Travail livré** :
- `sia_ingestion/qualify.py` + `make ingest-qualify` — nœud C du DAG, **fonction pure sur l'inventaire** (aucun accès fichier) : projet suggéré (1er niveau du chemin — la colonne s'appelle `projet_suggere` pour porter l'arbitrage A6 : suggestion à confirmer par le PO via S1.11), date dans le nom (ISO, compacte, FR), version (`v\d+` insensible aux `_`, `VF`, `final`), brouillon (`draft|brouillon|wip`), regroupement des versions par nom normalisé (sans accents/marqueurs/dates), **doublons par sha256** (canonique = non-« copie », sinon chemin le plus court ; jamais référence), **référence par groupe** (non-brouillon > version_no > marque finale > date nom sinon mtime — règle documentée dans le module, ajustable). `est_reference` alimentera le filtre « statut = référence » du RAG (E2).
- Migration 0004 : 8 colonnes de qualification sur `documents`.
- 9 TU (49 au total) dont **le jeu piégé du CA4** : spec_v1 / spec_v2_final_VF3 / copie conforme → même groupe, copie = doublon_de la v2 jamais référence, v2 (v2+finale+VF3) = référence, v1 non ; brouillon jamais référence face à une version propre ; dates ISO/compacte/FR ; groupes distincts par projet.
- Plan de test `docs/plans-test/s1.9-ingest-qualify.md` (7 étapes, enchaînable après S1.7/S1.8 sur la même base).

**Validation en session** : lint vert, **49 tests verts** (le CA4 est couvert par TU — les CA 1–3 se cochent après le plan sur base réelle).

**Mini-récap** :
- ✅ Fait : S1.9 code complet (qualify + migration 0004), 9 TU dont jeu piégé, TNR 49 verts
- ⏳ En cours : PR ouverte (CI) ; plans S1.7 → S1.9 enchaînables sur base réelle
- ⏳ À venir : S1.11 (entité Projet — l'association projet↔dossiers confirmée par le PO consommera `projet_suggere`), puis S1.6, S1.10

---

## Session 02/07/2026 (6) — S1.8 : parsing docling → markdown (code)

**Contexte** : même session remote, branche rebasée après merge de la PR #7 (« next » — merge avec réserve explicite : plan S1.7 sur base réelle toujours à jouer). Direction : suite du backlog → S1.8.

**Travail livré** :
- `sia_ingestion/parse.py` + `make ingest-parse CORPUS=<dossier>` — nœud B du DAG : lit les documents docx/pdf inventoriés (S1.7), convertit via docling en markdown, écrit les dérivés `derived/md/<sha256>.md` (hors repo), met à jour le statut en base. **Reprise sur hash (D9)** : dérivé existant pour le sha256 = « inchangé », pas de reconversion — couvre au passage les doublons byte-à-byte (un seul dérivé). **PDF sans couche texte** détectés par pypdf et marqués `ocr_requis` AVANT docling (OCR = sprint 2 ; OCR docling explicitement désactivé `do_ocr=False`). **Échec isolé** : statut `echec` + erreur en base, lot poursuivi, rapport `derived/rapport-parsing.csv`, exit 1 si échecs.
- Migration 0003 : colonnes statut_parsing (défaut `a_parser`), chemin_derive, erreur_parsing, date_parsing.
- Dépendances : docling (~2 Go avec torch — **import paresseux : jamais chargé par les TU**), pypdf (détection couche texte). CI : cache uv activé (`enable-cache`) pour absorber le poids.
- Fixtures régénérées : PDF **conformes** (xref correct, lisibles par pypdf) dont `scan-courrier-prefecture.pdf` réellement **sans couche texte** ; docx enrichis (styles Heading1/Heading2 + **tableau**) pour vérifier le CA « hiérarchie préservée, tableaux jamais détruits ».
- 9 TU (docling simulé par injection ; pypdf réel sur les fixtures) : lot nominal, échec isolé sans interruption, ocr_requis sans conversion, reprise sur hash sans appel convertisseur, détection réelle pdf avec/sans texte, filtre docx/pdf, `inchange` persisté `parse`, rapport CSV, DATABASE_URL absente.
- Plan de test `docs/plans-test/s1.8-ingest-parse.md` (9 étapes).

**Validation en session** : lint vert, **40 tests verts**. **Conversion docling RÉELLE démontrée sur la fixture docx** : `## Spécification authentification — v2 finale`, `### Critères d'acceptation`, tableau `| Critère | Valeur cible |` — hiérarchie et tableau préservés (CA1 docx ✅ en session). **PDF non démontrable en session** : docling télécharge ses modèles de layout au premier parsing PDF (huggingface.co) → 403 du proxy de session ; à jouer sur pod (réseau ouvert). Découverte consignée : le pipeline PDF docling par défaut tente aussi un téléchargement de modèles OCR (modelscope.cn) → `do_ocr=False` évite ce téléchargement ET est cohérent avec le CA4.

**Mini-récap** :
- ✅ Fait : S1.8 code complet (parse + migration 0003 + fixtures durcies + rapport), 9 TU, TNR 40 verts, conversion docx réelle démontrée
- ⏳ En cours : PR ouverte (CI — premier run avec docling : cache uv à chaud ensuite) ; plans S1.7 + S1.8 sur base réelle (enchaînables, mode A lève aussi la réserve S1.2)
- ⏳ À venir : S1.9 (qualification v0) selon l'ordre du backlog

---

## Session 02/07/2026 (5) — S1.7 : ingestion — scan & inventaire (code)

**Contexte** : même session remote, branche rebasée après merge de la PR #6 (« next »). Direction : suite du backlog → S1.7 (S1.4, S1.5, S1.3 livrées).

**Travail livré** :
- Membre workspace `ingestion` (`sia-ingestion`, dépendance psycopg seule — docling/boto3/Albert arrivent avec S1.8+) ; `ingestion/.gitkeep` retiré (dossier désormais peuplé).
- `sia_ingestion/scan.py` — nœud A du DAG : parcours récursif trié d'un dossier local (fichiers/dossiers cachés ignorés), sha256 par blocs de 1 Mo, extension normalisée, mtime ISO UTC ; upsert `ON CONFLICT (chemin) DO UPDATE` avec compteurs insérés/mis à jour (idiome `xmax = 0`) ; export CSV (`derived/inventaire.csv`, hors git) ; `make ingest-scan CORPUS=<dossier>`. **Choix assumé** : la clé d'idempotence est le **chemin relatif** (un fichier = une ligne ; relance = zéro doublon ; fichier modifié = ligne mise à jour) — les doublons de contenu (même sha256, chemins différents) restent des lignes distinctes, leur regroupement est le travail de S1.9 ; l'index sha256 sert aussi la reprise sur hash D9. `s3://` refusé avec message explicite (snapshot MinIO inexistant, prérequis §7) — lecture S3 avec E1, à arbitrer.
- Migration Alembic 0002 : table `documents` (chemin UNIQUE, sha256 indexé, premiere_vue/derniere_vue).
- 6 fixtures synthétiques dans `evals/fixtures` (aucun document réel) : spec v1 + v2_final_VF3 (docx minimaux valides) + copie byte-à-byte (doublon de hash), PDF natif avec texte, PDF « scanné », txt — servent aussi le jeu piégé de S1.9.
- 7 TU (aucune DB réelle : connexion/curseur simulés rejouant le RETURNING) : arborescence + hash + normalisation, corpus introuvable, doublons/versions sur les fixtures du repo, compteurs upsert + ancrage `ON CONFLICT (chemin)`, CSV, refus s3://, DATABASE_URL absente.
- Plan de test `docs/plans-test/s1.7-ingest-scan.md` (9 étapes — le mode A lève au passage la réserve compose S1.2) ; README et backlog à jour.

**Validation en session** : `make lint` vert, `make test` **31 tests verts**. Pas de PostgreSQL réelle en session (pas de daemon Docker) → **exécution du plan sur base réelle à jouer** (mode A poste/pod Docker, ou service PostgreSQL Onyxia en mode B) ; les CA restent non cochés d'ici là.

**Mini-récap** :
- ✅ Fait : S1.7 code complet (scan + migration 0002 + fixtures + CSV + make ingest-scan), 7 TU, TNR verte
- ⏳ En cours : PR ouverte (CI en juge de paix) ; exécution du plan de test sur base réelle
- ⏳ À venir : S1.8 (parsing docling) selon l'ordre du backlog ; arbitrage lecture S3 (E1)

---

## Session 02/07/2026 (4) — S1.3 : CI minimale (GitHub Actions)

**Contexte** : même session remote, branche `claude/backlog-continuation-6ftff4` rebasée sur `main` après merge de la PR #5 (« ok on continue »). Direction : suite du backlog → S1.3.

**Travail livré** :
- `.github/workflows/ci.yml` : la note prévoyait « GitLab CI ou équivalent — adapter au dépôt réel » → dépôt réel GitHub, donc GitHub Actions. Déclenchement sur `pull_request` et `push` sur `main`. Job `lint-tests` (setup-uv 0.8.17 aligné dev, `uv sync --all-packages`, `make lint`, `make test` — mêmes commandes que la baseline locale, aucun appel réseau dans les tests) ; matrice `build-images` api/web (Dockerfiles cible `runtime`, images non poussées).
- Plan de test `docs/plans-test/s1.3-ci.md` : CA1 = 3 checks verts observés sur la PR ; CA2 = procédure d'activation de la protection de branche par le référent, **avec la limite connue : dépôt privé en plan Free → protection non applicable** (repli : checks rouges visibles + règle de revue CLAUDE.md) ; test de blocage optionnel par PR jetable.
- README : badge CI.
- TU : sans objet (aucune fonction métier — workflow YAML) ; TNR : `make lint` + `make test` (24 verts) avant push.

**Validation stack-live** : **CA1 démontré sur la PR #6 elle-même — 3 checks verts** (`lint-tests` en 11 s, `build-images (web)` en 13 s, `build-images (api)` en 19 s ; run GitHub Actions 28614129420 du 02/07/2026 18:52 UTC). CA2 (merge bloqué) : action référent — protection de branche, les 3 checks sont désormais sélectionnables ; limite plan Free documentée dans le plan de test.

**Mini-récap** :
- ✅ Fait : workflow CI livré et démontré vert sur la PR #6 (CA1) ; plan de test + badge ; TNR verte
- ⏳ En cours : CA2 — activation de la protection de branche par le référent (Settings → Branches)
- ⏳ À venir : S1.7 (ingestion : scan & inventaire) selon l'ordre du backlog

---

## Session 02/07/2026 (3) — S1.5 : client Albert & sonde des limites (code)

**Contexte** : même session remote que S1.4, branche `claude/backlog-continuation-6ftff4`. Direction : « go pour la suite du backlog » → S1.5, prochaine story dans l'ordre. La PR #4 (S1.4) était encore ouverte au moment du développement — arbitrage rendu par le référent : **PR #4 mergée sur son instruction** (`dec80a9b`), branche rebasée sur `main`, **S1.5 livrée en PR #5 (draft)** — la règle « une story = une PR » est respectée.

**Travail livré** :
- `api/sia_api/albert.py` : `creer_client()` — client OpenAI pointé sur Albert, clé via `SecretStr` (S1.4), timeout et retries configurables par env (`ALBERT_TIMEOUT_S` défaut 30 s, `ALBERT_MAX_RETRIES` défaut 2, nouveaux champs Settings) ; aucun appel réseau à l'import.
- `api/sia_api/probe.py` + cible `make probe` : 4 relevés — `GET /v1/models` (catalogue complet + tableau id/type/aliases/max_context_length), `GET /v1/me/info` (**seul l'objet `limits` est conservé** — jamais d'email/identifiant dans le rapport), appel de chat minimal (alias chat, latence), appel d'embeddings minimal (dimension attendue 1024 pour bge-m3). Une erreur sur un relevé n'interrompt pas les autres ; messages d'erreur **expurgés de la clé** (`_sans_cle`) ; rapport écrit dans `docs/albert-limits.md` ; exit 0 seulement si les 4 relevés sont ok.
- 10 TU (Albert mocké, aucun appel réseau) : construction du client (base_url, timeouts par défaut et surchargés), sonde nominale + rapport, filtrage `limits`, avertissement si `limits` absent, panne réseau sans interruption des relevés suivants, expurgation de la clé des erreurs, affichage des échecs dans le rapport, timeout/retries dans la config.
- `.env.example` et compose : variables `ALBERT_TIMEOUT_S`/`ALBERT_MAX_RETRIES` ; README : `make probe` ; plan de test `docs/plans-test/s1.5-albert-probe.md` (6 étapes, test négatif clé invalide AVANT le relevé nominal, rapport à committer en clôture).
- openai ajouté aux dépendances api (httpx promu en dépendance runtime).
- **Retour du premier `make probe` réel sur pod (screenshot référent)** : quotas relevés ✅ (`limits` par routeur : rpm 50 / rpd 1000 / **tpm 128 000** / tpd ~2,46 M sur les routeurs 339/420 ; rpm 10 + tpd 1,28 M sur le 337 ; tpm/tpd `null` sur le 1085) — mais **appel de chat « ok » avec réponse VIDE** (latence 0,16 s) : gpt-oss-120b est un modèle à raisonnement, `max_tokens=16` était consommé avant tout contenu. **Fix livré (`f83181c`)** : `max_tokens=512`, `finish_reason` tracé dans le rapport, **réponse vide = relevé en échec explicite** (fini le « ok » de façade) ; TU dédié ajouté (24 tests verts). `make probe` à rejouer sur le pod après pull.
- **Deuxième run pod : chat ok ✅ (fix max_tokens validé stack-live), mais embeddings en échec — `InternalServerError`.** Diagnostic par curl sur le pod (référent) : l'alias `openweight-embeddings` existe (→ `BAAI/bge-m3`, **fenêtre 8192**, de même `openweight-rerank` → `BAAI/bge-reranker-v2-m3`, 8192) et l'endpoint répond **200 en curl** (input chaîne comme liste). Cause : **le SDK OpenAI envoie `encoding_format="base64"` par défaut, non supporté par le serveur d'embeddings d'Albert** (curl sans le paramètre = float = 200). **Fix : `encoding_format="float"` explicite** + TU vérifiant sa présence. ⚠️ **Gotcha à reproduire sur TOUT appel d'embeddings Albert via SDK — ingestion E1 comprise.**
- **Troisième run pod : 4/4 relevés ok, exit 0, 0 occurrence de la clé — rapport `docs/albert-limits.md` committé et poussé par le référent (`bb3127c`).** Au passage : les hooks pre-commit se sont installés et exécutés sur le pod lors du commit (réserve S1.1 quasi levée — un `pre-commit run --all-files` complet reste à jouer une fois).
- **Verdict no-go n°1 : GO ✅.** Fenêtre effective du chat `openweight-large` → openai/gpt-oss-120b = **131 072 tokens** ≫ budget 20 000/requête (marge ×6,5). Quotas (par routeur, mapping router_id↔modèle non exposé par l'API) : profils « génération » rpm 50 (10 sur un routeur), rpd 1000, **tpm 128 000** (~6 requêtes pleines/min), **tpd 2 460 000** (~120 requêtes pleines/jour — la vraie contrainte à surveiller : une session de rédaction E3 ≈ 6 étapes × ≤20k ≈ 120k tokens → ~20 sessions complètes/jour) ; profils sans limite de tokens rpm 500/rpd 50 000 (vraisemblablement embeddings/rerank — confortable pour l'ingestion, embeddings de nuit D9 en réserve si gros corpus). Latences : chat 0,27 s, embeddings 0,06 s. **Catalogue notable pour E6** : `openweight-medium` → Mistral-Small-3.2-24B (fenêtre 128k, alias secondaire `albert-large`) ; aussi `openweight-code` (Qwen3-Coder, 262k), `openweight-small` (Ministral 3 8B, 262k, multimodal), `openweight-audio` (whisper). Tous à coût 0.

**Validation en session** : `make lint` vert ; `make test` **23 tests verts**. Démonstration réelle de la gestion d'erreurs : `make probe` vers un hôte injoignable → rapport écrit, 4 relevés « échec — APIConnectionError/ConnectError » sans traceback, exit ≠ 0, clé factice absente du rapport (grep = 0). **L'exécution nominale exige le réseau Albert + la clé : à jouer sur le pod via le plan de test — c'est le test no-go n°1 (fenêtre effective et quotas, à comparer au budget 20k tokens).**

**Mini-récap** :
- ✅ Fait : S1.5 livrée et validée stack-live de bout en bout (plan de test 6/6, 4/4 relevés ok sur pod, rapport committé) ; **verdict no-go n°1 : GO** (fenêtre 131k ≫ budget 20k) ; 2 bugs découverts par les runs réels et corrigés (max_tokens/raisonnement, encoding_format float) ; PR #4 mergée ; PR #5 prête pour revue
- ⏳ En cours : revue et merge de la PR #5 par le référent
- ⏳ À venir : S1.3 (CI), puis S1.7 (ingestion : scan & inventaire) selon l'ordre du backlog ; vigilance tpd 2,46 M à réévaluer avec l'usage réel

---

## Session 02/07/2026 (2) — S1.4 : configuration & secrets

**Contexte** : session remote (claude.ai/code), branche dédiée `claude/backlog-continuation-6ftff4`. Direction : « go pour la suite du backlog » → S1.4, prochaine story dans l'ordre (S1.1/S1.2 mergées, cf. en-tête précédent).

**Travail livré** :
- `api/sia_api/config.py` : `Settings` pydantic-settings — `ALBERT_BASE_URL` (requise), `ALBERT_API_KEY` (requise, `SecretStr` : masquée dans str/repr donc jamais dans les logs), alias `ALBERT_MODEL_CHAT`/`_EMBEDDINGS`/`_RERANK` avec défauts `openweight-*` surchargeables par env. Chaîne vide traitée comme absence (cas compose `${VAR:-}`). `charger_settings()` convertit la ValidationError en RuntimeError explicite qui **nomme** les variables en cause sans jamais afficher de valeur.
- `api/sia_api/main.py` : lifespan FastAPI — config chargée au démarrage, échec = refus de démarrer (l'absence de clé se découvre au boot, pas au premier appel Albert). `/health` inchangé (toujours sans dépendance).
- `.env.example` documenté (Albert + variables compose) ; exception `!.env.example` ajoutée au `.gitignore` (le motif `.env.*` existant l'aurait ignoré) ; template Secret Kubernetes `infra/k8s/secret-albert.example.yaml` (aucune valeur réelle, usage kubectl documenté, consommation `envFrom` prévue avec S1.6).
- `infra/compose.yaml` : le service api reçoit les variables `ALBERT_*` (défaut = alias pour les modèles, vide pour URL/clé → refus de démarrer, visible via `docker compose logs api`) ; commentaire obsolète « arrive avec S1.4 » recalé.
- `api/tests/test_config.py` : 8 tests (chargement complet, alias par défaut + surcharge, clé absente/vide → RuntimeError nommant la variable, clé jamais dans str/repr, démarrage TestClient refusé sans config / OK avec). Aucun appel réseau.
- README : section « Configuration & secrets (S1.4) », prérequis de la stack locale mis à jour (`.env` requis).
- **Règle de méthode ajoutée à CLAUDE.md sur demande du référent : « TU + TNR + plan de test avant toute livraison »** — TU écrits et verts, baseline complète `make lint` + `make test` (TNR) verte avant tout push, et plan de test systématique versionné dans `docs/plans-test/<story>.md` (étapes numérotées, commandes préfixées, résultat attendu observable, environnement cible) référencé dans la PR.
- Premier plan de test versionné : `docs/plans-test/s1.4-config-secrets.md` (8 étapes, pod Onyxia mode B + étape 7 optionnelle mode A qui lève aussi la réserve compose S1.2).
- `docs/init-pod-onyxia.md` recalé : préalable commun `.env` au §4 (depuis S1.4 l'api refuse de démarrer sans clé — le mode B documenté aurait échoué), ligne de dépannage ajoutée.

**Validation stack-live** (pas de daemon Docker en session — même limite que S1.2, la réserve compose reste ouverte) : uvicorn **réel** sans variables → `RuntimeError: Configuration Albert invalide — variables d'environnement manquantes ou vides : ALBERT_API_KEY, ALBERT_BASE_URL…` puis `Application startup failed. Exiting.` (exit 3) ; uvicorn réel avec clé factice → `GET /health` = 200 et **0 occurrence de la clé dans le log de démarrage** (grep). `docker compose config` : variables `ALBERT_*` rendues sur le service api. `make lint` vert ; `make test` : 13 tests verts.

**Exécution du plan de test `docs/plans-test/s1.4-config-secrets.md` sur pod Onyxia réel** (référent, pod `vscode-python-gpu-165935` — rappel : prendre un pod **sans GPU** la prochaine fois) : étape 1 ✅ `make lint` vert + **13 tests verts** ; étape 2 ✅ refus sans variables (message explicite, `code retour = 3`) ; étape 3 ✅ refus variables vides ; étape 4 ✅ `GET /health` = 200 servi par le bon process (preuve : `Application startup complete` dans le log dédié `/tmp/api-s14.log`) ; étape 5 ✅ **0 occurrence de la clé dans le log** + repr `SecretStr('**********')` avec les trois alias `openweight-*`. Étape 7 (mode A compose) non jouée — la réserve compose de S1.2 reste ouverte (au plus tard S1.6). **Incidents de parcours instructifs** : (1) premier « 200 » de l'étape 4 = faux positif servi par l'api S1.2 encore vivante sur le port 8000 (lancée en début de session pod) — purge des jobs puis relance avec log dédié ; (2) premier passage de l'étape 5 invalide (`CLE` extraite du `.env` était vide → `grep -c ""` matche toutes les lignes, d'où un « 5 » trompeur) — rejoué avec la clé de l'environnement, plan de test durci en conséquence. **Découverte** : `ALBERT_API_KEY` est **déjà injectée dans l'environnement du pod** (`printenv | wc -c` = 159 ; elle prime sur le `.env`, précédence pydantic-settings) tandis que `ALBERT_BASE_URL` vient du `.env` — à retenir pour S1.5 : `make probe` fonctionnera sur ce pod sans manipulation de clé. Bonus début de session pod : revalidation S1.2 (5 tests verts, api 8000 et web 8081 = 200, bandeau D15 servi).

**Mini-récap** :
- ✅ Fait : S1.4 livrée, validée stack-live en session **et sur pod Onyxia (plan de test étapes 1–5 ✅)** ; PR #4 (draft) prête pour revue ; règle « TU + TNR + plan de test » dans CLAUDE.md ; plan de test S1.4 versionné puis durci après exécution ; procédure pod recalée
- ⏳ En cours : revue et merge de la PR #4 par le référent
- ⏳ À venir : S1.5 (client Albert + `make probe` — la clé est déjà dans l'env du pod), puis S1.3 (CI) ; étape 7 du plan (mode A compose) à jouer sur un hôte Docker — lève aussi la réserve S1.2

---

## Session 02/07/2026 — Kickoff : initialisation du repo & cadrage

**Contexte** : première session, repo GitHub `jdly956/GRIAC` vide. Direction : « installe le repo git, analyse le sujet et on débute le cadrage ».

**Travail livré** :
- Commit fondateur `6473f87` : structure documentaire cible — `CLAUDE.md` (racine), `docs/note-cadrage-sia-po.md`, `docs/sprint-1-backlog.md`, `evals/silver/stories-silver-candidates.md`. Poussé après déblocage des droits d'écriture de l'app GitHub (403 initial).
- Méthode de travail ajoutée à CLAUDE.md (adaptée du CLAUDE.md SIACT — même plateforme Onyxia SSP Cloud et Albert API pour le LLM, mais stack différente ici : tout conteneurisé, aucun GPU ni LLM local) : environnement et outils, commandes préfixées, démarrage de session, validation stack-live, pas de script de rattrapage sans fix pipeline, MAJ doc à chaque clôture, conventions code et git, garde-fous, format des réponses. Création de ce SESSIONS.md.
- Correction d'une dérive documentaire : CLAUDE.md référençait « 18 décisions (D1–D18) », la note v0.4 en compte 19 (D1–D19).
- Branche `main` créée et poussée (accord utilisateur) ; bascule en branche par défaut à faire côté GitHub.
- Cadrage : audit de cohérence des 4 documents (15 findings, dont 4 majeurs : référent, prompts absents, benchmark sans porteur, gold inatteignable par les seules silver), état des 11 prérequis externes, plan d'exécution S1.1/S1.2 (3 plans concurrents → jury → 12 corrections adversariales) livré au référent.
- Dépôt des 3 prompts SAFe fournis par le référent dans `/api/prompts/` (prompt-1 Epic, prompt-2 Features, prompt-3 Stories) — S1.10 partiellement débloquée (restent : templates structurés, validateur, gold).
- Cible fonctionnelle v2 arbitrée (9 arbitrages A1–A9) versionnée dans `docs/backlog-fonctionnel.md` + amendements induits (note §4, CLAUDE.md, backlog sprint 1) — PR #1 passée en revue.
- **PRs #1 (kickoff) et #2 (S1.1) mergées dans `main`** sur instruction du référent.
- **S1.2 livrée — code** (branche `feature/s1.2-dev-env`) : apps FastAPI `sia-api` (GET /health sans dépendance DB) et `sia-web` (page placeholder + bandeau D15 + /health), migration Alembic 0001 (pgvector, `DATABASE_URL` par env avec échec explicite, `script_location = %(here)s`), Dockerfiles multi-stage (builder/dev/runtime non-root, uv 0.8.17 épinglé), `infra/compose.yaml` (pgvector/pgvector:0.8.0-pg16, chaîne postgres healthy → migrate completed → api healthy → web, credentials substituables, bind-mounts code seul), `.dockerignore`, cibles make dev/dev-down/dev-logs/dev-reset/migrate/psql/dev-validate, workspace uv étendu (members api+web, testpaths, isort first-party), `docs/init-pod-onyxia.md` (procédure pod Onyxia, modes avec/sans daemon Docker). **Validations observées en session** : `make lint` vert ; `make test` 5 tests verts (la collecte des membres via `--all-packages` fonctionne) ; uvicorn réels : `/health` api=200, web=200, bandeau D15 servi ; alembic offline : SQL `CREATE EXTENSION IF NOT EXISTS vector` généré, échec propre sans URL ; `docker compose config` : chemins résolus dans le repo (piège `--project-directory` corrigé : bind-mounts en `./`). **Limite** : pas de daemon Docker en session → `make dev` + `make dev-validate` à jouer sur poste/pod (validation stack-live complète), résultat à consigner ici.
- **Validation S1.2 sur pod Onyxia réel** (référent, pod `vscode-python-gpu-165935` — NB : prendre un pod **sans GPU** la prochaine fois, contrainte CLAUDE.md) : `make install` OK (uv 0.11.26, CPython 3.12.3, 47 paquets, sia-api/sia-web installés), `make lint` vert, **`make test` : 5 tests verts sur le pod**, API lancée en réel : `GET /health` → 200 `{"status":"ok"}`. Incidents corrigés dans la PR #3 : port 8080 occupé par code-server sur les pods VSCode (web → 8081, `WEB_PORT` substituable dans le compose), repo déjà cloné (guide durci), uv masqué par celui de l'image. Complément après correction du port : **web sur 8081 validé par le référent (« ok, ça fonctionne »)** — `/health` = 200 et bandeau D15 servi sur le pod. **Décision de clôture du référent : S1.2 mergée avec réserve explicite** — la stack compose complète (`make dev` + `make dev-validate`) reste à démontrer sur un hôte avec daemon Docker, à la première occasion ou au plus tard avec S1.6.
- **S1.1 livrée** (branche `feature/s1.1-init-repo`, plan validé « ok go ») : workspace uv (`pyproject.toml` racine, `.python-version` 3.12, `uv.lock`), `Makefile` (help/install/lint/fmt/test), `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml` (ruff v0.15.20 aligné lock + hooks génériques + uv-lock), README, `tests/test_sanity.py`, `.gitkeep` (ingestion, web, infra, evals/gold). **Validation observée** : `make lint` vert (ruff check + format) et `make test` vert (2 tests, Python 3.12.3) dans le conteneur de session. Limite d'environnement : `pre-commit run --all-files` impossible en session (proxy git limité au repo du projet, 403 sur les dépôts de hooks) → à rejouer sur poste de dev ; hooks bien installés (`pre-commit install` OK), config validée (`validate-config`).

**Validation stack-live** : sans objet (aucun code livré — documentation uniquement).

**Mini-récap** :
- ✅ Fait : repo initialisé et poussé ; méthode de travail dans CLAUDE.md ; SESSIONS.md créé
- ⏳ En cours : analyse de cadrage multi-agents (cohérence des docs, prérequis, plan S1.1/S1.2 vérifié)
- ⏳ À venir : validation du plan S1.1/S1.2 par le référent ; création de `main` (accord utilisateur requis) ; implémentation S1.1 puis S1.2

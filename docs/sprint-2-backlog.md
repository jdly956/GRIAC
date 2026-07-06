# Sprint 2 — Fin d'ingestion & RAG (E1 + E2) — squelette

> Squelette proposé par l'assistant (02/07/2026, instruction « continue à coder les features à venir ») — **à amender/prioriser par le référent**. Les CA déclinent les exigences des epics E1/E2 de CLAUDE.md. Mêmes règles que le sprint 1 : une story = une PR, TU + TNR + plan de test, validation stack-live.

## S2.1 — Chunking par sections (E1, nœud D)

Critères d'acceptation :
- [x] Chunks par sections de titres, budget 500–800 tokens, chevauchement entre chunks consécutifs
- [x] Tableaux jamais coupés — la règle prime sur le budget (un tableau géant reste entier)
- [x] Table `chunks` (fil de titres pour la traçabilité des citations E2, sha256 pour la reprise D9) ; relance = documents inchangés sautés
- [x] `make ingest-chunk` ; TU sur fonctions pures (sans DB réelle)

*Code livré le 02/07/2026 : `sia_ingestion/chunk.py` (blocs paragraphes/tableaux sous fil de titres, assemblage glouton, scission des paragraphes géants, chevauchement d'un bloc ≤ 150 tokens), migration 0006 (table chunks avec `embedding vector(1024)` NULL — préparée pour S2.2), 12 TU (88 au total). Tokens ≈ caractères/4 (POC, à recaler via E6 si écart). CA à cocher via `docs/plans-test/s2.1-chunking.md` sur base réelle.*

## S2.2 — Embeddings bge-m3 par lots (E1, nœud E)

Critères d'acceptation :
- [x] Embeddings `openweight-embeddings` par lots ; `encoding_format="float"` (gotcha S1.5) ; clé via Settings S1.4
- [x] Écriture pgvector dans `chunks.embedding` ; reprise : seuls les chunks sans embedding sont vectorisés
- [x] Erreurs réseau/quotas gérées (lot en échec isolé, relance possible — embeddings de nuit D9 si quotas)
- [x] `make ingest-embed` ; TU (Albert mocké)

*Code livré le 02/07/2026 : `sia_ingestion/embed.py` (lots de 32, commit par lot — l'acquis survit aux échecs —, dimension 1024 contrôlée, vecteurs écrits par cast `::vector` sans dépendance Python pgvector, réutilise le client S1.5 via la dépendance workspace `sia-api`), 7 TU (95 au total). CA à cocher via `docs/plans-test/s2.2-embeddings.md` (exige la clé — pod).*

## S2.3 — RAG : recherche hybride (E2)

Critères d'acceptation :
- [x] BM25 (tsvector `french`) + similarité vectorielle (cosine pgvector), fusion des scores (RRF)
- [x] Filtres métadonnées : `est_reference = true` par défaut, filtre par projet (dossiers confirmés S1.11)
- [x] Endpoint api de recherche interne (consommé par E3, pas un écran) ; TU

*Code livré le 02/07/2026 : `api/sia_api/recherche.py` (`POST /recherche`, fusion RRF k=60 pure et testée, question vectorisée en float — gotcha S1.5 —, aucune source → avertissement anti-invention explicite), migration 0007 (index GIN français ; ivfflat différé à la vraie volumétrie). 8 TU (103 au total). CA à cocher via `docs/plans-test/s2.3-recherche-hybride.md`.*

**Note S2.4** : le rerank passe par l'endpoint `/v1/rerank` d'Albert, **hors périmètre du SDK OpenAI** — première action de la story : relever le schéma exact par curl sur le pod (à défaut, repli documenté sur l'ordre RRF avec signalement).

## S2.4 — RAG : rerank + assemblage du contexte (E2)

Critères d'acceptation :
- [x] Rerank des candidats via `openweight-rerank` (bge-reranker-v2-m3)
- [x] Assemblage : 8–15 chunks, budget total ≤ 20 000 tokens (gabarit + few-shot + chunks + brief)
- [x] Traçabilité : chaque chunk retenu porte document + section (citations obligatoires) ; signalement si aucune source récupérable

*Code livré le 02/07/2026 : `POST /contexte` (recherche hybride → rerank `/v1/rerank` — schéma albert-api en HYPOTHÈSE, étape 0 du plan le vérifie par curl — → assemblage cité). **Repli sûr** : rerank indisponible ⇒ ordre RRF conservé + `rerank_applique: false` + avertissement (jamais d'échec silencieux). Budget chunks : 6 000 tokens (part du ≤ 20k global, gabarit/few-shot/brief à part), 15 candidats max, le 1er chunk toujours servi même hors budget (tableau géant S2.1). 9 TU (112 au total). CA à cocher via `docs/plans-test/s2.4-rerank-contexte.md`.*

## S2.5 — E3.1 : machine à états du workflow + registre des hypothèses

Critères d'acceptation :
- [x] États = étapes 0→5 du prompt 3 ; « Oui » avance, « Non » itère sur place (règle 5) ; synthèse terminale
- [x] Registre des hypothèses persistant avec marquage d'origine A3 (corpus / po / modèle) ; **une validation d'étape ne lève JAMAIS une hypothèse** — décision individuelle uniquement (règle 3, A8)
- [x] Synthèse (étape 5) : récapitulatif des hypothèses non levées, transmis à l'export (E5/A8) ; refusée avant l'étape finale
- [x] Garde-fou règle 1 : contrôle « 3 questions max par lot » disponible pour le moteur ; TU sans DB réelle

*Code livré le 02/07/2026 : `sia_api/workflow.py` (machine PURE : transitions, extraction d'hypothèses via le marqueur S1.10, contrôle de lot), `sia_api/workflows.py` (sessions persistées : `POST/GET /workflows`, `/avancer`, `/hypotheses` + décision individuelle, `/synthese` avec avertissement A8), migration 0008 (3 tables, CHECK sur étapes/origines/statuts). 14 TU (126 au total). CA à cocher via `docs/plans-test/s2.5-workflow-etats.md`.*

## S2.6 — E3.2 : moteur conversationnel (Albert + RAG à chaque étape)

Critères d'acceptation :
- [x] `POST /workflows/{id}/message` : prompt 3 intégral en système + étape courante + contexte/NFR projet (E8) + extraits cités (`/contexte`, A2 : à chaque étape, question libre comprise) + few-shot (gold sinon repli silver JAMAIS présenté comme validé)
- [x] Réponses versées au fil (`workflow_messages`) ; [HYPOTHÈSE À VALIDER] extraites automatiquement vers le registre (origine `modele`, dédup textuelle v0)
- [x] Traçabilité A3 (sources mobilisées restituées) ; divergences corpus↔PO signalées `[DIVERGENCE]` avec source, arbitrées par le PO (A9)
- [x] Garde-fous : règle 1 signalée à l'interview, budget ~20k surveillé, réponse vide = 502 explicite, aucune source = avertissement ; TU Albert/RAG mockés

*Code livré le 02/07/2026 : `sia_api/moteur.py` (assemblage du prompt système testé, `max_tokens=4096` — gotcha raisonnement S1.5 —, historique borné à 8 messages + Feature). 12 TU (138 au total). **Première génération réelle = plan `docs/plans-test/s2.6-moteur.md`** (exige clé + base peuplée).*

## S2.7 — E5 : export CSV Jira + copier-coller formaté (récapitulatif A8)

Critères d'acceptation :
- [x] `GET /workflows/{id}/export/jira.csv` : CSV importable (Summary / Issue Type / Description), stories extraites des messages de rédaction, dédupliquées par titre (la dernière version gagne — itérations règle 5)
- [x] `GET /workflows/{id}/export/markdown` : copier-coller formaté avec **avertissement + récapitulatif des hypothèses non levées en tête** (arbitrage A8 — export autorisé mais jamais silencieux) et annotation de conformité S1.10 par story
- [x] Aucune story rédigée → 409 explicite ; pas d'appel API Jira (D10 : Jira injoignable du dev)

*Code livré le 02/07/2026 : `sia_api/export.py`, 8 TU (146 au total). Le CSV porte aussi l'en-tête `X-Hypotheses-Non-Levees`. CA à cocher via `docs/plans-test/s2.7-export.md` (après une session S2.6 réelle ayant produit des US).*

## S2.8 — E4.1 : écran de conversation du workflow (web DSFR)

Critères d'acceptation :
- [x] Accueil : sélection du projet + Feature collée → création de session (A6 : le projet porte ses dossiers confirmés)
- [x] Écran session : étape courante affichée (A5), fil de conversation, envoi de message (question libre comprise — A2), panneau **sources mobilisées** du dernier échange (A3), divergences A9 en alerte, avertissements affichés
- [x] Hypothèses : liste avec origine et statut, **décision individuelle Confirmer/Rejeter** (A8 rappelé à l'écran) ; validation d'étape Oui/Non (règle 5)
- [x] Exports E5 accessibles (proxy web → api) ; bandeau D15 sur toutes les pages ; **aucun JavaScript requis** (formulaires HTML) ; api injoignable → page/alerte lisible, jamais de traceback

*Code livré le 02/07/2026 : `sia_web/api_client.py` (SIA_API_URL, timeout 120 s, erreurs 599 lisibles), routes + gabarits Jinja (base DSFR CDN + styles de repli, index, session, erreur), endpoint api `GET /workflows/{id}/messages` ajouté pour le fil. v1 assumée : sources/avertissements affichés dans la réponse du POST (non persistés côté UI). 9 TU web + 1 TU api (156 au total). Restent pour E4 : écran projet complet (E4.2), écran « mes documents » + alerte couverture (E4.3, A5), note 1–5 + télémétrie (E4.4). CA à cocher via `docs/plans-test/s2.8-ui-conversation.md`.*

## S2.9 — E4.2 + E4.3 : écran projet (A6) et écran « mes documents » (A5)

Critères d'acceptation :
- [x] Écran projets : liste, création (nom, contexte, jusqu'à 3 NFR typées à la création — les 7 types E8), erreurs api lisibles (409 nom dupliqué affiché sur le formulaire)
- [x] Écran projet : détail (contexte, tableau NFR) + **association explicite projet ↔ dossiers (A6)** : suggestions S1.9 en cases à cocher avec nombre de documents (« elles ne valent pas association »), ajouts manuels visibles et décochables, dossier libre saisissable ; l'enregistrement passe par `PUT /projects/{id}` en préservant nom/contexte/NFR et les origines existantes (suggestion vs po)
- [x] Endpoints api : `GET /documents` (inventaire : statut de parsing, référence, doublon, projet suggéré) et `GET /documents/stats` (couverture = parsés/parsables, 1.0 si rien à parser)
- [x] Écran « mes documents » (A5) : état du corpus, inventaire avec statuts libellés (indexé/échec/OCR requis/en attente), **alerte « couverture faible » si couverture < 0,8** ; api injoignable → page lisible

*Code livré le 02/07/2026 : `sia_api/documents.py` (2 endpoints lecture seule sur la table `documents` de S1.7–S1.9), routes web `/projets`, `/projets/{id}`, `/projets/{id}/dossiers`, `/documents` + 3 gabarits Jinja + navigation dans `base.html`. Le volet conversationnel de l'alerte couverture (A5) est déjà porté par l'avertissement « aucune source récupérable » du moteur S2.6. 3 TU api + 7 TU web (166 au total). Reste pour E4 : note 1–5 + commentaire et télémétrie (E4.4). CA à cocher via `docs/plans-test/s2.9-ecrans-projet-documents.md`.*

## S2.10 — E4.4 : feedback par story (note 1–5) + télémétrie d'usage

Critères d'acceptation :
- [x] `POST /workflows/{id}/feedback` : note 1–5 (bornes contrôlées, 422 sinon) + commentaire par story ; `GET /workflows/{id}/stories` : titres des US produites (liste vide sans 409 tant que rien n'est rédigé)
- [x] Chaque validation Oui/Non d'étape est journalisée (`workflow_validations`) — matière première du taux d'édition
- [x] `GET /telemetrie` : les 3 indicateurs de CLAUDE.md en proxys v0 **assumés et affichés comme tels** (sans comptes A7 ni Jira D10) : actifs hebdo → sessions/semaine ; % stories conservées → part des notes ≥ 4 ; taux d'édition → part des « Non » (règle 5) ; aucune division par zéro sur base vide
- [x] Écran session : panneau « Noter les stories » (masqué sans US) ; écran « Télémétrie » ; navigation mise à jour

*Code livré le 02/07/2026 : migration 0009 (`story_feedbacks`, `workflow_validations`), `sia_api/feedback.py`, journalisation ajoutée à `/avancer`, panneau de notation + écran télémétrie côté web. 8 TU api + 1 TU journalisation + 5 TU web (180 au total). CA à cocher via `docs/plans-test/s2.10-feedback-telemetrie.md`.*

## S2.11 — E6 : harnais d'évals `make eval` (grille 3 axes)

Critères d'acceptation :
- [x] `make eval` : benchmark de génération sur `/evals/gold/` (repli `/evals/silver/` **affiché comme non validé** dans le rapport), modèles par défaut `openweight-large` vs `openweight-medium` (surchargables `MODELES=`), rapport markdown scoré (`SORTIE=` optionnel)
- [x] Grille 3 axes documentée (`evals/grille-notation.md`) avec proxys v0 automatiques : gabarit = validateur S1.10 (−0,2/violation) ; exactitude = règles métier du brief retrouvées + anti-invention (nombre non issu du brief hors ligne [HYPOTHÈSE À VALIDER] pénalisé) ; complétude = blocs remplis + ratio de CA vs référence
- [x] Brief reconstitué depuis la référence (récit, pré-requis, règles, attendus — jamais les CA) ; un modèle en échec ou une réponse vide n'arrête pas le banc (erreur portée au rapport) ; relevés latence/tokens par appel (préparation test de débit sous quotas)
- [ ] TU sans appel réseau (client injecté) ; recalibrage automatique sur gold dès fourniture

*Code livré le 02/07/2026 : `sia_api/evaluation.py` (CLI `--modeles/--max-cas/--sortie`), cible `make eval`, `evals/grille-notation.md`, README à jour. 17 TU (197 au total). Reste E6 : exécution réelle du banc (verdict comparatif) via `docs/plans-test/s2.11-harnais-evals.md` ; test de fenêtre de contexte effective déjà couvert par la sonde S1.5.*

## S2.12 — E3 : contrôle DoR/gabarit automatisé en sortie d'étape

Critères d'acceptation :
- [ ] En sortie des étapes de production (rédaction, contrôle DoR, synthèse), chaque US extraite de la réponse passe par `valider_us` (S1.10) ; toute non-conformité est signalée en avertissement avec le titre de l'US
- [ ] À l'étape 4, le **tableau DoR est isolé des tableaux de CA** puis passe par `valider_dor` : 10 critères présents, statuts valides, justifications remplies, « estimée et revue en backlog refinement » toujours 🔵 (l'estimation relève de l'équipe, jamais de l'IA)
- [ ] Le contrôle **signale, ne bloque jamais** (règle 5 : le PO arbitre) ; aucun contrôle aux étapes 0–2 ; TU purs + TU route (Albert/RAG mockés)

*Code livré le 03/07/2026 : `controler_conformite` + `_extraire_tableau_dor` dans `sia_api/moteur.py`, branchés sur `POST /workflows/{id}/message` (canal avertissements existant — affiché par l'UI S2.8 sans modification). 6 TU (203 au total). CA à cocher via `docs/plans-test/s2.12-controle-dor-auto.md` (dans la foulée du plan S2.6). **Le backlog macro côté code est complet** (E0→E6 + E8 ; E7 = post-go).*

## S2.13 — E3 : rapprochement décision d'interview ↔ registre A8 (« levée proposée »)

> Issue du réel (session de validation Onyxia, 06/07/2026) : une réponse d'interview du PO tranche souvent une [HYPOTHÈSE À VALIDER] déjà au registre, mais elle reste « en_attente » jusqu'à ce que le PO la retrouve et clique — bruit au récapitulatif A8 de l'export.

Critères d'acceptation :
- [ ] Les hypothèses **en attente** entrent au prompt système, numérotées (`#id`), avec la consigne de **proposer** la levée quand un message du PO ou un extrait cité la tranche : `[LEVÉE PROPOSÉE : #id — confirmée|rejetée — justification]`
- [ ] La proposition est persistée sur des colonnes dédiées (`statut_propose`, `justification_proposee`, `proposee_le` — migration 0010) : **le `statut` n'est JAMAIS modifié par le moteur** — la décision individuelle du PO reste le seul chemin de levée (invariant A8, vérifié par TU) ; identifiant halluciné ou déjà décidé → proposition ignorée
- [ ] Écran session : badge « Levée proposée » + justification à côté des boutons Confirmer/Rejeter (rappel « c'est vous qui décidez — A8 ») ; panneau du dernier échange : compteur des levées proposées
- [ ] TU purs (extraction du marqueur) + TU route (Albert/RAG mockés, invariant A8) + TU écran

*Code livré le 06/07/2026 : `extraire_levees_proposees` (pure, `sia_api/workflow.py`), registre en attente injecté au prompt + persistance des propositions (`sia_api/moteur.py`, `levees_proposees` dans la réponse), exposition dans `EtatSession` (`sia_api/workflows.py`), badge écran session. Migration 0010. 8 TU (220 au total). CA à cocher via `docs/plans-test/s2.13-rapprochement-a8.md` (exige clé + base — pod).*

## S2.14 — bascule du modèle de chat par défaut vers `openweight-medium` (à l'essai)

> Verdict E6 v0 (06/07/2026, `docs/eval-onyxia.md`) : `openweight-medium` **0,806** > `openweight-large` **0,498** — dérive de format de large corroborée en session réelle 8. Bascule **à l'essai** validée par le référent (« go pour la suite ») ; décision définitive au recalibrage gold.

Critères d'acceptation :
- [ ] `ALBERT_MODEL_CHAT` par défaut = `openweight-medium` partout où le défaut vit (`config.py`, `.env.example`, compose, exemple de Secret k8s, README) — **jamais en dur dans le code métier** (le moteur lit toujours `settings.albert_model_chat`)
- [ ] Réversibilité prouvée par TU : la surcharge `ALBERT_MODEL_CHAT=openweight-large` ramène large sans changement de code
- [ ] Le banc E6 (`make eval`) continue de comparer large vs medium par défaut — l'instrument de la décision définitive reste en place

*Code livré le 06/07/2026 : défaut basculé sur les 5 surfaces, TU du défaut recalées + TU de surcharge réorientée vers le chemin de retour (large). 220 tests verts. CA à cocher via `docs/plans-test/s2.14-modele-chat-medium.md` (probe + génération réelle + contre-épreuve de réversibilité — pod).*

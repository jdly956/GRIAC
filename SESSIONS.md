# SESSIONS.md — état stratégique & journal des sessions

> Journal inversé : l'entrée la plus récente en tête. Chaque session close ajoute une entrée (règle « MAJ documentation à chaque clôture de session », CLAUDE.md). L'en-tête « État stratégique » est recalé à chaque clôture.

## État stratégique

**Voie active** : **sprint 1 code-complet (11/11 stories, PRs #1–#14)** et **sprint 2 bien entamé : S2.1 (chunking), S2.2 (embeddings) et S2.3 (recherche hybride RRF) livrées (PRs #15–#17)** — la chaîne corpus → recherche citée est code-complète de bout en bout (hors lecture S3, snapshot MinIO attendu, prérequis §7). **S2.4 livrée (PR #18) : E2 est code-complet** — `POST /contexte` (rerank en hypothèse de schéma vérifiée à l'étape 0 du plan, repli RRF signalé, assemblage cité ≤ 6k tokens de chunks). **S2.5 livrée (PR #19) : E3.1 — machine à états du workflow** (étapes 0→5 persistées, registre des hypothèses avec origine A3, invariant A8 « une validation globale ne lève rien » vérifié par TU, synthèse = entrée de l'export E5). **Prochaine story : S2.6 (E3.2) — le moteur conversationnel** : Albert + prompt 3 + contexte projet/NFR + `/contexte` cité à chaque étape, divergences corpus↔PO (A9), few-shot silver, DoR automatisé via `valider_dor`. Squelettes dans `docs/sprint-2-backlog.md`. **Session Onyxia du référent (demain)** : dérouler la chaîne complète sur base réelle — service PostgreSQL du catalogue à lancer (aucun n'existe), puis migrations 0001→0006, plans S1.7, S1.8, S1.9, S2.1, S2.2, S1.11 (CRUD + A6), s'aider des plans `docs/plans-test/` ; **rotation de la clé Albert à confirmer** (incident session 10) ; CA2 S1.3 (protection de branche) ; réserve compose S1.2. S1.5 : **verdict no-go n°1 GO** (fenêtre gpt-oss-120b 131 072 ≫ budget 20k ; tpm 128k, **tpd 2,46 M = contrainte à surveiller** ; gotchas Albert consignés : max_tokens/raisonnement, **`encoding_format="float"` sur les embeddings SDK**). S1.3 : CI GitHub Actions démontrée verte sur la PR #6 ; **CA2 (protection de branche) = action référent en attente**. **S1.7 → S1.9, S1.11 et S1.6 mergées (PRs #7–#11)** — S1.6 avec job CI `helm-chart` vert (helm lint + template) dès le premier run. **Il ne reste au sprint 1 que S1.10** (templates structurés + validateur de conformité US). **En attente côté référent** : (1) **lancer un service PostgreSQL du catalogue Onyxia** (aucun n'a jamais existé — rectification session 10) puis dérouler la chaîne complète : migrations 0001→0005, plans S1.7 (scan), S1.8 (parsing, 1er run = téléchargement des modèles docling), S1.9 (qualification), S1.11 (CRUD + boucle A6) — commandes consolidées transmises en session ; (2) rendu helm S1.6 sur pod : **déjà validé ✅** (lint 0 failed, template réel 0 GPU) — reste le déploiement lab (prérequis : images poussées en registre) ; (3) CA2 S1.3 — protection de branche sur `main` ; (4) réserve compose S1.2 (mode A sur hôte Docker) ; (5) **rotation de la clé Albert à confirmer** (incident session 10). Les CA non cochés des stories mergées se cochent au fil de ces validations. **Découverte pod : `ALBERT_API_KEY` est injectée dans l'environnement du pod et prime sur le `.env`** (ALBERT_BASE_URL vient du `.env`). **NB : `make dev` exige un `.env` renseigné** (comportement voulu S1.4). Règle de méthode active : « TU + TNR + plan de test avant toute livraison » (CLAUDE.md). Réserve S1.2 (compose complet) inchangée — étape 7 des plans de test, au plus tard S1.6. Pod de dev : prendre un service `vscode-python` **sans GPU** ; checklist premier login (maxima CPU/RAM, MinIO — action n°7) toujours à consigner. Bascule de la branche par défaut sur `main` : à vérifier dans les settings GitHub.

**Réserves / dettes actées** : validation compose réelle (S1.2, voir ci-dessus) ; `pre-commit run --all-files` jamais exécuté de bout en bout (proxy des sessions Claude Code restreint ; hooks installés, config validée) — à jouer une fois sur le pod ; benchmark E6 et stories gold : statu quo (arbitrage du 02/07).

**Arbitrages du référent technique (02/07/2026)** : (1) le référent technique est désigné — c'est l'utilisateur de ces sessions ; (2) les 3 prompts SAFe sont fournis et versionnés ; (3) calendrier du benchmark E6 vs contenu du sprint 1 : statu quo pour l'instant, pas de décision ; (4) objectif 5–10 stories gold vs 3 silver disponibles : statu quo pour l'instant. **Cible fonctionnelle arbitrée en itération Q/R (9 arbitrages A1–A9, journal complet dans `docs/backlog-fonctionnel.md`)** — points saillants : le RAG est un mécanisme interne au service du LLM accompagnant (jamais une recherche autonome), mobilisé à chaque étape du workflow ; question libre conservée dans le fil ; transparence à 3 niveaux (citations inline, panneau sources avec extraits, marquage d'origine corpus/PO/modèle) ; divergences corpus↔PO signalées et arbitrées par le PO ; pas de jalon de démo intermédiaire (risque tunnel assumé) ; écran couverture + alerte conversationnelle ; PO autonome jusqu'à la sélection des dossiers documentaires de son projet ; instance partagée sans comptes au MVP ; export non bloquant avec récapitulatif des hypothèses. Amendements induits appliqués : note §4, CLAUDE.md (contexte, E3/E4/E5/E8, annexes), backlog sprint 1 (S1.9, S1.11). Plan S1.1/S1.2 validé (« ok go »).

**Prérequis en attente (note de cadrage §7)** : snapshot du corpus (PM) ; stories gold (extraction Jira et/ou validation des silver, avant fin sprint 1) ; panel des PO pilotes ; relevé des curseurs CPU/RAM et espace MinIO au premier login SSP Cloud (architecte). La clé Albert existe — le relevé des quotas est intégré à S1.5.

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

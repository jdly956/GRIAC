# Sprint 2 — Fin d'ingestion & RAG (E1 + E2) — squelette

> Squelette proposé par l'assistant (02/07/2026, instruction « continue à coder les features à venir ») — **à amender/prioriser par le référent**. Les CA déclinent les exigences des epics E1/E2 de CLAUDE.md. Mêmes règles que le sprint 1 : une story = une PR, TU + TNR + plan de test, validation stack-live.

## S2.1 — Chunking par sections (E1, nœud D)

Critères d'acceptation :
- [ ] Chunks par sections de titres, budget 500–800 tokens, chevauchement entre chunks consécutifs
- [ ] Tableaux jamais coupés — la règle prime sur le budget (un tableau géant reste entier)
- [ ] Table `chunks` (fil de titres pour la traçabilité des citations E2, sha256 pour la reprise D9) ; relance = documents inchangés sautés
- [ ] `make ingest-chunk` ; TU sur fonctions pures (sans DB réelle)

*Code livré le 02/07/2026 : `sia_ingestion/chunk.py` (blocs paragraphes/tableaux sous fil de titres, assemblage glouton, scission des paragraphes géants, chevauchement d'un bloc ≤ 150 tokens), migration 0006 (table chunks avec `embedding vector(1024)` NULL — préparée pour S2.2), 12 TU (88 au total). Tokens ≈ caractères/4 (POC, à recaler via E6 si écart). CA à cocher via `docs/plans-test/s2.1-chunking.md` sur base réelle.*

## S2.2 — Embeddings bge-m3 par lots (E1, nœud E)

Critères d'acceptation :
- [ ] Embeddings `openweight-embeddings` par lots ; `encoding_format="float"` (gotcha S1.5) ; clé via Settings S1.4
- [ ] Écriture pgvector dans `chunks.embedding` ; reprise : seuls les chunks sans embedding sont vectorisés
- [ ] Erreurs réseau/quotas gérées (lot en échec isolé, relance possible — embeddings de nuit D9 si quotas)
- [ ] `make ingest-embed` ; TU (Albert mocké)

*Code livré le 02/07/2026 : `sia_ingestion/embed.py` (lots de 32, commit par lot — l'acquis survit aux échecs —, dimension 1024 contrôlée, vecteurs écrits par cast `::vector` sans dépendance Python pgvector, réutilise le client S1.5 via la dépendance workspace `sia-api`), 7 TU (95 au total). CA à cocher via `docs/plans-test/s2.2-embeddings.md` (exige la clé — pod).*

## S2.3 — RAG : recherche hybride (E2)

Critères d'acceptation :
- [ ] BM25 (tsvector `french`) + similarité vectorielle (cosine pgvector), fusion des scores (RRF)
- [ ] Filtres métadonnées : `est_reference = true` par défaut, filtre par projet (dossiers confirmés S1.11)
- [ ] Endpoint api de recherche interne (consommé par E3, pas un écran) ; TU

*Code livré le 02/07/2026 : `api/sia_api/recherche.py` (`POST /recherche`, fusion RRF k=60 pure et testée, question vectorisée en float — gotcha S1.5 —, aucune source → avertissement anti-invention explicite), migration 0007 (index GIN français ; ivfflat différé à la vraie volumétrie). 8 TU (103 au total). CA à cocher via `docs/plans-test/s2.3-recherche-hybride.md`.*

**Note S2.4** : le rerank passe par l'endpoint `/v1/rerank` d'Albert, **hors périmètre du SDK OpenAI** — première action de la story : relever le schéma exact par curl sur le pod (à défaut, repli documenté sur l'ordre RRF avec signalement).

## S2.4 — RAG : rerank + assemblage du contexte (E2)

Critères d'acceptation :
- [ ] Rerank des candidats via `openweight-rerank` (bge-reranker-v2-m3)
- [ ] Assemblage : 8–15 chunks, budget total ≤ 20 000 tokens (gabarit + few-shot + chunks + brief)
- [ ] Traçabilité : chaque chunk retenu porte document + section (citations obligatoires) ; signalement si aucune source récupérable

*Code livré le 02/07/2026 : `POST /contexte` (recherche hybride → rerank `/v1/rerank` — schéma albert-api en HYPOTHÈSE, étape 0 du plan le vérifie par curl — → assemblage cité). **Repli sûr** : rerank indisponible ⇒ ordre RRF conservé + `rerank_applique: false` + avertissement (jamais d'échec silencieux). Budget chunks : 6 000 tokens (part du ≤ 20k global, gabarit/few-shot/brief à part), 15 candidats max, le 1er chunk toujours servi même hors budget (tableau géant S2.1). 9 TU (112 au total). CA à cocher via `docs/plans-test/s2.4-rerank-contexte.md`.*

## S2.5 — E3.1 : machine à états du workflow + registre des hypothèses

Critères d'acceptation :
- [ ] États = étapes 0→5 du prompt 3 ; « Oui » avance, « Non » itère sur place (règle 5) ; synthèse terminale
- [ ] Registre des hypothèses persistant avec marquage d'origine A3 (corpus / po / modèle) ; **une validation d'étape ne lève JAMAIS une hypothèse** — décision individuelle uniquement (règle 3, A8)
- [ ] Synthèse (étape 5) : récapitulatif des hypothèses non levées, transmis à l'export (E5/A8) ; refusée avant l'étape finale
- [ ] Garde-fou règle 1 : contrôle « 3 questions max par lot » disponible pour le moteur ; TU sans DB réelle

*Code livré le 02/07/2026 : `sia_api/workflow.py` (machine PURE : transitions, extraction d'hypothèses via le marqueur S1.10, contrôle de lot), `sia_api/workflows.py` (sessions persistées : `POST/GET /workflows`, `/avancer`, `/hypotheses` + décision individuelle, `/synthese` avec avertissement A8), migration 0008 (3 tables, CHECK sur étapes/origines/statuts). 14 TU (126 au total). CA à cocher via `docs/plans-test/s2.5-workflow-etats.md`.*

## S2.6 — E3.2 : moteur conversationnel (Albert + RAG à chaque étape)

Critères d'acceptation :
- [ ] `POST /workflows/{id}/message` : prompt 3 intégral en système + étape courante + contexte/NFR projet (E8) + extraits cités (`/contexte`, A2 : à chaque étape, question libre comprise) + few-shot (gold sinon repli silver JAMAIS présenté comme validé)
- [ ] Réponses versées au fil (`workflow_messages`) ; [HYPOTHÈSE À VALIDER] extraites automatiquement vers le registre (origine `modele`, dédup textuelle v0)
- [ ] Traçabilité A3 (sources mobilisées restituées) ; divergences corpus↔PO signalées `[DIVERGENCE]` avec source, arbitrées par le PO (A9)
- [ ] Garde-fous : règle 1 signalée à l'interview, budget ~20k surveillé, réponse vide = 502 explicite, aucune source = avertissement ; TU Albert/RAG mockés

*Code livré le 02/07/2026 : `sia_api/moteur.py` (assemblage du prompt système testé, `max_tokens=4096` — gotcha raisonnement S1.5 —, historique borné à 8 messages + Feature). 12 TU (138 au total). **Première génération réelle = plan `docs/plans-test/s2.6-moteur.md`** (exige clé + base peuplée).*

## S2.7 — E5 : export CSV Jira + copier-coller formaté (récapitulatif A8)

Critères d'acceptation :
- [ ] `GET /workflows/{id}/export/jira.csv` : CSV importable (Summary / Issue Type / Description), stories extraites des messages de rédaction, dédupliquées par titre (la dernière version gagne — itérations règle 5)
- [ ] `GET /workflows/{id}/export/markdown` : copier-coller formaté avec **avertissement + récapitulatif des hypothèses non levées en tête** (arbitrage A8 — export autorisé mais jamais silencieux) et annotation de conformité S1.10 par story
- [ ] Aucune story rédigée → 409 explicite ; pas d'appel API Jira (D10 : Jira injoignable du dev)

*Code livré le 02/07/2026 : `sia_api/export.py`, 8 TU (146 au total). Le CSV porte aussi l'en-tête `X-Hypotheses-Non-Levees`. CA à cocher via `docs/plans-test/s2.7-export.md` (après une session S2.6 réelle ayant produit des US).*

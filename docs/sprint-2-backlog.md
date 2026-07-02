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

## S2.3 — RAG : recherche hybride (E2)

Critères d'acceptation :
- [ ] BM25 (tsvector `french`) + similarité vectorielle (cosine pgvector), fusion des scores (RRF)
- [ ] Filtres métadonnées : `est_reference = true` par défaut, filtre par projet (dossiers confirmés S1.11)
- [ ] Endpoint api de recherche interne (consommé par E3, pas un écran) ; TU

## S2.4 — RAG : rerank + assemblage du contexte (E2)

Critères d'acceptation :
- [ ] Rerank des candidats via `openweight-rerank` (bge-reranker-v2-m3)
- [ ] Assemblage : 8–15 chunks, budget total ≤ 20 000 tokens (gabarit + few-shot + chunks + brief)
- [ ] Traçabilité : chaque chunk retenu porte document + section (citations obligatoires) ; signalement si aucune source récupérable

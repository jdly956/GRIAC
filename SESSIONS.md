# SESSIONS.md — état stratégique & journal des sessions

> Journal inversé : l'entrée la plus récente en tête. Chaque session close ajoute une entrée (règle « MAJ documentation à chaque clôture de session », CLAUDE.md). L'en-tête « État stratégique » est recalé à chaque clôture.

## État stratégique

**Voie active** : kickoff — repo initialisé, `main` créée (bascule en branche par défaut à faire dans les settings GitHub), méthode de travail intégrée à CLAUDE.md, cadrage livré : audit de cohérence (15 findings), 11 prérequis tracés, plan S1.1/S1.2 vérifié adversarialement et soumis au référent. Les 3 prompts SAFe sont déposés dans `/api/prompts/`. Prochaine étape : validation du backlog fonctionnel par le référent, puis validation du plan S1.1/S1.2 et implémentation (une story = une branche = une PR, depuis `main`).

**Arbitrages du référent technique (02/07/2026)** : (1) le référent technique est désigné — c'est l'utilisateur de ces sessions ; (2) les 3 prompts SAFe sont fournis et versionnés ; (3) calendrier du benchmark E6 vs contenu du sprint 1 : statu quo pour l'instant, pas de décision ; (4) objectif 5–10 stories gold vs 3 silver disponibles : statu quo pour l'instant. **Cible fonctionnelle arbitrée en itération Q/R (9 arbitrages A1–A9, journal complet dans `docs/backlog-fonctionnel.md`)** — points saillants : le RAG est un mécanisme interne au service du LLM accompagnant (jamais une recherche autonome), mobilisé à chaque étape du workflow ; question libre conservée dans le fil ; transparence à 3 niveaux (citations inline, panneau sources avec extraits, marquage d'origine corpus/PO/modèle) ; divergences corpus↔PO signalées et arbitrées par le PO ; pas de jalon de démo intermédiaire (risque tunnel assumé) ; écran couverture + alerte conversationnelle ; PO autonome jusqu'à la sélection des dossiers documentaires de son projet ; instance partagée sans comptes au MVP ; export non bloquant avec récapitulatif des hypothèses. Amendements induits appliqués : note §4, CLAUDE.md (contexte, E3/E4/E5/E8, annexes), backlog sprint 1 (S1.9, S1.11). Plan S1.1/S1.2 validé (« ok go »).

**Prérequis en attente (note de cadrage §7)** : snapshot du corpus (PM) ; stories gold (extraction Jira et/ou validation des silver, avant fin sprint 1) ; panel des PO pilotes ; relevé des curseurs CPU/RAM et espace MinIO au premier login SSP Cloud (architecte). La clé Albert existe — le relevé des quotas est intégré à S1.5.

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

**Validation stack-live** : sans objet (aucun code livré — documentation uniquement).

**Mini-récap** :
- ✅ Fait : repo initialisé et poussé ; méthode de travail dans CLAUDE.md ; SESSIONS.md créé
- ⏳ En cours : analyse de cadrage multi-agents (cohérence des docs, prérequis, plan S1.1/S1.2 vérifié)
- ⏳ À venir : validation du plan S1.1/S1.2 par le référent ; création de `main` (accord utilisateur requis) ; implémentation S1.1 puis S1.2

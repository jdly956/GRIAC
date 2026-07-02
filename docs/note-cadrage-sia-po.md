# Note de cadrage — Assistant IA de rédaction de user stories (SIA PO)

**Version 0.4 — 2 juillet 2026 — Statut : arbitrée en séance PM / architecte (19 décisions). v0.3 : gabarits internes intégrés (chaîne SAFe), entité Projet (D19). v0.4 : jeu d'évaluation « silver » en place, stories gold différées, statut des actions de semaine 0.**

## 1. Objet et opportunité

Outil interne d'aide aux Product Owners pour rédiger des user stories de qualité, ancrées sur la documentation projet par RAG avec citations sourcées. La génération suit le gabarit interne de l'organisation, produit les critères d'acceptation et un contrôle de Definition of Ready, puis s'exporte vers Jira. Le socle d'inférence est Albert API (DINUM) : modèles hébergés sur infrastructure souveraine certifiée SecNumCloud (Outscale), interface compatible OpenAI, modèles d'embedding, de reranking et OCR disponibles nativement. Le découpage automatique epic → feature est reporté en v2 ; la qualification du corpus est intégrée au pipeline d'ingestion sous forme minimale. La documentation d'Albert API indique par ailleurs qu'aucune trace des conversations envoyées aux modèles n'est conservée. Les gabarits internes existent aujourd'hui sous forme de trois prompts SAFe (cadrer l'Epic, découper en Features, rédiger les Stories) copiés manuellement dans des outils IA génériques : le SIA industrialise cette chaîne en y ajoutant l'ancrage documentaire par RAG, le contexte projet et les citations sourcées.

## 2. Journal des décisions

| N° | Décision | Implications / risques résiduels |
|----|----------|----------------------------------|
| D1 | Corpus public / interne non sensible | Offre mutualisée Albert API adaptée ; pas d'auto-hébergement d'OpenGateLLM |
| D2 | POC sur SSP Cloud (Onyxia/Insee), prod sur Outscale ou Scaleway | Conteneurisation dès le POC pour portabilité ; demande de clé Albert API à lancer immédiatement |
| D3 | MVP = rédaction assistée ancrée RAG ; découpage epic→feature en v2 | Qualification minimale du corpus maintenue comme prérequis qualité du RAG |
| D4 | Jira = cible d'intégration ; pas de plugin au MVP | Génération/validation dans l'app puis transfert vers Jira |
| D5 | Gabarits internes fournis : chaîne de 3 prompts SAFe (Epic → Features → Stories) avec interview par lots de 3 questions, marquage [HYPOTHÈSE À VALIDER] et contrôles DoR | Le MVP motorise le workflow du prompt 3 (stories) enrichi du RAG ; prompts 1–2 en v2 (cohérent avec D3). Gold différé : 3 candidates « silver » (entièrement marquées [HYPOTHÈSE À VALIDER]) servent de fixtures et de few-shot provisoire ; promotion en gold par validation des PO pilotes et/ou extraction Jira, attendue avant la fin du sprint 1 |
| D6 | KPI n°1 : adoption par les PO | Instrumentation de l'usage intégrée dès le POC |
| D7 | Corpus sur serveur de fichiers interne | POC sur snapshot déposé dans MinIO ; sync planifiée en prod ; métadonnées inférées (chemin, nom, dates), détection de versions |
| D8 | Formats Word / PDF | Parsing structuré (docling) + OCR Albert pour les PDF scannés ; chunking aligné sur les titres |
| D9 | Volumétrie 500–5 000 documents | Rescan complet nocturne avec reprise sur hash : seuls les fichiers modifiés sont re-parsés et re-vectorisés ; PostgreSQL + pgvector suffisant |
| D10 | Jira Data Center sur réseau interne | POC : copier-coller ou export CSV importable. Prod : agent connecteur déployé côté interne, flux HTTPS sortant uniquement, création des tickets via API Jira (PAT). Pattern à valider RSSI |
| D11 | Pipeline RAG dédié (vs RAG natif Albert) | Contrôle du chunking, des métadonnées et des citations ; coût de développement assumé |
| D12 | Développements réalisés par Claude Code | Référent technique humain requis (revue, secrets, exploitation, homologation) ; chantier « repo AI-ready » (cf. CLAUDE.md) |
| D13 | Homologation : processus connu, RSSI identifié | 3 jalons : avis sur l'outillage IA de dev, validation du pattern connecteur, dossier d'homologation avant prod |
| D14 | Repo privé | La validation RSSI de l'usage de Claude Code devient un **prérequis** (code d'État non public transitant par un service tiers). Secrets exclusivement en secrets Kubernetes |
| D15 | Données personnelles : hors périmètre MVP | Risque résiduel accepté par le PM. Mitigation à coût nul : ligne de garde dans l'UI + mention dans la charte d'usage des pilotes |
| D16 | Panel de 2 à 3 PO pilotes | Le seuil « ≥ 60 % d'adoption » perd son sens statistique : critère reformulé en usage hebdomadaire effectif de chaque pilote + verbatims |
| D17 | Pilote de 4 à 6 semaines avant go/no-go | Discipline de périmètre stricte ; benchmark des modèles intégré en semaine 1 |
| D18 | Notation continue par les PO | Feedback intégré à l'app sur chaque story générée (note 1–5 + commentaire) ; instrumente à la fois qualité et adoption |
| D19 | Entité Projet : le PO crée un projet et y associe un contexte et des NFR (performance, volumétrie, SSI, RGPD, accessibilité RGAA, disponibilité, auditabilité) | Contexte et NFR injectés dans l'interview et la génération (pré-remplissage des blocs NFR du gabarit, jamais levés silencieusement) ; le corpus est filtré par projet via la métadonnée D7 |

## 3. Architecture cible

Le même ensemble de conteneurs sert le POC et la production. Chaîne d'ingestion : snapshot (POC) ou synchronisation planifiée (prod) du serveur de fichiers vers un stockage objet S3 (MinIO sur Onyxia), puis parsing docling, OCR via Albert pour les PDF scannés, qualification minimale (projet, source, date, version inférée, statut, propriétaire, tag référence/obsolète), chunking par sections de titres (500–800 tokens, chevauchement, tableaux jamais coupés), vectorisation par lots via bge-m3 (alias openweight-embeddings, fenêtre d'entrée de 8 000 tokens), stockage PostgreSQL + pgvector, rescan nocturne avec reprise sur hash et rapport de couverture du corpus.

Chaîne de génération : le PO sélectionne son projet (contexte et NFR chargés, D19) et colle sa Feature → le moteur déroule le workflow du prompt 3 interne (interview par lots de 3 questions maximum, marquage [HYPOTHÈSE À VALIDER] jamais levé silencieusement, validation Oui/Non à chaque étape, contrôle DoR final) ; à chaque étape, recherche hybride (BM25 + vecteurs) filtrée par projet et statut = référence → reranker bge-reranker-v2-m3 → génération par le modèle de chat retenu à l'issue du benchmark (gpt-oss-120b vs Mistral-Small-3.2 en accès standard ; Mistral Medium, propriétaire, sous réserve d'un accompagnement ALLiaNCE), citations obligatoires vers les documents sources → validation par le PO avec notation → export. En production, authentification agent recommandée via ProConnect, et intégration Jira par l'agent connecteur interne (D10).

Dimensionnement du contexte : chaque requête mobilise 10 à 20 000 tokens (gabarit + few-shot ≈ 3 000, 8 à 15 chunks reclassés ≈ 6 000, brief du PO), très en deçà des fenêtres de classe 128 000 tokens annoncées par les fiches publiques de gpt-oss-120b et Mistral-Small-3.2. Le corpus entier ne transite jamais par le contexte : sa volumétrie est un enjeu de retrieval, traité par pgvector, la recherche hybride et le reranker. La fenêtre effectivement servie par le déploiement Albert sera vérifiée dès réception de la clé via GET /v1/models et l'objet limits de GET /v1/me/info.

## 4. Périmètre du MVP

Inclus : création de projets avec contexte et NFR associées (D19) ; workflow guidé de rédaction des stories conforme au prompt 3 interne (interview, hypothèses tracées, critères d'acceptation Gherkin, critères d'accessibilité DSFR, contrôle DoR), ancré par RAG avec citations ; question libre sur la documentation dans le fil de la rédaction, réponse sourcée — pas d'écran de recherche dédié : le RAG est un mécanisme interne mobilisé par le LLM pour accompagner le PO, jamais une recherche autonome (arbitrage A1 du 02/07/2026, cf. `backlog-fonctionnel.md`) ; feedback intégré (D18) ; export CSV compatible import Jira ; pipeline d'ingestion avec qualification minimale et rapport de couverture du corpus.

Exclus : prompts 1 et 2 de la chaîne (cadrage d'Epic, découpage en Features), reportés en v2 ; plugin Jira ; intégration API Jira temps réel (prod uniquement) ; traitement de données personnelles ; multi-organisations.

## 5. Prérequis et risques

Prérequis avant développement : clé d'accès Albert API (demande en ligne ouverte aux agents de la fonction publique d'État, identifiants annoncés sous 24 h, gestion des clés via le playground) ; relevé des quotas réels (TPM/TPD) via GET /v1/me/info pour dimensionner le pilote et l'indexation initiale ; avis RSSI sur l'usage de Claude Code (prérequis, D14) ; désignation du référent technique humain ; stories gold standard (différées : extraction Jira et/ou promotion des candidates silver, attendues avant le benchmark) ; snapshot du corpus ; comptes SSP Cloud des intervenants ; abonnement Claude Code (modalités : docs.claude.com).

Risques principaux : qualité hétérogène du corpus (versions multiples sur le serveur de fichiers) mitigée par la détection de versions et le rapport de couverture ; adoption insuffisante mitigée par la co-construction avec les pilotes et la notation continue ; quotas Albert insuffisants pour le pilote, à lever dès la semaine 0. Filet de sécurité structurel : la compatibilité OpenAI garantit l'absence de lock-in — bascule possible vers OpenGateLLM auto-hébergé si le benchmark de semaine 1 était défavorable (décision de repli, hors périmètre POC).

## 6. Protocole d'expérimentation et go/no-go

Semaine 1 : mise en place et benchmark des modèles de chat, grille de notation à trois axes (conformité au gabarit, exactitude par rapport à la documentation, complétude des critères d'acceptation) ; démarrage sur les candidates silver pour les axes conformité et complétude, recalibrage sur les stories gold dès leur fourniture — l'axe exactitude requiert de toute façon le snapshot du corpus. Deux tests no-go techniques s'y ajoutent : fenêtre de contexte effectivement servie (test d'aiguille sur vos documents réels) et débit d'embeddings soutenable sous les quotas TPM/TPD (annexe A, nœud F). Semaines 2 à 6 : pilote avec les 2–3 PO, notation continue en application, revue hebdomadaire des verbatims.

Critères de go (n = 2–3, lecture qualitative assumée) : chaque pilote utilise l'outil chaque semaine sans relance ; au moins la moitié des stories générées sont conservées, même éditées ; note qualité moyenne ≥ 3,5/5 ; verbatims majoritairement favorables ; aucun incident de sécurité. La décision go/no-go est documentée et conditionne l'engagement des chantiers de production (homologation, connecteur Jira, hébergement Outscale/Scaleway).

## 7. Actions immédiates (semaine 0)

1. ✅ Clé Albert API obtenue — reste le relevé des quotas réels via GET /v1/me/info (intégré à la story S1.5).
2. ✅ Avis RSSI favorable sur l'usage de Claude Code — reste la pré-validation du pattern connecteur Jira (jalon prod).
3. ⏳ PM : désignation nominative du référent technique humain.
4. ✅ Gabarits fournis (trois prompts SAFe). ⏳ Stories gold différées : extraction Jira et/ou validation des candidates silver par les PO pilotes, avant la fin du sprint 1.
5. ⏳ PM : constitution du snapshot du corpus (dossier représentatif du serveur de fichiers).
6. ✅ Prêt à lancer : initialisation du repo par Claude Code — backlog sprint 1 disponible (S1.1 → S1.11).
7. ⏳ Architecte : au premier login SSP Cloud, relever les maxima des curseurs CPU/RAM et l'espace MinIO disponible (annexe A).

## Annexe A — Estimation capacitaire SSP Cloud (mode DAG)

Hypothèses (scénario haut de fourchette, à ajuster après inventaire) : 5 000 documents, ~30 pages en moyenne soit 150 000 pages, 20 % de PDF scannés, ~400 tokens/page soit ~60 M tokens, chunks de 600 tokens soit ~120 000 chunks, embeddings bge-m3 en dimension 1024. Le dimensionnement varie linéairement avec la volumétrie réelle.

DAG d'ingestion : A liste S3 → B parse natifs (docling) ∥ C OCR scannés → D qualification (hash, versions, métadonnées) → E chunking → F embeddings (Albert) → G chargement pgvector → H rapport de couverture. Chaque nœud est un job conteneurisé idempotent (reprise sur hash), lancé à la demande sur Onyxia puis libéré.

| Nœud | Ressources | Durée estimée (scénario haut) |
|------|------------|-------------------------------|
| B parse natifs | job 8 vCPU · 16 Go | 2–6 h selon le mix docx/pdf |
| C OCR (30 000 p.) | 4 vCPU · 8 Go, ou endpoint OCR Albert | ~2 h en local |
| D+E qualification + chunking | 2 vCPU · 4 Go | < 30 min |
| F embeddings 60 M tokens | client léger ; borné par les quotas TPM/TPD Albert | ≈ tokens/(TPM×60) : 2–10 h, à étaler sur 1–3 nuits si TPD contraint |
| G pgvector | service 2 vCPU · 8 Go · 20 Go disque | index en minutes ; base ~3–5 Go |
| Services permanents (API + web + PostgreSQL) | ~5 vCPU · 13 Go cumulés | durée du POC |
| Stockage MinIO | ~25–30 Go (snapshot + dérivés) | — |
| GPU | aucun (inférence déportée sur Albert) | — |

Verdict : besoins très en deçà des capacités d'une plateforme de calcul à la demande ; le facteur limitant du DAG est le nœud F (quotas Albert), pas le SSP Cloud. Fair-use d'une plateforme mutualisée gratuite : jobs libérés après exécution, embeddings de nuit. Vérifications de 5 minutes au premier login : maxima des curseurs CPU/RAM d'un service et espace MinIO effectivement disponible.


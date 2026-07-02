# Backlog fonctionnel SIA PO — cible v2 (arbitrée en séance de cadrage avec le référent technique, 02/07/2026)

**Statut : v2.0 — consolide les 9 arbitrages rendus en itération Q/R (journal en §5). Soumis à validation finale (Oui/Non) avant versionnement dans `/docs` et amendement des documents fondateurs.**

---

## 1. L'Epic (au sens du prompt 1)

**# Assistant IA de rédaction de user stories (SIA PO)**

**CONTEXTE & PROBLÈME**
- Besoin : les PO copient manuellement trois prompts SAFe dans des outils IA génériques, sans ancrage sur la documentation projet — les gabarits existent, l'industrialisation manque.
- Enjeux : qualité des user stories, efficacité des PO, fiabilité (anti-invention), souveraineté (Albert API).
- En une phrase : les stories produites aujourd'hui ne sont pas systématiquement ancrées sur la documentation projet, et le workflow de qualité (interview, hypothèses, DoR) dépend de la discipline individuelle de chaque PO.

**QUI EST IMPACTÉ** : Product Owners de l'organisation (pilote : 2–3 PO, D16).

**IMPACT ATTENDU** : stories conformes au gabarit, plus rapides à produire, ancrées et sourcées ; backlog de meilleure qualité en refinement ; adoption = KPI n°1 (D6).

**RISQUE SI NON TRAITÉ** : impact opérationnel — perte de temps, qualité hétérogène, hypothèses non tracées.

**PRINCIPE DIRECTEUR (arbitrage A1)** : le PO n'interroge pas la documentation ; c'est le LLM qui la mobilise, via le RAG, pour accompagner le PO dans l'explicitation et la rédaction de son besoin. La recherche documentaire est un mécanisme interne (Feature Rouge), jamais une fonctionnalité de recherche autonome.

**CRITÈRES D'ACCEPTANCE (macro-capacités, format « [acteur] peut [action] »)**
- **MC1** — Le PO peut créer son **projet** en autonomie complète : contexte libre, NFR typées, **et sélection des dossiers documentaires associés** parmi ce qui est indexé (A6).
- **MC2** — Le PO peut **rédiger ses user stories accompagné à chaque étape** du workflow du gabarit interne (étapes 0→5 du prompt 3) par un LLM qui mobilise la documentation du projet **à chaque tour** (A2) : restitution de la Feature enrichie du contexte documentaire, propositions d'interview sourcées quand la doc le permet, rédaction et contrôle DoR ancrés.
- **MC3** — Le PO peut poser une **question libre sur sa documentation dans le fil de la conversation** de rédaction ; la réponse cite ses sources. Pas d'écran de recherche dédié (A1) [HYPOTHÈSE À VALIDER : forme exacte à confirmer avec la maquette E4].
- **MC4** — Le PO peut **noter (1–5) et commenter** chaque story générée (D18).
- **MC5** — Le PO peut **exporter ses stories vers Jira** (CSV importable, copier-coller formaté) ; si des [HYPOTHÈSE À VALIDER] ne sont pas levées, l'export est autorisé **avec avertissement et récapitulatif des hypothèses restantes** joint (A8).
- **MC6** — Le PO peut **voir ce que l'assistant connaît de son projet** : écran des documents avec statut (indexé, référence, obsolète, échec de parsing) **et** signalement dans la conversation quand la couverture est faible (A5).

**EXIGENCES TRANSVERSES DE TRANSPARENCE (A3)** — s'appliquent à toute production de l'assistant :
1. Citations inline (document + section) au fil des propositions.
2. Panneau « sources mobilisées » par étape, extrait exact consultable.
3. **Marquage d'origine de chaque élément** : issu du corpus (cité) / déclaré par le PO / proposé par le modèle sans source ([HYPOTHÈSE À VALIDER]). Le registre anti-invention est rendu visible.
4. **Détection de divergence (A9)** : quand une déclaration du PO contredit le corpus, l'assistant le signale, cite la source, et demande au PO d'arbitrer — le PO reste l'auteur.

**INDICATEURS DE SUCCÈS** (note §6) : usage hebdomadaire effectif de chaque pilote sans relance ; ≥ 50 % des stories conservées ; note moyenne ≥ 3,5/5 ; verbatims favorables ; zéro incident sécurité.

**ACCÈS AU MVP (A7)** : instance partagée sans comptes — les 2–3 PO pilotes voient tous les projets. ProConnect en prod uniquement (E7). *Point de vigilance : le critère de go « chaque pilote utilise l'outil chaque semaine » ne sera pas mesurable par la télémétrie seule sans attribution — porté par la revue hebdomadaire des verbatims (§6) [HYPOTHÈSE À VALIDER : champ optionnel « votre nom » sur le feedback si besoin].*

---

## 2. Les Features (au sens du prompt 2)

### Features Bleu — valeur directe pour le PO

| ID | Titre (orienté bénéfice) | Intention (1 phrase) | MC | Portée par |
|---|---|---|---|---|
| F1 | Gérer mes projets et leur périmètre documentaire | Le PO crée son projet, décrit contexte et NFR, et choisit les dossiers documentaires associés ; toutes les générations en tiennent compte. | MC1 | E8 (+ S1.11) |
| F2 | Rédiger mes stories, accompagné et ancré à chaque étape | Le PO colle sa Feature ; l'assistant déroule le workflow du prompt 3 en mobilisant la doc à chaque tour, origine de chaque élément tracée, divergences signalées. | MC2 (+A3, A9) | E3 — s'appuie sur E1, E2, E8, S1.10 |
| F3 | Poser une question libre dans le fil | À tout moment de la conversation, le PO demande « que dit la doc sur… » et obtient une réponse sourcée. | MC3 | E2 + E3 (même moteur que F2, pas d'écran dédié) |
| F4 | Évaluer et améliorer l'assistant | Note 1–5 + commentaire par story ; télémétrie d'usage (actifs hebdo, % conservées, taux d'édition). | MC4 | E4 (D18) |
| F5 | Transférer mes stories vers Jira | Export CSV / copier-coller, avec récapitulatif des hypothèses non levées. | MC5 | E5 (MVP) ; E7 (prod) |
| F6 | Savoir ce que l'assistant connaît | Écran « mes documents » (statuts) + alerte conversationnelle de couverture faible. | MC6 | E1 nœud H + E4 |

### Features Rouge — enablers techniques (invisibles du PO, indispensables)

| ID | Titre | Intention | Portée par |
|---|---|---|---|
| R1 | Socle d'exécution | Conteneurs, dev, config/secrets, CI, déploiement Onyxia. | E0 (S1.1–S1.6) |
| R2 | Connaissance documentaire | Scan, parsing, qualification (versions/brouillons/doublons), chunking, vectorisation du corpus. | E1 (S1.7–S1.9, puis sprint 2) |
| R3 | Recherche fiable et sourcée | Hybride BM25+vecteurs, reranking, assemblage du contexte avec traçabilité — le moteur d'ancrage de F2/F3, appelé à chaque tour (A2). | E2 |
| R4 | Gabarits motorisés | 3 prompts SAFe versionnés, templates structurés, validateur de conformité. | S1.10 |
| R5 | Choisir et surveiller le bon modèle | Benchmark grille 3 axes, tests no-go (fenêtre effective, débit embeddings). | E6 + S1.5 |
| R6 | Accès et intégration de production | ProConnect, connecteur Jira interne. | E7 (post go) |

**Règle de lecture** : une Feature Bleu n'est démontrable que quand ses Rouge sont posées (E0→E1→E2→E3).

---

## 3. Jalons et sprint 1 relus fonctionnellement

**Jalon de démonstration (A4)** : pas de jalon intermédiaire — la première démo aux PO pilotes est le **workflow complet de rédaction accompagnée** (F2 minimal : E1+E2+E3+E8+E4 minimal). *Risque assumé, tracé : tunnel sans feedback pilote jusqu'à ce point ; le « pilote semaines 2–6 » de la note glissera d'autant (statu quo calendaire arbitré le 02/07).*

Le sprint 1 (S1.1–S1.11) reste un sprint d'enablers presque pur (R1, amorce de R2, R4, modèle de données de F1) — conforme au prompt 2 : les prérequis techniques sont des Features Rouge légitimes et explicites.

**Retouches induites sur les stories du sprint 1** (à reporter au backlog sprint) :
- **S1.9** : l'inférence de la métadonnée `projet` (1er niveau du chemin) devient une **suggestion** ; l'association faisant foi est celle confirmée par le PO (A6).
- **S1.11** : ajouter l'**association explicite projet ↔ dossiers documentaires** (table dédiée, éditable) au modèle de données — tranche le finding d'audit sur le mapping.

---

## 4. Conséquences pour les epics techniques (specs enrichies)

| Epic | Exigences nouvelles issues des arbitrages |
|---|---|
| E2 | Recherche appelée à chaque tour de conversation (A2) — latence et quotas à confirmer par S1.5/E6 ; traçabilité de l'extrait exact (A3.2). |
| E3 | Marquage d'origine de chaque élément généré (corpus/PO/modèle — A3.3) ; détection et signalement des divergences corpus↔PO (A9) ; question libre dans le fil (F3) ; récapitulatif des hypothèses à l'export (A8). |
| E4 | Panneau « sources mobilisées » avec extraits (A3.2) ; écran « mes documents » + alerte couverture (A5) ; écran projet avec sélection des dossiers (A6) ; pas de gestion de comptes (A7). |
| E5 | Export avec avertissement + récapitulatif des hypothèses non levées (A8). |
| E8 | Association projet↔dossiers sélectionnée par le PO, l'inférence S1.9 en suggestion (A6). |

---

## 5. Journal des arbitrages fonctionnels (référent technique, 02/07/2026)

| # | Question | Arbitrage |
|---|---|---|
| A1 | Mode Q&A documentaire | Conservé, subordonné à l'accompagnement : question libre dans le fil, pas d'écran dédié ; le RAG est un mécanisme interne au service du LLM accompagnant |
| A2 | Où le LLM mobilise la doc | À chaque étape du workflow (étape 0, interview, rédaction, DoR) |
| A3 | Visibilité de l'ancrage | Citations inline + panneau sources avec extraits + marquage d'origine de chaque élément |
| A4 | Premier jalon démontrable | Pas de jalon intermédiaire : démo au workflow complet (risque tunnel assumé) |
| A5 | Couverture documentaire | Écran documents/statuts + alerte conversationnelle de couverture faible |
| A6 | Autonomie projet | PO autonome de bout en bout, y compris sélection des dossiers documentaires |
| A7 | Accès MVP | Instance partagée sans comptes, tous les projets visibles de tous |
| A8 | Export avec hypothèses non levées | Autorisé, avec avertissement + récapitulatif joint |
| A9 | Divergence corpus ↔ PO | Signalée avec source, arbitrage laissé au PO |

**Hypothèses restantes** : forme exacte de la question libre dans le fil (maquette E4) ; attribution du feedback sans comptes (champ nom optionnel ?) ; exposition détaillée de l'écran couverture (champs exacts).

**Amendements induits des documents fondateurs** (à faire après validation) : note §4 (reformuler « mode Q&A » en « question libre dans le fil de la rédaction ») ; CLAUDE.md contexte (idem) ; backlog sprint 1 (S1.9, S1.11 — §3 ci-dessus).

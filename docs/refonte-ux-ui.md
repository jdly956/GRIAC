# Refonte UX/UI — spécification cible et plan de mise en œuvre

> Produit de la session du 07/07/2026 (branche `claude/ux-ui-ergonomie-refonte-fggyen`).
> Démarche en deux étapes demandée par le PO : **(1)** rôle UX/UI — audit de l'existant puis
> interview du PO par lots de questions (à la manière du gabarit prompt 3) ; **(2)** développement
> avec validation des hypothèses par le PO. Ce document est le livrable de l'étape 1.
> Maquette navigable associée : `docs/maquettes/refonte-ux-ui.html` (3 écrans, données fictives).

## 1. Audit de l'existant (07/07/2026, après merge PR #35/#36 — 302 tests)

**Socle commun** (`web/sia_web/templates/base.html`)

- DSFR chargé par CDN mais employé superficiellement : classes `fr-btn`/`fr-input`/`fr-alert`
  posées sur du HTML maison ; pas de véritable en-tête DSFR, pas de grille, pas de composants
  navigation/accordéon ; styles ad hoc (`.panneau` gris uniforme).
- Navigation = 5 liens texte séparés par des `·`, sans état actif.
- Bandeau d'alerte « données personnelles » (D15) pleine largeur répété sur chaque page —
  il écrase la hiérarchie visuelle.
- Une seule colonne de 60 rem quel que soit l'écran.

**Écran session** (le cœur du produit) — page-fleuve d'une dizaine de blocs empilés :
titre + conso, panneau « Dernière réponse », **3 formulaires d'action séparés**
(message / story suivante / valider), registre d'hypothèses replié, fil coupé en deux
(4 derniers messages + anciens repliés, dernière réponse affichée en double), puis
4 blocs repliés (notation, édition/copie des stories, gestion session, export).
`hx-boost` remplace la page entière : pas de sensation de conversation.

**Constats des sessions réelles** (9, 11, 12) : « navigation lourde, aller-retours »,
16 hypothèses en attente non traitées en fin de session 12, actions dispersées.

**Autres écrans** : accueil qui met la création avant la reprise ; « Mes documents » dense,
inventaire à plat alors que le **dossier** est devenu la clé d'association A6 ; projets sans
édition après création ; fiche document riche mais brute ; télémétrie/paramètres bruts.

**Acquis à préserver** (lot pré-pilote S3.6→S3.14) : rendu markdown, anti double-envoi,
traçabilité A3 avec extrait exact borné (S3.20), levées proposées (S2.13) et lot relu (S3.21),
progressive enhancement sans JavaScript, htmx vendoré.

## 2. Journal des arbitrages UX (interview PO du 07/07/2026 — 3 lots, 12 décisions)

| # | Question | Arbitrage PO |
|---|----------|--------------|
| UX1 | Irritants prioritaires | **Les 4 confirmés** (session surchargée, aller-retours, manque de dynamisme, hiérarchie faible) + vision cible : **fenêtre principale de chat dynamique + panneaux latéraux fixes** (résultat des éditions/stories, sources, hypothèses) ; **sélection en masse des hypothèses** ; les **US sont le livrable final** → section dédiée avec plier/déplier par US, notation intégrée, **markdown correctement mis en forme** ; navigation des autres onglets à revoir ; **suppression/archivage** des sessions, projets et documents |
| UX2 | Matériel cible pilote | **Mixte laptop + grand écran** → layout adaptatif (rail visible en large, repliable/dessous en étroit) |
| UX3 | Périmètre | **Toute l'app, homogène** (les 8 écrans) |
| UX4 | Toujours visible pendant la rédaction | **Les 4** : étape + progression, hypothèses en attente, zone de saisie + actions, stories produites |
| UX5 | Organisation du rail latéral | **Panneaux empilés à droite** (Stories / Hypothèses / Sources visibles simultanément, repliables individuellement) — pas d'onglets |
| UX6 | Sens du fil | **Chat classique** : chronologique, nouveaux messages en bas, auto-scroll, saisie fixe en bas de colonne |
| UX7 | Dynamisme de génération | **Réponse d'un bloc + indicateur** (« l'assistant rédige… », boutons désactivés) — pas de streaming SSE au MVP |
| UX8 | Cycle de vie des objets | **Archiver + supprimer** (sessions, projets : archivage réversible ET suppression définitive confirmée) ; documents : suppression existante (S3.17) + **« marquer obsolète »** (exclu de la recherche sans destruction) |
| UX9 | Navigation principale | **4 entrées** : Sessions · Projets · Documents · **Suivi & réglages** (télémétrie + paramètres fusionnés) — état actif + fil d'Ariane |
| UX10 | Accueil | **Reprise d'abord** : liste des sessions en tête (badges étape, actions), « + Nouvelle session » ouvre le formulaire |
| UX11 | Bandeau D15 | **Notice discrète 1 ligne** sur toutes les pages + rappel micro près de la zone de saisie (l'obligation d'affichage D15 est tenue) |
| UX12 | Priorité si le temps se resserre | **Session + socle d'abord** (vague 1), puis accueil/documents/projets (vague 2), puis suivi & réglages/fiche document (vague 3) |
| UX13 | Validation de la maquette (go étape 2) | **« En phase, mais conformité DSFR obligatoire »** : l'implémentation utilise les composants DSFR officiels partout où ils existent (`fr-header`, `fr-nav`, `fr-notice`, `fr-breadcrumb`, `fr-stepper`, `fr-accordion`, `fr-badge`, `fr-btn`, `fr-table`, `fr-tag`, `fr-tile`…) et les tokens DSFR pour les rares parties sans composant natif (bulles du chat) ; le JS DSFR est chargé (les composants interactifs en dépendent). La maquette HTML n'est qu'une approximation visuelle assumée — l'implémentation fait foi |

## 3. Cible par écran

### 3.1 Socle commun (tous les écrans)

- En-tête DSFR compact : marque + baseline, navigation 4 entrées avec **état actif**
  (`aria-current="page"`), fil d'Ariane sur les sous-pages (session, fiche document, projet).
- Notice D15 fine (1 ligne, type `fr-notice`) sous l'en-tête — remplace l'alerte pleine largeur.
- Gabarit de page unique (largeur max ~96 rem pour les écrans applicatifs), cartes DSFR,
  badges sémantiques homogènes (statuts documents, étapes, hypothèses).
- Thèmes clair/sombre DSFR (`data-fr-scheme="system"` déjà en place).

### 3.2 Écran session (vague 1 — le cœur)

Structure en deux zones sous une **barre de session** :

- **Barre de session** (sticky) : retour Sessions, titre (renommable), **stepper d'étape**
  (segments 0→5 + libellé, badge A5 fidèle), modèle actif + conso compacte,
  actions : Exporter CSV / Copier markdown (avertissement A8 conservé), Renommer, Archiver.
- **Colonne chat** (principale) : fil **chronologique complet** à défilement interne,
  bulles PO (droite) / assistant (gauche), markdown rendu, sources par message repliées
  avec extrait exact (A3), divergences A9 et avertissements inline ; **composeur** en bas :
  rangée d'actions d'étape compacte (« Story suivante » aux étapes de production,
  « Valider l'étape — Oui / Non+commentaire » avec commentaire révélé à la demande),
  textarea + Envoyer, micro-rappel D15. Pendant la génération : bulle
  « l'assistant rédige… » + boutons désactivés ; la réponse arrive d'un bloc et les
  panneaux du rail se mettent à jour dans la foulée.
- **Rail droit** (~400 px, sticky, défilement propre ; passe sous le chat en écran étroit),
  3 panneaux empilés repliables :
  1. **Stories produites** (le livrable) : une entrée pliable par US — titre + badges
     (DoR, éditée, note), corps markdown rendu, **notation 1–5 + commentaire intégrés**,
     Éditer (textarea, la version éditée gagne à l'export), Copier ;
  2. **Hypothèses** : compteur « N en attente », liste avec origine
     (corpus / déclaré PO / modèle), levées proposées (S2.13) affichées,
     **cases à cocher + « Confirmer/Rejeter la sélection » + « Tout sélectionner »**,
     bouton « Appliquer les levées proposées (relues) » (S3.21) conservé,
     décision individuelle conservée — **A8 intact : chaque levée est un geste explicite du PO** ;
  3. **Sources de la dernière réponse** : document + section + extrait exact consultable ;
     l'historique complet reste dans le fil, message par message.
- Disparaissent : le panneau « Dernière réponse » dupliqué, les blocs bas de page
  (notation, édition, gérer, export) — leurs fonctions migrent dans le rail et la barre.

### 3.3 Accueil (vague 2)

Liste des sessions **en premier** (tableau : titre, badge étape, projet, dernière activité,
nb stories, actions Renommer/Archiver/Supprimer), « + Nouvelle session » proéminent qui
déplie le formulaire (projet + Feature collée), lien « Voir les sessions archivées (N) ».

### 3.4 Mes documents (vague 2)

- **Tuiles d'état** (documents, indexés, couverture %, échecs) — l'alerte couverture < 0,8 (A5) reste.
- Barre d'actions : Déposer (dossier obligatoire — S3.18), Indexer maintenant (quota),
  historique des runs replié (le suivi nœud par nœud existant y vit).
- **Inventaire regroupé par dossier** (la clé A6), avec le(s) projet(s) associé(s) affiché(s) ;
  par document : statut en badge, version/taille, actions Fiche / Original / **Obsolète** / Supprimer.

### 3.5 Projets & fiche projet (vague 2)

Liste + création conservées ; fiche : **édition du contexte et des NFR après création**,
association des dossiers A6 inchangée sur le fond (cases + compte de documents),
archivage/suppression du projet (voir H9).

### 3.6 Suivi & réglages (vague 3)

Une page à deux sections ancrées : Télémétrie (indicateurs + jauge tpd) et Paramètres
(modèle). Fiche document : alignée sur le socle (badges, fil d'Ariane) sans refonte de fond.

## 4. Registre des hypothèses à valider (étape 2 — avec le PO)

> À la manière du produit : rien n'est levé silencieusement. Chaque hypothèse est soumise
> au PO par lots pendant le développement ; celles marquées ⚙ engagent l'API ou une migration.

| # | Hypothèse | Statut |
|---|-----------|--------|
| H1 | Rail droit ~400 px dès ~1180 px de large ; en dessous il passe **sous** le chat (panneaux repliables). Pas d'optimisation mobile dédiée au MVP | à valider |
| H2 | Le fil charge l'**historique complet** (défilement interne) — plus de bloc « voir les N échanges précédents » ; poids maîtrisé car extraits bornés (S3.20) | à valider |
| H3 | Le panneau « Dernière réponse » disparaît (remplacé par le chat + le rail Sources) | à valider |
| H4 | Les 3 formulaires fusionnent dans le composeur ; le commentaire « Non — itérer » se révèle à la demande (toujours visible sans JavaScript — repli) | à valider |
| H5 | ⚙ Sélection en masse = nouvel endpoint `POST /workflows/{id}/hypotheses/decider-lot` (liste d'ids + statut unique, refus si vide) — distinct du lot « levées proposées » S3.21 qui reste ; jamais de statut inventé (A8) | à valider |
| H6 | Le panneau Sources du rail montre la **dernière réponse** seulement ; l'historique par message reste dans le fil (A3) | à valider |
| H7 | ⚙ Dynamisme = htmx **ciblé avec routes fragments** (le message s'ajoute au fil, panneaux mis à jour en out-of-band) — revient sur le choix « zéro route fragment » de S3.8, assumé ; repli sans JS = POST pleine page | **validée PO (07/07)** |
| H8 | Stepper : 6 segments + libellé, libellés = ceux de la machine à états réelle | à valider |
| H9 | ⚙ Suppression d'un projet : les sessions existantes survivent (référence projet → NULL, « projet supprimé » affiché). Alternative : blocage tant que des sessions non archivées y sont liées | **tranchée PO (07/07) : suppression libre** — sessions orphelines assumées (badge « projet supprimé », le moteur continue sans contexte/NFR projet) |
| H10 | ⚙ « Marquer obsolète » un document = exclusion des recherches (filtre statut) sans destruction, réversible — champ/statut à vérifier en base (migration si absent) | à valider |
| H11 | Notation intégrée au panneau Stories (étoiles + commentaire) ; le bloc bas de page disparaît ; télémétrie inchangée | à valider |
| H12 | « Suivi & réglages » = une page, deux sections ancrées ; anciennes routes redirigées | à valider |
| H13 | Export dans la barre de session (CSV / markdown) avec l'avertissement A8 à proximité | à valider |
| H14 | Sans JavaScript, tout reste utilisable (progressive enhancement conservé) — les gestes de masse dégradent en gestes individuels | à valider |
| H15 | Le JS DSFR (module 1.12) est chargé par CDN comme le CSS au MVP (vendoring prévu en E7) ; les composants restent dégradables sans lui (accordéons via `details` en repli) | à valider |

## 5. Découpage en stories (une story = une PR, TU + TNR + plan de test)

**Vague 1 — socle + session (priorité UX12)**

- **R1 — Socle DSFR & navigation** : en-tête + nav 4 entrées avec état actif, notice D15 fine,
  gabarit/cartes/badges partagés, fil d'Ariane — touche `base.html` + retouches minimales de
  chaque gabarit (aucun changement d'API).
- **R2 — Écran session : structure cible** : barre de session (stepper, meta, actions),
  colonne chat chronologique à défilement interne, composeur unifié, rail 3 panneaux —
  en POST pleine page d'abord (H7 arrive en R3). Suppression des blocs redondants.
  *Livrée avec le panneau Stories complet (notation, édition, copie) : **R5 absorbée**.*
- **R3 — Dynamisme fragments htmx** : envoi → le message s'ajoute au fil + mise à jour
  out-of-band des panneaux + indicateur de génération ; anti double-envoi conservé ; repli sans JS.
- **R4 — Hypothèses en masse** ⚙ : endpoint lot + cases à cocher + barre de sélection ;
  intégration des levées proposées / lot relu existants.
- **R5 — Panneau Stories complet** : *absorbée par R2 (le relogement notation/édition/copie
  n'avait pas de sens en deux temps — l'écran aurait été moitié ancien, moitié nouveau).*
- **R6 — Cycle de vie session** ⚙ : suppression définitive (l'archivage S3.13 existe),
  renommage dans la barre de session.

**Vague 2 — parcours quotidien**

- **R7 — Accueil refondu** : liste d'abord, tableau avec badges/actions, création repliée, archivées.
- **R8 — Mes documents refondu** : tuiles, regroupement par dossier (+ projets associés),
  actions par ligne, « marquer obsolète » ⚙ (H10), runs en historique replié.
- **R9 — Projets** ⚙ : édition contexte/NFR après création, archiver/supprimer (H9), écran fiche aligné.

**Vague 3 — périphérie**

- **R10 — Suivi & réglages + fiche document** : fusion télémétrie/paramètres (H12),
  fiche document alignée sur le socle.

## 6. Contraintes tenues (rappel des invariants)

- **DSFR réel — exigence UX13** : composants officiels partout où ils existent, tokens DSFR
  (custom properties) pour le custom, focus visibles, contrastes, thème clair/sombre —
  cohérent avec les critères d'accessibilité du gabarit ; police Marianne + JS DSFR via
  le CDN officiel (CDN au MVP, vendoring en E7).
- **D15** : la mention « Ne collez pas de données personnelles » reste affichée partout (notice fine).
- **Arbitrages produit intacts** : A2 (question libre, même fil), A3 (citations + extrait exact),
  A5 (étape fidèle, alerte couverture), A6 (association par dossiers), A7 (instance partagée,
  réglages globaux), **A8 (aucune levée silencieuse — la masse reste un geste explicite du PO)**,
  A9 (divergences signalées, PO arbitre).
- **Pas de framework lourd** : htmx (vendoré) + JavaScript minimal, progressive enhancement.
- **Le moteur E3/RAG n'est pas touché** : la refonte est UI/API de confort (endpoints de lot,
  cycle de vie) ; budget de contexte et prompts inchangés.

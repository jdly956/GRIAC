# Stories candidates « SILVER » — à valider par les PO pilotes

**Statut : SILVER — synthétiques, non validées. Chaque règle métier, seuil et format ci-dessous est une [HYPOTHÈSE À VALIDER]. Après validation (et correction) par un PO pilote, déplacer la story dans `/evals/gold/`. Usage immédiat : fixtures du validateur S1.10, few-shot provisoire, exercice d'embarquement du panel.**

**Grille de validation PO (par story)** : (1) Ce niveau de détail correspond-il à votre exigence de qualité ? (2) Les règles métier sont-elles plausibles pour votre domaine ? (3) Les CA sont-ils testables tels quels par un PO ? Corrigez directement dans le texte, puis levez ou reformulez chaque [HYPOTHÈSE À VALIDER].

Feature fictive de rattachement : « Suivi en ligne de l'avancement d'une demande » (téléservice usager, composants DSFR).

---
**US — Consulter l'état d'avancement de ma demande**

**En tant que** usager connecté titulaire d'une demande
**Je veux** consulter l'état d'avancement de ma demande depuis mon espace
**Afin de** savoir si une action m'est demandée sans solliciter le support

**Contexte** : première story de la Feature « Suivi en ligne » ; la demande a été déposée via le téléservice existant.
**Écran / module** : page « Ma demande » de l'espace usager
**Parcours concerné** : connexion → tableau de bord → détail de la demande
**Pré-requis** : usager authentifié ; au moins une demande déposée
**Règle(s) métier** : statuts possibles : Déposée, En instruction, Pièces attendues, Validée, Refusée [HYPOTHÈSE À VALIDER] ; seul le titulaire de la demande peut la consulter ; la date affichée est celle du dernier changement de statut

**Attendu fonctionnel** :
- Attendu 1 : l'usager voit le statut courant de sa demande et la date du dernier changement
- Attendu 2 : si une action lui incombe, un encart la décrit et pointe vers l'écran de réalisation
- Attendu 3 : un usager sans demande voit un message dédié et un lien vers le dépôt

**Maquettes** : à produire (action refinement)

**Critères d'acceptation** :

| # | Étant donné que… | Lorsque… | Alors… |
|---|---|---|---|
| CA1 | ma demande est au statut « En instruction » | j'ouvre la page « Ma demande » | le statut « En instruction » et la date du dernier changement de statut sont affichés |
| CA2 | ma demande est au statut « Pièces attendues » | j'ouvre la page « Ma demande » | un encart « Action attendue » liste la ou les pièces demandées et propose un lien vers l'écran de dépôt |
| CA3 | je n'ai aucune demande déposée | j'ouvre la page « Ma demande » | le message « Vous n'avez aucune demande en cours » et un lien vers le dépôt d'une demande sont affichés |
| CA4 | je suis authentifié comme usager A | j'accède à l'URL de la demande de l'usager B | l'accès est refusé et un message d'erreur de droits est affiché |

**Critères d'accessibilité** :
- Le statut est porté par un badge DSFR dont l'information n'est pas véhiculée par la seule couleur (libellé texte présent).
- Hiérarchie des titres logique ; titre d'onglet cohérent avec le contenu (« Ma demande — suivi »).
- Navigation clavier : l'encart « Action attendue » et son lien sont atteignables et activables au clavier.
- Zoom texte : la page zoomée à 200 % reste consultable.

---
**US — Déposer une pièce complémentaire demandée**

**En tant que** usager dont la demande est au statut « Pièces attendues »
**Je veux** téléverser la pièce demandée depuis la page de suivi
**Afin de** débloquer l'instruction de ma demande sans envoi postal

**Contexte** : suite directe du CA2 de la story « Consulter l'état d'avancement » ; l'instruction est suspendue tant que la pièce manque.
**Écran / module** : écran « Déposer une pièce » accessible depuis l'encart « Action attendue »
**Parcours concerné** : page « Ma demande » → encart action → dépôt → confirmation
**Pré-requis** : demande au statut « Pièces attendues » ; type de pièce attendu défini par l'instructeur
**Règle(s) métier** : formats acceptés : PDF, JPG, PNG [HYPOTHÈSE À VALIDER] ; taille maximale : 10 Mo par fichier [HYPOTHÈSE À VALIDER] ; une seule pièce par type demandé, le nouveau dépôt remplace le précédent ; dépôt possible uniquement au statut « Pièces attendues »

**Attendu fonctionnel** :
- Attendu 1 : l'usager téléverse un fichier conforme et obtient un accusé de dépôt horodaté
- Attendu 2 : un fichier non conforme (format, taille) est refusé avec un message indiquant la règle non respectée
- Attendu 3 : la pièce déposée apparaît dans la liste des pièces de la demande avec son horodatage

**Maquettes** : à produire (action refinement)

**Critères d'acceptation** :

| # | Étant donné que… | Lorsque… | Alors… |
|---|---|---|---|
| CA1 | ma demande est au statut « Pièces attendues » | je téléverse un fichier PDF de 2 Mo du type demandé | la pièce apparaît dans la liste avec la date et l'heure de dépôt et un accusé de dépôt est affiché |
| CA2 | je sélectionne un fichier de 15 Mo | je valide le téléversement | le fichier n'est pas enregistré et le message d'erreur indique la taille maximale autorisée (10 Mo) [HYPOTHÈSE À VALIDER] |
| CA3 | je sélectionne un fichier au format .docx | je valide le téléversement | le fichier n'est pas enregistré et le message d'erreur liste les formats acceptés |
| CA4 | ma demande est au statut « En instruction » | j'accède à l'écran de dépôt | le téléversement est indisponible et un message indique qu'aucune pièce n'est attendue |

**Critères d'accessibilité** :
- Formulaires : champ de téléversement labellisé, caractère obligatoire indiqué, messages d'erreur et de succès non véhiculés par la seule couleur.
- Navigation clavier : sélection du fichier, validation et consultation de l'accusé réalisables au clavier uniquement.
- Zoom texte : l'écran zoomé à 200 % reste utilisable (pas de texte superposé).

---
**US — Être notifié par courriel d'un changement de statut**

**En tant que** usager titulaire d'une demande
**Je veux** recevoir un courriel à chaque changement de statut de ma demande
**Afin de** être informé d'une avancée ou d'une action attendue sans consulter le téléservice

**Contexte** : complète les deux stories précédentes ; le courriel renvoie vers la page de suivi, qui reste la source de référence.
**Écran / module** : gabarit de courriel transactionnel ; aucun nouvel écran
**Parcours concerné** : changement de statut (instructeur ou système) → envoi du courriel → clic → page « Ma demande »
**Pré-requis** : adresse électronique vérifiée au niveau du compte
**Règle(s) métier** : envoi à l'adresse du compte uniquement ; le courriel ne contient aucune donnée sensible ni motif de décision — il renvoie vers l'espace authentifié [HYPOTHÈSE À VALIDER] ; aucune pièce jointe ; un courriel par changement de statut

**Attendu fonctionnel** :
- Attendu 1 : à chaque changement de statut, un courriel est envoyé dans un délai maximal de 15 minutes [HYPOTHÈSE À VALIDER]
- Attendu 2 : le courriel nomme le téléservice, indique le nouveau statut et contient un lien vers la page de suivi
- Attendu 3 : en cas de statut « Pièces attendues », le courriel mentionne qu'une action est attendue, sans détailler la pièce

**Maquettes** : gabarit de courriel à produire (action refinement)

**Critères d'acceptation** :

| # | Étant donné que… | Lorsque… | Alors… |
|---|---|---|---|
| CA1 | ma demande passe du statut « Déposée » à « En instruction » | le changement est enregistré | un courriel est envoyé à l'adresse du compte dans un délai maximal de 15 minutes [HYPOTHÈSE À VALIDER] |
| CA2 | je reçois le courriel de changement de statut | je clique sur le lien de suivi | j'atteins la page « Ma demande » après authentification |
| CA3 | ma demande passe au statut « Refusée » | le courriel est généré | il indique le statut « Refusée » et renvoie vers l'espace, sans contenir le motif de la décision |

**Critères d'accessibilité** :
- Le libellé du lien de suivi est explicite hors contexte (« Consulter le suivi de ma demande », pas « cliquez ici »).
- Structure du courriel HTML avec hiérarchie de titres logique ; version texte disponible.
- L'information de statut n'est pas véhiculée par la seule couleur.

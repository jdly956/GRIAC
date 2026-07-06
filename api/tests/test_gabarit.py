"""Tests S1.10 : validateur de conformité US + tableau DoR (fixtures = silver)."""

from pathlib import Path

from sia_api.gabarit import (
    CRITERE_DOR_REFINEMENT,
    CRITERES_DOR,
    extraire_stories_us,
    valider_dor,
    valider_us,
)

SILVER = Path(__file__).parents[2] / "evals" / "silver" / "stories-silver-candidates.md"

US_MINIMALE_CONFORME = """**US — Consulter mon dossier**

**En tant que** usager connecté
**Je veux** consulter mon dossier depuis mon espace
**Afin de** suivre son avancement sans appeler le support

**Contexte** : première story de la Feature « Suivi ».
**Écran / module** : page « Mon dossier »
**Parcours concerné** : connexion → tableau de bord → dossier
**Pré-requis** : usager authentifié
**Règle(s) métier** : seul le titulaire accède à son dossier

**Attendu fonctionnel** :
- Attendu 1 : l'usager voit le statut courant de son dossier

**Maquettes** : à produire (action refinement)

**Critères d'acceptation** :

| # | Étant donné que… | Lorsque… | Alors… |
|---|---|---|---|
| CA1 | mon dossier est en instruction | j'ouvre la page | le statut est affiché |

**Critères d'accessibilité** :
- Navigation clavier : la page est utilisable au clavier uniquement.
"""


def test_us_minimale_conforme() -> None:
    rapport = valider_us(US_MINIMALE_CONFORME)
    assert rapport.conforme, rapport.violations
    assert rapport.nb_ca == 1
    assert rapport.hypotheses == []


def test_les_trois_silver_sont_conformes() -> None:
    stories = extraire_stories_us(SILVER.read_text(encoding="utf-8"))
    assert len(stories) == 3
    for story in stories:
        rapport = valider_us(story)
        assert rapport.conforme, (story[:60], rapport.violations)
        assert rapport.nb_ca >= 3
        # Les silver conservent leurs marqueurs (jamais levés silencieusement)
        assert len(rapport.hypotheses) >= 1


def test_entete_us_manquante() -> None:
    rapport = valider_us(US_MINIMALE_CONFORME.replace("**US — Consulter mon dossier**", ""))
    assert any("entête" in violation for violation in rapport.violations)


def test_bloc_recit_manquant() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "**Afin de** suivre son avancement sans appeler le support", ""
        )
    )
    assert any("Afin de" in violation for violation in rapport.violations)


def test_bloc_recit_vide() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "**Je veux** consulter mon dossier depuis mon espace", "**Je veux**"
        )
    )
    assert any("Je veux" in violation and "vide" in violation for violation in rapport.violations)


def test_tableau_ca_absent() -> None:
    texte = (
        US_MINIMALE_CONFORME.replace("| # | Étant donné que… | Lorsque… | Alors… |", "")
        .replace("|---|---|---|---|", "")
        .replace(
            "| CA1 | mon dossier est en instruction | j'ouvre la page | le statut est affiché |", ""
        )
    )
    rapport = valider_us(texte)
    assert any("tableau des critères d'acceptation absent" in v for v in rapport.violations)


def test_tableau_ca_colonnes_incorrectes() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "| # | Étant donné que… | Lorsque… | Alors… |", "| # | Given | When | Then |"
        )
    )
    assert any("colonnes du tableau des CA" in violation for violation in rapport.violations)


def test_ligne_ca_incomplete() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "| CA1 | mon dossier est en instruction | j'ouvre la page | le statut est affiché |",
            "| CA1 | mon dossier est en instruction | | le statut est affiché |",
        )
    )
    assert any("ligne de CA incomplète" in violation for violation in rapport.violations)


def test_accessibilite_sans_critere() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "- Navigation clavier : la page est utilisable au clavier uniquement.", ""
        )
    )
    assert any("accessibilité" in violation for violation in rapport.violations)


def test_adverbe_flou_avertit_sans_bloquer() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "consulter mon dossier depuis mon espace",
            "consulter facilement mon dossier depuis mon espace",
        )
    )
    assert rapport.conforme  # non bloquant : le PO arbitre
    assert any("facilement" in avertissement for avertissement in rapport.avertissements)


def test_hypotheses_relevees_jamais_bloquantes() -> None:
    rapport = valider_us(
        US_MINIMALE_CONFORME.replace(
            "seul le titulaire accède à son dossier",
            "seul le titulaire accède à son dossier [HYPOTHÈSE À VALIDER]",
        )
    )
    assert rapport.conforme
    assert len(rapport.hypotheses) == 1


def _tableau_dor(surcharges: dict[str, tuple[str, str]] | None = None) -> str:
    surcharges = surcharges or {}
    lignes = ["| Critère DoR | Statut | Justification |", "|---|---|---|"]
    for critere in CRITERES_DOR:
        if critere == CRITERE_DOR_REFINEMENT:
            statut, justification = "🔵", "toujours à faire en équipe"
        else:
            statut, justification = "✅", "renseigné dans la story"
        statut, justification = surcharges.get(critere, (statut, justification))
        lignes.append(f"| {critere} | {statut} | {justification} |")
    return "\n".join(lignes)


def test_dor_conforme() -> None:
    rapport = valider_dor(_tableau_dor())
    assert rapport.conforme, rapport.violations


def test_dor_critere_manquant() -> None:
    texte = "\n".join(
        ligne for ligne in _tableau_dor().splitlines() if "use case concret" not in ligne
    )
    rapport = valider_dor(texte)
    assert any("Un use case concret est précisé" in violation for violation in rapport.violations)


def test_dor_statut_invalide() -> None:
    rapport = valider_dor(_tableau_dor({"Des critères d'acceptation existent": ("OK", "présents")}))
    assert any("statut DoR invalide" in violation for violation in rapport.violations)


def test_dor_estimation_reste_bleue() -> None:
    rapport = valider_dor(_tableau_dor({CRITERE_DOR_REFINEMENT: ("✅", "estimée par l'IA")}))
    assert any("jamais de l'IA" in violation for violation in rapport.violations)


def test_dor_justification_manquante() -> None:
    rapport = valider_dor(_tableau_dor({"Un use case concret est précisé": ("✅", "")}))
    assert any("justification manquante" in violation for violation in rapport.violations)


# --- typographie réelle des sorties Albert (faux positifs constatés pod 06/07/2026) ---

US_TYPOGRAPHIE_ALBERT = """**US — Authentifier l’agent**

**En tant que** agent de l’ATE
**Je veux** saisir mes identifiants professionnels
**Afin de** accéder au module d’actes

**Contexte** : première étape de la Feature.
**Écran / module** : page Connexion (DSFR).
**Parcours concerné** :
1. L’agent ouvre l’URL du module depuis le RIE.
2. Il saisit identifiant et mot‑de‑passe.
**Pré‑requis** :
- L’agent est connecté au RIE.
**Règle(s) métier** :
- Verrouillage temporaire après 5 échecs. **[HYPOTHÈSE À VALIDER]**
**Maquettes** : à produire.

**Attendu fonctionnel** :
- Réponse du serveur en moins d’une seconde.

**Critères d’acceptation** :

| # | Étant donné que… | Lorsque… | Alors… |
|---|---|---|---|
| CA1 | l’agent est sur le RIE | il saisit des identifiants valides | la réponse arrive en < 1 s |

**Critères d’accessibilité** :
- Les champs sont reliés à des labels explicites.
"""


def test_typographie_reelle_albert_conforme() -> None:
    # Tirets insécables (« Pré‑requis »), apostrophes typographiques
    # (« d’acceptation ») et blocs remplis sur les lignes suivantes : la
    # sortie réelle d'Albert doit passer sans faux positif (S2.12).
    rapport = valider_us(US_TYPOGRAPHIE_ALBERT)
    assert rapport.conforme, rapport.violations
    assert rapport.nb_ca == 1
    assert len(rapport.hypotheses) == 1


def test_bloc_reellement_vide_toujours_signale() -> None:
    # La tolérance « contenu sur les lignes suivantes » ne doit pas masquer
    # un bloc vraiment vide (suivi immédiatement du bloc suivant).
    texte = US_TYPOGRAPHIE_ALBERT.replace(
        "**Contexte** : première étape de la Feature.", "**Contexte** :"
    )
    rapport = valider_us(texte)
    assert any("Contexte" in violation for violation in rapport.violations)

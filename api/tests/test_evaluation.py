"""Tests S2.11 : harnais d'évals E6 — scoring pur, client Albert simulé."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from sia_api import evaluation
from sia_api.evaluation import (
    Cas,
    charger_cas,
    evaluer,
    executer,
    generer_rapport,
    score_completude,
    score_exactitude,
    score_gabarit,
)

FICHIER_SILVER = Path(__file__).parents[2] / "evals" / "silver" / "stories-silver-candidates.md"


@pytest.fixture
def cas_silver() -> list[Cas]:
    cas, origine = charger_cas()
    assert origine == "silver"  # tant que evals/gold/ est vide
    return cas


# --- chargement des cas et briefs ---


def test_charge_les_trois_cas_silver(cas_silver) -> None:
    assert len(cas_silver) == 3
    assert cas_silver[0].titre == "Consulter l'état d'avancement de ma demande"


def test_gold_prioritaire_sur_silver(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    gold = tmp_path / "gold"
    gold.mkdir()
    story = FICHIER_SILVER.read_text(encoding="utf-8")
    (gold / "valides.md").write_text(story, encoding="utf-8")
    monkeypatch.setattr(evaluation, "DOSSIER_GOLD", gold)
    cas, origine = charger_cas()
    assert origine == "gold"
    assert len(cas) == 3


def test_sans_reference_aucun_cas(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(evaluation, "DOSSIER_GOLD", tmp_path / "absent")
    monkeypatch.setattr(evaluation, "FICHIER_SILVER", tmp_path / "absent.md")
    assert charger_cas() == ([], "aucune")


def test_brief_garde_l_entree_po_et_exclut_la_sortie(cas_silver) -> None:
    brief = cas_silver[0].brief
    assert "**En tant que**" in brief
    assert "**Règle(s) métier**" in brief
    assert "**Attendu fonctionnel**" in brief
    assert "- Attendu 1" in brief
    assert "| CA1 |" not in brief  # les CA sont la sortie attendue, pas l'entrée
    assert "Critères d'accessibilité" not in brief


# --- grille 3 axes ---


def test_gabarit_parfait_sur_la_reference(cas_silver) -> None:
    # La référence elle-même est conforme S1.10 : le proxy doit rendre 1.0.
    assert score_gabarit(cas_silver[0].reference) == 1.0


def test_gabarit_penalise_les_violations() -> None:
    assert score_gabarit("**US — Story cassée**\n\nDu texte sans blocs.") < 0.5


def test_exactitude_pleine_quand_les_regles_sont_reprises(cas_silver) -> None:
    assert score_exactitude(cas_silver[0].reference, cas_silver[0].brief) == 1.0


def test_exactitude_chute_si_les_regles_manquent(cas_silver) -> None:
    genere = "**US — Consulter**\n\n**En tant que** usager\n**Je veux** voir\n**Afin de** savoir"
    assert score_exactitude(genere, cas_silver[0].brief) < 0.5


def test_exactitude_penalise_un_nombre_invente_non_marque(cas_silver) -> None:
    reference = cas_silver[0].reference
    avec_invention = reference + "\nLe délai de traitement est de 45 jours."
    assert score_exactitude(avec_invention, cas_silver[0].brief) < 1.0
    # Le même ajout marqué [HYPOTHÈSE À VALIDER] ne pénalise pas (anti-invention respectée).
    avec_marqueur = reference + "\nDélai de 45 jours [HYPOTHÈSE À VALIDER]"
    assert score_exactitude(avec_marqueur, cas_silver[0].brief) == 1.0


def test_completude_pleine_sur_la_reference(cas_silver) -> None:
    assert score_completude(cas_silver[0].reference, cas_silver[0].reference) == 1.0


def test_completude_chute_avec_moins_de_ca(cas_silver) -> None:
    reference = cas_silver[0].reference
    tronquee = "\n".join(
        ligne
        for ligne in reference.splitlines()
        if not ligne.startswith(("| CA2", "| CA3", "| CA4"))
    )
    assert score_completude(tronquee, reference) < score_completude(reference, reference)


# --- exécution avec client simulé (aucun appel réseau) ---


class FauxClient:
    def __init__(self, contenus: list[str]) -> None:
        self.contenus = contenus
        self.appels: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **parametres):
        self.appels.append(parametres)
        contenu = self.contenus[len(self.appels) - 1]
        if contenu == "ERREUR":
            raise RuntimeError("panne simulée")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=contenu))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=500),
        )


def test_executer_score_chaque_cas_et_survit_aux_echecs(cas_silver) -> None:
    cas = cas_silver[:2]
    client = FauxClient([cas[0].reference, "ERREUR"])
    tics = iter(range(10))
    resultats = executer(client, ["openweight-large"], cas, horloge=lambda: next(tics))
    assert len(resultats) == 2
    assert resultats[0].scores.moyenne == 1.0  # la référence rejouée score au plafond
    assert resultats[0].tokens_sortie == 500
    assert resultats[1].erreur is not None and "panne simulée" in resultats[1].erreur
    assert resultats[1].scores.moyenne == 0.0
    assert client.appels[0]["max_tokens"] == 4096  # gotcha raisonnement S1.5


def test_reponse_vide_est_un_echec_explicite(cas_silver) -> None:
    client = FauxClient([""])
    resultats = executer(client, ["openweight-large"], cas_silver[:1])
    assert resultats[0].erreur is not None and "vide" in resultats[0].erreur


def test_rapport_signale_le_repli_silver(cas_silver) -> None:
    client = FauxClient([cas_silver[0].reference])
    resultats = executer(client, ["openweight-large"], cas_silver[:1])
    rapport = generer_rapport(resultats, "silver")
    assert "SILVER" in rapport and "non validées" in rapport
    assert "| openweight-large |" in rapport
    assert "Moyennes par modèle" in rapport


def test_cli_ecrit_le_rapport(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cas_silver) -> None:
    client = FauxClient([cas_silver[0].reference])
    monkeypatch.setattr(evaluation, "charger_settings", lambda: object())
    monkeypatch.setattr(evaluation, "creer_client", lambda settings: client)
    sortie = tmp_path / "rapport.md"
    code = evaluation.main(
        ["--modeles", "openweight-large", "--max-cas", "1", "--sortie", str(sortie)]
    )
    assert code == 0
    assert "Benchmark génération" in sortie.read_text(encoding="utf-8")


def test_cli_sans_reference_code_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(evaluation, "DOSSIER_GOLD", tmp_path / "absent")
    monkeypatch.setattr(evaluation, "FICHIER_SILVER", tmp_path / "absent.md")
    assert evaluation.main([]) == 1


def test_moyenne_des_trois_axes() -> None:
    scores = evaluer("**US — X**\n\nrien", Cas(titre="X", brief="", reference="| CA1 |"))
    assert 0.0 <= scores.moyenne <= 1.0

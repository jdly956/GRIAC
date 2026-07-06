"""Tests E3.2 : moteur conversationnel — Albert et RAG simulés, invariants A2/A3/A8/A9."""

from collections import deque
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import sia_api.moteur as moteur
from sia_api.config import Settings
from sia_api.db import get_connexion
from sia_api.gabarit import CRITERE_DOR_REFINEMENT, CRITERES_DOR
from sia_api.main import app
from sia_api.moteur import (
    charger_few_shot,
    construire_prompt_systeme,
    controler_conformite,
    extraire_divergences,
)
from sia_api.recherche import ContexteResultat, SourceCitee, get_albert


def _settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        albert_base_url="https://albert.example/v1",
        albert_api_key="cle-de-test",
    )


# --- assemblage du prompt système (pur) ---


def test_prompt_systeme_contient_le_prompt3_et_les_consignes() -> None:
    prompt = construire_prompt_systeme("interview", None, "extraits cités ici", None)
    assert "PROMPT 3 — RÉDIGER MES USER STORIES" in prompt
    assert "Étape courante du workflow : **interview**" in prompt
    assert "extraits cités ici" in prompt
    assert "[HYPOTHÈSE À VALIDER]" in prompt
    assert "[DIVERGENCE]" in prompt  # A9
    assert "[Source :" in prompt  # A3
    # La validation passe par les boutons Oui/Non de l'UI (règle 5) — le modèle
    # ne doit plus la demander dans le texte (redondance constatée, 06/07/2026).
    assert "Ne demande JAMAIS de validation dans le texte" in prompt
    # Anti-invention durci (S2.15, constats sessions 9-11) : marqueur exact,
    # valeurs chiffrées inventées marquées, alternatives A/B/C non marquées.
    assert "EXACTEMENT le marqueur" in prompt
    assert "VALEUR CHIFFRÉE" in prompt
    assert "ALTERNATIVES" in prompt


def test_prompt_systeme_injecte_projet_et_nfr() -> None:
    projet = {
        "nom": "Téléservice X",
        "contexte": "Refonte du suivi.",
        "nfrs": [{"type": "rgpd", "formulation": "aucune donnée sensible", "valeur_cible": None}],
    }
    prompt = construire_prompt_systeme("interview", projet, "", None)
    assert "Téléservice X" in prompt
    assert "- rgpd : aucune donnée sensible" in prompt
    assert "bloc G" in prompt  # pré-remplissage NFR de l'interview (E8)


def test_prompt_une_seule_story_a_la_fois_aux_etapes_de_production() -> None:
    # Arbitrage S3.2 (06/07/2026) : le cycle réel est « une story = rédaction +
    # DoR » — le moteur n'enchaîne pas spontanément, l'UI a son bouton.
    prompt = construire_prompt_systeme("redaction", None, "", None)
    assert "UNE SEULE story à la fois" in prompt
    assert "Story suivante" in prompt
    assert "UNE SEULE story" not in construire_prompt_systeme("interview", None, "", None)


def test_prompt_systeme_sans_source_impose_le_signalement() -> None:
    prompt = construire_prompt_systeme("redaction", None, "", None)
    assert "AUCUNE source récupérable" in prompt


def test_few_shot_silver_jamais_presente_comme_valide() -> None:
    few_shot = charger_few_shot()
    assert few_shot is not None  # les silver du repo existent
    exemple, origine = few_shot
    assert origine == "silver"  # gold vide à ce jour
    prompt = construire_prompt_systeme("redaction", None, "", few_shot)
    assert "NON VALIDÉE" in prompt
    assert "**US — " in prompt  # l'exemple est bien inclus


def test_prompt_systeme_injecte_le_registre_en_attente() -> None:
    # Rapprochement interview↔registre (A8) : les hypothèses en attente entrent
    # au prompt, numérotées, avec la consigne de PROPOSER la levée — jamais de
    # la considérer acquise (la décision individuelle reste au PO).
    prompt = construire_prompt_systeme(
        "interview", None, "", None, [(3, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]")]
    )
    assert "#3 : Seuil 10 Mo" in prompt
    assert "[LEVÉE PROPOSÉE" in prompt
    assert "seul le PO confirme ou rejette" in prompt
    # Sans hypothèse en attente : ni section, ni consigne inutile.
    sans_registre = construire_prompt_systeme("interview", None, "", None)
    assert "REGISTRE DES HYPOTHÈSES EN ATTENTE" not in sans_registre
    # Session 9 (06/07/2026) : la consigne noyée en milieu de prompt n'a pas été
    # suivie — le registre vit désormais en DERNIÈRE position, après le few-shot.
    complet = construire_prompt_systeme(
        "interview", None, "", charger_few_shot(), [(3, "Seuil 10 Mo [HYPOTHÈSE À VALIDER]")]
    )
    assert complet.index("EXEMPLE DE FORMAT") < complet.index("REGISTRE DES HYPOTHÈSES EN ATTENTE")


def test_extraire_divergences() -> None:
    texte = (
        "Réponse.\n"
        "[DIVERGENCE] Le PO annonce 15 jours, la spec cite 30 jours [Source : spec].\n"
        "Suite."
    )
    assert len(extraire_divergences(texte)) == 1


# --- endpoint /workflows/{id}/message (DB scriptée, Albert et RAG simulés) ---


class FauxCurseur:
    def __init__(self, resultats: deque) -> None:
        self.resultats = resultats
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres or {}))

    def fetchone(self):
        return self.resultats.popleft()

    def fetchall(self):
        return self.resultats.popleft()

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, resultats: list) -> None:
        self.curseur = FauxCurseur(deque(resultats))
        self.commits = 0

    def cursor(self):
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


class FauxChat:
    def __init__(
        self, contenu: str, finish_reason: str = "stop", usage: tuple[int, int] | None = None
    ) -> None:
        self.appels: list[dict] = []
        self._contenu = contenu
        self._finish = finish_reason
        self._usage = usage  # (prompt_tokens, completion_tokens) — S3.11
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._creer))

    def _creer(self, **kwargs):
        self.appels.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._contenu), finish_reason=self._finish
                )
            ],
            usage=(
                SimpleNamespace(prompt_tokens=self._usage[0], completion_tokens=self._usage[1])
                if self._usage
                else None
            ),
        )


CONTEXTE_CANNE = ContexteResultat(
    contexte="[Source : spec_v2.docx — Spec > CA]\ncontenu",
    sources=[
        SourceCitee(
            document="projet-alpha/spec_v2.docx",
            nom="spec_v2.docx",
            section="Spec > CA",
            extrait="contenu exact du chunk cité",
        )
    ],
    nb_tokens=120,
    rerank_applique=True,
    avertissement=None,
)

client_http = TestClient(app)


@pytest.fixture
def brancher(monkeypatch: pytest.MonkeyPatch):
    def _brancher(
        resultats: list,
        reponse_llm: str,
        contexte: ContexteResultat = CONTEXTE_CANNE,
        finish_reason: str = "stop",
        usage: tuple[int, int] | None = None,
    ):
        connexion = FausseConnexion(resultats)
        faux_client = FauxChat(reponse_llm, finish_reason, usage)
        app.dependency_overrides[get_connexion] = lambda: connexion
        app.dependency_overrides[get_albert] = lambda: (faux_client, _settings())
        monkeypatch.setattr(moteur, "construire_contexte", lambda *a, **k: contexte)
        return connexion, faux_client

    yield _brancher
    app.dependency_overrides.clear()


SCRIPT_NOMINAL = [
    ("interview", None, "Ma Feature"),  # session
    None,  # parametres : pas de surcharge de modèle (S3.12)
    [("po", "Ma Feature")],  # historique
    [],  # registre des hypothèses (id, texte, statut) — vide
]


def test_message_nominal_alimente_fil_et_registre(brancher) -> None:
    reponse = "Q1 ? Q2 ?\nSeuil proposé : 10 Mo [HYPOTHÈSE À VALIDER]"
    connexion, faux_client = brancher(list(SCRIPT_NOMINAL), reponse)

    http = client_http.post("/workflows/7/message", json={"message": "quel seuil de taille ?"})
    assert http.status_code == 200
    corps = http.json()
    assert corps["reponse"] == reponse
    assert corps["sources"][0]["nom"] == "spec_v2.docx"  # panneau A3
    assert corps["hypotheses_ajoutees"] == ["Seuil proposé : 10 Mo [HYPOTHÈSE À VALIDER]"]
    assert corps["avertissements"] == []

    requetes = [r for r, _ in connexion.curseur.requetes]
    assert sum("INSERT INTO workflow_messages" in r for r in requetes) == 2  # PO + assistant
    assert any("INSERT INTO workflow_hypotheses" in r for r in requetes)
    assert connexion.commits == 1

    appel = faux_client.appels[0]
    assert appel["model"] == "openweight-medium"  # défaut à l'essai (verdict E6 v0)
    assert appel["max_tokens"] == 4096
    assert appel["messages"][0]["role"] == "system"
    assert "PROMPT 3" in appel["messages"][0]["content"]
    assert appel["messages"][-1]["content"] == "quel seuil de taille ?"


def test_hypothese_deja_connue_non_dupliquee(brancher) -> None:
    script = [
        ("interview", None, "Ma Feature"),
        None,  # pas de surcharge de modèle
        [],
        [(3, "Seuil proposé : 10 Mo [HYPOTHÈSE À VALIDER]", "en_attente")],  # déjà au registre
    ]
    # Même ligne exacte que celle du registre : la dédup v0 est textuelle.
    connexion, _ = brancher(script, "Seuil proposé : 10 Mo [HYPOTHÈSE À VALIDER]")
    corps = client_http.post("/workflows/7/message", json={"message": "ok ?"}).json()
    assert corps["hypotheses_ajoutees"] == []
    assert not any("INSERT INTO workflow_hypotheses" in r for r, _ in connexion.curseur.requetes)


def test_reformulation_du_registre_non_dupliquee(brancher) -> None:
    # S2.15 : un récapitulatif qui re-liste une hypothèse déjà au registre sous
    # d'autres mots ne crée pas d'entrée (bruit session 11 : 18 « en attente »).
    script = [
        ("interview", None, "Ma Feature"),
        None,  # pas de surcharge de modèle
        [],
        [(3, "- Taille maximale d'une pièce jointe : 10 Mo [HYPOTHÈSE À VALIDER]", "en_attente")],
    ]
    reponse = (
        "- **#3** : Taille maximale de la pièce jointe = 10 Mo, comme indiqué "
        "dans les critères d'acceptation de la Feature [HYPOTHÈSE À VALIDER]."
    )
    connexion, _ = brancher(script, reponse)
    corps = client_http.post("/workflows/7/message", json={"message": "récapitule"}).json()
    assert corps["hypotheses_ajoutees"] == []
    assert not any("INSERT INTO workflow_hypotheses" in r for r, _ in connexion.curseur.requetes)


def test_divergence_corpus_po_signalee(brancher) -> None:
    reponse = (
        "[DIVERGENCE] Vous annoncez 15 jours ; la spec indique 30 jours [Source : spec_v2.docx]."
    )
    brancher(list(SCRIPT_NOMINAL), reponse)
    corps = client_http.post("/workflows/7/message", json={"message": "le délai est 15 j"}).json()
    assert len(corps["divergences"]) == 1  # A9 : signalée, arbitrée par le PO


def test_regle_1_interview_signalee(brancher) -> None:
    brancher(list(SCRIPT_NOMINAL), "Q1 ? Q2 ? Q3 ? Q4 ?")
    corps = client_http.post("/workflows/7/message", json={"message": "allons-y"}).json()
    assert any("règle 1" in a for a in corps["avertissements"])


def test_aucune_source_avertit(brancher) -> None:
    contexte_vide = ContexteResultat(
        contexte="",
        sources=[],
        nb_tokens=0,
        rerank_applique=False,
        avertissement="Aucune source récupérable dans le corpus pour cette question — signalement.",
    )
    brancher(list(SCRIPT_NOMINAL), "Réponse prudente.", contexte=contexte_vide)
    corps = client_http.post("/workflows/7/message", json={"message": "sujet inconnu"}).json()
    assert any("Aucune source récupérable" in a for a in corps["avertissements"])


SCRIPT_REGISTRE_EN_ATTENTE = [
    ("interview", None, "Ma Feature"),  # session
    None,  # parametres : pas de surcharge de modèle (S3.12)
    [("po", "Ma Feature")],  # historique
    [(3, "Seuil proposé : 10 Mo [HYPOTHÈSE À VALIDER]", "en_attente")],  # registre
]


def test_levee_proposee_persistee_sans_toucher_le_statut(brancher) -> None:
    reponse = "Votre réponse fixe le seuil.\n[LEVÉE PROPOSÉE : #3 — confirmée — le PO a fixé 10 Mo]"
    connexion, faux_client = brancher(list(SCRIPT_REGISTRE_EN_ATTENTE), reponse)
    corps = client_http.post("/workflows/7/message", json={"message": "le seuil est 10 Mo"}).json()
    assert corps["levees_proposees"] == [
        {"hypothese_id": 3, "statut_propose": "confirmee", "justification": "le PO a fixé 10 Mo"}
    ]
    # Le registre en attente est bien entré au prompt système.
    assert "#3 : Seuil proposé : 10 Mo" in faux_client.appels[0]["messages"][0]["content"]
    maj = [p for r, p in connexion.curseur.requetes if "SET statut_propose" in r]
    assert maj == [
        {
            "statut_propose": "confirmee",
            "justification": "le PO a fixé 10 Mo",
            "hid": 3,
            "sid": 7,
        }
    ]
    # Invariant A8 : la proposition ne modifie JAMAIS le statut lui-même.
    assert not any("SET statut =" in r for r, _ in connexion.curseur.requetes)


def test_levee_proposee_hors_registre_ignoree(brancher) -> None:
    connexion, _ = brancher(
        list(SCRIPT_REGISTRE_EN_ATTENTE), "[LEVÉE PROPOSÉE : #99 — confirmée — numéro halluciné]"
    )
    corps = client_http.post("/workflows/7/message", json={"message": "ok"}).json()
    assert corps["levees_proposees"] == []
    assert not any("SET statut_propose" in r for r, _ in connexion.curseur.requetes)


def test_surcharge_modele_ui_appliquee_a_l_appel(brancher) -> None:
    # S3.12 : la surcharge de l'écran Paramètres (table parametres) prime sur
    # le défaut env/code, sans relance de l'api.
    script = [
        ("interview", None, "Ma Feature"),
        ("openweight-large",),  # surcharge UI
        [("po", "Ma Feature")],
        [],
    ]
    _, faux_client = brancher(script, "Réponse.")
    assert client_http.post("/workflows/7/message", json={"message": "ok"}).status_code == 200
    assert faux_client.appels[0]["model"] == "openweight-large"


def test_traces_persistees_sur_le_message(brancher) -> None:
    # S3.9 (A3 complet) : sources (avec extrait exact), avertissements et
    # divergences entrent dans message_traces — le fil les restitue au
    # rechargement, fin de la « v1 assumée » S2.8.
    reponse = "Réponse.\n[DIVERGENCE] 15 vs 30 jours [Source : spec_v2.docx].\nQ1 ? Q2 ? Q3 ? Q4 ?"
    connexion, _ = brancher(list(SCRIPT_NOMINAL), reponse)
    client_http.post("/workflows/7/message", json={"message": "délai ?"})
    traces = [p for r, p in connexion.curseur.requetes if "INSERT INTO message_traces" in r]
    assert {
        "nom": "spec_v2.docx",
        "section": "Spec > CA",
        "extrait": "contenu exact du chunk cité",
        "id": 7,
    } in traces  # la source + extrait
    assert any(p.get("type") == "avertissement" for p in traces)  # règle 1 (4 questions)
    assert any(p.get("type") == "divergence" for p in traces)


def test_usage_verse_au_registre_de_conso(brancher) -> None:
    # S3.11 : l'usage de chaque appel chat entre dans conso_tokens (jauge tpd) ;
    # sans usage dans la réponse (fixtures par défaut), aucun INSERT — couvert
    # par les autres tests qui n'attendent pas cette requête.
    connexion, _ = brancher(list(SCRIPT_NOMINAL), "Réponse.", usage=(1_200, 300))
    assert client_http.post("/workflows/7/message", json={"message": "ok"}).status_code == 200
    inserts = [p for r, p in connexion.curseur.requetes if "conso_tokens" in r]
    assert inserts == [{"id": 7, "modele": "openweight-medium", "entree": 1_200, "sortie": 300}]


def test_reponse_vide_erreur_explicite(brancher) -> None:
    brancher(list(SCRIPT_NOMINAL), "", finish_reason="length")
    http = client_http.post("/workflows/7/message", json={"message": "?"})
    assert http.status_code == 502
    assert "finish_reason=length" in http.json()["detail"]


def test_session_inconnue_404(brancher) -> None:
    brancher([None], "peu importe")
    assert client_http.post("/workflows/99/message", json={"message": "?"}).status_code == 404


# --- contrôle DoR/gabarit automatisé (S2.12, pur) ---

FICHIER_SILVER = moteur.FICHIER_SILVER


def _story_conforme() -> str:
    from sia_api.gabarit import extraire_stories_us

    return extraire_stories_us(FICHIER_SILVER.read_text(encoding="utf-8"))[0]


def _tableau_dor_conforme() -> str:
    lignes = ["| Critère DoR | Statut | Justification |", "|---|---|---|"]
    for critere in CRITERES_DOR:
        statut = "🔵" if critere == CRITERE_DOR_REFINEMENT else "✅"
        lignes.append(f"| {critere} | {statut} | vérifié en session |")
    return "\n".join(lignes)


def test_controle_conformite_silencieux_quand_tout_est_conforme() -> None:
    contenu = f"---\n{_story_conforme()}\n---\n\n{_tableau_dor_conforme()}"
    assert controler_conformite("controle_dor", contenu) == []


def test_controle_gabarit_signale_une_story_bancale() -> None:
    contenu = "---\n**US — Story bancale**\n\n**En tant que** PO pressé\n\nRien d'autre.\n---"
    rapports = controler_conformite("redaction", contenu)
    assert len(rapports) == 1
    assert "Story bancale" in rapports[0] and "Contrôle gabarit" in rapports[0]


def test_controle_dor_signale_le_tableau_absent() -> None:
    contenu = f"---\n{_story_conforme()}\n---"  # le tableau de CA ne fait pas illusion
    rapports = controler_conformite("controle_dor", contenu)
    assert len(rapports) == 1
    assert "Contrôle DoR automatisé" in rapports[0] and "absent" in rapports[0]


def test_controle_dor_refinement_doit_rester_bleu() -> None:
    tableau = _tableau_dor_conforme().replace(
        f"| {CRITERE_DOR_REFINEMENT} | 🔵 |", f"| {CRITERE_DOR_REFINEMENT} | ✅ |"
    )
    rapports = controler_conformite("controle_dor", tableau)
    assert any("🔵" in r for r in rapports)


def test_controle_dor_sur_toute_etape_de_production() -> None:
    # Session 9 (06/07/2026) : le cycle réel est « une story = rédaction + DoR »
    # et la machine à états file à `synthese` pendant que les tableaux DoR
    # continuent d'arriver — un tableau présent se contrôle quelle que soit
    # l'étape de production ; son absence ne se signale qu'à l'étape 4.
    tableau_bancal = _tableau_dor_conforme().replace(
        f"| {CRITERE_DOR_REFINEMENT} | 🔵 |", f"| {CRITERE_DOR_REFINEMENT} | ✅ |"
    )
    rapports = controler_conformite("synthese", tableau_bancal)
    assert any("Contrôle DoR automatisé" in r for r in rapports)
    assert controler_conformite("synthese", "du texte sans tableau DoR") == []


def test_pas_de_controle_hors_etapes_de_production() -> None:
    contenu = "---\n**US — Story bancale**\n\n**En tant que** PO pressé\n\nRien d'autre.\n---"
    assert controler_conformite("interview", contenu) == []


def test_route_remonte_les_controles_en_avertissements(brancher) -> None:
    script = [
        ("controle_dor", None, "Ma Feature"),  # session à l'étape 4
        None,  # pas de surcharge de modèle
        [("po", "Ma Feature")],  # historique
        [],  # hypothèses connues
    ]
    reponse = "---\n**US — Story bancale**\n\n**En tant que** PO pressé\n\nRien d'autre.\n---"
    brancher(script, reponse)
    http = client_http.post("/workflows/7/message", json={"message": "contrôle la DoR"})
    assert http.status_code == 200
    avertissements = http.json()["avertissements"]
    assert any("Contrôle gabarit" in a and "Story bancale" in a for a in avertissements)
    assert any("Contrôle DoR automatisé" in a for a in avertissements)

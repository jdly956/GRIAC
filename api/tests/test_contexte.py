"""Tests S2.4 : rerank Albert (HTTP simulé, repli RRF signalé) + assemblage cité."""

from collections import deque
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from sia_api.config import Settings
from sia_api.db import get_connexion
from sia_api.main import app
from sia_api.recherche import (
    ChunkTrouve,
    RechercheEntree,
    assembler_contexte,
    construire_contexte,
    get_albert,
    reranker,
)


def _settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        albert_base_url="https://albert.example/v1",
        albert_api_key="cle-de-test",
    )


def _chunk(nom: str, nb_tokens: int = 100) -> ChunkTrouve:
    return ChunkTrouve(
        document=f"projet-alpha/{nom}",
        nom=nom,
        section="Spec > CA",
        contenu=f"contenu de {nom}",
        nb_tokens=nb_tokens,
        score_rrf=0.01,
    )


class FauxHttp:
    """Simule httpx.post sur /v1/rerank ; peut échouer (404, réseau)."""

    def __init__(self, scores: list[float] | None = None, echoue: bool = False) -> None:
        self.scores = scores or []
        self.echoue = echoue
        self.appels: list[dict] = []

    def __call__(self, url: str, headers=None, json=None, timeout=None):
        self.appels.append({"url": url, "json": json, "timeout": timeout})
        if self.echoue:
            raise RuntimeError("404 Not Found")
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "data": [{"index": i, "score": score} for i, score in enumerate(self.scores)]
            },
        )


def test_reranker_ordonne_par_score_decroissant() -> None:
    http = FauxHttp(scores=[0.1, 0.9, 0.5])
    ordre = reranker(_settings(), "question", ["a", "b", "c"], http_post=http)
    assert ordre == [1, 2, 0]
    appel = http.appels[0]
    assert appel["url"].endswith("/rerank")
    assert appel["json"]["model"] == "openweight-rerank"
    assert appel["json"]["prompt"] == "question"
    assert appel["timeout"] == 30.0


def test_reranker_indisponible_retourne_none() -> None:
    assert reranker(_settings(), "q", ["a"], http_post=FauxHttp(echoue=True)) is None


def test_assemblage_respecte_le_budget_et_cite() -> None:
    chunks = [_chunk(f"doc{i}.docx", nb_tokens=400) for i in range(5)]
    contexte, retenus, total = assembler_contexte(chunks, budget_tokens=1000)
    assert len(retenus) == 2  # 400 + 400 ; le 3e dépasserait le budget
    assert total == 800
    assert contexte.startswith("[Source : doc0.docx — Spec > CA]")
    assert "\n\n---\n\n" in contexte


def test_assemblage_borne_a_15_candidats() -> None:
    chunks = [_chunk(f"doc{i}.docx", nb_tokens=1) for i in range(30)]
    _, retenus, _ = assembler_contexte(chunks, budget_tokens=10_000)
    assert len(retenus) == 15  # 8-15 chunks (E2)


def test_assemblage_garde_toujours_le_premier_chunk() -> None:
    contexte, retenus, _ = assembler_contexte([_chunk("gros.docx", nb_tokens=9000)])
    assert len(retenus) == 1  # un chunk hors budget seul reste servi (tableau géant S2.1)
    assert "[Source : gros.docx" in contexte


# --- construire_contexte : bout en bout avec DB/Albert/HTTP simulés ---


class FauxCurseur:
    def __init__(self, resultats: deque) -> None:
        self.resultats = resultats
        self.requetes: list[tuple[str, dict]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres or {}))

    def fetchall(self):
        return self.resultats.popleft()

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, resultats: list) -> None:
        self.curseur = FauxCurseur(deque(resultats))

    def cursor(self):
        return self.curseur


class FauxAlbert:
    def __init__(self) -> None:
        self.embeddings = SimpleNamespace(
            create=lambda **_: SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.5] * 4)])
        )


DETAILS = [
    (1, "projet-alpha/spec_v2.docx", "spec_v2.docx", "Spec > CA", "contenu un", 120),
    (2, "projet-alpha/guide.pdf", "guide.pdf", "Guide", "contenu deux", 80),
]


def test_construire_contexte_rerank_reordonne() -> None:
    connexion = FausseConnexion([[(1,), (2,)], [(1,), (2,)], DETAILS])
    http = FauxHttp(scores=[0.2, 0.9])  # le 2e candidat devient premier
    resultat = construire_contexte(
        connexion, FauxAlbert(), _settings(), RechercheEntree(question="délai"), http_post=http
    )
    assert resultat.rerank_applique is True
    assert resultat.sources[0].nom == "guide.pdf"
    assert resultat.nb_tokens == 200
    assert resultat.avertissement is None


def test_construire_contexte_repli_rrf_signale() -> None:
    connexion = FausseConnexion([[(1,), (2,)], [(1,), (2,)], DETAILS])
    resultat = construire_contexte(
        connexion,
        FauxAlbert(),
        _settings(),
        RechercheEntree(question="délai"),
        http_post=FauxHttp(echoue=True),
    )
    assert resultat.rerank_applique is False
    assert "ordre de la fusion RRF conservé" in (resultat.avertissement or "")
    assert resultat.sources[0].nom == "spec_v2.docx"  # ordre RRF d'origine


def test_construire_contexte_sans_source() -> None:
    connexion = FausseConnexion([[], []])
    resultat = construire_contexte(
        connexion,
        FauxAlbert(),
        _settings(),
        RechercheEntree(question="hors corpus"),
        http_post=FauxHttp(),
    )
    assert resultat.contexte == ""
    assert "Aucune source récupérable" in (resultat.avertissement or "")


# --- endpoint REST ---

client_http = TestClient(app)


@pytest.fixture
def brancher():
    def _brancher(resultats: list) -> None:
        connexion = FausseConnexion(resultats)
        app.dependency_overrides[get_connexion] = lambda: connexion
        app.dependency_overrides[get_albert] = lambda: (FauxAlbert(), _settings())

    yield _brancher
    app.dependency_overrides.clear()


def test_endpoint_contexte(brancher, monkeypatch: pytest.MonkeyPatch) -> None:
    import sia_api.recherche as module

    monkeypatch.setattr(module, "httpx", SimpleNamespace(post=FauxHttp(scores=[0.9, 0.1])))
    brancher([[(1,), (2,)], [(1,), (2,)], DETAILS])
    reponse = client_http.post("/contexte", json={"question": "délai d'instruction"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["contexte"].startswith("[Source :")
    assert len(corps["sources"]) == 2

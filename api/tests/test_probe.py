"""Tests S1.5 : sonde Albert (mocks — aucun appel réseau réel)."""

from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from sia_api.config import Settings
from sia_api.probe import executer_sonde, generer_rapport, relever_quotas

CLE_TEST = "cle-ultra-secrete-s15"


def _settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        albert_base_url="https://albert.example/v1",
        albert_api_key=CLE_TEST,
    )


class FauxClient:
    """Client OpenAI factice : catalogue, chat et embeddings canoniques."""

    def __init__(self) -> None:
        self.models = SimpleNamespace(
            list=lambda: SimpleNamespace(
                data=[
                    SimpleNamespace(
                        model_dump=lambda: {
                            "id": "openweight-large",
                            "type": "text-generation",
                            "max_context_length": 128000,
                        }
                    )
                ]
            )
        )
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_: SimpleNamespace(
                    model="gpt-oss-120b",
                    choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))],
                )
            )
        )
        self.embeddings = SimpleNamespace(
            create=lambda **_: SimpleNamespace(
                model="bge-m3",
                data=[SimpleNamespace(embedding=[0.0] * 1024)],
            )
        )


class FausseReponseHttp:
    def __init__(self, corps: dict[str, Any]) -> None:
        self._corps = corps

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self._corps


def test_sonde_nominale_et_rapport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx, "get", lambda *_, **__: FausseReponseHttp({"limits": {"tpm": 100000}})
    )
    donnees = executer_sonde(FauxClient(), _settings())  # type: ignore[arg-type]

    assert all(etape["statut"] == "ok" for etape in donnees["etapes"].values())
    assert donnees["etapes"]["embeddings"]["dimension"] == 1024
    assert donnees["etapes"]["chat"]["reponse"] == "OK"

    rapport = generer_rapport(donnees, "2026-07-02 00:00 UTC")
    assert "openweight-large" in rapport
    assert '"tpm": 100000' in rapport
    assert "1024" in rapport
    assert CLE_TEST not in rapport


def test_quotas_ne_gardent_que_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *_, **__: FausseReponseHttp({"email": "po@exemple.fr", "limits": {"rpm": 60}}),
    )
    quotas = relever_quotas(_settings())
    assert quotas == {"limits": {"rpm": 60}}  # jamais d'identifiants dans le rapport


def test_limits_absent_signale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *_, **__: FausseReponseHttp({"autre": 1}))
    assert "avertissement" in relever_quotas(_settings())


def test_erreur_reseau_geree_sans_interrompre(monkeypatch: pytest.MonkeyPatch) -> None:
    def _panne(*_: Any, **__: Any) -> Any:
        raise httpx.ConnectError("réseau injoignable")

    monkeypatch.setattr(httpx, "get", _panne)
    donnees = executer_sonde(FauxClient(), _settings())  # type: ignore[arg-type]

    assert donnees["etapes"]["quotas"]["statut"] == "échec"
    assert "ConnectError" in donnees["etapes"]["quotas"]["erreur"]
    # Les relevés suivants ont bien eu lieu malgré la panne.
    assert donnees["etapes"]["chat"]["statut"] == "ok"
    assert donnees["etapes"]["embeddings"]["statut"] == "ok"


def test_cle_expurgee_des_messages_derreur(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fuite(*_: Any, **__: Any) -> Any:
        raise RuntimeError(f"401 Unauthorized pour Bearer {CLE_TEST}")

    monkeypatch.setattr(httpx, "get", _fuite)
    donnees = executer_sonde(FauxClient(), _settings())  # type: ignore[arg-type]

    erreur = donnees["etapes"]["quotas"]["erreur"]
    assert CLE_TEST not in erreur
    assert "***" in erreur
    assert CLE_TEST not in generer_rapport(donnees, "2026-07-02 00:00 UTC")


def test_rapport_affiche_les_echecs(monkeypatch: pytest.MonkeyPatch) -> None:
    def _panne(*_: Any, **__: Any) -> Any:
        raise httpx.ConnectError("réseau injoignable")

    monkeypatch.setattr(httpx, "get", _panne)
    rapport = generer_rapport(
        executer_sonde(FauxClient(), _settings()),  # type: ignore[arg-type]
        "2026-07-02 00:00 UTC",
    )
    assert "**quotas** : échec" in rapport

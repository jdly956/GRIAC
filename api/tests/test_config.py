"""Tests S1.4 : config par l'environnement, échec propre sans clé, clé jamais en clair."""

import pytest
from fastapi.testclient import TestClient

from sia_api.config import charger_settings
from sia_api.main import app

VARIABLES_ALBERT = [
    "ALBERT_BASE_URL",
    "ALBERT_API_KEY",
    "ALBERT_MODEL_CHAT",
    "ALBERT_MODEL_EMBEDDINGS",
    "ALBERT_MODEL_RERANK",
]


@pytest.fixture
def env_vierge(monkeypatch, tmp_path):
    """Aucune variable ALBERT_* héritée, aucun .env parasite (cwd -> tmp_path)."""
    for variable in VARIABLES_ALBERT:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.chdir(tmp_path)
    return monkeypatch


def test_chargement_complet_et_alias_par_defaut(env_vierge) -> None:
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    env_vierge.setenv("ALBERT_API_KEY", "cle-de-test")
    settings = charger_settings()
    assert settings.albert_base_url == "https://albert.example/v1"
    assert settings.albert_api_key.get_secret_value() == "cle-de-test"
    # Alias Albert par défaut (CLAUDE.md : survivre aux rotations de catalogue)
    assert settings.albert_model_chat == "openweight-large"
    assert settings.albert_model_embeddings == "openweight-embeddings"
    assert settings.albert_model_rerank == "openweight-rerank"


def test_alias_surchargeables_par_env(env_vierge) -> None:
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    env_vierge.setenv("ALBERT_API_KEY", "cle-de-test")
    env_vierge.setenv("ALBERT_MODEL_CHAT", "openweight-medium")
    assert charger_settings().albert_model_chat == "openweight-medium"


def test_timeout_et_retries_par_defaut_et_surcharge(env_vierge) -> None:
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    env_vierge.setenv("ALBERT_API_KEY", "cle-de-test")
    settings = charger_settings()
    assert settings.albert_timeout_s == 30.0
    assert settings.albert_max_retries == 2
    env_vierge.setenv("ALBERT_TIMEOUT_S", "5")
    env_vierge.setenv("ALBERT_MAX_RETRIES", "0")
    settings = charger_settings()
    assert settings.albert_timeout_s == 5.0
    assert settings.albert_max_retries == 0


def test_cle_absente_echec_explicite(env_vierge) -> None:
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    with pytest.raises(RuntimeError) as excinfo:
        charger_settings()
    assert "ALBERT_API_KEY" in str(excinfo.value)
    assert ".env.example" in str(excinfo.value)


def test_cle_vide_echec_explicite(env_vierge) -> None:
    # Cas compose : `${ALBERT_API_KEY:-}` injecte une chaîne vide, pas une absence.
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    env_vierge.setenv("ALBERT_API_KEY", "   ")
    with pytest.raises(RuntimeError, match="ALBERT_API_KEY"):
        charger_settings()


def test_toutes_variables_absentes_listees(env_vierge) -> None:
    with pytest.raises(RuntimeError) as excinfo:
        charger_settings()
    assert "ALBERT_BASE_URL" in str(excinfo.value)
    assert "ALBERT_API_KEY" in str(excinfo.value)


def test_cle_jamais_en_clair(env_vierge) -> None:
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    env_vierge.setenv("ALBERT_API_KEY", "cle-ultra-secrete")
    settings = charger_settings()
    rendus = [
        str(settings),
        repr(settings),
        str(settings.albert_api_key),
        repr(settings.albert_api_key),
    ]
    for rendu in rendus:
        assert "cle-ultra-secrete" not in rendu


def test_demarrage_api_sans_cle_refuse(env_vierge) -> None:
    # Le lifespan (démarrage réel uvicorn/TestClient-contexte) refuse de démarrer.
    with pytest.raises(RuntimeError, match="ALBERT_"), TestClient(app):
        pass


def test_demarrage_api_avec_config_ok(env_vierge) -> None:
    env_vierge.setenv("ALBERT_BASE_URL", "https://albert.example/v1")
    env_vierge.setenv("ALBERT_API_KEY", "cle-de-test")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.settings.albert_model_chat == "openweight-large"

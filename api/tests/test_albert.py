"""Tests S1.5 : construction du client Albert (timeouts/retries configurés)."""

from sia_api.albert import creer_client
from sia_api.config import Settings


def _settings(**surcharges: object) -> Settings:
    valeurs: dict[str, object] = {
        "albert_base_url": "https://albert.example/v1",
        "albert_api_key": "cle-de-test",
    }
    valeurs.update(surcharges)
    return Settings(_env_file=None, **valeurs)  # type: ignore[arg-type]


def test_client_pointe_sur_albert() -> None:
    client = creer_client(_settings())
    assert str(client.base_url).startswith("https://albert.example/v1")
    assert client.api_key == "cle-de-test"


def test_timeouts_et_retries_par_defaut() -> None:
    client = creer_client(_settings())
    assert client.timeout == 30.0
    assert client.max_retries == 2


def test_timeouts_et_retries_surchargeables() -> None:
    client = creer_client(_settings(albert_timeout_s=5.0, albert_max_retries=0))
    assert client.timeout == 5.0
    assert client.max_retries == 0

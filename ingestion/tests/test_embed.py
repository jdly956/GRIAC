"""Tests S2.2 : embeddings par lots (Albert mocké), reprise, échec de lot isolé."""

from types import SimpleNamespace

import pytest

from sia_api.config import Settings
from sia_ingestion.embed import formater_vecteur, main, traiter_chunks


def _settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        albert_base_url="https://albert.example/v1",
        albert_api_key="cle-de-test",
    )


class FauxClient:
    """Renvoie des vecteurs déterministes ; peut échouer sur un lot donné."""

    def __init__(self, dimension: int = 1024, echoue_au_lot: int | None = None) -> None:
        self.dimension = dimension
        self.echoue_au_lot = echoue_au_lot
        self.appels: list[dict] = []
        self.embeddings = SimpleNamespace(create=self._creer)

    def _creer(self, **kwargs):
        self.appels.append(kwargs)
        if self.echoue_au_lot == len(self.appels):
            raise RuntimeError("429 Too Many Requests (quota)")
        contenus = kwargs["input"]
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=i, embedding=[float(i)] * self.dimension)
                for i in range(len(contenus))
            ]
        )


class FauxCurseur:
    def __init__(self, chunks) -> None:
        self.chunks = chunks
        self.requetes: list[tuple[str, dict | None]] = []

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres))

    def fetchall(self):
        return self.chunks

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, chunks) -> None:
        self.curseur = FauxCurseur(chunks)
        self.commits = 0

    def cursor(self):
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


def test_vectorisation_par_lots() -> None:
    connexion = FausseConnexion([(1, "a"), (2, "b"), (3, "c")])
    client = FauxClient()
    statistiques = traiter_chunks(connexion, client, _settings(), taille_lot=2)

    assert statistiques == {"vectorises": 3, "lots": 2, "lots_en_echec": 0}
    assert [len(appel["input"]) for appel in client.appels] == [2, 1]
    # Gotcha Albert (S1.5) : float explicite, jamais le base64 par défaut du SDK
    assert all(appel["encoding_format"] == "float" for appel in client.appels)
    assert all(appel["model"] == "openweight-embeddings" for appel in client.appels)
    majs = [p for r, p in connexion.curseur.requetes if "UPDATE chunks" in r]
    assert len(majs) == 3
    assert majs[0]["vecteur"].startswith("[0.0,")  # format pgvector ::vector
    assert connexion.commits == 2  # un commit par lot (l'acquis survit à un échec ultérieur)


def test_lot_en_echec_n_interrompt_pas(capsys: pytest.CaptureFixture) -> None:
    connexion = FausseConnexion([(1, "a"), (2, "b"), (3, "c"), (4, "d")])
    client = FauxClient(echoue_au_lot=1)
    statistiques = traiter_chunks(connexion, client, _settings(), taille_lot=2)

    assert statistiques == {"vectorises": 2, "lots": 2, "lots_en_echec": 1}
    assert "lot en échec (chunks 1–2)" in capsys.readouterr().err
    majs = [p for r, p in connexion.curseur.requetes if "UPDATE chunks" in r]
    assert [p["id"] for p in majs] == [3, 4]  # le second lot est bien passé


def test_dimension_inattendue_avertit(capsys: pytest.CaptureFixture) -> None:
    connexion = FausseConnexion([(1, "a")])
    traiter_chunks(connexion, FauxClient(dimension=768), _settings())
    assert "dimension 768 ≠ 1024" in capsys.readouterr().err


def test_aucun_chunk_a_vectoriser() -> None:
    connexion = FausseConnexion([])
    statistiques = traiter_chunks(connexion, FauxClient(), _settings())
    assert statistiques == {"vectorises": 0, "lots": 0, "lots_en_echec": 0}


def test_formater_vecteur() -> None:
    assert formater_vecteur([0.25, -1.5]) == "[0.25,-1.5]"


def test_main_exige_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL absente" in capsys.readouterr().err


def test_main_config_albert_manquante(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@localhost:5432/z")
    for variable in ("ALBERT_BASE_URL", "ALBERT_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.chdir(tmp_path)  # aucun .env parasite
    assert main([]) == 2
    assert "Configuration Albert invalide" in capsys.readouterr().err

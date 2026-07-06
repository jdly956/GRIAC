"""Tests S3.10 : orchestrateur du pipeline — enchaînement, politique d'échec, suivi."""

from sia_ingestion.pipeline import NOEUDS, executer_run


class FauxCurseur:
    def __init__(self, journal) -> None:
        self.journal = journal

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.journal.append((requete, parametres or {}))

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self) -> None:
        self.journal: list[tuple[str, dict]] = []
        self.commits = 0

    def cursor(self):
        return FauxCurseur(self.journal)

    def commit(self) -> None:
        self.commits += 1


def test_run_nominal_rapporte_noeud_par_noeud() -> None:
    connexion = FausseConnexion()
    appels: list[str] = []

    def noeud_ok(nom: str, corpus: str) -> int:
        appels.append(nom)
        return 0

    statut = executer_run(connexion, 1, "corpus", lancer_noeud=noeud_ok)
    assert statut == "termine"
    assert appels == list(NOEUDS)  # scan → parse → qualify → chunk → embed
    # Une mise à jour APRÈS CHAQUE nœud (l'écran de suivi lit en direct) + la finale.
    assert len(connexion.journal) == len(NOEUDS) + 1
    assert "termine_le = now()" in connexion.journal[-1][0]


def test_echecs_partiels_poursuivent(capsys=None) -> None:
    connexion = FausseConnexion()
    statut = executer_run(
        connexion, 1, "corpus", lancer_noeud=lambda nom, c: 1 if nom == "embed" else 0
    )
    assert statut == "echec_partiel"  # relance possible, reprise sur hash (D9)


def test_erreur_de_config_arrete_le_run() -> None:
    connexion = FausseConnexion()
    appels: list[str] = []

    def noeud(nom: str, corpus: str) -> int:
        appels.append(nom)
        return 2 if nom == "parse" else 0

    statut = executer_run(connexion, 1, "corpus", lancer_noeud=noeud)
    assert statut == "echec"
    assert appels == ["scan", "parse"]  # qualify/chunk/embed jamais lancés


def test_exception_imprevue_marque_l_echec() -> None:
    connexion = FausseConnexion()

    def noeud(nom: str, corpus: str) -> int:
        raise RuntimeError("disque plein")

    assert executer_run(connexion, 1, "corpus", lancer_noeud=noeud) == "echec"
    derniere = connexion.journal[-1]
    assert "disque plein" in derniere[1]["rapport"]

"""Tests E1-chunking : sections par titres, budget 500-800, tableaux entiers, reprise."""

from pathlib import Path

import pytest

from sia_ingestion.chunk import (
    TOKENS_MAX,
    chunker_markdown,
    decouper_en_blocs,
    estimer_tokens,
    main,
    traiter_documents,
)

PHRASE = "Le service instruit la demande dans les délais réglementaires prévus. "


def _paragraphe(nb_tokens: int) -> str:
    return (PHRASE * (nb_tokens * 4 // len(PHRASE) + 1))[: nb_tokens * 4]


def test_blocs_suivent_le_fil_des_titres() -> None:
    markdown = "# Guide\n\nIntro.\n\n## Installation\n\nÉtape une.\n\n## Usage\n\nÉtape deux.\n"
    blocs = decouper_en_blocs(markdown)
    assert [(bloc.section, bloc.contenu) for bloc in blocs] == [
        ("Guide", "Intro."),
        ("Guide > Installation", "Étape une."),
        ("Guide > Usage", "Étape deux."),
    ]


def test_tableau_est_un_bloc_atomique() -> None:
    markdown = "# T\n\nAvant.\n| a | b |\n|---|---|\n| 1 | 2 |\nAprès.\n"
    blocs = decouper_en_blocs(markdown)
    assert [bloc.est_tableau for bloc in blocs] == [False, True, False]
    assert blocs[1].contenu.count("|") >= 8


def test_petit_document_un_seul_chunk() -> None:
    chunks = chunker_markdown("# Doc\n\nUn paragraphe court.\n")
    assert len(chunks) == 1
    assert chunks[0].ordinal == 0
    assert chunks[0].section == "Doc"


def test_budget_max_respecte_hors_tableaux() -> None:
    markdown = "# Doc\n\n" + "\n\n".join(_paragraphe(300) for _ in range(6))
    chunks = chunker_markdown(markdown)
    assert len(chunks) > 1
    assert all(chunk.nb_tokens <= TOKENS_MAX + 50 for chunk in chunks)  # marge chevauchement


def test_tableau_geant_jamais_coupe() -> None:
    lignes = ["| colonne A | colonne B |", "|---|---|"] + [
        f"| valeur {i} très détaillée pour gonfler la taille | seuil {i} |" for i in range(200)
    ]
    markdown = "# Annexe\n\n" + "\n".join(lignes) + "\n"
    chunks = chunker_markdown(markdown)
    tableaux = [chunk for chunk in chunks if "| colonne A |" in chunk.contenu]
    assert len(tableaux) == 1  # le tableau entier vit dans UN chunk
    assert tableaux[0].contenu.count("| valeur") == 200  # aucune ligne perdue
    assert tableaux[0].nb_tokens > TOKENS_MAX  # la règle prime sur le budget


def test_chevauchement_entre_chunks_consecutifs() -> None:
    petits = "\n\n".join(_paragraphe(100) + f" repère-{i}." for i in range(20))
    chunks = chunker_markdown("# Doc\n\n" + petits)
    assert len(chunks) > 1
    # Le dernier morceau du chunk N ouvre le chunk N+1 (chevauchement).
    fin_premier = chunks[0].contenu.split("\n\n")[-1]
    assert chunks[1].contenu.startswith(fin_premier)


def test_paragraphe_geant_scinde() -> None:
    markdown = "# Doc\n\n" + "\n".join(_paragraphe(50) for _ in range(40))
    chunks = chunker_markdown(markdown)
    assert all(chunk.nb_tokens <= TOKENS_MAX + 50 for chunk in chunks)
    assert len(chunks) >= 2


def test_estimation_tokens() -> None:
    assert estimer_tokens("abcd" * 100) == 100
    assert estimer_tokens("") == 1


class FauxCurseur:
    def __init__(self, documents, chunks_existants: int) -> None:
        self.documents = documents
        self.chunks_existants = chunks_existants
        self.requetes: list[tuple[str, dict | None]] = []
        self._dernier: str = ""

    def execute(self, requete: str, parametres: dict | None = None) -> None:
        self.requetes.append((requete, parametres))
        self._dernier = requete

    def fetchall(self):
        return self.documents

    def fetchone(self):
        return (self.chunks_existants,)

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        pass


class FausseConnexion:
    def __init__(self, documents, chunks_existants: int = 0) -> None:
        self.curseur = FauxCurseur(documents, chunks_existants)
        self.commits = 0

    def cursor(self):
        return self.curseur

    def commit(self) -> None:
        self.commits += 1


def test_traitement_ecrit_les_chunks(tmp_path: Path) -> None:
    derive = tmp_path / "derived" / "md" / ("a" * 64 + ".md")
    derive.parent.mkdir(parents=True)
    derive.write_text("# Doc\n\nContenu du document.", encoding="utf-8")
    connexion = FausseConnexion([("p/doc.docx", "a" * 64, f"derived/md/{'a' * 64}.md")])

    statistiques = traiter_documents(connexion, tmp_path)

    assert statistiques == {"documents": 1, "inchanges": 0, "chunks": 1, "echecs": 0}
    requetes = [requete for requete, _ in connexion.curseur.requetes]
    assert any("DELETE FROM chunks" in requete for requete in requetes)
    assert any("INSERT INTO chunks" in requete for requete in requetes)
    assert connexion.commits == 1


def test_reprise_sur_hash_saute_les_inchanges(tmp_path: Path) -> None:
    connexion = FausseConnexion([("p/doc.docx", "a" * 64, "derived/md/x.md")], chunks_existants=3)
    statistiques = traiter_documents(connexion, tmp_path)
    assert statistiques["inchanges"] == 1
    assert statistiques["documents"] == 0
    assert not any("INSERT INTO chunks" in requete for requete, _ in connexion.curseur.requetes)


def test_derive_illisible_est_un_echec_isole(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    connexion = FausseConnexion(
        [
            ("p/absent.docx", "b" * 64, "derived/md/absent.md"),
        ]
    )
    statistiques = traiter_documents(connexion, tmp_path)
    assert statistiques["echecs"] == 1
    assert "échec — p/absent.docx" in capsys.readouterr().err


def test_main_exige_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL absente" in capsys.readouterr().err

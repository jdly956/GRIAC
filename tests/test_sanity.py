"""Test de socle S1.1 : interpréteur attendu et arborescence cible présente."""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REPERTOIRES_CIBLES = ["ingestion", "api", "web", "infra", "evals", "docs"]


def test_python_312() -> None:
    assert sys.version_info[:2] == (3, 12), (
        f"Python 3.12 attendu (stack CLAUDE.md), trouvé {sys.version}"
    )


def test_arborescence_cible() -> None:
    manquants = [d for d in REPERTOIRES_CIBLES if not (RACINE / d).is_dir()]
    assert manquants == [], f"Répertoires manquants : {manquants}"

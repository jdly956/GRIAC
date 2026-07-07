"""Corpus depuis l'UI — S3.10 : dépôt de documents + pipeline + suivi des runs.

Arbitrage du 06/07/2026 : indexation MANUELLE (bouton « Indexer maintenant »)
— maîtrise du quota d'embeddings (tpd). Le pipeline part en sous-processus
détaché (`python -m sia_ingestion.pipeline`) : sur le pod (pilote arbitré),
api et ingestion partagent le venv ; dans un déploiement conteneurisé par
image (compose/Helm), ce lancement exige l'image d'ingestion — limite
documentée, à traiter en E7. La sortie du sous-processus va dans un fichier
de log par run (`SIA_LOGS_DIR`).
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from sia_api.db import get_connexion

router = APIRouter(tags=["ingestion"])

Connexion = Annotated[Any, Depends(get_connexion)]

EXTENSIONS_ACCEPTEES = {".docx", ".pdf", ".md", ".txt", ".odt"}
TAILLE_MAX_OCTETS = 50 * 1024 * 1024  # au-delà, docling souffrira de toute façon


def dossier_corpus() -> Path:
    return Path(os.environ.get("SIA_CORPUS_DIR", "corpus"))


class DocumentDepose(BaseModel):
    chemin: str
    taille: int


class Run(BaseModel):
    id: int
    statut: str
    corpus: str
    rapport: dict
    demarre_le: str
    termine_le: str | None


@router.post("/documents/upload", status_code=201)
async def deposer_document(fichier: UploadFile) -> DocumentDepose:
    """Dépose un document dans le dossier corpus — indexé au prochain run."""
    nom = Path(fichier.filename or "").name  # neutralise tout chemin relatif
    if not nom:
        raise HTTPException(status_code=422, detail="Nom de fichier manquant.")
    extension = Path(nom).suffix.lower()
    if extension not in EXTENSIONS_ACCEPTEES:
        raise HTTPException(
            status_code=422,
            detail=f"Extension « {extension} » refusée — acceptées : "
            + ", ".join(sorted(EXTENSIONS_ACCEPTEES)),
        )
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(status_code=413, detail="Fichier > 50 Mo refusé.")
    destination = dossier_corpus() / nom
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(contenu)
    return DocumentDepose(chemin=str(destination), taille=len(contenu))


def _demarrer_pipeline(run_id: int, corpus: str) -> None:
    """Sous-processus détaché — remplacé dans les TU (jamais lancé en test)."""
    dossier_logs = Path(os.environ.get("SIA_LOGS_DIR", "."))
    dossier_logs.mkdir(parents=True, exist_ok=True)
    journal = open(dossier_logs / f"ingestion-run-{run_id}.log", "ab")  # noqa: SIM115
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "sia_ingestion.pipeline",
            "--corpus",
            corpus,
            "--run-id",
            str(run_id),
        ],
        stdout=journal,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # survit au redémarrage du worker api
    )


@router.post("/ingestion/lancer", status_code=202)
def lancer_ingestion(connexion: Connexion) -> Run:
    """Un seul run à la fois (409 sinon) — le quota d'embeddings se maîtrise mieux
    en série ; la relance reprend sur hash (D9)."""
    with connexion.cursor() as curseur:
        curseur.execute("SELECT id FROM ingestion_runs WHERE statut = 'en_cours'")
        en_cours = curseur.fetchone()
        if en_cours is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Le run {en_cours[0]} est déjà en cours — attendre sa fin "
                "(ou le marquer en échec s'il est bloqué).",
            )
        corpus = str(dossier_corpus())
        curseur.execute(
            "INSERT INTO ingestion_runs (corpus) VALUES (%(corpus)s) "
            "RETURNING id, statut, corpus, rapport, to_char(demarre_le, 'YYYY-MM-DD HH24:MI'), "
            "termine_le",
            {"corpus": corpus},
        )
        ligne = curseur.fetchone()
    connexion.commit()
    _demarrer_pipeline(ligne[0], corpus)
    return Run(
        id=ligne[0],
        statut=ligne[1],
        corpus=ligne[2],
        rapport=ligne[3] or {},
        demarre_le=ligne[4],
        termine_le=ligne[5],
    )


@router.get("/ingestion/runs")
def lister_runs(connexion: Connexion) -> list[Run]:
    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT id, statut, corpus, rapport, to_char(demarre_le, 'YYYY-MM-DD HH24:MI'), "
            "to_char(termine_le, 'YYYY-MM-DD HH24:MI') FROM ingestion_runs "
            "ORDER BY id DESC LIMIT 20"
        )
        return [
            Run(
                id=ligne[0],
                statut=ligne[1],
                corpus=ligne[2],
                rapport=ligne[3] or {},
                demarre_le=ligne[4],
                termine_le=ligne[5],
            )
            for ligne in curseur.fetchall()
        ]


@router.post("/ingestion/runs/{run_id}/echec")
def marquer_echec(run_id: int, connexion: Connexion) -> Run:
    """Débloque un run resté « en_cours » (processus mort sans rapport)."""
    with connexion.cursor() as curseur:
        curseur.execute(
            "UPDATE ingestion_runs SET statut = 'echec', termine_le = now() "
            "WHERE id = %(id)s RETURNING id, statut, corpus, rapport, "
            "to_char(demarre_le, 'YYYY-MM-DD HH24:MI'), to_char(termine_le, 'YYYY-MM-DD HH24:MI')",
            {"id": run_id},
        )
        ligne = curseur.fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} introuvable")
    connexion.commit()
    return Run(
        id=ligne[0],
        statut=ligne[1],
        corpus=ligne[2],
        rapport=ligne[3] or {},
        demarre_le=ligne[4],
        termine_le=ligne[5],
    )

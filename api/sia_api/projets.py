"""Entité Projet — contexte & NFR (S1.11, D19, prépare E8 puis E3).

CRUD minimal (création, lecture, mise à jour — l'écran DSFR arrive avec E4) et
association explicite projet ↔ dossiers documentaires (arbitrage A6) : la
suggestion inférée par S1.9 (`documents.projet_suggere`) est exposée par
`GET /dossiers/suggestions`, le PO confirme ou corrige via le champ `dossiers`
du projet. Les NFR typées seront injectées dans le prompt système et
pré-rempliront les blocs NFR de l'interview (E8/E3).
"""

from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sia_api.db import get_connexion

router = APIRouter(tags=["projets"])

# Connexion injectée par FastAPI (surchargée par les tests via dependency_overrides).
Connexion = Annotated[Any, Depends(get_connexion)]

TypeNFR = Literal[
    "performance",
    "volumetrie",
    "ssi",
    "rgpd",
    "accessibilite_rgaa",
    "disponibilite",
    "auditabilite",
]

OrigineDossier = Literal["po", "suggestion"]


class NFR(BaseModel):
    type: TypeNFR
    formulation: str = Field(min_length=1, description="formulation vérifiable")
    valeur_cible: str | None = None


class DossierAssocie(BaseModel):
    dossier: str = Field(min_length=1, description="1er niveau de chemin du corpus")
    origine: OrigineDossier = "po"


class ProjetEntree(BaseModel):
    nom: str = Field(min_length=1)
    contexte: str = ""
    nfrs: list[NFR] = []
    dossiers: list[DossierAssocie] = []


class Projet(ProjetEntree):
    id: int


class SuggestionDossier(BaseModel):
    dossier: str
    nb_documents: int
    deja_associe: bool


# --- Repository (SQL brut, connexion injectée — testé avec une fausse connexion) ---


def _remplacer_nfrs(curseur, projet_id: int, nfrs: list[NFR]) -> None:
    curseur.execute("DELETE FROM project_nfrs WHERE project_id = %(id)s", {"id": projet_id})
    for nfr in nfrs:
        curseur.execute(
            "INSERT INTO project_nfrs (project_id, type, formulation, valeur_cible) "
            "VALUES (%(id)s, %(type)s, %(formulation)s, %(valeur_cible)s)",
            {
                "id": projet_id,
                "type": nfr.type,
                "formulation": nfr.formulation,
                "valeur_cible": nfr.valeur_cible,
            },
        )


def _remplacer_dossiers(curseur, projet_id: int, dossiers: list[DossierAssocie]) -> None:
    curseur.execute("DELETE FROM project_dossiers WHERE project_id = %(id)s", {"id": projet_id})
    for dossier in dossiers:
        curseur.execute(
            "INSERT INTO project_dossiers (project_id, dossier, origine) "
            "VALUES (%(id)s, %(dossier)s, %(origine)s)",
            {"id": projet_id, "dossier": dossier.dossier, "origine": dossier.origine},
        )


def _lire_projet(curseur, projet_id: int) -> Projet | None:
    curseur.execute("SELECT id, nom, contexte FROM projects WHERE id = %(id)s", {"id": projet_id})
    ligne = curseur.fetchone()
    if ligne is None:
        return None
    curseur.execute(
        "SELECT type, formulation, valeur_cible FROM project_nfrs "
        "WHERE project_id = %(id)s ORDER BY id",
        {"id": projet_id},
    )
    nfrs = [NFR(type=n[0], formulation=n[1], valeur_cible=n[2]) for n in curseur.fetchall()]
    curseur.execute(
        "SELECT dossier, origine FROM project_dossiers WHERE project_id = %(id)s ORDER BY dossier",
        {"id": projet_id},
    )
    dossiers = [DossierAssocie(dossier=d[0], origine=d[1]) for d in curseur.fetchall()]
    return Projet(id=ligne[0], nom=ligne[1], contexte=ligne[2], nfrs=nfrs, dossiers=dossiers)


# --- Routes ---


@router.post("/projects", status_code=201)
def creer_projet(entree: ProjetEntree, connexion: Connexion) -> Projet:
    with connexion.cursor() as curseur:
        try:
            curseur.execute(
                "INSERT INTO projects (nom, contexte) VALUES (%(nom)s, %(contexte)s) RETURNING id",
                {"nom": entree.nom, "contexte": entree.contexte},
            )
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(
                status_code=409, detail=f"Projet « {entree.nom} » déjà existant"
            ) from exc
        projet_id = curseur.fetchone()[0]
        _remplacer_nfrs(curseur, projet_id, entree.nfrs)
        _remplacer_dossiers(curseur, projet_id, entree.dossiers)
        projet = _lire_projet(curseur, projet_id)
    connexion.commit()
    return projet


@router.get("/projects")
def lister_projets(connexion: Connexion) -> list[Projet]:
    with connexion.cursor() as curseur:
        curseur.execute("SELECT id FROM projects ORDER BY nom")
        identifiants = [ligne[0] for ligne in curseur.fetchall()]
        return [_lire_projet(curseur, identifiant) for identifiant in identifiants]


@router.get("/projects/{projet_id}")
def lire_projet(projet_id: int, connexion: Connexion) -> Projet:
    with connexion.cursor() as curseur:
        projet = _lire_projet(curseur, projet_id)
    if projet is None:
        raise HTTPException(status_code=404, detail=f"Projet {projet_id} introuvable")
    return projet


@router.put("/projects/{projet_id}")
def maj_projet(projet_id: int, entree: ProjetEntree, connexion: Connexion) -> Projet:
    with connexion.cursor() as curseur:
        curseur.execute(
            "UPDATE projects SET nom = %(nom)s, contexte = %(contexte)s, modifie_le = now() "
            "WHERE id = %(id)s RETURNING id",
            {"id": projet_id, "nom": entree.nom, "contexte": entree.contexte},
        )
        if curseur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"Projet {projet_id} introuvable")
        _remplacer_nfrs(curseur, projet_id, entree.nfrs)
        _remplacer_dossiers(curseur, projet_id, entree.dossiers)
        projet = _lire_projet(curseur, projet_id)
    connexion.commit()
    return projet


@router.get("/dossiers/suggestions")
def suggestions_dossiers(connexion: Connexion) -> list[SuggestionDossier]:
    """Suggestions issues de la qualification S1.9 — à confirmer ou corriger (A6)."""
    with connexion.cursor() as curseur:
        curseur.execute(
            """
            SELECT d.projet_suggere, count(*) AS nb_documents,
                   bool_or(pd.dossier IS NOT NULL) AS deja_associe
            FROM documents d
            LEFT JOIN project_dossiers pd ON pd.dossier = d.projet_suggere
            WHERE d.projet_suggere IS NOT NULL
            GROUP BY d.projet_suggere
            ORDER BY d.projet_suggere
            """
        )
        return [
            SuggestionDossier(dossier=ligne[0], nb_documents=ligne[1], deja_associe=ligne[2])
            for ligne in curseur.fetchall()
        ]

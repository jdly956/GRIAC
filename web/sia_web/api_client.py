"""Client serveur → api SIA PO (E4).

L'interface web ne parle jamais à PostgreSQL ni à Albert : elle consomme l'api
(URL via SIA_API_URL — compose : http://api:8000 ; pod mode B : localhost:8000).
Une api injoignable produit un statut 599 avec un détail lisible : l'écran
affiche l'erreur, jamais de traceback.
"""

import os
from typing import Any

import httpx

DELAI_S = 120.0  # les messages du workflow attendent une génération LLM


def url_api() -> str:
    return os.environ.get("SIA_API_URL", "http://localhost:8000").rstrip("/")


def appeler(methode: str, chemin: str, json: Any = None) -> tuple[int, Any]:
    """(statut, corps) — corps JSON décodé, ou {"detail": …} lisible en erreur."""
    try:
        reponse = httpx.request(methode, url_api() + chemin, json=json, timeout=DELAI_S)
    except httpx.HTTPError as erreur:
        return 599, {"detail": f"API injoignable ({url_api()}) : {type(erreur).__name__}"}
    try:
        return reponse.status_code, reponse.json()
    except ValueError:
        return reponse.status_code, {"brut": reponse.text}


def envoyer_fichier(chemin: str, nom: str, contenu: bytes, content_type: str) -> tuple[int, Any]:
    """POST multipart (dépôt de document, S3.10) — même contrat que `appeler`."""
    try:
        reponse = httpx.post(
            url_api() + chemin,
            files={"fichier": (nom, contenu, content_type or "application/octet-stream")},
            timeout=DELAI_S,
        )
    except httpx.HTTPError as erreur:
        return 599, {"detail": f"API injoignable ({url_api()}) : {type(erreur).__name__}"}
    try:
        return reponse.status_code, reponse.json()
    except ValueError:
        return reponse.status_code, {"brut": reponse.text}


def telecharger(chemin: str) -> tuple[int, str, str]:
    """(statut, contenu, content-type) — pour les exports E5 proxifiés."""
    try:
        reponse = httpx.get(url_api() + chemin, timeout=DELAI_S)
    except httpx.HTTPError as erreur:
        return 599, f"API injoignable : {type(erreur).__name__}", "text/plain"
    return reponse.status_code, reponse.text, reponse.headers.get("content-type", "text/plain")


def telecharger_binaire(chemin: str) -> tuple[int, bytes, str, str | None]:
    """(statut, octets, content-type, content-disposition) — originaux S3.17.

    Variante binaire de `telecharger` : un .docx/.pdf passé par `.text` serait
    corrompu. Le Content-Disposition de l'api (nom de fichier) est propagé.
    """
    try:
        reponse = httpx.get(url_api() + chemin, timeout=DELAI_S)
    except httpx.HTTPError as erreur:
        return 599, f"API injoignable : {type(erreur).__name__}".encode(), "text/plain", None
    return (
        reponse.status_code,
        reponse.content,
        reponse.headers.get("content-type", "application/octet-stream"),
        reponse.headers.get("content-disposition"),
    )

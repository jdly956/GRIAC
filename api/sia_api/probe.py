"""Sonde des limites Albert (S1.5) — cible `make probe`.

Relève, avant tout tuning (test no-go n°1, note de cadrage §6) : le catalogue
de modèles servi (GET /v1/models), les quotas du compte (GET /v1/me/info,
objet `limits`), puis vérifie qu'un appel de chat minimal et un appel
d'embeddings aboutissent sur les alias configurés. Écrit le rapport dans
`docs/albert-limits.md`. Une erreur réseau sur un relevé n'interrompt pas les
suivants ; la clé n'apparaît jamais dans le rapport ni dans la sortie (les
messages d'erreur sont expurgés par précaution).
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from sia_api.albert import creer_client
from sia_api.config import Settings, charger_settings

CHEMIN_RAPPORT = Path("docs/albert-limits.md")
COLONNES_MODELES = ("id", "type", "aliases", "max_context_length", "owned_by")


def relever_modeles(client: OpenAI) -> list[dict[str, Any]]:
    """GET /v1/models — catalogue complet tel que servi par Albert."""
    return [modele.model_dump() for modele in client.models.list().data]


def relever_quotas(settings: Settings) -> dict[str, Any]:
    """GET /v1/me/info — ne conserve que l'objet `limits` (jamais d'identifiants)."""
    reponse = httpx.get(
        settings.albert_base_url.rstrip("/") + "/me/info",
        headers={"Authorization": f"Bearer {settings.albert_api_key.get_secret_value()}"},
        timeout=settings.albert_timeout_s,
    )
    reponse.raise_for_status()
    limits = reponse.json().get("limits")
    if limits is None:
        return {"avertissement": "objet `limits` absent de la réponse — schéma à vérifier"}
    return {"limits": limits}


def tester_chat(client: OpenAI, settings: Settings) -> dict[str, Any]:
    """Un appel de chat minimal sur l'alias configuré.

    max_tokens large à dessein : les modèles à raisonnement (gpt-oss-120b)
    consomment des tokens de raisonnement AVANT le contenu — constaté sur le
    premier run pod (16 tokens => réponse vide). Une réponse vide est un échec
    explicite, pas un « ok » de façade : l'appel API qui aboutit ne suffit pas.
    """
    debut = time.perf_counter()
    reponse = client.chat.completions.create(
        model=settings.albert_model_chat,
        messages=[{"role": "user", "content": "Réponds uniquement : OK"}],
        max_tokens=512,
    )
    choix = reponse.choices[0]
    contenu = (choix.message.content or "").strip()
    if not contenu:
        raise RuntimeError(
            f"réponse de chat vide (finish_reason={choix.finish_reason}) — l'appel API "
            "aboutit mais aucun contenu n'est produit ; augmenter max_tokens ?"
        )
    return {
        "alias_demande": settings.albert_model_chat,
        "modele_resolu": reponse.model,
        "reponse": contenu,
        "finish_reason": choix.finish_reason,
        "latence_s": round(time.perf_counter() - debut, 2),
    }


def tester_embeddings(client: OpenAI, settings: Settings) -> dict[str, Any]:
    """Un appel d'embeddings minimal sur l'alias configuré.

    encoding_format="float" obligatoire : le défaut du SDK OpenAI est base64,
    non supporté par le serveur d'embeddings d'Albert (500 constaté sur pod,
    curl sans le paramètre = 200). À reproduire sur TOUT appel d'embeddings
    Albert via le SDK (ingestion E1 comprise).
    """
    debut = time.perf_counter()
    reponse = client.embeddings.create(
        model=settings.albert_model_embeddings,
        input="sonde SIA PO",
        encoding_format="float",
    )
    return {
        "alias_demande": settings.albert_model_embeddings,
        "modele_resolu": reponse.model,
        "dimension": len(reponse.data[0].embedding),
        "latence_s": round(time.perf_counter() - debut, 2),
    }


def _sans_cle(texte: str, settings: Settings) -> str:
    # Aucun message d'erreur ne doit pouvoir refléter la clé (corps 401, URL…).
    return texte.replace(settings.albert_api_key.get_secret_value(), "***")


def executer_sonde(client: OpenAI, settings: Settings) -> dict[str, Any]:
    """Déroule les 4 relevés ; une erreur sur l'un n'interrompt pas les autres."""
    releves = (
        ("modeles", lambda: {"modeles": relever_modeles(client)}),
        ("quotas", lambda: relever_quotas(settings)),
        ("chat", lambda: tester_chat(client, settings)),
        ("embeddings", lambda: tester_embeddings(client, settings)),
    )
    etapes: dict[str, dict[str, Any]] = {}
    for nom, releve in releves:
        try:
            etapes[nom] = {"statut": "ok", **releve()}
        except Exception as exc:  # réseau/HTTP/auth : géré, jamais de traceback
            etapes[nom] = {
                "statut": "échec",
                "erreur": _sans_cle(f"{type(exc).__name__}: {exc}", settings),
            }
    return {"base_url": settings.albert_base_url, "etapes": etapes}


def _tableau_modeles(modeles: list[dict[str, Any]]) -> str:
    lignes = [
        "| " + " | ".join(COLONNES_MODELES) + " |",
        "|" + "---|" * len(COLONNES_MODELES),
    ]
    lignes += [
        "| " + " | ".join(str(modele.get(col, "—")) for col in COLONNES_MODELES) + " |"
        for modele in modeles
    ]
    return "\n".join(lignes)


def generer_rapport(donnees: dict[str, Any], date_releve: str) -> str:
    """Markdown du rapport — uniquement des données issues de la sonde, jamais la clé."""
    etapes = donnees["etapes"]
    blocs = [
        "# Limites Albert — relevé `make probe` (S1.5)",
        "",
        f"Relevé du {date_releve} sur `{donnees['base_url']}`. Fichier généré — ne pas éditer.",
        "",
        "## Statut des relevés",
        "",
    ]
    for nom, etape in etapes.items():
        suffixe = f" — {etape['erreur']}" if etape["statut"] == "échec" else ""
        blocs.append(f"- **{nom}** : {etape['statut']}{suffixe}")
    if etapes["modeles"]["statut"] == "ok":
        blocs += [
            "",
            "## Modèles servis (GET /v1/models)",
            "",
            _tableau_modeles(etapes["modeles"]["modeles"]),
            "",
            "<details><summary>Réponse complète</summary>",
            "",
            "```json",
            json.dumps(etapes["modeles"]["modeles"], ensure_ascii=False, indent=2),
            "```",
            "",
            "</details>",
        ]
    if etapes["quotas"]["statut"] == "ok":
        contenu = {cle: val for cle, val in etapes["quotas"].items() if cle != "statut"}
        blocs += [
            "",
            "## Quotas du compte (GET /v1/me/info — objet `limits`)",
            "",
            "```json",
            json.dumps(contenu, ensure_ascii=False, indent=2),
            "```",
        ]
    titres = (("chat", "Appel de chat minimal"), ("embeddings", "Appel d'embeddings minimal"))
    for nom, titre in titres:
        if etapes[nom]["statut"] == "ok":
            details = {cle: val for cle, val in etapes[nom].items() if cle != "statut"}
            blocs += ["", f"## {titre}", ""]
            blocs += [f"- {cle} : `{val}`" for cle, val in details.items()]
    blocs.append("")
    return "\n".join(blocs)


def main() -> int:
    """Point d'entrée `make probe` : écrit le rapport, retourne 0 si tout est ok."""
    settings = charger_settings()
    client = creer_client(settings)
    donnees = executer_sonde(client, settings)
    date_releve = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    CHEMIN_RAPPORT.parent.mkdir(parents=True, exist_ok=True)
    CHEMIN_RAPPORT.write_text(generer_rapport(donnees, date_releve), encoding="utf-8")
    print(f"Rapport écrit : {CHEMIN_RAPPORT}")
    succes = True
    for nom, etape in donnees["etapes"].items():
        suffixe = f" — {etape['erreur']}" if etape["statut"] == "échec" else ""
        print(f"  {nom} : {etape['statut']}{suffixe}")
        succes = succes and etape["statut"] == "ok"
    return 0 if succes else 1


if __name__ == "__main__":
    raise SystemExit(main())

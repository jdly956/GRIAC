"""Client Albert — API compatible OpenAI (S1.5).

Point de construction unique du client vers Albert : `base_url` et clé
viennent exclusivement des Settings (S1.4), timeouts et retries sont
configurables par l'environnement (`ALBERT_TIMEOUT_S`, `ALBERT_MAX_RETRIES`).
Aucun appel réseau à l'import : le client se crée à la demande.
"""

from openai import OpenAI

from sia_api.config import Settings


def creer_client(settings: Settings) -> OpenAI:
    """Client OpenAI pointé sur Albert, timeouts et retries configurés."""
    return OpenAI(
        base_url=settings.albert_base_url,
        api_key=settings.albert_api_key.get_secret_value(),
        timeout=settings.albert_timeout_s,
        max_retries=settings.albert_max_retries,
    )

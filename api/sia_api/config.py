"""Configuration par variables d'environnement (S1.4).

Source unique de la configuration Albert : l'environnement (ou un fichier
`.env` en dev local — jamais commité, modèle dans `.env.example`). Aucune URL
ni clé en dur dans le code (contrainte CLAUDE.md). La clé est portée par un
``SecretStr`` : masquée dans les repr/str, donc jamais en clair dans les logs.
En déploiement Kubernetes, les variables viennent d'un Secret
(`infra/k8s/secret-albert.example.yaml`).
"""

from pydantic import SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables ALBERT_* — chaque champ correspond à la variable en majuscules.

    Les alias de modèles (`openweight-*`) sont les valeurs par défaut : ils
    survivent aux rotations du catalogue Albert (CLAUDE.md) ; on ne les
    surcharge qu'en cas de besoin (ex. benchmark E6).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    albert_base_url: str
    albert_api_key: SecretStr
    albert_model_chat: str = "openweight-large"
    albert_model_embeddings: str = "openweight-embeddings"
    albert_model_rerank: str = "openweight-rerank"
    # Réseau (S1.5) : appliqués au client Albert, surchargeables par env.
    albert_timeout_s: float = 30.0
    albert_max_retries: int = 2

    @field_validator("albert_base_url", "albert_api_key", mode="before")
    @classmethod
    def _vide_vaut_absent(cls, valeur: object) -> object:
        # Une variable présente mais vide (cas compose `${ALBERT_API_KEY:-}`)
        # doit produire le même échec explicite qu'une variable absente.
        if isinstance(valeur, str) and not valeur.strip():
            return None
        return valeur


def charger_settings() -> Settings:
    """Charge la configuration ou échoue proprement avec un message explicite.

    Le message ne cite que les NOMS des variables en cause, jamais leur
    valeur : aucune fuite possible de la clé par les logs de démarrage.
    """
    try:
        return Settings()
    except ValidationError as exc:
        variables = sorted({str(erreur["loc"][0]).upper() for erreur in exc.errors()})
        raise RuntimeError(
            "Configuration Albert invalide — variables d'environnement manquantes ou "
            f"vides : {', '.join(variables)}. En dev : copier .env.example vers .env "
            "puis renseigner la clé (cp .env.example .env). En déploiement : Secret "
            "Kubernetes (infra/k8s/secret-albert.example.yaml). La clé ne doit jamais "
            "figurer dans le repo ni dans les logs (CLAUDE.md)."
        ) from exc

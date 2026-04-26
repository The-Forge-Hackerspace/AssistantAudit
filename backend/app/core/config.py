"""
Configuration de l'application via Pydantic Settings.
Charge automatiquement les variables depuis .env
"""

import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _validate_hex_key(value: str, name: str, expected_len: int = 64) -> None:
    """Valide qu'une clé est un hex valide de la longueur attendue."""
    if len(value) != expected_len:
        raise ValueError(
            f"{name} doit faire exactement {expected_len} caractères hexadécimaux "
            f"(actuellement {len(value)}). "
            f"Générez avec : python -c 'import os; print(os.urandom(32).hex())'"
        )
    try:
        bytes.fromhex(value)
    except ValueError:
        raise ValueError(
            f"{name} contient des caractères non-hexadécimaux. "
            f"Générez avec : python -c 'import os; print(os.urandom(32).hex())'"
        )


# Racine du projet (2 niveaux au-dessus de ce fichier)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Configuration centralisée de l'application"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "AssistantAudit"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENV: str = "development"  # development | testing | production
    SQL_ECHO: bool = False

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- Base de données ---
    # PostgreSQL par défaut en production, SQLite en dev si non configuré
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'instance' / 'assistantaudit.db'}"

    # --- Chiffrement au repos (AES-256-GCM) ---
    # 64 caractères hex = 32 bytes = 256 bits. Générer avec :
    # python -c 'import os; print(os.urandom(32).hex())'
    ENCRYPTION_KEY: str = ""  # Clé pour EncryptedText (colonnes sensibles en base)
    FILE_ENCRYPTION_KEY: str = ""  # KEK pour envelope encryption (fichiers sur disque)

    # --- Certificats mTLS (communication serveur ↔ agent) ---
    CA_CERT_PATH: str = str(BASE_DIR / "certs" / "ca.pem")
    CA_KEY_PATH: str = str(BASE_DIR / "certs" / "ca.key")
    CRL_PATH: str = str(BASE_DIR / "certs" / "crl.pem")

    # --- Sécurité / JWT ---
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"

    def model_post_init(self, __context):
        """Initialise la SECRET_KEY après le chargement de la config."""
        # Si SECRET_KEY n'est pas définie, la générer
        if not self.SECRET_KEY:
            env_key = os.getenv("SECRET_KEY")
            if env_key:
                self.SECRET_KEY = env_key
            else:
                # Générer une clé sécurisée automatiquement en développement
                self.SECRET_KEY = secrets.token_urlsafe(64)
                if self.ENV in ("production", "preprod", "staging"):
                    raise ValueError(
                        "ERREUR CRITIQUE: SECRET_KEY doit être défini en production!\n"
                        "Générez une clé avec: python -c 'import secrets; print(secrets.token_urlsafe(64))'\n"
                        "Puis ajoutez SECRET_KEY=<clé> dans votre fichier .env"
                    )
                logger.warning(
                    "SECRET_KEY non définie — clé auto-générée pour le développement. "
                    "Définissez SECRET_KEY dans .env pour la persistance entre redémarrages."
                )

        # Avertissement si SECRET_KEY trop courte en non-production
        if len(self.SECRET_KEY) < 32 and self.ENV not in ("production", "preprod", "staging"):
            logger.warning(
                "SECRET_KEY fait moins de 32 caractères (%d). Utilisez une clé plus longue pour plus de sécurité.",
                len(self.SECRET_KEY),
            )

        # Validation des clés hex dès qu'elles sont renseignées (tout environnement)
        if self.ENCRYPTION_KEY:
            _validate_hex_key(self.ENCRYPTION_KEY, "ENCRYPTION_KEY")
        if self.FILE_ENCRYPTION_KEY:
            _validate_hex_key(self.FILE_ENCRYPTION_KEY, "FILE_ENCRYPTION_KEY")

        # Validation en production
        is_safe_env = self.ENV in ("production", "preprod", "staging")
        if is_safe_env and len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY trop courte en production (min 32 caractères). "
                "Générez-en une avec : python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        if is_safe_env and not self.ENCRYPTION_KEY:
            raise ValueError(
                "ENCRYPTION_KEY doit être défini en production (64 hex chars = 256 bits). "
                "Générez avec : python -c 'import os; print(os.urandom(32).hex())'"
            )
        if is_safe_env and not self.FILE_ENCRYPTION_KEY:
            raise ValueError(
                "FILE_ENCRYPTION_KEY doit être défini en production (64 hex chars = 256 bits). "
                "Générez avec : python -c 'import os; print(os.urandom(32).hex())'"
            )

        # Validation CORS en production : pas de wildcard
        if is_safe_env:
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CORS_ORIGINS ne doit pas contenir '*' en production. Listez explicitement les origines autorisées."
                )
            for origin in self.CORS_ORIGINS:
                if not origin.startswith(("http://", "https://")):
                    raise ValueError(
                        f"CORS_ORIGINS invalide : '{origin}' — chaque origine doit commencer par http:// ou https://"
                    )

    # --- CORS ---
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = [
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ]

    # --- Upload ---
    MAX_CONFIG_UPLOAD_SIZE_MB: int = 5  # taille max fichier config analysis

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Sécur: accès court (15 min), refresh plus long
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Uploads ---
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 16

    # --- Frameworks / Référentiels ---
    FRAMEWORKS_DIR: str = str(BASE_DIR.parent / "frameworks")

    # --- WebSocket agents (fiabilisation TOS-12) ---
    # Delai sans heartbeat avant de considerer un agent offline et de marquer
    # ses taches running/dispatched/pending comme failed.
    AGENT_HEARTBEAT_TIMEOUT_SECONDS: int = 90
    # Frequence du sweeper qui detecte les agents timeout.
    AGENT_HEARTBEAT_SWEEP_INTERVAL_SECONDS: int = 15

    # --- Collectes orphelines (TOS-16) ---
    # Une collecte SSH/WinRM dispatchee sur un agent reste en `running` tant
    # que l'agent n'a pas renvoye de task_result. Si l'agent disparait (perte
    # WS, crash) avant de repondre, la collecte resterait bloquee. Le sweeper
    # marque FAILED toute collecte `running` plus ancienne que ce delai.
    COLLECT_TIMEOUT_SECONDS: int = 15 * 60
    COLLECT_SWEEP_INTERVAL_SECONDS: int = 60

    # --- Outils intégrés ---
    NMAP_TIMEOUT: int = 600  # secondes
    MONKEY365_PATH: str = ""  # chemin vers Invoke-Monkey365.ps1
    MONKEY365_TIMEOUT: int = 600  # secondes
    MONKEY365_AUTO_CLONE: bool = False  # autoriser le clonage git automatique de monkey365

    # --- Données / Stockage ---
    DATA_DIR: str = "./data"  # base directory for scan output storage

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = str(BASE_DIR / "logs")

    # --- Monitoring: Sentry ---
    SENTRY_DSN: str = ""  # Sentry error tracking DSN (optional)
    SENTRY_TRACING_ENABLED: bool = False  # Enable performance tracing (uses more resources)
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # Fraction of transactions to trace (0.0-1.0)

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


@lru_cache()
def get_settings() -> Settings:
    """Retourne l'instance de settings (singleton via cache)"""
    s = Settings()
    return s

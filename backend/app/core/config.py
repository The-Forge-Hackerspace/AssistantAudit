"""
Configuration de l'application via Pydantic Settings.
Charge automatiquement les variables depuis .env
"""
import os
import secrets
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'instance' / 'assistantaudit.db'}"

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
        
        # Validation en production
        is_safe_env = self.ENV in ("production", "preprod", "staging")
        if is_safe_env and len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY trop courte en production (min 32 caractères). "
                "Générez-en une avec : python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )

    # --- CORS ---
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = [
        "Authorization", "Content-Type", "Accept",
        "Origin", "X-Requested-With",
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

    # --- Outils intégrés ---
    NMAP_TIMEOUT: int = 600  # secondes
    MONKEY365_PATH: str = ""  # chemin vers Invoke-Monkey365.ps1
    MONKEY365_TIMEOUT: int = 600  # secondes

    # --- PingCastle ---
    PINGCASTLE_PATH: str = ""  # chemin vers PingCastle.exe
    PINGCASTLE_TIMEOUT: int = 300  # secondes
    PINGCASTLE_OUTPUT_DIR: str = str(BASE_DIR / "uploads" / "pingcastle")

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

"""
Schémas Pydantic pour les pipelines de collecte (TOS-13 / US009).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class PipelineCreate(BaseModel):
    """Paramètres pour lancer un pipeline multi-étapes scan → equipements → collectes."""

    site_id: int = Field(..., description="Site sur lequel rattacher les équipements")
    agent_id: int = Field(..., description="Agent qui exécutera le scan Nmap")
    target: str = Field(
        ...,
        description="IP, CIDR ou hostname à scanner",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/\-]{0,254}$",
        examples=["192.168.1.0/24", "10.0.0.1"],
    )

    # Credentials communs utilisés pour toutes les collectes
    username: str = Field(..., min_length=1, max_length=255)
    password: Optional[str] = Field(None, max_length=4096)
    private_key: Optional[str] = Field(None, max_length=32768, description="Clé privée SSH au format PEM")
    passphrase: Optional[str] = Field(None, max_length=4096)

    # Options WinRM
    use_ssl: bool = Field(False, description="Utiliser WinRM HTTPS (port 5986) quand applicable")
    transport: Literal["ntlm", "basic", "kerberos", "credssp"] = Field(
        "ntlm", description="Mécanisme d'authentification WinRM"
    )

    @model_validator(mode="after")
    def _check_credentials(self) -> "PipelineCreate":
        if not self.password and not self.private_key:
            raise ValueError("Un mot de passe ou une clé privée est requis")
        return self


class PipelineRead(BaseModel):
    """État complet d'un pipeline (exposé au frontend)."""

    id: int
    site_id: int
    created_by: int
    target: str

    status: str
    error_message: Optional[str] = None

    agent_id: Optional[int] = None
    scan_task_uuid: Optional[str] = None
    scan_status: str
    hosts_discovered: int

    equipments_status: str
    equipments_created: int
    hosts_skipped: int

    collects_status: str
    collects_total: int
    collects_done: int
    collects_failed: int

    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

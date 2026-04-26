"""
Schemas Agent : gestion des agents et taches.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

# Liste fermee des outils que l'agent peut etre autorise a executer.
# Toute valeur hors de ce set est rejetee a la creation et a l'update.
SUPPORTED_AGENT_TOOLS: tuple[str, ...] = (
    "nmap",
    "oradad",
    "config-oradad",
    "ad_collector",
    "ssh-collect",
    "winrm-collect",
)

# ── Requetes ──────────────────────────────────────────────────────────


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    allowed_tools: list[str] = Field(default=list(SUPPORTED_AGENT_TOOLS))
    target_user_id: Optional[int] = None

    @field_validator("allowed_tools")
    @classmethod
    def _validate_tools(cls, v: list[str]) -> list[str]:
        invalid = [t for t in v if t not in SUPPORTED_AGENT_TOOLS]
        if invalid:
            raise ValueError(f"Outils non supportes : {invalid}")
        return v


class AgentUpdateRequest(BaseModel):
    """Update partiel d'un agent — uniquement les champs administrables."""

    allowed_tools: Optional[list[str]] = Field(default=None)

    @field_validator("allowed_tools")
    @classmethod
    def _validate_tools(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        invalid = [t for t in v if t not in SUPPORTED_AGENT_TOOLS]
        if invalid:
            raise ValueError(f"Outils non supportes : {invalid}")
        return v


class EnrollRequest(BaseModel):
    enrollment_code: str = Field(..., min_length=1, max_length=20)


class HeartbeatRequest(BaseModel):
    agent_version: Optional[str] = None
    os_info: Optional[str] = None


class TaskDispatchRequest(BaseModel):
    agent_uuid: str = Field(..., min_length=1)
    audit_id: Optional[int] = None
    tool: str = Field(..., min_length=1, max_length=50)
    parameters: dict = Field(default_factory=dict)


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(running|completed|failed|cancelled)$")
    error_message: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class TaskResultSubmit(BaseModel):
    result_summary: Optional[dict] = None
    result_raw: Optional[str] = None
    error_message: Optional[str] = None


# ── Reponses ──────────────────────────────────────────────────────────


class AgentCreateResponse(BaseModel):
    agent_uuid: str
    enrollment_code: str
    expires_at: datetime


class EnrollResponse(BaseModel):
    agent_uuid: str
    agent_token: str
    client_cert_pem: str
    client_key_pem: str
    ca_cert_pem: str = ""
    allowed_tools: list[str] = []
    agent_name: str = ""


class AgentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    agent_uuid: str
    name: str
    status: str
    last_seen: Optional[datetime] = None
    last_ip: Optional[str] = None
    allowed_tools: list[str]
    os_info: Optional[str] = None
    agent_version: Optional[str] = None
    owner_name: Optional[str] = None
    revoked_at: Optional[datetime] = None
    cert_expires_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer("last_seen", "revoked_at", "cert_expires_at", "created_at")
    @classmethod
    def serialize_utc(cls, v: datetime | None) -> str | None:
        """Force le suffixe Z sur les datetimes — SQLite retourne des naive datetimes."""
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class TaskResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    task_uuid: str
    agent_id: int
    owner_id: int
    audit_id: Optional[int] = None
    tool: str
    parameters: dict
    status: str
    progress: int
    status_message: Optional[str] = None
    result_summary: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    dispatched_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_serializer("created_at", "dispatched_at", "started_at", "completed_at")
    @classmethod
    def serialize_utc(cls, v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


# ── Artifacts ──────────────────────────────────────────────────────────


class ArtifactUploadResponse(BaseModel):
    file_id: int
    filename: str
    size: int


class ArtifactRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    file_uuid: str
    original_filename: str
    mime_type: str
    file_size: int
    uploaded_at: datetime
    download_url: str = ""

"""
Schemas Agent : gestion des agents et taches.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Requetes ──────────────────────────────────────────────────────────


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    allowed_tools: list[str] = Field(
        default=["nmap", "oradad", "ad_collector"]
    )


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
    created_at: datetime


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

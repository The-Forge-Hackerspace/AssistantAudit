from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

LINK_TYPE_PATTERN = r"^(ethernet|fiber|wifi|vpn|wan|serial|other)$"


class NetworkLinkBase(BaseModel):
    source_equipement_id: int
    target_equipement_id: int
    source_interface: Optional[str] = Field(default=None, max_length=100)
    target_interface: Optional[str] = Field(default=None, max_length=100)
    link_type: str = Field(default="ethernet", pattern=LINK_TYPE_PATTERN)
    bandwidth: Optional[str] = Field(default=None, max_length=50)
    vlan: Optional[str] = Field(default=None, max_length=100)
    network_segment: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None


class NetworkLinkCreate(NetworkLinkBase):
    site_id: int


class NetworkLinkUpdate(BaseModel):
    source_interface: Optional[str] = Field(default=None, max_length=100)
    target_interface: Optional[str] = Field(default=None, max_length=100)
    link_type: Optional[str] = Field(default=None, pattern=LINK_TYPE_PATTERN)
    bandwidth: Optional[str] = Field(default=None, max_length=50)
    vlan: Optional[str] = Field(default=None, max_length=100)
    network_segment: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None


class NetworkLinkRead(NetworkLinkBase):
    id: int
    site_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NetworkLayoutSaveRequest(BaseModel):
    layout_data: dict


class NetworkMapNode(BaseModel):
    id: str
    equipement_id: int
    site_id: int
    type_equipement: str
    ip_address: str
    hostname: Optional[str] = None
    label: str
    metadata: dict = {}
    position: Optional[dict] = None


class NetworkMapEdge(BaseModel):
    id: str
    link_id: int
    source: str
    target: str
    metadata: dict = {}


class NetworkMapRead(BaseModel):
    site_id: int
    nodes: list[NetworkMapNode]
    edges: list[NetworkMapEdge]
    layout_data: dict = {}


class SiteConnectionBase(BaseModel):
    source_site_id: int
    target_site_id: int
    link_type: str = Field(default="wan", pattern=r"^(wan|vpn|mpls|sdwan|other)$")
    bandwidth: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class SiteConnectionCreate(SiteConnectionBase):
    entreprise_id: int


class SiteConnectionUpdate(BaseModel):
    link_type: Optional[str] = Field(default=None, pattern=r"^(wan|vpn|mpls|sdwan|other)$")
    bandwidth: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class SiteConnectionRead(SiteConnectionBase):
    id: int
    entreprise_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MultiSiteNode(BaseModel):
    id: str
    site_id: int
    site_name: str
    equipement_count: int


class MultiSiteEdge(BaseModel):
    id: str
    connection_id: int
    source: str
    target: str
    metadata: dict = {}


class MultiSiteOverviewRead(BaseModel):
    entreprise_id: int
    nodes: list[MultiSiteNode]
    edges: list[MultiSiteEdge]

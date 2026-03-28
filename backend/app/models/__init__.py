"""
Package models : tous les modèles SQLAlchemy.
Importés ici pour qu'Alembic et create_all les détectent automatiquement.
"""
from .user import User
from .entreprise import Entreprise, Contact
from .audit import Audit, AuditStatus
from .site import Site
from .equipement import (
    Equipement,
    EquipementReseau,
    EquipementServeur,
    EquipementFirewall,
    EquipementSwitch,
    EquipementRouter,
    EquipementAccessPoint,
    EquipementPrinter,
    EquipementCamera,
    EquipementNAS,
    EquipementHyperviseur,
    EquipementTelephone,
    EquipementIoT,
    EquipementCloudGateway,
    EquipementAuditStatus,
    EQUIPEMENT_TYPE_VALUES,
    EQUIPEMENT_TYPE_CLASS_MAP,
)
from .scan import ScanReseau, ScanHost, ScanPort
from .network_map import NetworkLink, NetworkMapLayout, SiteConnection
from .framework import (
    Framework,
    FrameworkCategory,
    Control,
    ControlSeverity,
    CheckType,
)
from .assessment import (
    AssessmentCampaign,
    Assessment,
    ControlResult,
    ComplianceStatus,
    CampaignStatus,
)
from .attachment import Attachment
from .config_analysis import ConfigAnalysis
from .collect_result import CollectResult, CollectMethod, CollectStatus
from .ad_audit_result import ADAuditResultModel, ADAuditStatus
from .monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus
from .agent import Agent
from .agent_task import AgentTask
from .task_artifact import TaskArtifact
from .anssi_checklist import AnssiCheckpoint

__all__ = [
    "User",
    "Entreprise",
    "Contact",
    "Audit",
    "AuditStatus",
    "Site",
    "Equipement",
    "EquipementReseau",
    "EquipementServeur",
    "EquipementFirewall",
    "EquipementSwitch",
    "EquipementRouter",
    "EquipementAccessPoint",
    "EquipementPrinter",
    "EquipementCamera",
    "EquipementNAS",
    "EquipementHyperviseur",
    "EquipementTelephone",
    "EquipementIoT",
    "EquipementCloudGateway",
    "EquipementAuditStatus",
    "EQUIPEMENT_TYPE_VALUES",
    "EQUIPEMENT_TYPE_CLASS_MAP",
    "ScanReseau",
    "ScanHost",
    "ScanPort",
    "NetworkLink",
    "NetworkMapLayout",
    "SiteConnection",
    "Framework",
    "FrameworkCategory",
    "Control",
    "ControlSeverity",
    "CheckType",
    "AssessmentCampaign",
    "Assessment",
    "ControlResult",
    "ComplianceStatus",
    "CampaignStatus",
    "ConfigAnalysis",
    "CollectResult",
    "CollectMethod",
    "CollectStatus",
    "ADAuditResultModel",
    "ADAuditStatus",
    "Monkey365ScanResult",
    "Monkey365ScanStatus",
    "Agent",
    "AgentTask",
    "TaskArtifact",
    "AnssiCheckpoint",
]

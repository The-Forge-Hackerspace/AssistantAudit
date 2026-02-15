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
    EquipementAuditStatus,
)
from .scan import ScanReseau, ScanHost, ScanPort
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
from .pingcastle_result import PingCastleResult, PingCastleStatus

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
    "EquipementAuditStatus",
    "ScanReseau",
    "ScanHost",
    "ScanPort",
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
    "PingCastleResult",
    "PingCastleStatus",
]

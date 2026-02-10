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
]

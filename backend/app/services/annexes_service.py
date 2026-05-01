"""Service de generation des annexes du rapport (TOS-25 section 7).

Aggrege les donnees de l'audit pour les annexes :
- Liste des equipements audites
- Recapitulatif des resultats par controle (statuts agreges)
- Liste des frameworks utilises avec leur version
"""

import logging

from sqlalchemy.orm import Session

from ..core.helpers import check_audit_access
from ..models.assessment import (
    AssessmentCampaign,
    ComplianceStatus,
)
from ..models.equipement import Equipement
from ..models.site import Site
from ..schemas.annexes import (
    AnnexControlResult,
    AnnexEquipement,
    AnnexFramework,
    AuditAnnexes,
)

logger = logging.getLogger(__name__)


class AnnexesService:
    """Calcule les donnees consolidees pour les annexes d'un audit."""

    @staticmethod
    def generate(
        db: Session, audit_id: int, user_id: int, is_admin: bool
    ) -> AuditAnnexes:
        """Donnees consolidees pour les annexes du rapport."""
        audit = check_audit_access(db, audit_id, user_id, is_admin)

        campaigns = (
            db.query(AssessmentCampaign)
            .filter(AssessmentCampaign.audit_id == audit.id)
            .all()
        )

        # --- Equipements audites (deduplique sur eq.id) ---
        eq_ids: set[int] = set()
        equipements: list[AnnexEquipement] = []
        sites_cache: dict[int, str] = {}
        for camp in campaigns:
            for assess in camp.assessments:
                if not assess.equipement or assess.equipement.id in eq_ids:
                    continue
                eq_ids.add(assess.equipement.id)
                eq: Equipement = assess.equipement
                site_name = None
                if eq.site_id:
                    if eq.site_id not in sites_cache:
                        site = db.query(Site).filter(Site.id == eq.site_id).first()
                        sites_cache[eq.site_id] = site.nom if site else ""
                    site_name = sites_cache.get(eq.site_id) or None
                equipements.append(
                    AnnexEquipement(
                        hostname=eq.hostname,
                        ip_address=eq.ip_address,
                        type_equipement=eq.type_equipement or "equipement",
                        site_name=site_name,
                    )
                )
        equipements.sort(key=lambda e: (e.site_name or "", e.hostname or e.ip_address or ""))

        # --- Recapitulatif par controle ---
        # control_id -> {ref, title, severity, framework_name, count par statut}
        results_acc: dict[int, dict] = {}
        for camp in campaigns:
            for assess in camp.assessments:
                fw_name = assess.framework.name if assess.framework else ""
                for r in assess.results:
                    if not r.control:
                        continue
                    cid = r.control.id
                    if cid not in results_acc:
                        results_acc[cid] = {
                            "control_ref": r.control.ref_id,
                            "title": r.control.title,
                            "severity": r.control.severity.value,
                            "framework_name": fw_name,
                            "compliant": 0,
                            "non_compliant": 0,
                            "not_applicable": 0,
                            "pending": 0,
                        }
                    if r.status == ComplianceStatus.COMPLIANT:
                        results_acc[cid]["compliant"] += 1
                    elif r.status == ComplianceStatus.NON_COMPLIANT:
                        results_acc[cid]["non_compliant"] += 1
                    elif r.status == ComplianceStatus.NOT_APPLICABLE:
                        results_acc[cid]["not_applicable"] += 1
                    else:
                        results_acc[cid]["pending"] += 1

        results = [AnnexControlResult(**v) for v in results_acc.values()]
        results.sort(key=lambda r: (r.framework_name, r.control_ref))

        # --- Frameworks utilises (deduplique) ---
        fw_ids: set[int] = set()
        frameworks: list[AnnexFramework] = []
        for camp in campaigns:
            for assess in camp.assessments:
                fw = assess.framework
                if not fw or fw.id in fw_ids:
                    continue
                fw_ids.add(fw.id)
                frameworks.append(
                    AnnexFramework(
                        ref_id=fw.ref_id,
                        name=fw.name,
                        version=fw.version,
                        source=fw.source or None,
                        author=fw.author or None,
                    )
                )
        frameworks.sort(key=lambda f: f.name)

        return AuditAnnexes(
            audit_id=audit.id,
            equipements=equipements,
            results=results,
            frameworks=frameworks,
        )

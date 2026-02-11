"""
Service Assessment : campagnes d'évaluation, scoring, résultats.
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.assessment import (
    AssessmentCampaign,
    Assessment,
    ControlResult,
    CampaignStatus,
    ComplianceStatus,
)
from ..models.framework import Framework
from ..models.equipement import Equipement

logger = logging.getLogger(__name__)


class AssessmentService:

    # --- Campagnes ---

    @staticmethod
    def create_campaign(
        db: Session, name: str, audit_id: int, description: str = None
    ) -> AssessmentCampaign:
        """Crée une nouvelle campagne d'évaluation"""
        campaign = AssessmentCampaign(
            name=name,
            description=description,
            audit_id=audit_id,
            status=CampaignStatus.DRAFT,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info(f"Campagne créée : '{name}' pour audit #{audit_id}")
        return campaign

    @staticmethod
    def get_campaign(db: Session, campaign_id: int) -> Optional[AssessmentCampaign]:
        return db.get(AssessmentCampaign, campaign_id)

    @staticmethod
    def list_campaigns(
        db: Session, audit_id: int = None, offset: int = 0, limit: int = 20
    ) -> tuple[list[AssessmentCampaign], int]:
        query = db.query(AssessmentCampaign)
        if audit_id:
            query = query.filter(AssessmentCampaign.audit_id == audit_id)
        total = query.count()
        campaigns = query.order_by(AssessmentCampaign.created_at.desc()).offset(offset).limit(limit).all()
        return campaigns, total

    @staticmethod
    def update_campaign(db: Session, campaign_id: int, data) -> AssessmentCampaign:
        """Met à jour une campagne (nom, description, statut)"""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data:
            update_data["status"] = CampaignStatus(update_data["status"])
        for field, value in update_data.items():
            setattr(campaign, field, value)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def start_campaign(db: Session, campaign_id: int) -> AssessmentCampaign:
        """Démarre une campagne"""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        campaign.status = CampaignStatus.IN_PROGRESS
        campaign.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def complete_campaign(db: Session, campaign_id: int) -> AssessmentCampaign:
        """Termine une campagne"""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    # --- Assessments (évaluation d'un équipement) ---

    @staticmethod
    def create_assessment(
        db: Session,
        campaign_id: int,
        equipement_id: int,
        framework_id: int,
        assessed_by: str = None,
    ) -> Assessment:
        """
        Crée un assessment : lie un équipement à un framework dans une campagne.
        Génère automatiquement les ControlResult (un par contrôle du framework).
        """
        # Vérifications
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")

        equipement = db.get(Equipement, equipement_id)
        if not equipement:
            raise ValueError(f"Équipement {equipement_id} introuvable")

        framework = db.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework {framework_id} introuvable")

        # Créer l'assessment
        assessment = Assessment(
            campaign_id=campaign_id,
            equipement_id=equipement_id,
            framework_id=framework_id,
            assessed_by=assessed_by,
        )
        db.add(assessment)
        db.flush()

        # Générer un ControlResult pour chaque contrôle du framework
        control_count = 0
        for category in framework.categories:
            for control in category.controls:
                result = ControlResult(
                    assessment_id=assessment.id,
                    control_id=control.id,
                    status=ComplianceStatus.NOT_ASSESSED,
                )
                db.add(result)
                control_count += 1

        db.commit()
        db.refresh(assessment)
        logger.info(
            f"Assessment créé : équipement #{equipement_id} × "
            f"framework '{framework.ref_id}' → {control_count} contrôles"
        )
        return assessment

    @staticmethod
    def get_assessment(db: Session, assessment_id: int) -> Optional[Assessment]:
        return db.get(Assessment, assessment_id)

    # --- Résultats de contrôle ---

    @staticmethod
    def update_control_result(
        db: Session,
        result_id: int,
        status: str,
        evidence: str = None,
        comment: str = None,
        remediation_note: str = None,
        assessed_by: str = None,
    ) -> ControlResult:
        """Met à jour le résultat d'un contrôle"""
        result = db.get(ControlResult, result_id)
        if not result:
            raise ValueError(f"ControlResult {result_id} introuvable")

        result.status = ComplianceStatus(status)
        result.evidence = evidence
        result.comment = comment
        result.remediation_note = remediation_note
        result.assessed_by = assessed_by
        result.assessed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def bulk_update_results(
        db: Session,
        updates: list[dict],
        assessed_by: str = None,
    ) -> int:
        """Met à jour plusieurs résultats en une fois (ex: résultats auto)"""
        count = 0
        now = datetime.now(timezone.utc)
        for upd in updates:
            result = db.get(ControlResult, upd["result_id"])
            if not result:
                continue
            result.status = ComplianceStatus(upd["status"])
            result.evidence = upd.get("evidence")
            result.auto_result = upd.get("auto_result")
            result.is_auto_assessed = upd.get("is_auto", False)
            result.assessed_by = assessed_by
            result.assessed_at = now
            count += 1

        db.commit()
        logger.info(f"Mise à jour en masse : {count} résultats")
        return count

    @staticmethod
    def compute_score(results: list[ControlResult]) -> dict:
        """
        Calcule un score de conformité détaillé à partir d'une liste de ControlResult.
        Retourne un dict compatible avec ScoreResponse.
        """
        total = len(results)
        counts = defaultdict(int)
        by_severity = defaultdict(lambda: defaultdict(int))

        for r in results:
            counts[r.status.value] += 1
            sev = r.control.severity.value if r.control else "unknown"
            by_severity[sev]["total"] += 1
            by_severity[sev][r.status.value] += 1

        assessed = total - counts["not_assessed"] - counts["not_applicable"]
        score = None
        if assessed > 0:
            score = round(
                (counts["compliant"] + 0.5 * counts["partially_compliant"]) / assessed * 100, 1
            )

        return {
            "compliance_score": score,
            "total_controls": total,
            "assessed_controls": assessed,
            "compliant": counts["compliant"],
            "non_compliant": counts["non_compliant"],
            "partially_compliant": counts["partially_compliant"],
            "not_applicable": counts["not_applicable"],
            "not_assessed": counts["not_assessed"],
            "by_severity": dict(by_severity),
        }

    @staticmethod
    def get_assessment_score(db: Session, assessment_id: int) -> dict | None:
        """Calcule le score d'un assessment"""
        assessment = db.get(Assessment, assessment_id)
        if not assessment:
            return None
        return AssessmentService.compute_score(assessment.results)

    @staticmethod
    def get_campaign_score(db: Session, campaign_id: int) -> dict | None:
        """Calcule le score d'une campagne (agrégé sur tous ses assessments)"""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            return None
        all_results = []
        for assessment in campaign.assessments:
            all_results.extend(assessment.results)
        return AssessmentService.compute_score(all_results)

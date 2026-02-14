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
from ..models.equipement import Equipement, EquipementAuditStatus

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

        # Si le statut change vers in_progress ou completed, déléguer aux méthodes dédiées
        if "status" in update_data:
            new_status = CampaignStatus(update_data["status"])
            if new_status == CampaignStatus.IN_PROGRESS and campaign.status != CampaignStatus.IN_PROGRESS:
                return AssessmentService.start_campaign(db, campaign_id)
            if new_status == CampaignStatus.COMPLETED and campaign.status != CampaignStatus.COMPLETED:
                return AssessmentService.complete_campaign(db, campaign_id)
            update_data["status"] = new_status

        for field, value in update_data.items():
            setattr(campaign, field, value)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def start_campaign(db: Session, campaign_id: int) -> AssessmentCampaign:
        """Démarre une campagne et passe les équipements associés en EN_COURS."""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        campaign.status = CampaignStatus.IN_PROGRESS
        campaign.started_at = datetime.now(timezone.utc)

        # Passer tous les équipements liés à cette campagne en EN_COURS
        for assessment in campaign.assessments:
            eq = db.get(Equipement, assessment.equipement_id)
            if eq and eq.status_audit == EquipementAuditStatus.A_AUDITER:
                eq.status_audit = EquipementAuditStatus.EN_COURS
                logger.info(f"Équipement #{eq.id} '{eq.hostname}' → EN_COURS (campagne démarrée)")

        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def complete_campaign(db: Session, campaign_id: int) -> AssessmentCampaign:
        """Termine une campagne et met à jour le statut des équipements."""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.now(timezone.utc)

        # Mettre à jour le statut de chaque équipement selon ses résultats
        for assessment in campaign.assessments:
            eq = db.get(Equipement, assessment.equipement_id)
            if not eq:
                continue
            score = AssessmentService.compute_score(assessment.results)
            if score["non_compliant"] > 0:
                eq.status_audit = EquipementAuditStatus.NON_CONFORME
            elif score["assessed_controls"] > 0 and score["non_compliant"] == 0:
                eq.status_audit = EquipementAuditStatus.CONFORME
            logger.info(
                f"Équipement #{eq.id} '{eq.hostname}' → {eq.status_audit.value} "
                f"(campagne terminée, score={score['compliance_score']}%)"
            )

        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def delete_campaign(db: Session, campaign_id: int) -> None:
        """Supprime une campagne et tous ses assessments/résultats associés."""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        db.delete(campaign)
        db.commit()
        logger.info(f"Campagne supprimée : id={campaign_id} '{campaign.name}'")

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

        # Vérifier qu'il n'existe pas déjà un assessment pour cette combinaison
        existing = db.query(Assessment).filter_by(
            campaign_id=campaign_id,
            equipement_id=equipement_id,
            framework_id=framework_id,
        ).first()
        if existing:
            raise ValueError(
                f"Un assessment existe déjà pour cette combinaison "
                f"(campagne={campaign_id}, équipement={equipement_id}, framework={framework_id})"
            )

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

        # Si la campagne est déjà en cours, passer l'équipement en EN_COURS
        if campaign.status == CampaignStatus.IN_PROGRESS:
            if equipement.status_audit == EquipementAuditStatus.A_AUDITER:
                equipement.status_audit = EquipementAuditStatus.EN_COURS
                logger.info(f"Équipement #{equipement_id} '{equipement.hostname}' → EN_COURS (assessment créé)")

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

    @staticmethod
    def delete_assessment(db: Session, assessment_id: int) -> None:
        """Supprime un assessment et tous ses résultats de contrôle / pièces jointes."""
        assessment = db.get(Assessment, assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} introuvable")
        db.delete(assessment)
        db.commit()
        logger.info(f"Assessment supprimé : id={assessment_id}")

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
        if evidence is not None:
            result.evidence = evidence
        if comment is not None:
            result.comment = comment
        if remediation_note is not None:
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

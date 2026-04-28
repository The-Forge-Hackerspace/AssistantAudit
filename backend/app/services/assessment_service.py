"""
Service Assessment : campagnes d'évaluation, scoring, résultats.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from ..core.errors import NotFoundError
from ..core.helpers import get_or_404
from ..models.assessment import (
    Assessment,
    AssessmentCampaign,
    CampaignStatus,
    ComplianceStatus,
    ControlResult,
)
from ..models.audit import Audit
from ..models.equipement import Equipement, EquipementAuditStatus
from ..models.framework import Control, Framework
from ..models.monkey365_scan_result import Monkey365ScanResult, Monkey365ScanStatus
from ..models.site import Site

logger = logging.getLogger(__name__)


class AssessmentService:
    @staticmethod
    def _check_audit_access(
        db: Session,
        audit_id: int,
        user_id: int | None,
        is_admin: bool,
    ) -> None:
        """Verifie l'acces a un audit. 404 si non autorise."""
        if is_admin or user_id is None:
            return
        audit = get_or_404(db, Audit, audit_id)
        if audit.owner_id != user_id:
            raise NotFoundError("Ressource introuvable")

    @staticmethod
    def _check_campaign_access(
        db: Session,
        campaign: AssessmentCampaign,
        user_id: int | None,
        is_admin: bool,
    ) -> None:
        """Verifie l'acces via Campaign → Audit."""
        AssessmentService._check_audit_access(db, campaign.audit_id, user_id, is_admin)

    @staticmethod
    def _check_assessment_access(
        db: Session,
        assessment: Assessment,
        user_id: int | None,
        is_admin: bool,
    ) -> None:
        """Verifie l'acces via Assessment → Campaign → Audit."""
        campaign = db.get(AssessmentCampaign, assessment.campaign_id)
        if not campaign:
            raise NotFoundError("Ressource introuvable")
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)

    # --- Campagnes ---

    @staticmethod
    def create_campaign(
        db: Session,
        name: str,
        audit_id: int,
        description: str = None,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> AssessmentCampaign:
        """Crée une nouvelle campagne d'évaluation"""
        AssessmentService._check_audit_access(db, audit_id, user_id, is_admin)
        campaign = AssessmentCampaign(
            name=name,
            description=description,
            audit_id=audit_id,
            status=CampaignStatus.DRAFT,
        )
        db.add(campaign)
        db.flush()
        db.refresh(campaign)
        logger.info(f"Campagne créée : '{name}' pour audit #{audit_id}")
        return campaign

    @staticmethod
    def get_campaign(
        db: Session,
        campaign_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> Optional[AssessmentCampaign]:
        campaign = db.get(AssessmentCampaign, campaign_id)
        if campaign:
            AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)
        return campaign

    @staticmethod
    def list_campaigns(
        db: Session,
        audit_id: int = None,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> tuple[list[AssessmentCampaign], int]:
        """
        List assessment campaigns with pagination.
        Optimized to avoid N+1 queries by eagerly loading assessments.
        """
        if audit_id:
            AssessmentService._check_audit_access(db, audit_id, user_id, is_admin)

        query = db.query(AssessmentCampaign).options(
            selectinload(AssessmentCampaign.assessments),
            selectinload(AssessmentCampaign.audit),
        )
        if audit_id:
            query = query.filter(AssessmentCampaign.audit_id == audit_id)
        elif user_id is not None and not is_admin:
            query = query.join(Audit, AssessmentCampaign.audit_id == Audit.id).filter(Audit.owner_id == user_id)
        total = query.count()
        campaigns = query.order_by(AssessmentCampaign.created_at.desc()).offset(offset).limit(limit).all()
        return campaigns, total

    @staticmethod
    def update_campaign(
        db: Session,
        campaign_id: int,
        data,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> AssessmentCampaign:
        """Met à jour une campagne (nom, description, statut)"""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)
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
        db.flush()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def start_campaign(
        db: Session,
        campaign_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> AssessmentCampaign:
        """Démarre une campagne et passe les équipements associés en EN_COURS."""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)
        campaign.status = CampaignStatus.IN_PROGRESS
        campaign.started_at = datetime.now(timezone.utc)

        # Passer tous les équipements liés à cette campagne en EN_COURS
        for assessment in campaign.assessments:
            eq = db.get(Equipement, assessment.equipement_id)
            if eq and eq.status_audit == EquipementAuditStatus.A_AUDITER:
                eq.status_audit = EquipementAuditStatus.EN_COURS
                logger.info(f"Équipement #{eq.id} '{eq.hostname}' → EN_COURS (campagne démarrée)")

        db.flush()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def complete_campaign(
        db: Session,
        campaign_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> AssessmentCampaign:
        """Termine une campagne et met à jour le statut des équipements."""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)
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

        db.flush()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def delete_campaign(
        db: Session,
        campaign_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        """Supprime une campagne et tous ses assessments/résultats associés."""
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)
        db.delete(campaign)
        db.flush()
        logger.info(f"Campagne supprimée : id={campaign_id} '{campaign.name}'")

    # --- Assessments (évaluation d'un équipement) ---

    @staticmethod
    def create_assessment(
        db: Session,
        campaign_id: int,
        equipement_id: int,
        framework_id: int,
        assessed_by: str | None = None,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> Assessment:
        """
        Crée un assessment : lie un équipement à un framework dans une campagne.
        Génère automatiquement les ControlResult (un par contrôle du framework).
        """
        # Vérifications
        campaign = db.get(AssessmentCampaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campagne {campaign_id} introuvable")
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)

        equipement = db.get(Equipement, equipement_id)
        if not equipement:
            raise ValueError(f"Équipement {equipement_id} introuvable")

        framework = db.get(Framework, framework_id)
        if not framework:
            raise ValueError(f"Framework {framework_id} introuvable")

        # Vérifier qu'il n'existe pas déjà un assessment pour cette combinaison
        existing = (
            db.query(Assessment)
            .filter_by(
                campaign_id=campaign_id,
                equipement_id=equipement_id,
                framework_id=framework_id,
            )
            .first()
        )
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

        db.flush()
        db.refresh(assessment)
        logger.info(
            f"Assessment créé : équipement #{equipement_id} × "
            f"framework '{framework.ref_id}' → {control_count} contrôles"
        )
        return assessment

    @staticmethod
    def get_assessment(
        db: Session,
        assessment_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> Optional[Assessment]:
        assessment = db.get(Assessment, assessment_id)
        if assessment:
            AssessmentService._check_assessment_access(db, assessment, user_id, is_admin)
        return assessment

    @staticmethod
    def delete_assessment(
        db: Session,
        assessment_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        """Supprime un assessment et tous ses résultats de contrôle / pièces jointes."""
        assessment = db.get(Assessment, assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} introuvable")
        AssessmentService._check_assessment_access(db, assessment, user_id, is_admin)
        db.delete(assessment)
        db.flush()
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
        assessed_by: str | None = None,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> ControlResult:
        """Met à jour le résultat d'un contrôle"""
        result = db.get(ControlResult, result_id)
        if not result:
            raise ValueError(f"ControlResult {result_id} introuvable")
        assessment = db.get(Assessment, result.assessment_id)
        if assessment:
            AssessmentService._check_assessment_access(db, assessment, user_id, is_admin)

        result.status = ComplianceStatus(status)
        if evidence is not None:
            result.evidence = evidence
        if comment is not None:
            result.comment = comment
        if remediation_note is not None:
            result.remediation_note = remediation_note
        result.assessed_by = assessed_by
        result.assessed_at = datetime.now(timezone.utc)

        db.flush()
        db.refresh(result)
        return result

    @staticmethod
    def bulk_update_results(
        db: Session,
        updates: list[dict],
        assessed_by: str | None = None,
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

        db.flush()
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
            score = round((counts["compliant"] + 0.5 * counts["partially_compliant"]) / assessed * 100, 1)

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
    def get_assessment_score(
        db: Session,
        assessment_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> dict | None:
        """
        Calculate compliance score for an assessment.
        Optimized to eagerly load control results.
        """
        assessment = (
            db.query(Assessment)
            .options(
                selectinload(Assessment.results).selectinload(ControlResult.control),
            )
            .filter(Assessment.id == assessment_id)
            .first()
        )

        if not assessment:
            return None
        AssessmentService._check_assessment_access(db, assessment, user_id, is_admin)
        return AssessmentService.compute_score(assessment.results)

    @staticmethod
    def get_campaign_score(
        db: Session,
        campaign_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> dict | None:
        """
        Calculate compliance score for a campaign (aggregated across all assessments).
        Optimized to eagerly load assessment results.
        """
        campaign = (
            db.query(AssessmentCampaign)
            .options(
                selectinload(AssessmentCampaign.assessments).selectinload(Assessment.results),
            )
            .filter(AssessmentCampaign.id == campaign_id)
            .first()
        )

        if not campaign:
            return None
        AssessmentService._check_campaign_access(db, campaign, user_id, is_admin)
        all_results = []
        for assessment in campaign.assessments:
            all_results.extend(assessment.results)
        return AssessmentService.compute_score(all_results)

    # ── Importation Monkey365 ─────────────────────────────────────────────────

    @staticmethod
    def import_monkey365_scan(
        db: Session,
        scan_result_id: int,
        audit_id: int,
        assessed_by: str | None = None,
    ) -> dict:
        """
        Importe un scan Monkey365 réussi dans un audit existant.

        - Crée (ou réutilise) un équipement virtuel cloud_gateway par site
        - Crée une campagne et un assessment liés au framework CIS-M365-V5
        - Remplit les ControlResult automatiquement à partir des findings Monkey365
        - Démarre la campagne (statut IN_PROGRESS)

        Retourne : { campaign_id, assessment_id, controls_mapped, controls_total }
        """
        from ..tools.monkey365_runner.parser import Monkey365Parser

        # Charger et valider le scan
        scan = db.get(Monkey365ScanResult, scan_result_id)
        if not scan:
            raise ValueError(f"Scan Monkey365 #{scan_result_id} introuvable")
        if scan.status != Monkey365ScanStatus.SUCCESS:
            raise ValueError("L'import n'est possible que pour les scans réussis")

        # Charger et valider l'audit
        audit = db.get(Audit, audit_id)
        if not audit:
            raise ValueError(f"Audit #{audit_id} introuvable")
        if audit.entreprise_id != scan.entreprise_id:
            raise ValueError("Le scan Monkey365 appartient à une entreprise différente de l'audit cible")

        # Trouver le framework CIS-M365-V5
        framework = db.query(Framework).filter(Framework.ref_id == "CIS-M365-V5").first()
        if not framework:
            raise ValueError("Framework CIS-M365-V5 introuvable — vérifiez que le YAML a bien été importé")

        # Trouver ou créer le site dédié aux audits Microsoft 365.
        # On cherche explicitement nom='Cloud' pour éviter de prendre
        # un site physique existant et de mélanger cloud/on-prem.
        site = (
            db.query(Site)
            .filter(
                Site.entreprise_id == scan.entreprise_id,
                Site.nom == "Cloud",
            )
            .first()
        )
        if not site:
            site = Site(
                nom="Cloud",
                description="Site virtuel créé automatiquement pour les audits Microsoft 365",
                entreprise_id=scan.entreprise_id,
            )
            db.add(site)
            db.flush()
            logger.info(f"Site virtuel 'Cloud' créé pour entreprise #{scan.entreprise_id}")

        # Trouver ou créer un équipement virtuel cloud_gateway (IP 0.0.0.0 par site)
        virtual_eq = (
            db.query(Equipement)
            .filter(
                Equipement.site_id == site.id,
                Equipement.ip_address == "0.0.0.0",
                Equipement.type_equipement == "cloud_gateway",
            )
            .first()
        )
        if not virtual_eq:
            virtual_eq = Equipement(
                site_id=site.id,
                ip_address="0.0.0.0",
                type_equipement="cloud_gateway",
                hostname="Microsoft 365 Tenant",
            )
            db.add(virtual_eq)
            db.flush()
            logger.info(f"Équipement virtuel cloud_gateway créé pour site #{site.id}")

        # Créer la campagne
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entreprise_label = scan.entreprise_slug or f"entreprise-{scan.entreprise_id}"
        campaign_name = f"Audit M365 Cloud — {entreprise_label} — {date_str}"

        campaign = AssessmentCampaign(
            name=campaign_name,
            description=f"Import automatique du scan Monkey365 #{scan_result_id}",
            audit_id=audit_id,
            status=CampaignStatus.DRAFT,
        )
        db.add(campaign)
        db.flush()

        # Créer l'assessment
        assessment = Assessment(
            campaign_id=campaign.id,
            equipement_id=virtual_eq.id,
            framework_id=framework.id,
            assessed_by=assessed_by,
        )
        db.add(assessment)
        db.flush()

        # Générer un ControlResult par contrôle du framework
        all_controls: list[Control] = []
        for category in framework.categories:
            all_controls.extend(category.controls)

        results_by_control: dict[int, ControlResult] = {}
        for control in all_controls:
            cr = ControlResult(
                assessment_id=assessment.id,
                control_id=control.id,
                status=ComplianceStatus.NOT_ASSESSED,
            )
            db.add(cr)
            results_by_control[control.id] = cr
        db.flush()

        # Parser les findings Monkey365
        scan_dir: Path | None = None
        if scan.output_path:
            candidate = Path(scan.output_path)
            if candidate.exists():
                scan_dir = candidate

        findings_by_rule: dict[str, str] = {}
        if scan_dir:
            try:
                findings = Monkey365Parser.parse_output_directory(str(scan_dir))
                for f in findings:
                    if f.rule_id:
                        findings_by_rule[f.rule_id.lower()] = f.status_text
                logger.info(f"Monkey365Parser : {len(findings)} findings, {len(findings_by_rule)} règles distinctes")
            except Exception:
                logger.exception("Erreur lors du parsing des findings Monkey365")
        else:
            logger.warning(f"Aucun répertoire de sortie accessible pour le scan #{scan_result_id}")

        # Mapping status_text → ComplianceStatus
        STATUS_MAP = {
            "compliant": ComplianceStatus.COMPLIANT,
            "non_compliant": ComplianceStatus.NON_COMPLIANT,
            "partially_compliant": ComplianceStatus.PARTIALLY_COMPLIANT,
            "not_assessed": ComplianceStatus.NOT_ASSESSED,
        }

        # Appliquer les findings aux ControlResult
        controls_mapped = 0
        now = datetime.now(timezone.utc)
        for control in all_controls:
            rule_id = control.engine_rule_id
            if not rule_id:
                continue
            status_text = findings_by_rule.get(rule_id.lower())
            if status_text and status_text in STATUS_MAP:
                cr = results_by_control.get(control.id)
                if cr is None:
                    continue
                cr.status = STATUS_MAP[status_text]
                cr.is_auto_assessed = True
                cr.assessed_by = assessed_by or "monkey365"
                cr.assessed_at = now
                controls_mapped += 1

        # Démarrer la campagne
        campaign.status = CampaignStatus.IN_PROGRESS
        campaign.started_at = now
        virtual_eq.status_audit = EquipementAuditStatus.EN_COURS

        db.flush()
        db.refresh(campaign)
        db.refresh(assessment)

        logger.info(
            f"Import Monkey365 #{scan_result_id} → audit #{audit_id} : "
            f"campagne #{campaign.id}, assessment #{assessment.id}, "
            f"{controls_mapped}/{len(all_controls)} contrôles mappés"
        )

        return {
            "campaign_id": campaign.id,
            "assessment_id": assessment.id,
            "controls_mapped": controls_mapped,
            "controls_total": len(all_controls),
        }

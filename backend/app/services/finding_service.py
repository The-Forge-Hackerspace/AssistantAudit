"""Service Finding — logique métier pour les non-conformités."""

from ..core.errors import BusinessRuleError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.assessment import Assessment, AssessmentCampaign, ComplianceStatus, ControlResult
from ..models.audit import Audit
from ..models.finding import (
    VALID_TRANSITIONS,
    Finding,
    FindingStatus,
    FindingStatusHistory,
)


class FindingService:
    """Opérations CRUD et métier sur les findings."""

    @staticmethod
    def generate_from_assessment(db: Session, assessment_id: int, user_id: int | None = None) -> tuple[int, int]:
        """
        Génère des findings pour chaque ControlResult NON_COMPLIANT
        ou PARTIALLY_COMPLIANT d'un assessment donné.

        Retourne (generated, skipped).
        """
        # Récupérer les ControlResult non-conformes
        results = (
            db.execute(
                select(ControlResult).where(
                    ControlResult.assessment_id == assessment_id,
                    ControlResult.status.in_(
                        [
                            ComplianceStatus.NON_COMPLIANT,
                            ComplianceStatus.PARTIALLY_COMPLIANT,
                        ]
                    ),
                )
            )
            .scalars()
            .all()
        )

        generated = 0
        skipped = 0

        for cr in results:
            # Vérifier qu'un finding n'existe pas déjà pour ce ControlResult
            existing = db.execute(
                select(Finding).where(
                    Finding.control_result_id == cr.id,
                    Finding.assessment_id == assessment_id,
                )
            ).scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            severity = cr.control.severity.value if cr.control else "medium"
            title = cr.control.title if cr.control else f"Contrôle #{cr.control_id}"

            finding = Finding(
                control_result_id=cr.id,
                assessment_id=assessment_id,
                equipment_id=cr.assessment.equipement_id,
                title=title,
                description=cr.comment,
                severity=severity,
                status=FindingStatus.OPEN,
                remediation_note=cr.remediation_note,
                created_by=user_id,
            )
            db.add(finding)
            generated += 1

        db.flush()
        db.commit()
        return generated, skipped

    @staticmethod
    def get_finding(db: Session, finding_id: int) -> Finding | None:
        """Récupère un finding par ID."""
        return db.get(Finding, finding_id)

    @staticmethod
    def list_findings(
        db: Session,
        *,
        assessment_id: int | None = None,
        equipment_id: int | None = None,
        status: str | None = None,
        severity: str | None = None,
        offset: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> tuple[list[Finding], int]:
        """
        Liste les findings avec filtres optionnels.
        Retourne (findings, total).
        """
        query = select(Finding)
        count_query = select(func.count(Finding.id))

        # RBAC : restreindre aux audits de l'utilisateur
        if user_id is not None and not is_admin:
            owned_finding_ids = (
                select(Finding.id)
                .select_from(Finding)
                .join(Assessment, Finding.assessment_id == Assessment.id)
                .join(AssessmentCampaign, Assessment.campaign_id == AssessmentCampaign.id)
                .join(Audit, AssessmentCampaign.audit_id == Audit.id)
                .where(Audit.owner_id == user_id)
                .scalar_subquery()
            )
            query = query.where(Finding.id.in_(owned_finding_ids))
            count_query = count_query.where(Finding.id.in_(owned_finding_ids))

        if assessment_id is not None:
            query = query.where(Finding.assessment_id == assessment_id)
            count_query = count_query.where(Finding.assessment_id == assessment_id)
        if equipment_id is not None:
            query = query.where(Finding.equipment_id == equipment_id)
            count_query = count_query.where(Finding.equipment_id == equipment_id)
        if status is not None:
            try:
                parsed_status = FindingStatus(status)
            except ValueError:
                raise BusinessRuleError(f"Statut invalide : '{status}'. Valeurs acceptées : {', '.join(s.value for s in FindingStatus)}")
            query = query.where(Finding.status == parsed_status)
            count_query = count_query.where(Finding.status == parsed_status)
        if severity is not None:
            query = query.where(Finding.severity == severity)
            count_query = count_query.where(Finding.severity == severity)

        total = db.execute(count_query).scalar() or 0

        findings = db.execute(query.order_by(Finding.created_at.desc()).offset(offset).limit(limit)).scalars().all()

        return list(findings), total

    @staticmethod
    def update_status(
        db: Session,
        finding: Finding,
        new_status_str: str,
        user_id: int | None = None,
        comment: str | None = None,
        assigned_to: str | None = None,
    ) -> Finding:
        """
        Transition de statut avec validation et audit trail.
        Lève ValueError si la transition n'est pas autorisée.
        """
        new_status = FindingStatus(new_status_str)
        old_status = finding.status

        if new_status not in VALID_TRANSITIONS.get(old_status, set()):
            raise ValueError(
                f"Transition invalide : {old_status.value} → {new_status.value}. "
                f"Transitions autorisées : {', '.join(s.value for s in VALID_TRANSITIONS.get(old_status, set()))}"
            )

        # Enregistrer l'historique
        history = FindingStatusHistory(
            finding_id=finding.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=user_id,
            comment=comment,
        )
        db.add(history)

        # Mettre à jour le finding
        finding.status = new_status
        if assigned_to is not None:
            finding.assigned_to = assigned_to

        db.flush()
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def link_duplicate(
        db: Session,
        finding: Finding,
        duplicate_of_id: int,
    ) -> Finding:
        """
        Lie un finding comme doublon d'un autre.
        Le finding secondaire hérite du statut de remédiation.
        """
        original = db.get(Finding, duplicate_of_id)
        if original is None:
            raise ValueError(f"Finding original #{duplicate_of_id} introuvable")

        if original.id == finding.id:
            raise ValueError("Un finding ne peut pas être doublon de lui-même")

        finding.duplicate_of_id = duplicate_of_id

        # Hériter du statut de remédiation si applicable
        if original.remediation_note and not finding.remediation_note:
            finding.remediation_note = original.remediation_note

        db.flush()
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def counts_by_status(
        db: Session,
        assessment_id: int | None = None,
    ) -> dict[str, int]:
        """Compteurs par statut pour un assessment donné."""
        query = select(Finding.status, func.count(Finding.id))
        if assessment_id is not None:
            query = query.where(Finding.assessment_id == assessment_id)
        query = query.group_by(Finding.status)

        rows = db.execute(query).all()
        counts = {s.value: 0 for s in FindingStatus}
        total = 0
        for status, count in rows:
            counts[status.value] = count
            total += count
        counts["total"] = total
        return counts

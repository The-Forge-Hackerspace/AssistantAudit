"""
Routes Assessments : campagnes, évaluations, résultats de contrôle.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import PaginationParams, RbacContext, get_current_auditeur, get_rbac_context, get_rbac_context_auditeur
from ...models.user import User
from ...schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    CampaignCreate,
    CampaignRead,
    CampaignSummary,
    CampaignUpdate,
    ControlResultUpdate,
    M365ScanResponse,
    M365ScanSimulateRequest,
)
from ...schemas.common import MessageResponse, PaginatedResponse, ScoreResponse
from ...services.assessment_service import AssessmentService
from ...services.monkey365_service import Monkey365Service

router = APIRouter()


# --- Campagnes ---


@router.get("/campaigns", response_model=PaginatedResponse[CampaignSummary])
def list_campaigns(
    audit_id: int = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Liste les campagnes d'évaluation"""
    uid, adm = rbac.user_id, rbac.is_admin
    campaigns, total = AssessmentService.list_campaigns(
        db,
        audit_id=audit_id,
        offset=pagination.offset,
        limit=pagination.page_size,
        user_id=uid,
        is_admin=adm,
    )
    items = []
    for c in campaigns:
        items.append(
            CampaignSummary(
                id=c.id,
                name=c.name,
                status=c.status.value,
                audit_id=c.audit_id,
                created_at=c.created_at,
                compliance_score=c.compliance_score,
                total_assessments=len(c.assessments),
            )
        )
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("/campaigns", response_model=CampaignSummary, status_code=status.HTTP_201_CREATED)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Crée une nouvelle campagne d'évaluation"""
    uid, adm = rbac.user_id, rbac.is_admin
    campaign = AssessmentService.create_campaign(
        db,
        name=body.name,
        audit_id=body.audit_id,
        description=body.description,
        user_id=uid,
        is_admin=adm,
    )
    return CampaignSummary(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status.value,
        audit_id=campaign.audit_id,
        created_at=campaign.created_at,
        compliance_score=None,
        total_assessments=0,
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignRead)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Détail d'une campagne avec ses assessments"""
    uid, adm = rbac.user_id, rbac.is_admin
    campaign = AssessmentService.get_campaign(db, campaign_id, user_id=uid, is_admin=adm)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignSummary)
def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Met à jour une campagne (nom, description, statut)"""
    uid, adm = rbac.user_id, rbac.is_admin
    campaign = AssessmentService.update_campaign(
        db,
        campaign_id,
        body,
        user_id=uid,
        is_admin=adm,
    )
    return CampaignSummary(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status.value,
        audit_id=campaign.audit_id,
        created_at=campaign.created_at,
        compliance_score=campaign.compliance_score,
        total_assessments=len(campaign.assessments),
    )


@router.post("/campaigns/{campaign_id}/start", response_model=MessageResponse)
def start_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Démarre une campagne"""
    uid, adm = rbac.user_id, rbac.is_admin
    AssessmentService.start_campaign(db, campaign_id, user_id=uid, is_admin=adm)
    return MessageResponse(message="Campagne démarrée")


@router.post("/campaigns/{campaign_id}/complete", response_model=MessageResponse)
def complete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Termine une campagne"""
    uid, adm = rbac.user_id, rbac.is_admin
    AssessmentService.complete_campaign(db, campaign_id, user_id=uid, is_admin=adm)
    return MessageResponse(message="Campagne terminée")


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Supprime une campagne et toutes ses évaluations"""
    uid, adm = rbac.user_id, rbac.is_admin
    AssessmentService.delete_campaign(db, campaign_id, user_id=uid, is_admin=adm)


# --- Assessments ---


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: AssessmentCreate,
    campaign_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Crée un assessment (évaluation d'un équipement selon un référentiel)"""
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id est requis en query param")
    uid, adm = rbac.user_id, rbac.is_admin
    assessment = AssessmentService.create_assessment(
        db,
        campaign_id=campaign_id,
        equipement_id=body.equipement_id,
        framework_id=body.framework_id,
        assessed_by=current_user.username,
        user_id=uid,
        is_admin=adm,
    )
    return assessment


@router.get("/{assessment_id}", response_model=AssessmentRead)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Détail d'un assessment avec tous ses résultats de contrôle"""
    uid, adm = rbac.user_id, rbac.is_admin
    assessment = AssessmentService.get_assessment(db, assessment_id, user_id=uid, is_admin=adm)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment introuvable")
    return assessment


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Supprime un assessment et tous ses résultats"""
    uid, adm = rbac.user_id, rbac.is_admin
    AssessmentService.delete_assessment(db, assessment_id, user_id=uid, is_admin=adm)


# --- Résultats de contrôle ---


@router.put("/results/{result_id}", response_model=MessageResponse)
def update_control_result(
    result_id: int,
    body: ControlResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """Met à jour le résultat d'un contrôle"""
    uid, adm = rbac.user_id, rbac.is_admin
    AssessmentService.update_control_result(
        db,
        result_id=result_id,
        status=body.status,
        evidence=body.evidence,
        comment=body.comment,
        remediation_note=body.remediation_note,
        assessed_by=current_user.username,
        user_id=uid,
        is_admin=adm,
    )
    return MessageResponse(message="Résultat mis à jour")


# --- Scoring ---


@router.get("/{assessment_id}/score", response_model=ScoreResponse)
def get_assessment_score(
    assessment_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Calcule le score de conformité d'un assessment"""
    uid, adm = rbac.user_id, rbac.is_admin
    result = AssessmentService.get_assessment_score(db, assessment_id, user_id=uid, is_admin=adm)
    if result is None:
        raise HTTPException(status_code=404, detail="Assessment introuvable")
    return ScoreResponse(**result)


@router.get("/campaigns/{campaign_id}/score", response_model=ScoreResponse)
def get_campaign_score(
    campaign_id: int,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context),
):
    """Calcule le score de conformité agrégé d'une campagne"""
    uid, adm = rbac.user_id, rbac.is_admin
    result = AssessmentService.get_campaign_score(db, campaign_id, user_id=uid, is_admin=adm)
    if result is None:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return ScoreResponse(**result)


# --- Monkey365 / M365 Scan ---


@router.post("/{assessment_id}/scan/simulate", response_model=M365ScanResponse)
def simulate_m365_scan(
    assessment_id: int,
    body: M365ScanSimulateRequest,
    db: Session = Depends(get_db),
    rbac: RbacContext = Depends(get_rbac_context_auditeur),
):
    """
    Simule un scan Monkey365 en injectant des findings manuels.
    Utile pour le développement et les tests sans tenant M365.
    """
    result = Monkey365Service.simulate_scan(
        db,
        assessment_id,
        body.findings,
    )
    return M365ScanResponse(
        scan_id=result.scan_id,
        status=result.status,
        findings_count=result.findings_count,
        mapped_count=result.mapped_count,
        unmapped_count=result.unmapped_count,
        error=result.error,
        mapping_details=result.mapping_details,
        manual_controls=result.manual_controls,
    )

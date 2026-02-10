"""
Routes Assessments : campagnes, évaluations, résultats de contrôle.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, PaginationParams
from ...models.user import User
from ...schemas.assessment import (
    CampaignCreate,
    CampaignRead,
    CampaignSummary,
    CampaignUpdate,
    AssessmentCreate,
    AssessmentRead,
    ControlResultUpdate,
    ControlResultRead,
)
from ...schemas.common import PaginatedResponse, MessageResponse
from ...services.assessment_service import AssessmentService

router = APIRouter()


# --- Campagnes ---

@router.get("/campaigns", response_model=PaginatedResponse[CampaignSummary])
async def list_campaigns(
    audit_id: int = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste les campagnes d'évaluation"""
    campaigns, total = AssessmentService.list_campaigns(
        db, audit_id=audit_id, offset=pagination.offset, limit=pagination.page_size
    )
    items = []
    for c in campaigns:
        items.append(CampaignSummary(
            id=c.id,
            name=c.name,
            status=c.status.value,
            audit_id=c.audit_id,
            created_at=c.created_at,
            compliance_score=c.compliance_score,
            total_assessments=len(c.assessments),
        ))
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.post("/campaigns", response_model=CampaignSummary, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Crée une nouvelle campagne d'évaluation"""
    campaign = AssessmentService.create_campaign(
        db, name=body.name, audit_id=body.audit_id, description=body.description
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
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'une campagne avec ses assessments"""
    campaign = AssessmentService.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return campaign


@router.post("/campaigns/{campaign_id}/start", response_model=MessageResponse)
async def start_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Démarre une campagne"""
    try:
        AssessmentService.start_campaign(db, campaign_id)
        return MessageResponse(message="Campagne démarrée")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/campaigns/{campaign_id}/complete", response_model=MessageResponse)
async def complete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Termine une campagne"""
    try:
        AssessmentService.complete_campaign(db, campaign_id)
        return MessageResponse(message="Campagne terminée")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Assessments ---

@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: AssessmentCreate,
    campaign_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée un assessment (évaluation d'un équipement selon un référentiel)"""
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id est requis en query param")
    try:
        assessment = AssessmentService.create_assessment(
            db,
            campaign_id=campaign_id,
            equipement_id=body.equipement_id,
            framework_id=body.framework_id,
            assessed_by=current_user.username,
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{assessment_id}", response_model=AssessmentRead)
async def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Détail d'un assessment avec tous ses résultats de contrôle"""
    assessment = AssessmentService.get_assessment(db, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment introuvable")
    return assessment


# --- Résultats de contrôle ---

@router.put("/results/{result_id}", response_model=MessageResponse)
async def update_control_result(
    result_id: int,
    body: ControlResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Met à jour le résultat d'un contrôle"""
    try:
        AssessmentService.update_control_result(
            db,
            result_id=result_id,
            status=body.status,
            evidence=body.evidence,
            comment=body.comment,
            remediation_note=body.remediation_note,
            assessed_by=current_user.username,
        )
        return MessageResponse(message="Résultat mis à jour")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

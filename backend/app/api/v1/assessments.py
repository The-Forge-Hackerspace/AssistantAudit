"""
Routes Assessments : campagnes, évaluations, résultats de contrôle.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur, PaginationParams
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
    M365ScanRequest,
    M365ScanSimulateRequest,
    M365ScanResponse,
)
from ...schemas.common import PaginatedResponse, MessageResponse, ScoreResponse
from ...services.assessment_service import AssessmentService
from ...services.monkey365_service import Monkey365Service, ScanRequest

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
    _: User = Depends(get_current_auditeur),
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


@router.put("/campaigns/{campaign_id}", response_model=CampaignSummary)
async def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Met à jour une campagne (nom, description, statut)"""
    try:
        campaign = AssessmentService.update_campaign(db, campaign_id, body)
        return CampaignSummary(
            id=campaign.id,
            name=campaign.name,
            status=campaign.status.value,
            audit_id=campaign.audit_id,
            created_at=campaign.created_at,
            compliance_score=campaign.compliance_score,
            total_assessments=len(campaign.assessments),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/campaigns/{campaign_id}/start", response_model=MessageResponse)
async def start_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
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
    _: User = Depends(get_current_auditeur),
):
    """Termine une campagne"""
    try:
        AssessmentService.complete_campaign(db, campaign_id)
        return MessageResponse(message="Campagne terminée")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Supprime une campagne et toutes ses évaluations"""
    try:
        AssessmentService.delete_campaign(db, campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Assessments ---

@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: AssessmentCreate,
    campaign_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
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


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """Supprime un assessment et tous ses résultats"""
    try:
        AssessmentService.delete_assessment(db, assessment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Résultats de contrôle ---

@router.put("/results/{result_id}", response_model=MessageResponse)
async def update_control_result(
    result_id: int,
    body: ControlResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_auditeur),
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


# --- Scoring ---

@router.get("/{assessment_id}/score", response_model=ScoreResponse)
async def get_assessment_score(
    assessment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Calcule le score de conformité d'un assessment"""
    result = AssessmentService.get_assessment_score(db, assessment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Assessment introuvable")
    return ScoreResponse(**result)


@router.get("/campaigns/{campaign_id}/score", response_model=ScoreResponse)
async def get_campaign_score(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Calcule le score de conformité agrégé d'une campagne"""
    result = AssessmentService.get_campaign_score(db, campaign_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return ScoreResponse(**result)


# --- Monkey365 / M365 Scan ---

@router.post("/{assessment_id}/scan/m365", response_model=M365ScanResponse)
async def run_m365_scan(
    assessment_id: int,
    body: M365ScanRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """
    Lance un scan Monkey365 sur un assessment M365.
    L'assessment doit utiliser un framework avec engine=monkey365.
    Les résultats sont automatiquement mappés vers les contrôles.
    """
    from ...core.config import get_settings
    settings = get_settings()

    scan_req = ScanRequest(
        tenant_id=body.tenant_id,
        client_id=body.client_id,
        client_secret=body.client_secret,
        auth_method=body.auth_method,
        provider=body.provider,
        plugins=body.plugins,
    )
    result = Monkey365Service.run_scan_and_map(
        db, assessment_id, scan_req,
        monkey365_path=settings.MONKEY365_PATH or None,
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


@router.post("/{assessment_id}/scan/simulate", response_model=M365ScanResponse)
async def simulate_m365_scan(
    assessment_id: int,
    body: M365ScanSimulateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_auditeur),
):
    """
    Simule un scan Monkey365 en injectant des findings manuels.
    Utile pour le développement et les tests sans tenant M365.
    """
    result = Monkey365Service.simulate_scan(
        db, assessment_id, body.findings,
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

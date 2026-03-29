import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from ....core.database import get_db
from ....core.deps import get_current_user, get_current_auditeur
from ....models.user import User
from ....schemas.scan import (
    ConfigAnalysisResult,
    ConfigUploadResponse,
    ConfigAnalysisRead,
    ConfigAnalysisSummary,
    PrefillResult,
)
from ....schemas.common import MessageResponse
from ....tools.config_parsers import get_parser, ConfigParserBase
from ....services.config_analysis_service import (
    save_config_analysis,
    get_config_analysis,
    delete_config_analysis,
    prefill_assessment_from_config,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/config-analysis", response_model=ConfigUploadResponse)
def analyze_config(
    file: UploadFile = File(...),
    equipement_id: int | None = Form(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Upload un fichier de configuration réseau et retourne l'analyse.
    Détection automatique du vendor (Fortinet, OPNsense).
    Si equipement_id est fourni, l'analyse est sauvegardée et liée à l'équipement.
    """
    if not file.filename:
        raise HTTPException(400, "Nom de fichier manquant")

    # ── Limite de taille du fichier ──────────────────────────────────────
    from ....core.config import get_settings
    _settings = get_settings()
    max_bytes = _settings.MAX_CONFIG_UPLOAD_SIZE_MB * 1024 * 1024
    raw = file.file.read(max_bytes + 1)  # lire 1 octet de plus pour détecter
    if len(raw) > max_bytes:
        raise HTTPException(
            413,
            f"Fichier trop volumineux (max {_settings.MAX_CONFIG_UPLOAD_SIZE_MB} Mo).",
        )

    # Try UTF-8, then latin-1
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")

    # Detect vendor
    vendor = ConfigParserBase.detect_vendor(content)
    if not vendor:
        raise HTTPException(
            422,
            "Format de configuration non reconnu. "
            "Formats supportés : FortiGate (texte), OPNsense (XML).",
        )

    parser = get_parser(content)
    if not parser:
        raise HTTPException(422, f"Pas de parser disponible pour le vendor '{vendor}'.")

    try:
        result = parser.parse(content)
    except Exception as exc:
        logger.exception("Erreur lors du parsing de la configuration")
        raise HTTPException(500, f"Erreur d'analyse : {exc}") from exc

    # Si un équipement est spécifié, persister l'analyse
    config_analysis_id = None
    if equipement_id:
        try:
            saved = save_config_analysis(
                db=db,
                equipement_id=equipement_id,
                filename=file.filename,
                analysis=result,
                raw_config=content,
            )
            config_analysis_id = saved.id
        except ValueError as ve:
            raise HTTPException(404, str(ve)) from ve

    return ConfigUploadResponse(
        filename=file.filename,
        vendor=vendor,
        equipement_id=equipement_id,
        analysis=result,
        config_analysis_id=config_analysis_id,
    )


@router.post("/config-analysis/raw", response_model=ConfigAnalysisResult)
def analyze_config_raw(
    content: str = Form(...),
    vendor_hint: str | None = Form(None),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Analyse une configuration envoyée en texte brut (sans upload de fichier).
    """
    detected_vendor = vendor_hint or ConfigParserBase.detect_vendor(content)
    if not detected_vendor:
        raise HTTPException(422, "Format de configuration non reconnu.")

    parser = get_parser(content)
    if not parser:
        raise HTTPException(422, f"Pas de parser disponible pour '{detected_vendor}'.")

    try:
        return parser.parse(content)
    except Exception as exc:
        logger.exception("Erreur lors du parsing")
        raise HTTPException(500, "Erreur interne lors de l'analyse de la configuration.") from exc


@router.get("/config-analysis/vendors")
def list_vendors(
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les vendors supportés par les parsers de configuration."""
    return {
        "vendors": [
            {
                "id": "fortinet",
                "name": "Fortinet FortiGate",
                "format": "text",
                "description": "Configuration FortiGate exportée via 'show full-configuration' ou backup.",
            },
            {
                "id": "opnsense",
                "name": "OPNsense",
                "format": "xml",
                "description": "Configuration OPNsense exportée via System > Configuration > Backups.",
            },
        ]
    }


@router.get("/config-analyses", response_model=list[ConfigAnalysisSummary])
def list_analyses(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Liste les analyses de configuration sauvegardées, optionnellement filtrées par équipement."""
    from ....models.config_analysis import ConfigAnalysis as CA

    query = db.query(CA)
    if equipement_id:
        query = query.filter(CA.equipement_id == equipement_id)
    analyses = (
        query.order_by(CA.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Convertir en summary avec findings_count calculé
    results = []
    for a in analyses:
        results.append(ConfigAnalysisSummary(
            id=a.id,
            equipement_id=a.equipement_id,
            filename=a.filename,
            vendor=a.vendor,
            hostname=a.hostname,
            firmware_version=a.firmware_version,
            findings_count=len(a.findings) if a.findings else 0,
            created_at=a.created_at,
        ))
    return results


@router.get("/config-analyses/{config_id}", response_model=ConfigAnalysisRead)
def get_analysis(
    config_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Récupère le détail d'une analyse de configuration."""
    config = get_config_analysis(db, config_id)
    if not config:
        raise HTTPException(404, "Analyse de configuration introuvable")
    return config


@router.delete("/config-analyses/{config_id}", response_model=MessageResponse)
def remove_analysis(
    config_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime une analyse de configuration."""
    if not delete_config_analysis(db, config_id):
        raise HTTPException(404, "Analyse de configuration introuvable")
    return MessageResponse(message="Analyse supprimée")


@router.post("/config-analyses/{config_id}/prefill/{assessment_id}", response_model=PrefillResult)
def prefill_audit(
    config_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Pré-remplit les contrôles d'un assessment à partir des findings
    d'une analyse de configuration liée.
    Mappe automatiquement les findings aux contrôles du framework firewall.
    """
    try:
        result = prefill_assessment_from_config(db, config_id, assessment_id)
    except ValueError as ve:
        raise HTTPException(404, str(ve)) from ve
    except Exception as exc:
        logger.exception("Erreur lors du pré-remplissage")
        raise HTTPException(500, "Erreur interne lors du pré-remplissage.") from exc
    return PrefillResult(**result)


@router.get("/assessments-for-equipment/{equipement_id}")
def list_assessments_for_equipment(
    equipement_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Liste les assessments liés à un équipement (pour sélectionner
    lequel pré-remplir depuis une analyse de configuration).
    """
    from ....models.assessment import Assessment

    assessments = (
        db.query(Assessment)
        .filter(Assessment.equipement_id == equipement_id)
        .all()
    )
    results = []
    for a in assessments:
        framework_name = a.framework.name if a.framework else "—"
        results.append({
            "id": a.id,
            "campaign_id": a.campaign_id,
            "framework_id": a.framework_id,
            "framework_name": framework_name,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return results

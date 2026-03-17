"""
Routes API pour les outils d'infrastructure.

- POST /config-analysis        : Upload et analyse d'un fichier de configuration
- GET  /config-analyses         : Liste des analyses sauvegardées
- GET  /config-analyses/{id}    : Détail d'une analyse
- DELETE /config-analyses/{id}  : Suppression
- POST /config-analyses/{id}/prefill/{assessment_id} : Pré-remplir audit
- POST /ssl-check               : Vérification SSL/TLS d'un hôte
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_user, get_current_auditeur
from ...models.user import User
from ...schemas.scan import (
    ConfigAnalysisResult,
    ConfigUploadResponse,
    SSLCheckRequest,
    SSLCheckResult,
    SecurityFinding,
    ConfigAnalysisRead,
    ConfigAnalysisSummary,
    PrefillResult,
    CollectCreate,
    CollectResultSummary,
    CollectResultRead,
    ADAuditCreate,
    ADAuditResultSummary,
    ADAuditResultRead,
    PingCastleCreate,
    PingCastleResultSummary,
    PingCastleResultRead,
    Monkey365ScanCreate,
    Monkey365ScanResultSummary,
    Monkey365ScanResultRead,
)
from ...schemas.common import MessageResponse
from ...tools.config_parsers import get_parser, ConfigParserBase
from ...tools.ssl_checker.checker import check_ssl
from ...services.config_analysis_service import (
    save_config_analysis,
    list_config_analyses,
    get_config_analysis,
    delete_config_analysis,
    prefill_assessment_from_config,
)
from ...services.collect_service import (
    create_pending_collect,
    execute_collect_background,
    list_collect_results,
    get_collect_result,
    delete_collect_result,
    prefill_assessment_from_collect,
)
from ...services.ad_audit_service import (
    create_pending_ad_audit,
    execute_ad_audit_background,
    list_ad_audit_results,
    get_ad_audit_result,
    delete_ad_audit_result,
    prefill_assessment_from_ad_audit,
)
from ...services.pingcastle_service import (
    create_pending_pingcastle,
    execute_pingcastle_background,
    list_pingcastle_results,
    get_pingcastle_result,
    delete_pingcastle_result,
    prefill_assessment_from_pingcastle,
)
from ...services.monkey365_scan_service import Monkey365ScanService
from ...models.entreprise import Entreprise

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


# ──────────────────────────────────────────────
# Config Analysis
# ──────────────────────────────────────────────

@router.post("/config-analysis", response_model=ConfigUploadResponse)
async def analyze_config(
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
    from ...core.config import get_settings
    _settings = get_settings()
    max_bytes = _settings.MAX_CONFIG_UPLOAD_SIZE_MB * 1024 * 1024
    raw = await file.read(max_bytes + 1)  # lire 1 octet de plus pour détecter
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
async def analyze_config_raw(
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
async def list_vendors(
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


# ──────────────────────────────────────────────
# Config Analyses — CRUD persisté
# ──────────────────────────────────────────────

@router.get("/config-analyses", response_model=list[ConfigAnalysisSummary])
async def list_analyses(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Liste les analyses de configuration sauvegardées, optionnellement filtrées par équipement."""
    from ...models.config_analysis import ConfigAnalysis as CA

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
async def get_analysis(
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
async def remove_analysis(
    config_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime une analyse de configuration."""
    if not delete_config_analysis(db, config_id):
        raise HTTPException(404, "Analyse de configuration introuvable")
    return MessageResponse(message="Analyse supprimée")


@router.post("/config-analyses/{config_id}/prefill/{assessment_id}", response_model=PrefillResult)
async def prefill_audit(
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
async def list_assessments_for_equipment(
    equipement_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Liste les assessments liés à un équipement (pour sélectionner
    lequel pré-remplir depuis une analyse de configuration).
    """
    from ...models.assessment import Assessment

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


# ──────────────────────────────────────────────
# SSL/TLS Checker
# ──────────────────────────────────────────────

@router.post("/ssl-check", response_model=SSLCheckResult)
async def ssl_check(
    request: SSLCheckRequest,
    _current_user: User = Depends(get_current_auditeur),
):
    """Vérifie le certificat SSL/TLS et les protocoles supportés par un hôte."""
    try:
        result = check_ssl(
            host=request.host,
            port=request.port,
            timeout=request.timeout or 10,
        )
    except Exception as exc:
        logger.exception("Erreur SSL check pour %s:%d", request.host, request.port)
        raise HTTPException(500, "Erreur interne lors de la vérification SSL.") from exc

    return result


@router.post("/ssl-check/batch", response_model=list[SSLCheckResult])
async def ssl_check_batch(
    hosts: list[SSLCheckRequest],
    _current_user: User = Depends(get_current_auditeur),
):
    """Vérifie SSL/TLS pour plusieurs hôtes en séquence."""
    if len(hosts) > 20:
        raise HTTPException(400, "Maximum 20 hôtes par requête batch.")

    results: list[SSLCheckResult] = []
    for req in hosts:
        try:
            result = check_ssl(host=req.host, port=req.port, timeout=req.timeout or 10)
            results.append(result)
        except Exception as exc:
            logger.warning("SSL check failed for %s:%d : %s", req.host, req.port, exc)
            # Return a result with error
            results.append(SSLCheckResult(
                host=req.host,
                port=req.port,
                certificate=None,  # type: ignore[arg-type]
                protocols=[],
                findings=[SecurityFinding(
                    severity="high",
                    category="Connexion",
                    title=f"Impossible de se connecter à {req.host}:{req.port}",
                    description=str(exc),
                    remediation="Vérifier l'accessibilité de l'hôte et le port.",
                )],
            ))

    return results


# ──────────────────────────────────────────────
# Collecte SSH / WinRM
# ──────────────────────────────────────────────

@router.post("/collect", response_model=CollectResultSummary)
async def launch_collect(
    params: CollectCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance une collecte d'informations système via SSH ou WinRM.
    La collecte s'exécute en arrière-plan.
    """
    import threading

    if params.method not in ("ssh", "winrm"):
        raise HTTPException(400, "Méthode invalide. Utilisez 'ssh' ou 'winrm'.")

    try:
        collect = create_pending_collect(
            db=db,
            equipement_id=params.equipement_id,
            method=params.method,
            target_host=params.target_host,
            target_port=params.target_port,
            username=params.username,
            device_profile=params.device_profile,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    # Lancer la collecte en arrière-plan
    thread = threading.Thread(
        target=execute_collect_background,
        kwargs={
            "collect_id": collect.id,
            "password": params.password,
            "private_key": params.private_key,
            "passphrase": params.passphrase,
            "use_ssl": params.use_ssl,
            "transport": params.transport,
        },
        daemon=True,
    )
    thread.start()

    logger.info(f"Collecte #{collect.id} lancée en background ({params.method} → {params.target_host})")
    return collect


@router.get("/collects", response_model=list[CollectResultSummary])
async def list_collects(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les collectes, optionnellement filtrées par équipement."""
    return list_collect_results(
        db,
        equipement_id=equipement_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )


@router.get("/collects/{collect_id}", response_model=CollectResultRead)
async def get_collect(
    collect_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'une collecte."""
    collect = get_collect_result(db, collect_id)
    if not collect:
        raise HTTPException(404, f"Collecte #{collect_id} introuvable")
    return collect


@router.delete("/collects/{collect_id}", response_model=MessageResponse)
async def delete_collect(
    collect_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime une collecte."""
    if not delete_collect_result(db, collect_id):
        raise HTTPException(404, f"Collecte #{collect_id} introuvable")
    return MessageResponse(message=f"Collecte #{collect_id} supprimée")


@router.post("/collects/{collect_id}/prefill/{assessment_id}", response_model=PrefillResult)
async def prefill_from_collect(
    collect_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Pré-remplit un assessment à partir des résultats d'une collecte."""
    try:
        result = prefill_assessment_from_collect(db, collect_id, assessment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


# ──────────────────────────────────────────────
# Audit Active Directory (LDAP)
# ──────────────────────────────────────────────

@router.post("/ad-audit", response_model=ADAuditResultSummary)
async def launch_ad_audit(
    params: ADAuditCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un audit Active Directory via LDAP.
    L'audit s'exécute en arrière-plan.
    """
    import threading

    try:
        audit = create_pending_ad_audit(
            db=db,
            equipement_id=params.equipement_id,
            target_host=params.target_host,
            target_port=params.target_port,
            username=params.username,
            domain=params.domain,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    thread = threading.Thread(
        target=execute_ad_audit_background,
        kwargs={
            "audit_id": audit.id,
            "password": params.password,
            "use_ssl": params.use_ssl,
            "auth_method": params.auth_method,
        },
        daemon=True,
    )
    thread.start()

    logger.info(
        f"AD Audit #{audit.id} lancé en background "
        f"(LDAP → {params.target_host}:{params.target_port})"
    )
    return audit


@router.get("/ad-audits", response_model=list[ADAuditResultSummary])
async def list_ad_audits(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les audits AD, optionnellement filtrés par équipement."""
    return list_ad_audit_results(
        db,
        equipement_id=equipement_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )


@router.get("/ad-audits/{audit_id}", response_model=ADAuditResultRead)
async def get_ad_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'un audit AD."""
    audit = get_ad_audit_result(db, audit_id)
    if not audit:
        raise HTTPException(404, f"Audit AD #{audit_id} introuvable")
    return audit


@router.delete("/ad-audits/{audit_id}", response_model=MessageResponse)
async def delete_ad_audit(
    audit_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime un audit AD."""
    if not delete_ad_audit_result(db, audit_id):
        raise HTTPException(404, f"Audit AD #{audit_id} introuvable")
    return MessageResponse(message=f"Audit AD #{audit_id} supprimé")


@router.post("/ad-audits/{audit_id}/prefill/{assessment_id}", response_model=PrefillResult)
async def prefill_from_ad_audit(
    audit_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Pré-remplit un assessment à partir des résultats d'un audit AD."""
    try:
        result = prefill_assessment_from_ad_audit(db, audit_id, assessment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


# ──────────────────────────────────────────────
# PingCastle (Audit AD avancé)
# ──────────────────────────────────────────────

@router.post("/pingcastle", response_model=PingCastleResultSummary)
async def launch_pingcastle(
    params: PingCastleCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un audit PingCastle (healthcheck) sur un contrôleur de domaine AD.
    L'audit s'exécute en arrière-plan.
    """
    import threading

    try:
        pc_result = create_pending_pingcastle(
            db=db,
            equipement_id=params.equipement_id,
            target_host=params.target_host,
            domain=params.domain,
            username=params.username,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    thread = threading.Thread(
        target=execute_pingcastle_background,
        kwargs={
            "result_id": pc_result.id,
            "password": params.password,
        },
        daemon=True,
    )
    thread.start()

    logger.info(
        f"PingCastle #{pc_result.id} lancé en background "
        f"(DC={params.target_host}, domain={params.domain})"
    )
    return pc_result


@router.get("/pingcastle-results", response_model=list[PingCastleResultSummary])
async def list_pingcastle(
    equipement_id: int | None = None,
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Éléments par page"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les audits PingCastle, optionnellement filtrés par équipement."""
    return list_pingcastle_results(
        db,
        equipement_id=equipement_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )


@router.get("/pingcastle-results/{result_id}", response_model=PingCastleResultRead)
async def get_pingcastle(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'un audit PingCastle."""
    result = get_pingcastle_result(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit PingCastle #{result_id} introuvable")
    return result


@router.delete("/pingcastle-results/{result_id}", response_model=MessageResponse)
async def delete_pingcastle(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Supprime un audit PingCastle."""
    if not delete_pingcastle_result(db, result_id):
        raise HTTPException(404, f"Audit PingCastle #{result_id} introuvable")
    return MessageResponse(message=f"Audit PingCastle #{result_id} supprimé")


@router.post("/pingcastle-results/{result_id}/prefill/{assessment_id}", response_model=PrefillResult)
async def prefill_from_pingcastle(
    result_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Pré-remplit un assessment à partir des résultats d'un audit PingCastle."""
    try:
        result = prefill_assessment_from_pingcastle(db, result_id, assessment_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


# ──────────────────────────────────────────────
# Monkey365 (Audit Microsoft 365 / Azure AD)
# ──────────────────────────────────────────────

@router.post("/monkey365/run", response_model=Monkey365ScanResultSummary, status_code=201)
async def launch_monkey365_scan(
    request: Monkey365ScanCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Lance un audit Monkey365 sur Microsoft 365 / Azure AD.
    L'audit s'exécute en arrière-plan.
    """
    # Verify entreprise exists
    entreprise = db.get(Entreprise, request.entreprise_id)
    if not entreprise:
        raise HTTPException(404, f"Entreprise #{request.entreprise_id} introuvable")

    try:
        result = Monkey365ScanService.launch_scan(
            db=db,
            entreprise_id=request.entreprise_id,
            config=request.config,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    logger.info(
        f"Monkey365 scan #{result.id} lancé en background "
        f"(tenant={request.config.tenant_id}, entreprise={request.entreprise_id})"
    )
    return result


@router.get("/monkey365/scans/{entreprise_id}", response_model=list[Monkey365ScanResultSummary])
async def list_monkey365_scans(
    entreprise_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Liste les audits Monkey365 pour une entreprise."""
    return Monkey365ScanService.list_scans(
        db=db,
        entreprise_id=entreprise_id,
    )


@router.get("/monkey365/scans/result/{result_id}", response_model=Monkey365ScanResultRead)
async def get_monkey365_scan_result(
    result_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_auditeur),
):
    """Récupère le détail d'un audit Monkey365."""
    result = Monkey365ScanService.get_scan(db, result_id)
    if not result:
        raise HTTPException(404, f"Audit Monkey365 #{result_id} introuvable")
    return result

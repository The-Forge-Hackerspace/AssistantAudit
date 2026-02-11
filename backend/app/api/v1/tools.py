"""
Routes API pour les outils d'infrastructure.

- POST /config-analysis   : Upload et analyse d'un fichier de configuration
- POST /ssl-check          : Vérification SSL/TLS d'un hôte
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.deps import get_current_auditeur
from ...models.user import User
from ...schemas.scan import (
    ConfigAnalysisResult,
    ConfigUploadResponse,
    SSLCheckRequest,
    SSLCheckResult,
    SecurityFinding,
)
from ...tools.config_parsers import get_parser, ConfigParserBase
from ...tools.ssl_checker.checker import check_ssl

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


# ──────────────────────────────────────────────
# Config Analysis
# ──────────────────────────────────────────────

@router.post("/config-analysis", response_model=ConfigUploadResponse)
async def analyze_config(
    file: UploadFile = File(...),
    equipement_id: int | None = Form(None),
    _current_user: User = Depends(get_current_auditeur),
):
    """
    Upload un fichier de configuration réseau et retourne l'analyse.
    Détection automatique du vendor (Fortinet, OPNsense).
    """
    if not file.filename:
        raise HTTPException(400, "Nom de fichier manquant")

    raw = await file.read()

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

    return ConfigUploadResponse(
        filename=file.filename,
        vendor=vendor,
        equipement_id=equipement_id,
        analysis=result,
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
        raise HTTPException(500, f"Erreur d'analyse : {exc}") from exc


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
        raise HTTPException(500, f"Erreur lors de la vérification SSL : {exc}") from exc

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

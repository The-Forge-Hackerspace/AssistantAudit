import logging

from fastapi import APIRouter, Depends, HTTPException

from ....core.deps import get_current_auditeur
from ....models.user import User
from ....schemas.scan import SecurityFinding, SSLCheckRequest, SSLCheckResult
from ....tools.ssl_checker.checker import check_ssl

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ssl-check", response_model=SSLCheckResult)
def ssl_check(
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
def ssl_check_batch(
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
            results.append(
                SSLCheckResult(
                    host=req.host,
                    port=req.port,
                    certificate=None,
                    protocols=[],
                    findings=[
                        SecurityFinding(
                            severity="high",
                            category="Connexion",
                            title=f"Impossible de se connecter à {req.host}:{req.port}",
                            description=str(exc),
                            remediation="Vérifier l'accessibilité de l'hôte et le port.",
                        )
                    ],
                )
            )

    return results

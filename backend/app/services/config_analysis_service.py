"""
Service Config Analysis — Persistance et pré-remplissage d'audit
à partir des résultats de parsing de configuration.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models.assessment import Assessment, ComplianceStatus, ControlResult
from ..models.config_analysis import ConfigAnalysis
from ..models.equipement import Equipement, EquipementFirewall
from ..models.site import Site
from ..schemas.scan import ConfigAnalysisResult

logger = logging.getLogger(__name__)

# ── Mapping findings → contrôles de l'audit firewall ──────────
# Chaque entrée associe une catégorie + mots-clés de finding
# à un control ref_id du framework firewall_audit.
# Quand un finding matche, le contrôle est pré-rempli
# comme non_compliant (problème détecté) ou compliant (pas de problème).

FINDING_CONTROL_MAP: list[dict] = [
    # FW-001 : Firmware à jour
    {
        "control_ref": "FW-001",
        "finding_category": "Maintenance",
        "finding_keywords": ["obsolète", "firmware", "version", "fortiOS"],
        "on_found": "non_compliant",  # Si le finding existe → non conforme
    },
    # FW-002 : Accès administration sécurisé
    {
        "control_ref": "FW-002",
        "finding_category": "Administration",
        "finding_keywords": ["HTTP non chiffré", "HTTP et HTTPS", "Telnet"],
        "on_found": "non_compliant",
    },
    # FW-011 : Absence de règle any-any
    {
        "control_ref": "FW-011",
        "finding_category": "Règles de filtrage",
        "finding_keywords": ["any-any", "ANY-ANY", "trop permissive"],
        "on_found": "non_compliant",
    },
    # FW-014 : Pas de règle source/destination large inutile
    {
        "control_ref": "FW-014",
        "finding_category": "Règles de filtrage",
        "finding_keywords": ["service 'ALL'", "trop permissive", "tous les protocoles"],
        "on_found": "non_compliant",
    },
    # FW-020 : Logging activé
    {
        "control_ref": "FW-020",
        "finding_category": "Journalisation",
        "finding_keywords": ["sans journalisation", "sans log"],
        "on_found": "non_compliant",
    },
    # FW-040 : Protocoles VPN sécurisés
    {
        "control_ref": "FW-040",
        "finding_category": "VPN",
        "finding_keywords": ["cryptographiques faibles", "DES", "3DES", "MD5"],
        "on_found": "non_compliant",
    },
    # FW-050 : SNMP sécurisé (pas de community publique)
    {
        "control_ref": "FW-050",
        "finding_category": "SNMP",
        "finding_keywords": ["community SNMP", "public"],
        "on_found": "non_compliant",
    },
]


def save_config_analysis(
    db: Session,
    equipement_id: int,
    filename: str,
    analysis: ConfigAnalysisResult,
    raw_config: Optional[str] = None,
) -> ConfigAnalysis:
    """
    Persiste le résultat d'analyse de configuration et le lie à un équipement.
    Met également à jour les métadonnées de l'équipement (hostname, fabricant, firmware).
    """
    equipement = db.get(Equipement, equipement_id)
    if not equipement:
        raise ValueError(f"Équipement {equipement_id} introuvable")

    # Sérialiser les listes Pydantic → dicts pour JSON
    config = ConfigAnalysis(
        equipement_id=equipement_id,
        filename=filename,
        vendor=analysis.vendor,
        device_type=analysis.device_type,
        hostname=analysis.hostname,
        firmware_version=analysis.firmware_version,
        serial_number=analysis.serial_number,
        interfaces=[iface.model_dump() for iface in analysis.interfaces],
        firewall_rules=[rule.model_dump() for rule in analysis.firewall_rules],
        findings=[f.model_dump() for f in analysis.findings],
        summary=analysis.summary,
        raw_config=raw_config,
    )
    db.add(config)

    # Enrichir l'équipement avec les infos extraites
    if analysis.hostname and not equipement.hostname:
        equipement.hostname = analysis.hostname
    if analysis.vendor and not equipement.fabricant:
        equipement.fabricant = analysis.vendor

    # Si c'est un firewall, mettre à jour firmware + rules_count
    if isinstance(equipement, EquipementFirewall):
        if analysis.firmware_version:
            # Il n'y a pas de firmware_version sur EquipementFirewall
            # mais on peut le stocker dans notes_audit
            pass
        if analysis.firewall_rules:
            equipement.rules_count = len(analysis.firewall_rules)

    db.flush()
    db.refresh(config)

    logger.info(
        f"Config analysis #{config.id} sauvegardée pour équipement #{equipement_id} "
        f"({analysis.vendor}, {len(analysis.findings)} findings)"
    )
    return config


def list_config_analyses(
    db: Session,
    equipement_id: int,
) -> list[ConfigAnalysis]:
    """Liste toutes les analyses de configuration d'un équipement."""
    return (
        db.query(ConfigAnalysis)
        .filter(ConfigAnalysis.equipement_id == equipement_id)
        .order_by(ConfigAnalysis.created_at.desc())
        .all()
    )


def _check_config_access(db: Session, config: ConfigAnalysis, user_id: int | None, is_admin: bool) -> bool:
    """Verifie l'acces via Equipement → Site → Entreprise."""
    if user_id is None or is_admin:
        return True
    from ..core.helpers import user_has_access_to_entreprise

    equip = db.get(Equipement, config.equipement_id)
    if not equip:
        return False
    site = db.get(Site, equip.site_id)
    if not site:
        return False
    return user_has_access_to_entreprise(db, site.entreprise_id, user_id)


def get_config_analysis(
    db: Session,
    config_id: int,
    user_id: int | None = None,
    is_admin: bool = False,
) -> Optional[ConfigAnalysis]:
    """Récupère une analyse de configuration par ID. Vérifie ownership."""
    config = db.get(ConfigAnalysis, config_id)
    if config and not _check_config_access(db, config, user_id, is_admin):
        return None
    return config


def delete_config_analysis(
    db: Session,
    config_id: int,
    user_id: int | None = None,
    is_admin: bool = False,
) -> bool:
    """Supprime une analyse de configuration. Vérifie ownership."""
    config = db.get(ConfigAnalysis, config_id)
    if not config:
        return False
    if not _check_config_access(db, config, user_id, is_admin):
        return False
    db.delete(config)
    db.flush()
    return True


def prefill_assessment_from_config(
    db: Session,
    config_analysis_id: int,
    assessment_id: int,
) -> dict:
    """
    Pré-remplit les contrôles d'un assessment à partir des findings
    d'une analyse de configuration.

    Logique :
    - Pour chaque mapping (finding_category/keywords → control_ref_id),
      on cherche si un finding correspondant existe dans l'analyse
    - Si oui → le contrôle est marqué non_compliant avec le finding comme preuve
    - Si non → le contrôle est marqué compliant (pas de problème détecté)
    - Seuls les contrôles qui ont un mapping sont pré-remplis

    Returns:
        dict avec compteurs et détails
    """
    config = db.get(ConfigAnalysis, config_analysis_id)
    if not config:
        raise ValueError(f"Analyse de configuration #{config_analysis_id} introuvable")

    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise ValueError(f"Assessment #{assessment_id} introuvable")

    # Récupérer les findings de l'analyse
    findings: list[dict] = config.findings or []

    # Récupérer tous les control_results de l'assessment
    control_results = db.query(ControlResult).filter(ControlResult.assessment_id == assessment_id).all()

    # Créer un index ref_id → ControlResult
    ref_to_result: dict[str, ControlResult] = {}
    for cr in control_results:
        if cr.control and cr.control.ref_id:
            ref_to_result[cr.control.ref_id] = cr

    prefilled = 0
    compliant = 0
    non_compliant = 0
    partial = 0
    details = []

    for mapping in FINDING_CONTROL_MAP:
        control_ref = mapping["control_ref"]
        cr = ref_to_result.get(control_ref)
        if not cr:
            continue  # Ce contrôle n'existe pas dans cet assessment

        # Vérifier si un finding matche
        matched_findings = _find_matching_findings(
            findings,
            mapping["finding_category"],
            mapping["finding_keywords"],
        )

        if matched_findings:
            # Problème détecté
            evidence_parts = []
            for f in matched_findings:
                evidence_parts.append(
                    f"[{f.get('severity', 'medium').upper()}] {f.get('title', '')}\n{f.get('description', '')}"
                )
                if f.get("remediation"):
                    evidence_parts.append(f"→ Recommandation : {f['remediation']}")

            cr.status = ComplianceStatus.NON_COMPLIANT
            cr.evidence = "\n\n".join(evidence_parts)
            cr.auto_result = f"Config parser: {len(matched_findings)} finding(s) détecté(s)"
            cr.is_auto_assessed = True
            cr.assessed_at = datetime.now(timezone.utc)
            cr.assessed_by = "config_parser"
            non_compliant += 1
            details.append(
                {
                    "control_ref": control_ref,
                    "control_title": cr.control.title if cr.control else "",
                    "status": "non_compliant",
                    "findings_count": len(matched_findings),
                }
            )
        else:
            # Aucun problème détecté pour ce contrôle
            cr.status = ComplianceStatus.COMPLIANT
            cr.evidence = (
                f"Aucun problème détecté par l'analyse automatique de la configuration "
                f"({config.vendor}, fichier: {config.filename})"
            )
            cr.auto_result = "Config parser: aucun finding correspondant"
            cr.is_auto_assessed = True
            cr.assessed_at = datetime.now(timezone.utc)
            cr.assessed_by = "config_parser"
            compliant += 1
            details.append(
                {
                    "control_ref": control_ref,
                    "control_title": cr.control.title if cr.control else "",
                    "status": "compliant",
                    "findings_count": 0,
                }
            )

        prefilled += 1

    db.flush()
    logger.info(
        f"Pré-remplissage terminé: {prefilled} contrôles ({compliant} conformes, {non_compliant} non-conformes)"
    )

    return {
        "controls_prefilled": prefilled,
        "controls_compliant": compliant,
        "controls_non_compliant": non_compliant,
        "controls_partial": partial,
        "details": details,
    }


def _find_matching_findings(
    findings: list[dict],
    category: str,
    keywords: list[str],
) -> list[dict]:
    """
    Cherche dans les findings ceux qui matchent une catégorie
    et au moins un mot-clé dans le titre ou la description.
    """
    matched = []
    for f in findings:
        f_cat = f.get("category", "")
        f_title = f.get("title", "")
        f_desc = f.get("description", "")
        text = f"{f_title} {f_desc}".lower()

        # Vérifier catégorie (souple : contient)
        if category.lower() not in f_cat.lower():
            continue

        # Vérifier au moins un mot-clé
        for kw in keywords:
            if kw.lower() in text:
                matched.append(f)
                break

    return matched

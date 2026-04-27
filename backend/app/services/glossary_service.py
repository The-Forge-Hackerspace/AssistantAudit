"""Service de generation du glossaire dynamique d'un audit (TOS-25 section 8).

Charge un glossaire de reference (YAML versionne) et ne retient que les
termes effectivement presents dans les controles non-conformes de l'audit.
Le matching est case-insensitive avec frontieres de mots et applique sur
title + description + remediation des controles.
"""

import logging
import re
from pathlib import Path

import yaml
from ..core.errors import NotFoundError
from sqlalchemy.orm import Session

from ..models.assessment import AssessmentCampaign, ComplianceStatus
from ..models.audit import Audit
from ..schemas.glossary import Glossary, GlossaryEntry

logger = logging.getLogger(__name__)

GLOSSARY_PATH = Path(__file__).parent.parent / "data" / "glossary.yaml"


def _load_glossary() -> list[GlossaryEntry]:
    """Charge le glossaire YAML de reference."""
    if not GLOSSARY_PATH.exists():
        logger.warning("Glossaire introuvable : %s", GLOSSARY_PATH)
        return []
    with open(GLOSSARY_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    entries = []
    for raw in data.get("glossary", []):
        if not raw.get("term") or not raw.get("definition"):
            continue
        entries.append(
            GlossaryEntry(
                term=raw["term"].strip(),
                definition=raw["definition"].strip(),
                aliases=[a.strip() for a in raw.get("aliases", []) if a],
            )
        )
    return entries


def _entry_matches(entry: GlossaryEntry, haystack: str) -> bool:
    """Vrai si le terme ou un de ses alias apparait dans le texte (case-insensitive, mot entier)."""
    candidates = [entry.term, *entry.aliases]
    for c in candidates:
        # \b ne joue pas bien avec des termes a espace ou tiret — on encadre par
        # du non-alphanumerique pour rester safe.
        pattern = r"(?<![A-Za-z0-9])" + re.escape(c) + r"(?![A-Za-z0-9])"
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            return True
    return False


class GlossaryService:
    """Genere un glossaire restreint aux termes presents dans l'audit."""

    @staticmethod
    def _check_audit_access(
        db: Session, audit_id: int, user_id: int, is_admin: bool
    ) -> Audit:
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise NotFoundError("Audit non trouve")
        if not is_admin and audit.owner_id != user_id:
            raise NotFoundError("Audit non trouve")
        return audit

    @staticmethod
    def generate(
        db: Session, audit_id: int, user_id: int, is_admin: bool
    ) -> Glossary:
        """Glossaire dynamique : termes detectes dans les controles non-conformes."""
        audit = GlossaryService._check_audit_access(db, audit_id, user_id, is_admin)
        all_entries = _load_glossary()
        if not all_entries:
            return Glossary(audit_id=audit.id, entries=[], total=0)

        campaigns = (
            db.query(AssessmentCampaign)
            .filter(AssessmentCampaign.audit_id == audit.id)
            .all()
        )

        # Concatener tous les textes pertinents des controles non-conformes
        text_parts: list[str] = []
        for camp in campaigns:
            for assess in camp.assessments:
                for r in assess.results:
                    if r.status != ComplianceStatus.NON_COMPLIANT or not r.control:
                        continue
                    ctrl = r.control
                    text_parts.append(ctrl.title or "")
                    text_parts.append(ctrl.description or "")
                    text_parts.append(ctrl.remediation or "")
        haystack = "\n".join(text_parts)

        if not haystack.strip():
            return Glossary(audit_id=audit.id, entries=[], total=0)

        matched = [e for e in all_entries if _entry_matches(e, haystack)]
        matched.sort(key=lambda e: e.term.casefold())

        return Glossary(audit_id=audit.id, entries=matched, total=len(matched))

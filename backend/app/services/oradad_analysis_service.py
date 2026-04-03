"""
Service d'analyse ORADAD — parse les archives tar ORADAD et verifie
les donnees contre le referentiel ANSSI.
"""

import csv
import io
import logging
import tarfile
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.anssi_checklist import AnssiCheckpoint

logger = logging.getLogger(__name__)

# userAccountControl flags
UAC_ACCOUNTDISABLE = 0x0002
UAC_DONT_EXPIRE_PASSWD = 0x10000
UAC_DONT_REQUIRE_PREAUTH = 0x400000
UAC_TRUSTED_FOR_DELEGATION = 0x80000
UAC_SERVER_TRUST_ACCOUNT = 0x2000
UAC_ENCRYPTED_TEXT_PASSWORD_ALLOWED = 0x0080
UAC_USE_DES_KEY_ONLY = 0x200000

# Well-known privileged group RIDs
PRIVILEGED_GROUP_RIDS = {
    "512",  # Domain Admins
    "519",  # Enterprise Admins
    "518",  # Schema Admins
    "516",  # Domain Controllers
    "498",  # Enterprise Read-only Domain Controllers
    "500",  # Administrator (built-in)
}

# Default primaryGroupID values
DEFAULT_PRIMARY_GROUP_IDS = {513, 515, 516, 521}


class OradadAnalysisService:
    """Analyse les donnees ORADAD contre le referentiel ANSSI."""

    @staticmethod
    def parse_oradad_tar(tar_data: bytes) -> dict[str, list[dict[str, str]]]:
        """
        Parse une archive tar ORADAD.
        Retourne un dict structure : {"users": [...], "computers": [...], ...}
        """
        result: dict[str, list[dict[str, str]]] = {}

        # Mapping des noms de fichiers TSV vers des cles logiques
        file_key_map = {
            "user.tsv": "users",
            "computer.tsv": "computers",
            "group.tsv": "groups",
            "trust.tsv": "trusts",
            "gpo.tsv": "gpos",
            "ou.tsv": "ous",
            "dns.tsv": "dns_zones",
            "cert_template.tsv": "cert_templates",
            "site.tsv": "sites",
            "subnet.tsv": "subnets",
        }

        try:
            with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue

                    filename = member.name.rsplit("/", 1)[-1].lower()
                    key = file_key_map.get(filename)
                    if key is None:
                        continue

                    f = tar.extractfile(member)
                    if f is None:
                        continue

                    content = f.read().decode("utf-8", errors="replace")
                    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
                    result[key] = list(reader)

        except tarfile.TarError as e:
            logger.error("Erreur lors du parsing de l'archive ORADAD: %s", e)
            raise ValueError(f"Archive ORADAD invalide: {e}") from e

        return result

    @staticmethod
    def run_anssi_checks(db: Session, parsed_data: dict[str, list[dict[str, str]]]) -> list[dict]:
        """
        Verifie chaque point de controle ANSSI auto_checkable contre les donnees parsees.
        Retourne une liste de findings.
        """
        checkpoints = db.query(AnssiCheckpoint).filter(AnssiCheckpoint.auto_checkable.is_(True)).all()

        # Map vuln_id → check function
        check_dispatch = {
            "vuln1_privileged_members": OradadAnalysisService._check_privileged_members,
            "vuln1_dont_expire_priv": OradadAnalysisService._check_dont_expire_priv,
            "vuln1_spn_priv": OradadAnalysisService._check_spn_priv,
            "vuln1_kerberos_properties_preauth_priv": OradadAnalysisService._check_preauth_priv,
            "vuln1_password_change_priv": OradadAnalysisService._check_password_change_priv,
            "vuln1_user_accounts_dormant": OradadAnalysisService._check_dormant_accounts,
            "vuln2_delegation_t4d": OradadAnalysisService._check_delegation_t4d,
            "vuln2_dont_expire": OradadAnalysisService._check_dont_expire_all,
            "vuln2_krbtgt": OradadAnalysisService._check_krbtgt,
            "vuln3_protected_users": OradadAnalysisService._check_protected_users,
            "vuln3_reversible_password": OradadAnalysisService._check_reversible_password,
        }

        findings = []
        for cp in checkpoints:
            check_fn = check_dispatch.get(cp.vuln_id)
            if check_fn is not None:
                finding = check_fn(cp, parsed_data)
            else:
                # Points de controle necessitant nTSecurityDescriptor ou non encore implementes
                finding = {
                    "vuln_id": cp.vuln_id,
                    "level": cp.level,
                    "title_fr": cp.title_fr,
                    "status": "not_checked",
                    "details": "Verification non implementee (necessite analyse ACL nTSecurityDescriptor).",
                    "affected_objects": [],
                }
            findings.append(finding)

        return findings

    @staticmethod
    def calculate_score(findings: list[dict]) -> dict:
        """
        Calcule un score global a partir des findings.
        """
        total = len(findings)
        passed = sum(1 for f in findings if f["status"] == "pass")
        failed = sum(1 for f in findings if f["status"] == "fail")
        warning = sum(1 for f in findings if f["status"] == "warning")
        not_checked = sum(1 for f in findings if f["status"] == "not_checked")

        # Worst level among failed findings (1=worst)
        failed_levels = [f["level"] for f in findings if f["status"] == "fail"]
        worst_level = min(failed_levels) if failed_levels else 5

        # Score 0-100: start at 100, deduct based on severity_score of failed checks
        max_severity = sum(f.get("severity_score", 0) for f in findings if f.get("severity_score"))
        failed_severity = sum(
            f.get("severity_score", 0) for f in findings if f["status"] == "fail" and f.get("severity_score")
        )
        score = round(100 * (1 - failed_severity / max_severity)) if max_severity > 0 else 100

        return {
            "level": worst_level,
            "score": max(0, min(100, score)),
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "warning": warning,
            "not_checked": not_checked,
        }

    # ─── Check implementations ───────────────────────────────────────

    @staticmethod
    def _get_uac(user: dict[str, str]) -> int:
        try:
            return int(user.get("userAccountControl", "0"))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _is_privileged(user: dict[str, str]) -> bool:
        admin_count = user.get("adminCount", "")
        if admin_count == "1":
            return True
        member_of = user.get("memberOf", "")
        for rid in PRIVILEGED_GROUP_RIDS:
            if f"-{rid}" in member_of:
                return True
        return False

    @staticmethod
    def _is_active(user: dict[str, str]) -> bool:
        uac = OradadAnalysisService._get_uac(user)
        return not (uac & UAC_ACCOUNTDISABLE)

    @staticmethod
    def _parse_ad_timestamp(value: str) -> datetime | None:
        """Parse AD timestamp (Windows FILETIME or ISO-like)."""
        if not value or value == "0":
            return None
        try:
            ts = int(value)
            if ts <= 0:
                return None
            # Windows FILETIME: 100-nanosecond intervals since 1601-01-01
            epoch_diff = 116444736000000000
            if ts > epoch_diff:
                unix_ts = (ts - epoch_diff) / 10_000_000
                return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
        except (ValueError, OSError):
            pass
        return None

    @staticmethod
    def _check_privileged_members(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        priv_users = [
            u for u in users if OradadAnalysisService._is_privileged(u) and OradadAnalysisService._is_active(u)
        ]
        count = len(priv_users)
        status = "fail" if count > 50 else "pass"
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": status,
            "severity_score": cp.severity_score,
            "details": f"{count} comptes privilegies actifs (seuil: 50).",
            "affected_objects": [u.get("sAMAccountName", "") for u in priv_users[:20]],
        }

    @staticmethod
    def _check_dont_expire_priv(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        affected = [
            u.get("sAMAccountName", "")
            for u in users
            if OradadAnalysisService._is_privileged(u)
            and OradadAnalysisService._is_active(u)
            and (OradadAnalysisService._get_uac(u) & UAC_DONT_EXPIRE_PASSWD)
        ]
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes privilegies avec DONT_EXPIRE_PASSWD.",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_spn_priv(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        affected = [
            u.get("sAMAccountName", "")
            for u in users
            if OradadAnalysisService._is_privileged(u)
            and OradadAnalysisService._is_active(u)
            and u.get("servicePrincipalName", "").strip()
        ]
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes privilegies avec SPN (Kerberoasting possible).",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_preauth_priv(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        affected = [
            u.get("sAMAccountName", "")
            for u in users
            if OradadAnalysisService._is_privileged(u)
            and OradadAnalysisService._is_active(u)
            and (OradadAnalysisService._get_uac(u) & UAC_DONT_REQUIRE_PREAUTH)
        ]
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes privilegies sans pre-auth Kerberos.",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_password_change_priv(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        now = datetime.now(timezone.utc)
        three_years_seconds = 3 * 365.25 * 86400
        affected = []
        for u in users:
            if not OradadAnalysisService._is_privileged(u):
                continue
            if not OradadAnalysisService._is_active(u):
                continue
            pwd_last = OradadAnalysisService._parse_ad_timestamp(u.get("pwdLastSet", "0"))
            if pwd_last and (now - pwd_last).total_seconds() > three_years_seconds:
                affected.append(u.get("sAMAccountName", ""))
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes privilegies avec mdp > 3 ans.",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_dormant_accounts(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        now = datetime.now(timezone.utc)
        one_year_seconds = 365.25 * 86400
        active_users = [u for u in users if OradadAnalysisService._is_active(u)]
        if not active_users:
            return {
                "vuln_id": cp.vuln_id,
                "level": cp.level,
                "title_fr": cp.title_fr,
                "status": "pass",
                "severity_score": cp.severity_score,
                "details": "Aucun compte actif trouve.",
                "affected_objects": [],
            }

        dormant = []
        for u in active_users:
            last_logon = OradadAnalysisService._parse_ad_timestamp(u.get("lastLogonTimestamp", "0"))
            if last_logon and (now - last_logon).total_seconds() > one_year_seconds:
                dormant.append(u.get("sAMAccountName", ""))
            elif not last_logon:
                dormant.append(u.get("sAMAccountName", ""))

        pct = (len(dormant) / len(active_users)) * 100 if active_users else 0
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if pct > 25 else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(dormant)}/{len(active_users)} comptes dormants ({pct:.0f}%, seuil: 25%).",
            "affected_objects": dormant[:20],
        }

    @staticmethod
    def _check_delegation_t4d(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        """Comptes avec TRUSTED_FOR_DELEGATION (hors DC)."""
        affected = []
        for obj_type in ("users", "computers"):
            for obj in data.get(obj_type, []):
                uac = OradadAnalysisService._get_uac(obj)
                if not (uac & UAC_TRUSTED_FOR_DELEGATION):
                    continue
                # Exclude DCs (SERVER_TRUST_ACCOUNT)
                if uac & UAC_SERVER_TRUST_ACCOUNT:
                    continue
                if not OradadAnalysisService._is_active(obj):
                    continue
                affected.append(obj.get("sAMAccountName", ""))
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes avec delegation non contrainte (hors DC).",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_dont_expire_all(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        affected = [
            u.get("sAMAccountName", "")
            for u in users
            if OradadAnalysisService._is_active(u) and (OradadAnalysisService._get_uac(u) & UAC_DONT_EXPIRE_PASSWD)
        ]
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes avec DONT_EXPIRE_PASSWD.",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_krbtgt(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        now = datetime.now(timezone.utc)
        one_year_seconds = 365.25 * 86400

        krbtgt = [u for u in users if u.get("sAMAccountName", "").lower() == "krbtgt"]
        if not krbtgt:
            return {
                "vuln_id": cp.vuln_id,
                "level": cp.level,
                "title_fr": cp.title_fr,
                "status": "not_checked",
                "severity_score": cp.severity_score,
                "details": "Compte krbtgt non trouve dans les donnees.",
                "affected_objects": [],
            }

        user = krbtgt[0]
        pwd_last = OradadAnalysisService._parse_ad_timestamp(user.get("pwdLastSet", "0"))
        if pwd_last and (now - pwd_last).total_seconds() > one_year_seconds:
            age_days = int((now - pwd_last).total_seconds() / 86400)
            return {
                "vuln_id": cp.vuln_id,
                "level": cp.level,
                "title_fr": cp.title_fr,
                "status": "fail",
                "severity_score": cp.severity_score,
                "details": f"Mot de passe krbtgt inchange depuis {age_days} jours.",
                "affected_objects": ["krbtgt"],
            }

        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "pass",
            "severity_score": cp.severity_score,
            "details": "Mot de passe krbtgt change recemment.",
            "affected_objects": [],
        }

    @staticmethod
    def _check_protected_users(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        affected = []
        for u in users:
            if not OradadAnalysisService._is_privileged(u):
                continue
            if not OradadAnalysisService._is_active(u):
                continue
            member_of = u.get("memberOf", "").lower()
            if "protected users" not in member_of and "cn=protected users" not in member_of:
                affected.append(u.get("sAMAccountName", ""))
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes privilegies non membres de Protected Users.",
            "affected_objects": affected[:20],
        }

    @staticmethod
    def _check_reversible_password(cp: AnssiCheckpoint, data: dict[str, list[dict[str, str]]]) -> dict:
        users = data.get("users", [])
        affected = [
            u.get("sAMAccountName", "")
            for u in users
            if OradadAnalysisService._is_active(u)
            and (OradadAnalysisService._get_uac(u) & UAC_ENCRYPTED_TEXT_PASSWORD_ALLOWED)
        ]
        return {
            "vuln_id": cp.vuln_id,
            "level": cp.level,
            "title_fr": cp.title_fr,
            "status": "fail" if affected else "pass",
            "severity_score": cp.severity_score,
            "details": f"{len(affected)} comptes avec mot de passe reversible.",
            "affected_objects": affected[:20],
        }

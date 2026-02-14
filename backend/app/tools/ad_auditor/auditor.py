"""
AD Auditor — Audit Active Directory via requêtes LDAP (ldap3).

Se connecte à un contrôleur de domaine, collecte les informations
critiques (comptes, groupes, GPO, réplication, politique de MdP…)
et évalue la conformité par rapport au référentiel AD.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import ldap3
from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE, ALL_ATTRIBUTES
from ldap3.core.exceptions import LDAPException

logger = logging.getLogger(__name__)

# Timeouts
LDAP_CONNECT_TIMEOUT = 15
LDAP_RECEIVE_TIMEOUT = 30

# Windows FILETIME epoch delta (1601-01-01 → 1970-01-01) in 100-ns ticks
_FILETIME_EPOCH_DIFF = 116444736000000000

# Regex for safe input validation
_HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:\-]{0,254}$")


def _filetime_to_datetime(ft: int) -> Optional[datetime]:
    """Convertit un Windows FILETIME (ticks 100ns depuis 1601) en datetime UTC."""
    if not ft or ft <= 0 or ft == 9223372036854775807:  # 'never' sentinel
        return None
    try:
        ts = (ft - _FILETIME_EPOCH_DIFF) / 10_000_000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


@dataclass
class ADAuditFinding:
    """Un constat d'audit AD individuel."""
    control_ref: str
    title: str
    description: str
    severity: str  # critical | high | medium | low
    category: str
    status: str  # compliant | non_compliant | partial | info
    evidence: str = ""
    remediation: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class ADAuditResult:
    """Résultat complet d'un audit AD."""
    success: bool = False
    error: Optional[str] = None

    # Infos domaine
    domain_name: str = ""
    domain_dn: str = ""
    forest_name: str = ""
    domain_functional_level: str = ""
    forest_functional_level: str = ""
    dc_list: list[dict] = field(default_factory=list)

    # Comptes & Groupes
    total_users: int = 0
    enabled_users: int = 0
    disabled_users: int = 0
    domain_admins: list[dict] = field(default_factory=list)
    enterprise_admins: list[dict] = field(default_factory=list)
    schema_admins: list[dict] = field(default_factory=list)
    inactive_users: list[dict] = field(default_factory=list)
    never_expire_password: list[dict] = field(default_factory=list)
    never_logged_in: list[dict] = field(default_factory=list)
    admin_account_status: dict = field(default_factory=dict)

    # Politique de mots de passe
    password_policy: dict = field(default_factory=dict)
    fine_grained_policies: list[dict] = field(default_factory=list)

    # GPO
    gpo_list: list[dict] = field(default_factory=list)

    # Réplication
    replication_metadata: list[dict] = field(default_factory=list)

    # LAPS
    laps_deployed: bool = False
    laps_schema_present: bool = False

    # Findings (constats d'audit)
    findings: list[ADAuditFinding] = field(default_factory=list)

    # Résumé
    summary: dict = field(default_factory=dict)

    # Données brutes pour debug
    raw_data: dict = field(default_factory=dict)


class ADAuditor:
    """
    Audit Active Directory via requêtes LDAP.

    Se connecte à un DC, collecte les données d'audit et évalue
    la conformité par rapport au référentiel active_directory_audit.yaml.
    """

    def __init__(
        self,
        host: str,
        port: int = 389,
        use_ssl: bool = False,
        username: str = "",
        password: str = "",
        domain: str = "",
        auth_method: str = "ntlm",
    ):
        # Validation des entrées
        if not _HOSTNAME_PATTERN.match(host):
            raise ValueError(f"Adresse DC invalide : '{host}'")

        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.domain = domain
        self.auth_method = auth_method.lower()
        self._conn: Optional[Connection] = None
        self._base_dn: str = ""

    def _build_base_dn(self) -> str:
        """Construit le DN de base à partir du nom de domaine."""
        if not self.domain:
            return ""
        parts = self.domain.split(".")
        return ",".join(f"DC={p}" for p in parts)

    def _connect(self) -> Connection:
        """Établit la connexion LDAP au contrôleur de domaine."""
        server = Server(
            self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            get_info=ALL,
            connect_timeout=LDAP_CONNECT_TIMEOUT,
        )

        if self.auth_method == "ntlm":
            # NTLM : DOMAIN\username
            user = f"{self.domain.split('.')[0].upper()}\\{self.username}" if self.domain else self.username
            conn = Connection(
                server,
                user=user,
                password=self.password,
                authentication=NTLM,
                receive_timeout=LDAP_RECEIVE_TIMEOUT,
                auto_bind=True,
            )
        else:
            # Simple bind (LDAP standard)
            user_dn = self.username
            if "@" not in self.username and "=" not in self.username:
                user_dn = f"{self.username}@{self.domain}"
            conn = Connection(
                server,
                user=user_dn,
                password=self.password,
                authentication=SIMPLE,
                receive_timeout=LDAP_RECEIVE_TIMEOUT,
                auto_bind=True,
            )

        self._base_dn = self._build_base_dn()
        # Fallback: use server info
        if not self._base_dn and server.info and server.info.other:
            dn_list = server.info.other.get("defaultNamingContext", [])
            if dn_list:
                self._base_dn = dn_list[0]

        return conn

    def _search(
        self,
        search_base: str,
        search_filter: str,
        attributes: list[str] | str = ALL_ATTRIBUTES,
        size_limit: int = 1000,
    ) -> list[dict]:
        """Effectue une recherche LDAP et retourne les résultats."""
        if not self._conn:
            return []
        try:
            self._conn.search(
                search_base=search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes,
                size_limit=size_limit,
            )
            results = []
            for entry in self._conn.entries:
                entry_dict = {}
                entry_dict["dn"] = str(entry.entry_dn)
                for attr in entry.entry_attributes:
                    val = entry[attr].value
                    if isinstance(val, bytes):
                        val = val.hex()
                    elif isinstance(val, list):
                        val = [v.hex() if isinstance(v, bytes) else str(v) for v in val]
                    elif isinstance(val, datetime):
                        val = val.isoformat()
                    else:
                        val = str(val) if val is not None else None
                    entry_dict[attr] = val
                results.append(entry_dict)
            return results
        except LDAPException as e:
            logger.warning(f"Erreur LDAP recherche '{search_filter}': {e}")
            return []

    # ── Collecte des données ──────────────────────────────────────────

    def _collect_domain_info(self, result: ADAuditResult) -> None:
        """Collecte les informations du domaine."""
        if not self._conn or not self._conn.server.info:
            return
        info = self._conn.server.info
        if info.other:
            result.domain_dn = (info.other.get("defaultNamingContext", [""])[0])
            result.forest_name = (info.other.get("rootDomainNamingContext", [""])[0])
            fl = info.other.get("domainFunctionality", [""])[0]
            ffl = info.other.get("forestFunctionality", [""])[0]

            level_map = {
                "0": "2000", "1": "2003 Interim", "2": "2003",
                "3": "2008", "4": "2008 R2", "5": "2012",
                "6": "2012 R2", "7": "2016",
            }
            result.domain_functional_level = level_map.get(fl, fl)
            result.forest_functional_level = level_map.get(ffl, ffl)

        result.domain_name = self.domain

    def _collect_domain_controllers(self, result: ADAuditResult) -> None:
        """Liste les contrôleurs de domaine."""
        ou_dc = f"OU=Domain Controllers,{self._base_dn}"
        entries = self._search(ou_dc, "(objectClass=computer)", [
            "cn", "dNSHostName", "operatingSystem", "operatingSystemVersion",
            "whenCreated", "whenChanged",
        ])
        for e in entries:
            result.dc_list.append({
                "name": e.get("cn", ""),
                "dns_hostname": e.get("dNSHostName", ""),
                "os": e.get("operatingSystem", ""),
                "os_version": e.get("operatingSystemVersion", ""),
            })

    def _collect_users(self, result: ADAuditResult) -> None:
        """Collecte les informations sur les comptes utilisateurs."""
        now = datetime.now(timezone.utc)
        ninety_days_ago = now - timedelta(days=90)

        # Tous les utilisateurs
        entries = self._search(self._base_dn, "(&(objectClass=user)(objectCategory=person))", [
            "sAMAccountName", "displayName", "userAccountControl",
            "lastLogonTimestamp", "pwdLastSet", "whenCreated",
            "memberOf", "adminCount",
        ])

        for e in entries:
            uac = int(e.get("userAccountControl", "0") or "0")
            is_disabled = bool(uac & 0x2)
            pwd_never_expires = bool(uac & 0x10000)
            sam = e.get("sAMAccountName", "")

            result.total_users += 1
            if is_disabled:
                result.disabled_users += 1
            else:
                result.enabled_users += 1

            # Mots de passe qui n'expirent jamais
            if pwd_never_expires and not is_disabled:
                result.never_expire_password.append({
                    "username": sam,
                    "display_name": e.get("displayName", ""),
                })

            # Utilisateurs jamais connectés
            last_logon_raw = e.get("lastLogonTimestamp")
            if last_logon_raw:
                last_logon = _filetime_to_datetime(int(last_logon_raw))
            else:
                last_logon = None

            if not last_logon and not is_disabled:
                result.never_logged_in.append({
                    "username": sam,
                    "display_name": e.get("displayName", ""),
                    "created": e.get("whenCreated", ""),
                })

            # Utilisateurs inactifs (> 90 jours)
            if last_logon and last_logon < ninety_days_ago and not is_disabled:
                result.inactive_users.append({
                    "username": sam,
                    "display_name": e.get("displayName", ""),
                    "last_logon": last_logon.isoformat(),
                    "days_inactive": (now - last_logon).days,
                })

        # Compte Administrator intégré (RID 500)
        admin_entries = self._search(self._base_dn, "(&(objectClass=user)(objectSid=*-500))", [
            "sAMAccountName", "userAccountControl", "pwdLastSet", "lastLogonTimestamp",
        ])
        if admin_entries:
            adm = admin_entries[0]
            uac = int(adm.get("userAccountControl", "0") or "0")
            result.admin_account_status = {
                "username": adm.get("sAMAccountName", ""),
                "is_disabled": bool(uac & 0x2),
                "is_renamed": adm.get("sAMAccountName", "").lower() != "administrator",
            }

    def _collect_privileged_groups(self, result: ADAuditResult) -> None:
        """Collecte les membres des groupes privilégiés."""
        groups = {
            "Domain Admins": result.domain_admins,
            "Enterprise Admins": result.enterprise_admins,
            "Schema Admins": result.schema_admins,
        }
        for group_name, target_list in groups.items():
            entries = self._search(self._base_dn, f"(&(objectClass=group)(cn={group_name}))", [
                "member",
            ])
            if entries and entries[0].get("member"):
                members = entries[0]["member"]
                if isinstance(members, str):
                    members = [members]
                for member_dn in members:
                    # Extraire le CN du DN
                    cn_match = re.match(r"CN=([^,]+)", member_dn)
                    cn = cn_match.group(1) if cn_match else member_dn
                    # Chercher le sAMAccountName
                    member_info = self._search(
                        self._base_dn,
                        f"(&(objectClass=user)(distinguishedName={member_dn}))",
                        ["sAMAccountName", "userAccountControl"],
                        size_limit=1,
                    )
                    sam = member_info[0].get("sAMAccountName", cn) if member_info else cn
                    uac = int(member_info[0].get("userAccountControl", "0") or "0") if member_info else 0
                    target_list.append({
                        "name": cn,
                        "username": sam,
                        "is_enabled": not bool(uac & 0x2),
                    })

    def _collect_password_policy(self, result: ADAuditResult) -> None:
        """Collecte la politique de mot de passe du domaine."""
        entries = self._search(self._base_dn, "(objectClass=domainDNS)", [
            "minPwdLength", "minPwdAge", "maxPwdAge",
            "pwdHistoryLength", "lockoutThreshold",
            "lockoutDuration", "lockoutObservationWindow",
            "pwdProperties",
        ], size_limit=1)
        if entries:
            pol = entries[0]
            # Convertir les durées (valeurs négatives en 100ns ticks)
            def ticks_to_days(val: str) -> float:
                try:
                    v = abs(int(val))
                    return round(v / 864000000000, 1)  # 100ns → jours
                except (ValueError, TypeError):
                    return 0.0

            def ticks_to_minutes(val: str) -> int:
                try:
                    v = abs(int(val))
                    return int(v / 600000000)  # 100ns → minutes
                except (ValueError, TypeError):
                    return 0

            pwd_props = int(pol.get("pwdProperties", "0") or "0")
            result.password_policy = {
                "min_length": int(pol.get("minPwdLength", "0") or "0"),
                "min_age_days": ticks_to_days(pol.get("minPwdAge", "0")),
                "max_age_days": ticks_to_days(pol.get("maxPwdAge", "0")),
                "history_length": int(pol.get("pwdHistoryLength", "0") or "0"),
                "complexity_required": bool(pwd_props & 1),
                "lockout_threshold": int(pol.get("lockoutThreshold", "0") or "0"),
                "lockout_duration_minutes": ticks_to_minutes(pol.get("lockoutDuration", "0")),
                "lockout_observation_minutes": ticks_to_minutes(pol.get("lockoutObservationWindow", "0")),
            }

        # Fine-Grained Password Policies (PSO)
        pso_base = f"CN=Password Settings Container,CN=System,{self._base_dn}"
        pso_entries = self._search(pso_base, "(objectClass=msDS-PasswordSettings)", [
            "cn", "msDS-MinimumPasswordLength", "msDS-MaximumPasswordAge",
            "msDS-PasswordComplexityEnabled", "msDS-LockoutThreshold",
            "msDS-PSOAppliesTo", "msDS-PasswordSettingsPrecedence",
        ])
        for pso in pso_entries:
            result.fine_grained_policies.append({
                "name": pso.get("cn", ""),
                "min_length": pso.get("msDS-MinimumPasswordLength", ""),
                "complexity": pso.get("msDS-PasswordComplexityEnabled", ""),
                "lockout_threshold": pso.get("msDS-LockoutThreshold", ""),
                "precedence": pso.get("msDS-PasswordSettingsPrecedence", ""),
                "applies_to_count": len(pso.get("msDS-PSOAppliesTo", []) or []),
            })

    def _collect_gpo(self, result: ADAuditResult) -> None:
        """Liste les GPO du domaine."""
        gpo_base = f"CN=Policies,CN=System,{self._base_dn}"
        entries = self._search(gpo_base, "(objectClass=groupPolicyContainer)", [
            "displayName", "cn", "gPCFileSysPath", "whenCreated", "whenChanged",
            "flags",
        ])
        for e in entries:
            flags = int(e.get("flags", "0") or "0")
            result.gpo_list.append({
                "name": e.get("displayName", ""),
                "guid": e.get("cn", ""),
                "path": e.get("gPCFileSysPath", ""),
                "created": e.get("whenCreated", ""),
                "modified": e.get("whenChanged", ""),
                "user_disabled": bool(flags & 1),
                "computer_disabled": bool(flags & 2),
            })

    def _collect_laps(self, result: ADAuditResult) -> None:
        """Vérifie si LAPS est déployé (attribut ms-Mcs-AdmPwd dans le schéma)."""
        schema_dn = f"CN=ms-Mcs-AdmPwd,CN=Schema,CN=Configuration,{self._base_dn}"
        entries = self._search(
            f"CN=Schema,CN=Configuration,{self._base_dn}",
            "(lDAPDisplayName=ms-Mcs-AdmPwd)",
            ["cn"],
            size_limit=1,
        )
        result.laps_schema_present = len(entries) > 0

        # Vérifier aussi Windows LAPS (nouveau)
        if not result.laps_schema_present:
            entries_new = self._search(
                f"CN=Schema,CN=Configuration,{self._base_dn}",
                "(lDAPDisplayName=msLAPS-Password)",
                ["cn"],
                size_limit=1,
            )
            result.laps_schema_present = len(entries_new) > 0

        # Compter les machines avec un mot de passe LAPS
        if result.laps_schema_present:
            laps_entries = self._search(
                self._base_dn,
                "(&(objectClass=computer)(ms-Mcs-AdmPwd=*))",
                ["cn"],
                size_limit=10,
            )
            result.laps_deployed = len(laps_entries) > 0

    # ── Analyse & Findings ────────────────────────────────────────────

    def _analyze(self, result: ADAuditResult) -> None:
        """Analyse les données collectées et génère les findings."""

        # AD-001 : Niveau fonctionnel
        fl = result.domain_functional_level
        if fl in ("2016", "2019", "2022"):
            result.findings.append(ADAuditFinding(
                control_ref="AD-001", title="Niveau fonctionnel forêt/domaine",
                category="Architecture & Design", severity="medium",
                status="compliant",
                evidence=f"Niveau fonctionnel domaine : {fl}",
                remediation="",
            ))
        else:
            result.findings.append(ADAuditFinding(
                control_ref="AD-001", title="Niveau fonctionnel forêt/domaine",
                category="Architecture & Design", severity="medium",
                status="non_compliant",
                evidence=f"Niveau fonctionnel domaine : {fl} (obsolète)",
                remediation="Élever le niveau fonctionnel après vérification de compatibilité.",
            ))

        # AD-002 : Nombre de DC
        dc_count = len(result.dc_list)
        if dc_count >= 2:
            result.findings.append(ADAuditFinding(
                control_ref="AD-002", title="Nombre de contrôleurs de domaine",
                category="Architecture & Design", severity="high",
                status="compliant",
                evidence=f"{dc_count} DC détectés.",
                details={"dc_list": [dc["name"] for dc in result.dc_list]},
            ))
        else:
            result.findings.append(ADAuditFinding(
                control_ref="AD-002", title="Nombre de contrôleurs de domaine",
                category="Architecture & Design", severity="high",
                status="non_compliant",
                evidence=f"Seulement {dc_count} DC détecté(s). Redondance insuffisante.",
                remediation="Déployer un second DC pour la haute disponibilité.",
            ))

        # AD-010 : Nombre de Domain Admins (≤ 5)
        da_count = len(result.domain_admins)
        if da_count <= 5:
            result.findings.append(ADAuditFinding(
                control_ref="AD-010", title="Nombre de Domain Admins",
                category="Comptes Privilégiés", severity="critical",
                status="compliant",
                evidence=f"{da_count} membre(s) dans Domain Admins.",
                details={"members": [m["username"] for m in result.domain_admins]},
            ))
        else:
            result.findings.append(ADAuditFinding(
                control_ref="AD-010", title="Nombre de Domain Admins",
                category="Comptes Privilégiés", severity="critical",
                status="non_compliant",
                evidence=f"{da_count} membres dans Domain Admins (> 5). Risque élevé.",
                remediation="Réduire les Domain Admins au strict nécessaire.",
                details={"members": [m["username"] for m in result.domain_admins]},
            ))

        # AD-012 : Compte Administrator intégré protégé
        admin = result.admin_account_status
        if admin:
            if admin.get("is_disabled") or admin.get("is_renamed"):
                status = "compliant"
                ev = "Le compte Administrator intégré est "
                ev += "désactivé" if admin.get("is_disabled") else f"renommé ({admin.get('username')})"
            else:
                status = "non_compliant"
                ev = "Le compte Administrator intégré est actif et non renommé."
            result.findings.append(ADAuditFinding(
                control_ref="AD-012", title="Compte Administrateur intégré protégé",
                category="Comptes Privilégiés", severity="critical",
                status=status, evidence=ev,
                remediation="Désactiver ou renommer le compte Administrator intégré.",
            ))

        # AD-013 : LAPS déployé
        if result.laps_deployed:
            result.findings.append(ADAuditFinding(
                control_ref="AD-013", title="LAPS déployé",
                category="Comptes Privilégiés", severity="high",
                status="compliant",
                evidence="LAPS est déployé et actif sur au moins une machine.",
            ))
        elif result.laps_schema_present:
            result.findings.append(ADAuditFinding(
                control_ref="AD-013", title="LAPS déployé",
                category="Comptes Privilégiés", severity="high",
                status="partial",
                evidence="Le schéma LAPS est présent mais aucune machine n'a de mot de passe LAPS.",
                remediation="Déployer LAPS via GPO sur les postes et serveurs.",
            ))
        else:
            result.findings.append(ADAuditFinding(
                control_ref="AD-013", title="LAPS déployé",
                category="Comptes Privilégiés", severity="high",
                status="non_compliant",
                evidence="LAPS n'est pas déployé (schéma absent).",
                remediation="Installer et configurer LAPS pour la gestion des mots de passe locaux.",
            ))

        # AD-020 : Politique de mot de passe
        pol = result.password_policy
        if pol:
            min_len = pol.get("min_length", 0)
            complexity = pol.get("complexity_required", False)
            if min_len >= 12 and complexity:
                status = "compliant"
                ev = f"Politique : {min_len} caractères minimum, complexité activée."
            elif min_len >= 8 and complexity:
                status = "partial"
                ev = f"Politique : {min_len} caractères (< 12 recommandés), complexité activée."
            else:
                status = "non_compliant"
                ev = f"Politique insuffisante : {min_len} caractères, complexité={'oui' if complexity else 'non'}."
            result.findings.append(ADAuditFinding(
                control_ref="AD-020", title="Politique de mot de passe domaine",
                category="Politique de Mots de Passe", severity="high",
                status=status, evidence=ev,
                remediation="Configurer la politique pour imposer au moins 12 caractères avec complexité.",
                details=pol,
            ))

        # AD-021 : Fine-Grained Password Policies
        if result.fine_grained_policies:
            result.findings.append(ADAuditFinding(
                control_ref="AD-021", title="Fine-Grained Password Policies",
                category="Politique de Mots de Passe", severity="medium",
                status="compliant",
                evidence=f"{len(result.fine_grained_policies)} PSO configurée(s).",
                details={"policies": [p["name"] for p in result.fine_grained_policies]},
            ))
        else:
            result.findings.append(ADAuditFinding(
                control_ref="AD-021", title="Fine-Grained Password Policies",
                category="Politique de Mots de Passe", severity="medium",
                status="non_compliant",
                evidence="Aucune PSO (Fine-Grained Password Policy) configurée.",
                remediation="Créer des PSO renforcées pour les comptes privilégiés.",
            ))

        # AD-022 : Mots de passe qui n'expirent jamais
        nep_count = len(result.never_expire_password)
        if nep_count == 0:
            result.findings.append(ADAuditFinding(
                control_ref="AD-022", title="Mots de passe qui n'expirent jamais",
                category="Politique de Mots de Passe", severity="high",
                status="compliant",
                evidence="Aucun compte actif n'a le flag 'password never expires'.",
            ))
        else:
            result.findings.append(ADAuditFinding(
                control_ref="AD-022", title="Mots de passe qui n'expirent jamais",
                category="Politique de Mots de Passe", severity="high",
                status="non_compliant",
                evidence=f"{nep_count} compte(s) actif(s) avec mot de passe qui n'expire jamais.",
                remediation="Corriger ces comptes sauf justification documentée.",
                details={"accounts": [u["username"] for u in result.never_expire_password[:20]]},
            ))

        # AD-040 : Réplication (basée sur le nombre de DC)
        if dc_count >= 2:
            result.findings.append(ADAuditFinding(
                control_ref="AD-040", title="Réplication fonctionnelle",
                category="Réplication & Santé", severity="critical",
                status="info",
                evidence=f"{dc_count} DC détectés. Vérifier manuellement la réplication (repadmin /showrepl).",
                remediation="Exécuter 'repadmin /showrepl' pour vérifier la réplication.",
            ))

        # AD-041 : DNS intégré
        result.findings.append(ADAuditFinding(
            control_ref="AD-041", title="DNS intégré fonctionnel",
            category="Réplication & Santé", severity="critical",
            status="info",
            evidence="La vérification DNS nécessite un test réseau dédié.",
            remediation="Vérifier la résolution DNS sur tous les DC.",
        ))

        # AD-050 : Audit des événements (info — nécessite GPO review)
        result.findings.append(ADAuditFinding(
            control_ref="AD-050", title="Audit des événements AD",
            category="Audit & Journalisation", severity="high",
            status="info",
            evidence="L'audit avancé doit être vérifié via les GPO sur les DC.",
            remediation="Configurer la stratégie d'audit avancée via GPO.",
        ))

        # Résumé
        compliant = sum(1 for f in result.findings if f.status == "compliant")
        non_compliant = sum(1 for f in result.findings if f.status == "non_compliant")
        partial = sum(1 for f in result.findings if f.status == "partial")
        info_count = sum(1 for f in result.findings if f.status == "info")

        total = len(result.findings)
        score = round((compliant / (total - info_count)) * 100, 1) if (total - info_count) > 0 else 0.0

        result.summary = {
            "domain": result.domain_name,
            "domain_functional_level": result.domain_functional_level,
            "dc_count": len(result.dc_list),
            "total_users": result.total_users,
            "enabled_users": result.enabled_users,
            "disabled_users": result.disabled_users,
            "domain_admins_count": len(result.domain_admins),
            "inactive_users_count": len(result.inactive_users),
            "never_expire_count": len(result.never_expire_password),
            "gpo_count": len(result.gpo_list),
            "laps_deployed": result.laps_deployed,
            "total_checks": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partial": partial,
            "info": info_count,
            "compliance_score": score,
        }

    # ── Exécution ─────────────────────────────────────────────────────

    def audit(self) -> ADAuditResult:
        """
        Exécute l'audit AD complet :
        1. Connexion LDAP
        2. Collecte des données
        3. Analyse et génération des findings
        """
        result = ADAuditResult()

        try:
            logger.info(f"[AD_AUDIT] Connexion à {self.host}:{self.port} ({self.auth_method})...")
            self._conn = self._connect()
            logger.info(f"[AD_AUDIT] Connecté. Base DN : {self._base_dn}")

            # Collecte
            logger.info("[AD_AUDIT] Collecte des informations domaine...")
            self._collect_domain_info(result)

            logger.info("[AD_AUDIT] Collecte des contrôleurs de domaine...")
            self._collect_domain_controllers(result)

            logger.info("[AD_AUDIT] Collecte des comptes utilisateurs...")
            self._collect_users(result)

            logger.info("[AD_AUDIT] Collecte des groupes privilégiés...")
            self._collect_privileged_groups(result)

            logger.info("[AD_AUDIT] Collecte de la politique de mots de passe...")
            self._collect_password_policy(result)

            logger.info("[AD_AUDIT] Collecte des GPO...")
            self._collect_gpo(result)

            logger.info("[AD_AUDIT] Vérification LAPS...")
            self._collect_laps(result)

            # Analyse
            logger.info("[AD_AUDIT] Analyse et génération des findings...")
            self._analyze(result)

            result.success = True
            logger.info(
                f"[AD_AUDIT] Audit terminé : {result.summary.get('compliance_score', 0)}% "
                f"({result.summary.get('compliant', 0)}/{result.summary.get('total_checks', 0)} conformes)"
            )

        except LDAPException as e:
            result.error = f"Erreur LDAP : {e}"
            logger.error(f"[AD_AUDIT] {result.error}")
        except Exception as e:
            result.error = f"Erreur inattendue : {e}"
            logger.exception(f"[AD_AUDIT] {result.error}")
        finally:
            if self._conn:
                try:
                    self._conn.unbind()
                except Exception:
                    pass
                self._conn = None

        return result

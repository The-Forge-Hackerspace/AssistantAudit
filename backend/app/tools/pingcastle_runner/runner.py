"""
PingCastle Runner — Exécution de PingCastle en mode non interactif (healthcheck)
et parsing des résultats XML pour intégration dans le pipeline d'audit AD.

PingCastle est un outil d'audit Active Directory développé par Netwrix :
https://github.com/netwrix/pingcastle

L'exécutable PingCastle.exe doit être installé sur le système Windows
et son chemin configuré via PINGCASTLE_PATH dans les settings.
"""
import logging
import os
import subprocess
import defusedxml.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Mapping des catégories PingCastle vers des niveaux de sévérité
RISK_CATEGORY_SEVERITY = {
    "PrivilegedAccounts": "critical",
    "StaleObjects": "high",
    "Trusts": "high",
    "Anomalies": "medium",
}

# Mapping points → sévérité pour les risk rules individuelles
def _points_to_severity(points: int) -> str:
    """Convertit un nombre de points PingCastle en sévérité."""
    if points >= 50:
        return "critical"
    elif points >= 20:
        return "high"
    elif points >= 5:
        return "medium"
    else:
        return "low"


def _score_to_maturity_label(maturity_level: int) -> str:
    """Convertit le niveau de maturité PingCastle en label lisible."""
    labels = {
        1: "Niveau 1 – Initial",
        2: "Niveau 2 – Managed",
        3: "Niveau 3 – Defined",
        4: "Niveau 4 – Managed & Measurable",
        5: "Niveau 5 – Optimized",
    }
    return labels.get(maturity_level, f"Niveau {maturity_level}")


@dataclass
class PingCastleRunResult:
    """Résultat de l'exécution de PingCastle."""
    success: bool
    error: Optional[str] = None

    # Scores
    global_score: int = 0
    stale_objects_score: int = 0
    privileged_accounts_score: int = 0
    trust_score: int = 0
    anomaly_score: int = 0
    maturity_level: int = 0

    # Données détaillées
    risk_rules: list = field(default_factory=list)
    domain_info: dict = field(default_factory=dict)
    raw_report: dict = field(default_factory=dict)

    # Findings standardisés pour le framework
    findings: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    # Chemins des rapports
    report_html_path: Optional[str] = None
    report_xml_path: Optional[str] = None


class PingCastleRunner:
    """
    Exécute PingCastle.exe en mode non interactif (healthcheck)
    et parse les résultats XML.
    """

    def __init__(
        self,
        pingcastle_path: str,
        target_host: str,
        domain: str,
        username: str,
        password: str,
        output_dir: str,
        timeout: int = 300,
    ):
        self.pingcastle_path = pingcastle_path
        self.target_host = target_host
        self.domain = domain
        self.username = username
        self.password = password
        self.output_dir = output_dir
        self.timeout = timeout

    def run_healthcheck(self) -> PingCastleRunResult:
        """
        Exécute PingCastle en mode healthcheck contre le DC cible.
        Parse le rapport XML et retourne un résultat structuré.
        """
        # ── Vérifications préliminaires ──
        if not self.pingcastle_path:
            return PingCastleRunResult(
                success=False,
                error="PINGCASTLE_PATH non configuré. "
                      "Définissez le chemin vers PingCastle.exe dans la configuration.",
            )

        exe_path = Path(self.pingcastle_path)
        if not exe_path.exists():
            return PingCastleRunResult(
                success=False,
                error=f"PingCastle.exe introuvable : {self.pingcastle_path}",
            )

        # Créer le répertoire de sortie
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # ── Construction de la commande ──
        # PingCastle --healthcheck --server DC --no-enum-limit --level Full
        # L'authentification se fait via le contexte Windows ou via --login
        cmd = [
            str(exe_path),
            "--healthcheck",
            "--server", self.target_host,
            "--no-enum-limit",
            "--level", "Full",
        ]

        # Ajouter les credentials si fournis
        if self.username and self.password:
            # Format : DOMAIN\username
            login = self.username
            if "\\" not in login and self.domain:
                login = f"{self.domain}\\{self.username}"
            cmd.extend(["--login", login, "--password", self.password])

        logger.info(
            f"[PINGCASTLE] Lancement healthcheck sur {self.target_host} "
            f"(domain={self.domain}, timeout={self.timeout}s)"
        )

        # ── Exécution du process ──
        try:
            # On exécute depuis le répertoire de PingCastle pour que
            # les rapports soient générés à côté de l'exe
            working_dir = str(exe_path.parent)

            process_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=working_dir,
                # Pas de shell=True pour des raisons de sécurité
            )

            logger.info(
                f"[PINGCASTLE] Process terminé (returncode={process_result.returncode})"
            )

            if process_result.returncode != 0:
                stderr = process_result.stderr or process_result.stdout or f"PingCastle exited with code {process_result.returncode} (no output)"
                logger.warning(f"[PINGCASTLE] Erreur PingCastle : {stderr[:500]}")
                # PingCastle peut retourner un code non-zero mais
                # générer quand même un rapport. On essaie de parser.

        except subprocess.TimeoutExpired:
            return PingCastleRunResult(
                success=False,
                error=f"Timeout dépassé ({self.timeout}s). "
                      f"L'audit PingCastle a pris trop de temps.",
            )
        except FileNotFoundError:
            return PingCastleRunResult(
                success=False,
                error=f"Impossible de lancer PingCastle : {self.pingcastle_path}",
            )
        except Exception as e:
            return PingCastleRunResult(
                success=False,
                error=f"Erreur lors de l'exécution de PingCastle : {str(e)}",
            )

        # ── Recherche du rapport XML généré ──
        xml_path = self._find_report(working_dir, "xml")
        html_path = self._find_report(working_dir, "html")

        if not xml_path:
            return PingCastleRunResult(
                success=False,
                error="Aucun rapport XML PingCastle trouvé après l'exécution. "
                      "Vérifiez les droits d'accès et la configuration.",
            )

        # ── Déplacer les rapports vers le répertoire de sortie ──
        try:
            import shutil
            final_xml = out_dir / xml_path.name
            shutil.move(str(xml_path), str(final_xml))
            xml_path = final_xml

            final_html = None
            if html_path:
                final_html = out_dir / html_path.name
                shutil.move(str(html_path), str(final_html))
                html_path = final_html
        except Exception as e:
            logger.warning(f"[PINGCASTLE] Impossible de déplacer les rapports : {e}")

        # ── Parsing du rapport XML ──
        try:
            parsed = self.parse_xml_report(str(xml_path))
        except Exception as e:
            return PingCastleRunResult(
                success=False,
                error=f"Erreur lors du parsing du rapport XML : {str(e)}",
                report_xml_path=str(xml_path),
                report_html_path=str(html_path) if html_path else None,
            )

        # ── Génération des findings standardisés ──
        findings = self.generate_findings(parsed)
        summary = self._generate_summary(parsed, findings)

        return PingCastleRunResult(
            success=True,
            global_score=parsed.get("global_score", 0),
            stale_objects_score=parsed.get("stale_objects_score", 0),
            privileged_accounts_score=parsed.get("privileged_accounts_score", 0),
            trust_score=parsed.get("trust_score", 0),
            anomaly_score=parsed.get("anomaly_score", 0),
            maturity_level=parsed.get("maturity_level", 0),
            risk_rules=parsed.get("risk_rules", []),
            domain_info=parsed.get("domain_info", {}),
            raw_report=parsed,
            findings=findings,
            summary=summary,
            report_xml_path=str(xml_path),
            report_html_path=str(html_path) if html_path else None,
        )

    def _find_report(self, directory: str, extension: str) -> Optional[Path]:
        """Trouve le dernier rapport PingCastle généré dans un répertoire."""
        pattern = f"ad_hc_*.{extension}"
        dir_path = Path(directory)
        reports = sorted(
            dir_path.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return reports[0] if reports else None

    def parse_xml_report(self, xml_path: str) -> dict:
        """
        Parse le rapport XML PingCastle et extrait les données structurées.

        Structure XML PingCastle (simplifiée) :
        <HealthcheckData>
          <GlobalScore>42</GlobalScore>
          <StaleObjectsScore>10</StaleObjectsScore>
          <PrivilegiedGroupScore>15</PrivilegiedGroupScore>
          <TrustScore>5</TrustScore>
          <AnomalyScore>12</AnomalyScore>
          <MaturityLevel>3</MaturityLevel>
          <DomainFQDN>corp.local</DomainFQDN>
          <ForestFQDN>corp.local</ForestFQDN>
          <DomainFunctionalLevel>...</DomainFunctionalLevel>
          <SchemaVersion>...</SchemaVersion>
          <NumberOfDC>2</NumberOfDC>
          <RiskRules>
            <HealthcheckRiskRule>
              <Points>10</Points>
              <Category>PrivilegedAccounts</Category>
              <Model>AccountTakeOver</Model>
              <RiskId>A-AdminPwdTooOld</RiskId>
              <Rationale>The password of the admin... </Rationale>
            </HealthcheckRiskRule>
            ...
          </RiskRules>
        </HealthcheckData>
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Gérer le namespace PingCastle (si présent)
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        def _get_text(tag: str, default: str = "") -> str:
            elem = root.find(f"{ns}{tag}")
            return elem.text if elem is not None and elem.text else default

        def _get_int(tag: str, default: int = 0) -> int:
            try:
                return int(_get_text(tag, str(default)))
            except (ValueError, TypeError):
                return default

        # ── Scores ──
        global_score = _get_int("GlobalScore")
        stale_objects_score = _get_int("StaleObjectsScore")
        privileged_accounts_score = _get_int("PrivilegiedGroupScore")
        trust_score = _get_int("TrustScore")
        anomaly_score = _get_int("AnomalyScore")
        maturity_level = _get_int("MaturityLevel")

        # ── Infos Domaine ──
        domain_info = {
            "domain_fqdn": _get_text("DomainFQDN"),
            "forest_fqdn": _get_text("ForestFQDN"),
            "domain_functional_level": _get_text("DomainFunctionalLevel"),
            "forest_functional_level": _get_text("ForestFunctionalLevel"),
            "schema_version": _get_text("SchemaVersion"),
            "schema_internal_version": _get_text("SchemaInternalVersion"),
            "number_of_dc": _get_int("NumberOfDC"),
            "generation_date": _get_text("GenerationDate"),
            "engine_version": _get_text("EngineVersion"),
        }

        # ── Risk Rules ──
        risk_rules = []
        risk_rules_elem = root.find(f"{ns}RiskRules")
        if risk_rules_elem is not None:
            for rule_elem in risk_rules_elem.findall(f"{ns}HealthcheckRiskRule"):
                points_text = rule_elem.findtext(f"{ns}Points", "0")
                try:
                    points = int(points_text)
                except (ValueError, TypeError):
                    points = 0

                category = rule_elem.findtext(f"{ns}Category", "")
                risk_id = rule_elem.findtext(f"{ns}RiskId", "")
                rationale = rule_elem.findtext(f"{ns}Rationale", "")
                model = rule_elem.findtext(f"{ns}Model", "")

                risk_rules.append({
                    "rule_id": risk_id,
                    "category": category,
                    "model": model,
                    "points": points,
                    "rationale": rationale,
                    "severity": _points_to_severity(points),
                })

        # Trier par points décroissants
        risk_rules.sort(key=lambda r: r["points"], reverse=True)

        return {
            "global_score": global_score,
            "stale_objects_score": stale_objects_score,
            "privileged_accounts_score": privileged_accounts_score,
            "trust_score": trust_score,
            "anomaly_score": anomaly_score,
            "maturity_level": maturity_level,
            "domain_info": domain_info,
            "risk_rules": risk_rules,
        }

    def generate_findings(self, parsed_data: dict) -> list[dict]:
        """
        Transforme les données PingCastle en findings standardisés
        compatibles avec le format du framework d'audit.
        """
        findings = []

        # ── Finding global : score de risque ──
        global_score = parsed_data.get("global_score", 0)
        if global_score == 0:
            score_status = "compliant"
            score_severity = "info"
        elif global_score <= 25:
            score_status = "compliant"
            score_severity = "low"
        elif global_score <= 50:
            score_status = "partial"
            score_severity = "medium"
        elif global_score <= 75:
            score_status = "non_compliant"
            score_severity = "high"
        else:
            score_status = "non_compliant"
            score_severity = "critical"

        findings.append({
            "control_ref": "PC-GLOBAL",
            "title": "Score global PingCastle",
            "description": f"Score de risque global du domaine : {global_score}/100 "
                           f"(0 = excellent, 100 = critique)",
            "severity": score_severity,
            "category": "PingCastle",
            "status": score_status,
            "evidence": f"Global Score: {global_score}, "
                        f"Maturity Level: {parsed_data.get('maturity_level', 'N/A')}",
            "remediation": "Consultez le rapport PingCastle détaillé pour les recommandations.",
        })

        # ── Findings par catégorie de score ──
        score_categories = [
            ("PC-STALE", "Objets obsolètes (Stale Objects)",
             "stale_objects_score", "StaleObjects"),
            ("PC-PRIV", "Comptes privilégiés (Privileged Accounts)",
             "privileged_accounts_score", "PrivilegedAccounts"),
            ("PC-TRUST", "Relations d'approbation (Trusts)",
             "trust_score", "Trusts"),
            ("PC-ANOMALY", "Anomalies",
             "anomaly_score", "Anomalies"),
        ]

        for ref, title, score_key, category in score_categories:
            score = parsed_data.get(score_key, 0)
            if score == 0:
                status = "compliant"
                sev = "info"
            elif score <= 10:
                status = "compliant"
                sev = "low"
            elif score <= 30:
                status = "partial"
                sev = "medium"
            elif score <= 50:
                status = "non_compliant"
                sev = "high"
            else:
                status = "non_compliant"
                sev = "critical"

            # Compter les règles violées dans cette catégorie
            cat_rules = [
                r for r in parsed_data.get("risk_rules", [])
                if r.get("category") == category
            ]

            findings.append({
                "control_ref": ref,
                "title": title,
                "description": f"Score {title} : {score}/100. "
                               f"{len(cat_rules)} règle(s) violée(s) dans cette catégorie.",
                "severity": sev,
                "category": "PingCastle",
                "status": status,
                "evidence": f"Score: {score}, Règles: {len(cat_rules)}",
                "remediation": ", ".join(
                    r.get("rule_id", "") for r in cat_rules[:5]
                ) if cat_rules else "Aucune règle violée.",
                "details": {
                    "score": score,
                    "rules_count": len(cat_rules),
                    "top_rules": cat_rules[:10],
                },
            })

        # ── Findings individuels pour les règles critiques/élevées ──
        for rule in parsed_data.get("risk_rules", []):
            if rule.get("points", 0) >= 10:  # Seulement les règles significatives
                findings.append({
                    "control_ref": f"PC-RULE-{rule.get('rule_id', 'UNKNOWN')}",
                    "title": f"[PingCastle] {rule.get('rule_id', 'Règle inconnue')}",
                    "description": rule.get("rationale", ""),
                    "severity": rule.get("severity", "medium"),
                    "category": f"PingCastle/{rule.get('category', '')}",
                    "status": "non_compliant",
                    "evidence": f"Points: {rule.get('points', 0)}, "
                                f"Modèle: {rule.get('model', 'N/A')}",
                    "remediation": f"Voir la documentation PingCastle pour la règle "
                                   f"{rule.get('rule_id', '')}.",
                })

        return findings

    def _generate_summary(self, parsed_data: dict, findings: list[dict]) -> dict:
        """Génère un résumé des résultats PingCastle."""
        total = len(findings)
        compliant = sum(1 for f in findings if f.get("status") == "compliant")
        non_compliant = sum(1 for f in findings if f.get("status") == "non_compliant")
        partial = sum(1 for f in findings if f.get("status") == "partial")

        domain_info = parsed_data.get("domain_info", {})

        return {
            "tool": "PingCastle",
            "domain": domain_info.get("domain_fqdn", ""),
            "global_score": parsed_data.get("global_score", 0),
            "maturity_level": parsed_data.get("maturity_level", 0),
            "maturity_label": _score_to_maturity_label(
                parsed_data.get("maturity_level", 0)
            ),
            "total_findings": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partial": partial,
            "total_risk_rules": len(parsed_data.get("risk_rules", [])),
            "critical_rules": sum(
                1 for r in parsed_data.get("risk_rules", [])
                if r.get("severity") == "critical"
            ),
            "high_rules": sum(
                1 for r in parsed_data.get("risk_rules", [])
                if r.get("severity") == "high"
            ),
            "scores": {
                "global": parsed_data.get("global_score", 0),
                "stale_objects": parsed_data.get("stale_objects_score", 0),
                "privileged_accounts": parsed_data.get("privileged_accounts_score", 0),
                "trust": parsed_data.get("trust_score", 0),
                "anomaly": parsed_data.get("anomaly_score", 0),
            },
        }

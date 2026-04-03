"""
Tests d'infrastructure — Validation du durcissement Docker (TOS-60 / US002).

Valide la configuration CI/CD et Docker par analyse statique des fichiers,
sans nécessiter de runtime Docker.
"""

import re
from pathlib import Path

import pytest
import yaml

# Chemins relatifs depuis la racine du projet
ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
DOCKERIGNORE = ROOT / ".dockerignore"
DOCKERFILE = ROOT / "Dockerfile"


@pytest.fixture(scope="module")
def ci_config():
    """Charge et parse le workflow CI."""
    assert CI_WORKFLOW.exists(), f"Fichier CI introuvable : {CI_WORKFLOW}"
    return yaml.safe_load(CI_WORKFLOW.read_text())


@pytest.fixture(scope="module")
def dockerignore_content():
    """Charge le contenu du .dockerignore."""
    assert DOCKERIGNORE.exists(), f".dockerignore introuvable : {DOCKERIGNORE}"
    return DOCKERIGNORE.read_text()


@pytest.fixture(scope="module")
def dockerfile_content():
    """Charge le contenu du Dockerfile."""
    assert DOCKERFILE.exists(), f"Dockerfile introuvable : {DOCKERFILE}"
    return DOCKERFILE.read_text()


# -------------------------------------------------------------------------
# E2E-POS : Configuration Trivy valide dans le workflow CI (Priorité 15)
# -------------------------------------------------------------------------
class TestCiTrivyScanConfigValid:
    """Valide que le job Trivy est correctement configuré dans le CI."""

    def test_scan_job_exists_with_trivy_action(self, ci_config):
        """Le job 'scan' utilise l'action aquasecurity/trivy-action."""
        jobs = ci_config.get("jobs", {})
        assert "scan" in jobs, "Job 'scan' absent du workflow CI"

        scan_steps = jobs["scan"].get("steps", [])
        trivy_steps = [s for s in scan_steps if "aquasecurity/trivy-action" in s.get("uses", "")]
        assert len(trivy_steps) >= 1, "Aucune step utilisant trivy-action trouvée"

    def test_trivy_exit_code_blocks_pipeline(self, ci_config):
        """exit-code: '1' pour que le pipeline échoue sur détection."""
        trivy_step = _find_trivy_step(ci_config)
        exit_code = str(trivy_step.get("with", {}).get("exit-code", ""))
        assert exit_code == "1", f"exit-code doit être '1' (bloquant), trouvé : '{exit_code}'"

    def test_trivy_severity_critical(self, ci_config):
        """severity: CRITICAL — seuil correct."""
        trivy_step = _find_trivy_step(ci_config)
        severity = trivy_step.get("with", {}).get("severity", "")
        assert "CRITICAL" in severity, f"Severity doit inclure 'CRITICAL', trouvé : '{severity}'"

    def test_scan_depends_on_build(self, ci_config):
        """Le job scan dépend du job build (chaîne correcte)."""
        scan_job = ci_config["jobs"]["scan"]
        needs = scan_job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "build" in needs, f"Le job scan doit dépendre de build, trouvé : {needs}"


# -------------------------------------------------------------------------
# E2E-NEG : Le pipeline rejette une mauvaise config Trivy (Priorité 15)
# -------------------------------------------------------------------------
class TestCiTrivyScanBlocksOnCritical:
    """Valide le comportement bloquant et le reporting Trivy."""

    def test_exit_code_is_not_zero(self, ci_config):
        """exit-code ne doit PAS être '0' (sinon le scan est non-bloquant)."""
        trivy_step = _find_trivy_step(ci_config)
        exit_code = str(trivy_step.get("with", {}).get("exit-code", ""))
        assert exit_code != "0", "exit-code '0' rend le scan non-bloquant"

    def test_trivy_format_readable(self, ci_config):
        """Format de sortie lisible (table ou sarif)."""
        trivy_step = _find_trivy_step(ci_config)
        fmt = trivy_step.get("with", {}).get("format", "")
        assert fmt in ("table", "sarif", "json"), f"Format Trivy doit être lisible, trouvé : '{fmt}'"

    def test_trivy_results_uploaded_as_artifact(self, ci_config):
        """Les résultats Trivy sont uploadés comme artefact CI."""
        scan_steps = ci_config["jobs"]["scan"]["steps"]
        upload_steps = [s for s in scan_steps if "upload-artifact" in s.get("uses", "")]
        assert len(upload_steps) >= 1, "Aucune step upload-artifact dans le job scan"


# -------------------------------------------------------------------------
# SEC-1 : Validation SHA pin de l'action Trivy (Priorité 20)
# -------------------------------------------------------------------------
class TestCiTrivyActionShaPinned:
    """
    Valide que trivy-action utilise une référence SHA immuable.

    EXPECTED FAIL — L'action utilise actuellement un tag mutable (@0.35.0).
    Ce test sert de garde de régression pour quand le fix sera appliqué.
    Ref: CVE-2026-33634 (supply chain via tags GitHub Actions mutables).
    """

    @pytest.mark.xfail(
        reason="W1: trivy-action utilise un tag mutable (@0.35.0) — à corriger",
        strict=True,
    )
    def test_trivy_action_uses_sha_reference(self, ci_config):
        """L'action Trivy doit utiliser un hash SHA complet (40+ hex chars)."""
        trivy_step = _find_trivy_step(ci_config)
        uses_ref = trivy_step["uses"]
        # Format attendu: aquasecurity/trivy-action@<sha_hex_40+>
        sha_pattern = re.compile(r"@[0-9a-f]{40,}")
        assert sha_pattern.search(uses_ref), f"trivy-action doit être épinglé par SHA, trouvé : '{uses_ref}'"


# -------------------------------------------------------------------------
# SEC-2 : Pas de secrets dans l'image Docker (Priorité 15)
# -------------------------------------------------------------------------
class TestDockerignoreExcludesSecrets:
    """Valide que .dockerignore empêche l'inclusion de fichiers sensibles."""

    @pytest.mark.parametrize(
        "pattern",
        [
            ".env",
            ".env.*",
            "*.db",
            "*.sqlite",
            "certs/",
            ".git",
        ],
    )
    def test_sensitive_pattern_excluded(self, dockerignore_content, pattern):
        """Le pattern sensible est présent dans .dockerignore."""
        # Normalise : supprime les commentaires et lignes vides
        lines = [
            line.strip()
            for line in dockerignore_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert pattern in lines, f"Pattern '{pattern}' absent de .dockerignore"


class TestDockerfileNoSecretCopy:
    """Valide que le Dockerfile ne copie pas explicitement de fichiers secrets."""

    @pytest.mark.parametrize(
        "forbidden_pattern",
        [
            r"COPY\s+.*\.env",
            r"COPY\s+.*\.env\.",
            r"COPY\s+.*credentials",
            r"COPY\s+.*\.key\s",
            r"COPY\s+.*\.pem\s",
            r"ADD\s+.*\.env",
        ],
    )
    def test_no_secret_copy_directive(self, dockerfile_content, forbidden_pattern):
        """Aucune directive COPY/ADD ne référence des fichiers secrets."""
        matches = re.findall(forbidden_pattern, dockerfile_content, re.IGNORECASE)
        assert not matches, f"Directive dangereuse trouvée dans Dockerfile : {matches}"


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def _find_trivy_step(ci_config):
    """Retourne la step Trivy du job scan."""
    scan_steps = ci_config["jobs"]["scan"]["steps"]
    for step in scan_steps:
        uses = step.get("uses", "")
        if isinstance(uses, str) and "aquasecurity/trivy-action" in uses:
            return step
    pytest.fail("Step trivy-action introuvable dans le job scan")

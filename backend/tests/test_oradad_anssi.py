"""
Tests pour le modele AnssiCheckpoint, le script de seed et le service OradadAnalysisService.
"""

import csv
import io
import tarfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.models.anssi_checklist import AnssiCheckpoint
from app.services.oradad_analysis_service import (
    UAC_ACCOUNTDISABLE,
    UAC_DONT_EXPIRE_PASSWD,
    UAC_DONT_REQUIRE_PREAUTH,
    UAC_ENCRYPTED_TEXT_PASSWORD_ALLOWED,
    UAC_SERVER_TRUST_ACCOUNT,
    UAC_TRUSTED_FOR_DELEGATION,
    OradadAnalysisService,
)
from scripts.seed_anssi_checkpoints import ANSSI_CHECKPOINTS, seed

# ─── Helpers ──────────────────────────────────────────────────────────


def _make_tar(files: dict[str, list[dict[str, str]]]) -> bytes:
    """Create a tar archive from dict of {filename: [rows]}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for filename, rows in files.items():
            if not rows:
                continue
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
            data = output.getvalue().encode("utf-8")
            info = tarfile.TarInfo(name=f"domain/{filename}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _ad_timestamp(dt: datetime) -> str:
    """Convert datetime to AD FILETIME string."""
    epoch_diff = 116444736000000000
    unix_ts = dt.timestamp()
    return str(int(unix_ts * 10_000_000 + epoch_diff))


def _seed_checkpoints(db: Session) -> None:
    """Seed only the checkpoints needed for tests."""
    seed(db)


def _make_user(
    name: str = "testuser",
    uac: int = 512,
    admin_count: str = "0",
    member_of: str = "",
    spn: str = "",
    pwd_last_set: str = "0",
    last_logon: str = "0",
    primary_group_id: str = "513",
) -> dict[str, str]:
    return {
        "sAMAccountName": name,
        "userAccountControl": str(uac),
        "adminCount": admin_count,
        "memberOf": member_of,
        "servicePrincipalName": spn,
        "pwdLastSet": pwd_last_set,
        "lastLogonTimestamp": last_logon,
        "primaryGroupID": primary_group_id,
    }


# ─── Model CRUD ──────────────────────────────────────────────────────


class TestAnssiCheckpointModel:
    def test_create_checkpoint(self, db_session: Session):
        cp = AnssiCheckpoint(
            vuln_id="test_vuln_1",
            level=1,
            title_fr="Test checkpoint",
            description="Description test",
            recommendation="Recommendation test",
            category="accounts",
            required_attributes=["attr1"],
            target_object_types=["user"],
            auto_checkable=True,
            severity_score=80,
        )
        db_session.add(cp)
        db_session.commit()

        result = db_session.query(AnssiCheckpoint).filter_by(vuln_id="test_vuln_1").first()
        assert result is not None
        assert result.level == 1
        assert result.severity_score == 80
        assert result.required_attributes == ["attr1"]

    def test_vuln_id_unique(self, db_session: Session):
        cp1 = AnssiCheckpoint(
            vuln_id="unique_test",
            level=1,
            title_fr="A",
            description="D",
            recommendation="R",
            category="accounts",
            required_attributes=[],
            target_object_types=[],
            auto_checkable=True,
            severity_score=50,
        )
        cp2 = AnssiCheckpoint(
            vuln_id="unique_test",
            level=2,
            title_fr="B",
            description="D2",
            recommendation="R2",
            category="permissions",
            required_attributes=[],
            target_object_types=[],
            auto_checkable=True,
            severity_score=60,
        )
        db_session.add(cp1)
        db_session.commit()
        db_session.add(cp2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_repr(self, db_session: Session):
        cp = AnssiCheckpoint(
            vuln_id="repr_test",
            level=2,
            title_fr="Repr",
            description="D",
            recommendation="R",
            category="accounts",
            required_attributes=[],
            target_object_types=[],
            auto_checkable=True,
            severity_score=50,
        )
        assert "repr_test" in repr(cp)


# ─── Seed script ─────────────────────────────────────────────────────


class TestSeedScript:
    def test_seed_inserts_all(self, db_session: Session):
        result = seed(db_session)
        assert result["inserted"] == len(ANSSI_CHECKPOINTS)
        assert result["updated"] == 0
        count = db_session.query(AnssiCheckpoint).count()
        assert count == len(ANSSI_CHECKPOINTS)

    def test_seed_idempotent(self, db_session: Session):
        seed(db_session)
        result = seed(db_session)
        assert result["inserted"] == 0
        assert result["updated"] == len(ANSSI_CHECKPOINTS)
        count = db_session.query(AnssiCheckpoint).count()
        assert count == len(ANSSI_CHECKPOINTS)

    def test_seed_updates_values(self, db_session: Session):
        seed(db_session)
        # Verify a specific checkpoint
        cp = db_session.query(AnssiCheckpoint).filter_by(vuln_id="vuln1_privileged_members").first()
        assert cp is not None
        assert cp.level == 1
        assert cp.category == "accounts"
        assert cp.severity_score == 80


# ─── Tar parsing ─────────────────────────────────────────────────────


class TestParseTar:
    def test_parse_user_tsv(self):
        users = [
            {"sAMAccountName": "admin1", "userAccountControl": "512"},
            {"sAMAccountName": "user1", "userAccountControl": "514"},
        ]
        tar_data = _make_tar({"user.tsv": users})
        result = OradadAnalysisService.parse_oradad_tar(tar_data)
        assert "users" in result
        assert len(result["users"]) == 2
        assert result["users"][0]["sAMAccountName"] == "admin1"

    def test_parse_multiple_types(self):
        tar_data = _make_tar(
            {
                "user.tsv": [{"sAMAccountName": "u1", "userAccountControl": "512"}],
                "group.tsv": [{"sAMAccountName": "g1", "member": "u1"}],
                "computer.tsv": [{"sAMAccountName": "PC1$", "userAccountControl": "4096"}],
            }
        )
        result = OradadAnalysisService.parse_oradad_tar(tar_data)
        assert len(result["users"]) == 1
        assert len(result["groups"]) == 1
        assert len(result["computers"]) == 1

    def test_parse_empty_tar(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w"):
            pass
        result = OradadAnalysisService.parse_oradad_tar(buf.getvalue())
        assert result == {}

    def test_parse_invalid_tar(self):
        with pytest.raises(ValidationError, match="Archive ORADAD invalide"):
            OradadAnalysisService.parse_oradad_tar(b"not a tar file")


# ─── ANSSI checks ────────────────────────────────────────────────────


class TestAnssiChecks:
    @pytest.fixture(autouse=True)
    def _seed(self, db_session: Session):
        _seed_checkpoints(db_session)

    def test_privileged_members_pass(self, db_session: Session):
        users = [_make_user(f"admin{i}", admin_count="1") for i in range(10)]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_privileged_members")
        assert f["status"] == "pass"

    def test_privileged_members_fail(self, db_session: Session):
        users = [_make_user(f"admin{i}", admin_count="1") for i in range(60)]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_privileged_members")
        assert f["status"] == "fail"
        assert "60" in f["details"]

    def test_dont_expire_priv(self, db_session: Session):
        users = [
            _make_user("badadmin", uac=512 | UAC_DONT_EXPIRE_PASSWD, admin_count="1"),
            _make_user("goodadmin", uac=512, admin_count="1"),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_dont_expire_priv")
        assert f["status"] == "fail"
        assert "badadmin" in f["affected_objects"]

    def test_spn_priv(self, db_session: Session):
        users = [
            _make_user("spnadmin", admin_count="1", spn="MSSQLSvc/server:1433"),
            _make_user("cleanadmin", admin_count="1"),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_spn_priv")
        assert f["status"] == "fail"
        assert "spnadmin" in f["affected_objects"]

    def test_preauth_priv(self, db_session: Session):
        users = [
            _make_user("nopreauth", uac=512 | UAC_DONT_REQUIRE_PREAUTH, admin_count="1"),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_kerberos_properties_preauth_priv")
        assert f["status"] == "fail"

    def test_password_change_priv(self, db_session: Session):
        old_time = datetime.now(timezone.utc) - timedelta(days=4 * 365)
        users = [
            _make_user("oldpwd", admin_count="1", pwd_last_set=_ad_timestamp(old_time)),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_password_change_priv")
        assert f["status"] == "fail"

    def test_dormant_accounts_pass(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=30)
        users = [_make_user(f"active{i}", last_logon=_ad_timestamp(recent)) for i in range(10)]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_user_accounts_dormant")
        assert f["status"] == "pass"

    def test_dormant_accounts_fail(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=30)
        old = datetime.now(timezone.utc) - timedelta(days=400)
        users = [_make_user("active1", last_logon=_ad_timestamp(recent))]
        users += [_make_user(f"dormant{i}", last_logon=_ad_timestamp(old)) for i in range(5)]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_user_accounts_dormant")
        assert f["status"] == "fail"

    def test_delegation_t4d(self, db_session: Session):
        data = {
            "users": [
                _make_user("deleg_user", uac=512 | UAC_TRUSTED_FOR_DELEGATION),
            ],
            "computers": [
                # DC — should be excluded
                {
                    "sAMAccountName": "DC1$",
                    "userAccountControl": str(UAC_SERVER_TRUST_ACCOUNT | UAC_TRUSTED_FOR_DELEGATION),
                },
                # Non-DC server with unconstrained delegation
                {"sAMAccountName": "SRV1$", "userAccountControl": str(4096 | UAC_TRUSTED_FOR_DELEGATION)},
            ],
        }
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln2_delegation_t4d")
        assert f["status"] == "fail"
        assert "deleg_user" in f["affected_objects"]
        assert "SRV1$" in f["affected_objects"]
        assert "DC1$" not in f["affected_objects"]

    def test_dont_expire_all(self, db_session: Session):
        users = [
            _make_user("svc1", uac=512 | UAC_DONT_EXPIRE_PASSWD),
            _make_user("normal1", uac=512),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln2_dont_expire")
        assert f["status"] == "fail"

    def test_krbtgt_old_password(self, db_session: Session):
        old = datetime.now(timezone.utc) - timedelta(days=400)
        users = [_make_user("krbtgt", pwd_last_set=_ad_timestamp(old))]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln2_krbtgt")
        assert f["status"] == "fail"
        assert "400" in f["details"] or "399" in f["details"]

    def test_krbtgt_recent_password(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=30)
        users = [_make_user("krbtgt", pwd_last_set=_ad_timestamp(recent))]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln2_krbtgt")
        assert f["status"] == "pass"

    def test_protected_users(self, db_session: Session):
        users = [
            _make_user("admin_protected", admin_count="1", member_of="CN=Protected Users,CN=Users"),
            _make_user("admin_unprotected", admin_count="1", member_of="CN=Domain Admins"),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln3_protected_users")
        assert f["status"] == "fail"
        assert "admin_unprotected" in f["affected_objects"]
        assert "admin_protected" not in f["affected_objects"]

    def test_reversible_password(self, db_session: Session):
        users = [
            _make_user("reversible", uac=512 | UAC_ENCRYPTED_TEXT_PASSWORD_ALLOWED),
            _make_user("normal", uac=512),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln3_reversible_password")
        assert f["status"] == "fail"
        assert "reversible" in f["affected_objects"]

    def test_disabled_accounts_excluded(self, db_session: Session):
        users = [
            _make_user("disabled_admin", uac=UAC_ACCOUNTDISABLE | UAC_DONT_EXPIRE_PASSWD, admin_count="1"),
        ]
        data = {"users": users}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        f = next(f for f in findings if f["vuln_id"] == "vuln1_dont_expire_priv")
        assert f["status"] == "pass"

    def test_not_checked_acl_vulns(self, db_session: Session):
        data = {"users": []}
        findings = OradadAnalysisService.run_anssi_checks(db_session, data)
        acl_findings = [f for f in findings if f["vuln_id"] == "vuln1_permissions_naming_context"]
        assert acl_findings[0]["status"] == "not_checked"


# ─── Score calculation ────────────────────────────────────────────────


class TestCalculateScore:
    def test_all_pass(self):
        findings = [
            {"status": "pass", "level": 1, "severity_score": 80},
            {"status": "pass", "level": 2, "severity_score": 60},
        ]
        score = OradadAnalysisService.calculate_score(findings)
        assert score["score"] == 100
        assert score["level"] == 5
        assert score["passed"] == 2
        assert score["failed"] == 0

    def test_all_fail(self):
        findings = [
            {"status": "fail", "level": 1, "severity_score": 100},
            {"status": "fail", "level": 2, "severity_score": 60},
        ]
        score = OradadAnalysisService.calculate_score(findings)
        assert score["score"] == 0
        assert score["level"] == 1
        assert score["failed"] == 2

    def test_mixed(self):
        findings = [
            {"status": "pass", "level": 1, "severity_score": 100},
            {"status": "fail", "level": 2, "severity_score": 60},
            {"status": "not_checked", "level": 3, "severity_score": 40},
        ]
        score = OradadAnalysisService.calculate_score(findings)
        assert score["level"] == 2
        assert 0 < score["score"] < 100
        assert score["passed"] == 1
        assert score["failed"] == 1
        assert score["not_checked"] == 1
        assert score["total_checks"] == 3

    def test_empty_findings(self):
        score = OradadAnalysisService.calculate_score([])
        assert score["score"] == 100
        assert score["level"] == 5
        assert score["total_checks"] == 0

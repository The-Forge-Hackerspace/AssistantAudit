"""Tests pré-remplissage assessment depuis pipeline (TOS-15 / US011)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.agent_task import AgentTask
from app.models.assessment import ComplianceStatus, ControlResult
from app.models.collect_pipeline import CollectPipeline, PipelineStatus, PipelineStepStatus
from app.models.entreprise import Entreprise
from app.models.site import Site
from app.services.pipeline_service import (
    NMAP_CONTROL_MAP,
    prefill_assessment_from_pipeline,
)
from tests.factories import (
    AssessmentCampaignFactory,
    AssessmentFactory,
    AuditFactory,
    ControlFactory,
    ControlResultFactory,
    EquipementFactory,
    FrameworkCategoryFactory,
    FrameworkFactory,
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def _site(db_session: Session, auditeur_user):
    ent = Entreprise(
        nom="Ent Prefill",
        secteur_activite="IT",
        adresse="1 rue Prefill",
        siret="88888888800010",
        owner_id=auditeur_user.id,
    )
    db_session.add(ent)
    db_session.flush()
    site = Site(nom="Site Prefill", entreprise_id=ent.id, adresse="2 rue Prefill")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


@pytest.fixture()
def _agent(db_session: Session, auditeur_user):
    agent = Agent(
        name="Agent Prefill",
        user_id=auditeur_user.id,
        status="active",
        allowed_tools=["nmap"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture()
def _scan_task(db_session: Session, _agent, auditeur_user):
    """AgentTask nmap completed avec result_summary contenant 2 hôtes."""
    task = AgentTask(
        agent_id=_agent.id,
        owner_id=auditeur_user.id,
        tool="nmap",
        parameters={"target": "10.0.0.0/24"},
        status="completed",
        result_summary={
            "hosts": [
                {
                    "ip": "10.0.0.1",
                    "hostname": "telnet-host",
                    "ports": [
                        {"port": 23, "protocol": "tcp", "state": "open", "service": "telnet"},
                        {"port": 22, "protocol": "tcp", "state": "open", "service": "ssh"},
                    ],
                },
                {
                    "ip": "10.0.0.2",
                    "hostname": "rdp-host",
                    "ports": [
                        {"port": 3389, "protocol": "tcp", "state": "open", "service": "ms-wbt-server"},
                    ],
                },
            ]
        },
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture()
def _pipeline(db_session: Session, _site, _agent, _scan_task, auditeur_user):
    """Pipeline completed lié à un scan task non vide."""
    p = CollectPipeline(
        site_id=_site.id,
        agent_id=_agent.id,
        target="10.0.0.0/24",
        created_by=auditeur_user.id,
        status=PipelineStatus.COMPLETED,
        scan_status=PipelineStepStatus.COMPLETED,
        equipments_status=PipelineStepStatus.COMPLETED,
        collects_status=PipelineStepStatus.COMPLETED,
        scan_task_uuid=_scan_task.task_uuid,
        hosts_discovered=2,
        equipments_created=2,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture()
def _assessment_with_controls(db_session: Session, _site, auditeur_user):
    """Assessment + framework + controles avec ref_id mappés dans NMAP_CONTROL_MAP."""
    fw = FrameworkFactory.create(db_session, ref_id="FW_PREFILL", name="FW Prefill")
    cat = FrameworkCategoryFactory.create(db_session, framework_id=fw.id)

    controls = {
        ref: ControlFactory.create(db_session, category_id=cat.id, ref_id=ref, title=f"Contrôle {ref}")
        for ref in ("SW-004", "LSRV-021", "WSRV-031", "SW-030")
    }

    eq = EquipementFactory.create(db_session, site_id=_site.id, hostname="eq-prefill")
    audit = AuditFactory.create(db_session, entreprise_id=_site.entreprise_id, owner_id=auditeur_user.id)
    campaign = AssessmentCampaignFactory.create(db_session, audit_id=audit.id)
    assessment = AssessmentFactory.create(
        db_session, campaign_id=campaign.id, equipement_id=eq.id, framework_id=fw.id
    )

    results = {
        ref: ControlResultFactory.create(
            db_session, assessment_id=assessment.id, control_id=ctrl.id, status="not_assessed"
        )
        for ref, ctrl in controls.items()
    }
    return {"assessment": assessment, "controls": controls, "results": results}


# ── Mapping ─────────────────────────────────────────────────────────────────


class TestNmapControlMap:
    def test_map_has_required_fields(self):
        for entry in NMAP_CONTROL_MAP:
            assert {"port", "proto", "control_ref", "service", "reason"} <= entry.keys()
            assert isinstance(entry["port"], int)
            assert entry["proto"] in {"tcp", "udp"}

    def test_map_covers_telnet_rdp_snmp(self):
        refs = {(e["port"], e["proto"]) for e in NMAP_CONTROL_MAP}
        assert (23, "tcp") in refs
        assert (3389, "tcp") in refs
        assert (161, "udp") in refs


# ── Service ─────────────────────────────────────────────────────────────────


class TestPrefillService:
    def test_prefill_marks_non_compliant(self, db_session, _pipeline, _assessment_with_controls):
        result = prefill_assessment_from_pipeline(
            db_session, _pipeline.id, _assessment_with_controls["assessment"].id
        )
        db_session.commit()

        assert result["controls_compliant"] == 0
        assert result["controls_non_compliant"] >= 2
        assert result["controls_prefilled"] == result["controls_non_compliant"]
        refs_in_details = {d["control_ref"] for d in result["details"]}
        # Telnet → SW-004 + LSRV-021, RDP → WSRV-031
        assert {"SW-004", "LSRV-021", "WSRV-031"} <= refs_in_details

    def test_prefill_writes_evidence_and_metadata(
        self, db_session, _pipeline, _assessment_with_controls
    ):
        prefill_assessment_from_pipeline(
            db_session, _pipeline.id, _assessment_with_controls["assessment"].id
        )
        db_session.commit()

        sw004 = _assessment_with_controls["results"]["SW-004"]
        db_session.refresh(sw004)
        assert sw004.status == ComplianceStatus.NON_COMPLIANT
        assert sw004.is_auto_assessed is True
        assert sw004.assessed_by == "pipeline_nmap"
        assert sw004.assessed_at is not None
        assert "10.0.0.1" in sw004.evidence
        assert "Telnet" in sw004.evidence

    def test_prefill_skips_controls_without_findings(
        self, db_session, _pipeline, _assessment_with_controls
    ):
        prefill_assessment_from_pipeline(
            db_session, _pipeline.id, _assessment_with_controls["assessment"].id
        )
        db_session.commit()

        # SW-030 cible SNMP (161/udp), absent du scan → reste not_assessed
        sw030 = _assessment_with_controls["results"]["SW-030"]
        db_session.refresh(sw030)
        assert sw030.status == ComplianceStatus.NOT_ASSESSED
        assert sw030.is_auto_assessed is False

    def test_prefill_unknown_pipeline_raises(self, db_session, _assessment_with_controls):
        with pytest.raises(ValueError, match="introuvable"):
            prefill_assessment_from_pipeline(
                db_session, 999999, _assessment_with_controls["assessment"].id
            )

    def test_prefill_pipeline_not_completed_raises(
        self, db_session, _site, _agent, auditeur_user, _assessment_with_controls
    ):
        p = CollectPipeline(
            site_id=_site.id,
            agent_id=_agent.id,
            target="10.0.0.0/24",
            created_by=auditeur_user.id,
            status=PipelineStatus.RUNNING,
        )
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)

        with pytest.raises(ValueError, match="n'est pas terminé"):
            prefill_assessment_from_pipeline(
                db_session, p.id, _assessment_with_controls["assessment"].id
            )

    def test_prefill_unknown_assessment_raises(self, db_session, _pipeline):
        with pytest.raises(ValueError, match="introuvable"):
            prefill_assessment_from_pipeline(db_session, _pipeline.id, 999999)

    def test_prefill_empty_scan_raises(
        self, db_session, _site, _agent, auditeur_user, _assessment_with_controls
    ):
        p = CollectPipeline(
            site_id=_site.id,
            agent_id=_agent.id,
            target="10.0.0.0/24",
            created_by=auditeur_user.id,
            status=PipelineStatus.COMPLETED,
            scan_task_uuid=None,
        )
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)

        with pytest.raises(ValueError, match="scan vide"):
            prefill_assessment_from_pipeline(
                db_session, p.id, _assessment_with_controls["assessment"].id
            )


# ── API ─────────────────────────────────────────────────────────────────────


class TestPrefillEndpoint:
    def test_prefill_endpoint_returns_200(
        self, client, auditeur_headers, _pipeline, _assessment_with_controls
    ):
        resp = client.post(
            f"/api/v1/pipelines/{_pipeline.id}/prefill/{_assessment_with_controls['assessment'].id}",
            headers=auditeur_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["controls_non_compliant"] >= 2
        assert data["controls_compliant"] == 0

    def test_prefill_endpoint_unknown_pipeline_returns_404(
        self, client, auditeur_headers, _assessment_with_controls
    ):
        resp = client.post(
            f"/api/v1/pipelines/999999/prefill/{_assessment_with_controls['assessment'].id}",
            headers=auditeur_headers,
        )
        assert resp.status_code == 404

    def test_prefill_endpoint_lecteur_forbidden(
        self, client, lecteur_headers, _pipeline, _assessment_with_controls
    ):
        resp = client.post(
            f"/api/v1/pipelines/{_pipeline.id}/prefill/{_assessment_with_controls['assessment'].id}",
            headers=lecteur_headers,
        )
        assert resp.status_code == 403

    def test_prefill_endpoint_unauthenticated_returns_401(
        self, client, _pipeline, _assessment_with_controls
    ):
        resp = client.post(
            f"/api/v1/pipelines/{_pipeline.id}/prefill/{_assessment_with_controls['assessment'].id}",
        )
        assert resp.status_code == 401

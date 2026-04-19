"""
Génère un jeu de données de démonstration enrichi pour les démos & tests UI.

Crée :
- 4 entreprises clientes (industriel, services, santé/HDS, secteur public)
  avec contacts, sites multiples, équipements variés
- 6 audits couvrant tous les statuts (NOUVEAU, EN_COURS, TERMINE, ARCHIVE)
- Campagnes dans tous les états (DRAFT, IN_PROGRESS, REVIEW, COMPLETED, ARCHIVED)
- ControlResult variés (compliant / non_compliant / not_assessed)
- Findings ouverts/en cours/clos
- 2 agents (1 active Windows, 1 offline Linux) avec historique de tâches

Idempotent : re-exécutable sans duplication (vérifie l'existence par identifiant unique).

Usage : python scripts/seed_demo.py
"""

import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: F401 — enregistre tous les modèles
from app.core.database import SessionLocal
from app.models.agent import Agent
from app.models.agent_task import AgentTask
from app.models.assessment import (
    Assessment,
    AssessmentCampaign,
    CampaignStatus,
    ComplianceStatus,
    ControlResult,
)
from app.models.audit import Audit, AuditStatus
from app.models.entreprise import Contact, Entreprise
from app.models.equipement import (
    EquipementAccessPoint,
    EquipementAuditStatus,
    EquipementCamera,
    EquipementFirewall,
    EquipementHyperviseur,
    EquipementIoT,
    EquipementNAS,
    EquipementRouter,
    EquipementServeur,
    EquipementSwitch,
)
from app.models.finding import Finding, FindingStatus
from app.models.framework import Framework
from app.models.site import Site
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_admin(db) -> User:
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        raise RuntimeError("Utilisateur 'admin' introuvable — démarrer le backend au moins une fois")
    return admin


def _ensure_entreprise(db, owner_id: int, nom: str, **fields) -> Entreprise:
    ent = db.query(Entreprise).filter(Entreprise.nom == nom).first()
    if ent:
        return ent
    ent = Entreprise(nom=nom, owner_id=owner_id, **fields)
    db.add(ent)
    db.flush()
    return ent


def _ensure_contact(db, entreprise_id: int, nom: str, **fields) -> Contact:
    c = db.query(Contact).filter(Contact.nom == nom, Contact.entreprise_id == entreprise_id).first()
    if c:
        return c
    c = Contact(nom=nom, entreprise_id=entreprise_id, **fields)
    db.add(c)
    db.flush()
    return c


def _ensure_site(db, entreprise_id: int, nom: str, **fields) -> Site:
    s = db.query(Site).filter(Site.nom == nom, Site.entreprise_id == entreprise_id).first()
    if s:
        return s
    s = Site(nom=nom, entreprise_id=entreprise_id, **fields)
    db.add(s)
    db.flush()
    return s


def _ensure_equipement(db, model_cls, site_id: int, ip_address: str, **fields):
    from app.models.equipement import Equipement

    eq = (
        db.query(Equipement)
        .filter(Equipement.site_id == site_id, Equipement.ip_address == ip_address)
        .first()
    )
    if eq:
        return eq
    eq = model_cls(site_id=site_id, ip_address=ip_address, **fields)
    db.add(eq)
    db.flush()
    return eq


def _ensure_audit(db, owner_id: int, entreprise_id: int, nom_projet: str, **fields) -> Audit:
    a = (
        db.query(Audit)
        .filter(Audit.nom_projet == nom_projet, Audit.entreprise_id == entreprise_id)
        .first()
    )
    if a:
        return a
    a = Audit(nom_projet=nom_projet, owner_id=owner_id, entreprise_id=entreprise_id, **fields)
    db.add(a)
    db.flush()
    return a


def _ensure_campaign(db, audit_id: int, name: str, **fields) -> AssessmentCampaign:
    c = (
        db.query(AssessmentCampaign)
        .filter(AssessmentCampaign.name == name, AssessmentCampaign.audit_id == audit_id)
        .first()
    )
    if c:
        return c
    c = AssessmentCampaign(name=name, audit_id=audit_id, **fields)
    db.add(c)
    db.flush()
    return c


def _ensure_assessment(db, campaign_id: int, equipement_id: int, framework_id: int) -> Assessment:
    a = (
        db.query(Assessment)
        .filter(
            Assessment.campaign_id == campaign_id,
            Assessment.equipement_id == equipement_id,
            Assessment.framework_id == framework_id,
        )
        .first()
    )
    if a:
        return a
    a = Assessment(
        campaign_id=campaign_id,
        equipement_id=equipement_id,
        framework_id=framework_id,
        assessed_by="admin",
    )
    db.add(a)
    db.flush()
    return a


def _seed_control_results(db, assessment: Assessment, framework: Framework) -> list[ControlResult]:
    """Pour chaque control du framework, crée un ControlResult avec status varié."""
    rng = random.Random(assessment.id)  # déterministe par assessment
    results: list[ControlResult] = []
    existing_by_control = {cr.control_id: cr for cr in assessment.results}

    weights = [
        (ComplianceStatus.COMPLIANT, 0.55),
        (ComplianceStatus.NON_COMPLIANT, 0.20),
        (ComplianceStatus.PARTIALLY_COMPLIANT, 0.10),
        (ComplianceStatus.NOT_ASSESSED, 0.10),
        (ComplianceStatus.NOT_APPLICABLE, 0.05),
    ]
    statuses, probs = zip(*weights)

    for cat in framework.categories:
        for ctrl in cat.controls:
            if ctrl.id in existing_by_control:
                results.append(existing_by_control[ctrl.id])
                continue
            status = rng.choices(statuses, probs, k=1)[0]
            cr = ControlResult(
                assessment_id=assessment.id,
                control_id=ctrl.id,
                status=status,
                evidence=("Contrôle vérifié manuellement" if status != ComplianceStatus.NOT_ASSESSED else None),
                comment=None,
                is_auto_assessed=False,
                assessed_at=_utcnow() if status != ComplianceStatus.NOT_ASSESSED else None,
                assessed_by="admin" if status != ComplianceStatus.NOT_ASSESSED else None,
            )
            db.add(cr)
            results.append(cr)
    db.flush()
    return results


def _seed_findings(db, assessment: Assessment, results: list[ControlResult]) -> int:
    """Crée un Finding pour chaque ControlResult NON_COMPLIANT ou PARTIALLY_COMPLIANT."""
    created = 0
    for cr in results:
        if cr.status not in (ComplianceStatus.NON_COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT):
            continue
        existing = (
            db.query(Finding)
            .filter(Finding.control_result_id == cr.id, Finding.assessment_id == assessment.id)
            .first()
        )
        if existing:
            continue
        ctrl = cr.control
        severity = ctrl.severity.value if ctrl else "medium"
        status = random.Random(cr.id).choice(
            [FindingStatus.OPEN, FindingStatus.OPEN, FindingStatus.IN_PROGRESS, FindingStatus.REMEDIATED]
        )
        finding = Finding(
            control_result_id=cr.id,
            assessment_id=assessment.id,
            equipment_id=assessment.equipement_id,
            title=(ctrl.title if ctrl else "Non-conformité détectée")[:500],
            description=ctrl.description if ctrl else None,
            severity=severity,
            status=status,
            remediation_note=("À planifier sous 30 jours" if status != FindingStatus.OPEN else None),
            assigned_to=("auditeur" if status != FindingStatus.OPEN else None),
        )
        db.add(finding)
        created += 1
    db.flush()
    return created


def _ensure_agent(db, owner_id: int, name: str, agent_uuid: str, **fields) -> Agent:
    a = db.query(Agent).filter(Agent.agent_uuid == agent_uuid).first()
    if a:
        return a
    defaults = dict(
        status="active",
        last_seen=_utcnow(),
        os_info="Windows 11 Pro 23H2",
        agent_version="1.0.0",
        last_ip="172.16.20.50",
    )
    defaults.update(fields)
    a = Agent(
        agent_uuid=agent_uuid,
        name=name,
        user_id=owner_id,
        **defaults,
    )
    db.add(a)
    db.flush()
    return a


def _seed_agent_tasks(db, agent: Agent, owner_id: int, audit_id: int, presets: list[dict]) -> int:
    """Crée un historique de tâches variées pour l'agent."""
    if db.query(AgentTask).filter(AgentTask.agent_id == agent.id).count() > 0:
        return 0

    for p in presets:
        task = AgentTask(
            task_uuid=str(uuid.uuid4()),
            agent_id=agent.id,
            owner_id=owner_id,
            audit_id=audit_id,
            **p,
        )
        db.add(task)
    db.flush()
    return len(presets)


def _agent_a_presets(now: datetime) -> list[dict]:
    """Tâches variées pour l'agent Windows actif (Acme)."""
    return [
        {
            "tool": "nmap",
            "parameters": {"target": "192.168.10.0/24", "options": "-sV -O"},
            "status": "completed",
            "progress": 100,
            "result_summary": {"hosts_found": 12, "open_ports": 47},
            "dispatched_at": now - timedelta(days=2),
            "started_at": now - timedelta(days=2, minutes=-1),
            "completed_at": now - timedelta(days=2, minutes=-15),
        },
        {
            "tool": "nmap",
            "parameters": {"target": "10.0.0.0/24", "options": "-sn"},
            "status": "completed",
            "progress": 100,
            "result_summary": {"hosts_found": 5, "open_ports": 0},
            "dispatched_at": now - timedelta(days=1),
            "started_at": now - timedelta(days=1, minutes=-1),
            "completed_at": now - timedelta(days=1, minutes=-3),
        },
        {
            "tool": "ad_collector",
            "parameters": {"domain": "client-a.local", "credentials_ref": "vault:demo"},
            "status": "failed",
            "progress": 35,
            "error_message": "Connexion LDAP refusée (timeout)",
            "dispatched_at": now - timedelta(hours=8),
            "started_at": now - timedelta(hours=8, minutes=-1),
            "completed_at": now - timedelta(hours=7),
        },
        {
            "tool": "oradad",
            "parameters": {"domain": "client-a.local"},
            "status": "running",
            "progress": 42,
            "dispatched_at": now - timedelta(minutes=20),
            "started_at": now - timedelta(minutes=18),
        },
        {
            "tool": "nmap",
            "parameters": {"target": "192.168.20.1", "options": "-A"},
            "status": "pending",
            "progress": 0,
        },
        {
            "tool": "nmap",
            "parameters": {"target": "192.168.10.50", "options": "-sV --script vuln"},
            "status": "completed",
            "progress": 100,
            "result_summary": {"hosts_found": 1, "open_ports": 8, "vulns": 2},
            "dispatched_at": now - timedelta(days=3),
            "started_at": now - timedelta(days=3, minutes=-2),
            "completed_at": now - timedelta(days=3, minutes=-25),
        },
        {
            "tool": "monkey365",
            "parameters": {"tenant": "acme.onmicrosoft.com", "instance": "All"},
            "status": "completed",
            "progress": 100,
            "result_summary": {"findings": 18, "high": 3, "medium": 9, "low": 6},
            "dispatched_at": now - timedelta(days=4),
            "started_at": now - timedelta(days=4, minutes=-1),
            "completed_at": now - timedelta(days=4, minutes=-50),
        },
    ]


def _agent_b_presets(now: datetime) -> list[dict]:
    """Tâches pour l'agent offline Linux (Gamma) — historique uniquement."""
    return [
        {
            "tool": "nmap",
            "parameters": {"target": "10.20.0.0/16", "options": "-sn"},
            "status": "completed",
            "progress": 100,
            "result_summary": {"hosts_found": 87, "open_ports": 0},
            "dispatched_at": now - timedelta(days=10),
            "started_at": now - timedelta(days=10, minutes=-2),
            "completed_at": now - timedelta(days=10, minutes=-12),
        },
        {
            "tool": "ad_collector",
            "parameters": {"domain": "gamma.local"},
            "status": "completed",
            "progress": 100,
            "result_summary": {"users": 312, "groups": 47, "computers": 124},
            "dispatched_at": now - timedelta(days=9),
            "started_at": now - timedelta(days=9, minutes=-1),
            "completed_at": now - timedelta(days=9, minutes=-6),
        },
        {
            "tool": "nmap",
            "parameters": {"target": "10.20.10.5", "options": "-A"},
            "status": "cancelled",
            "progress": 18,
            "error_message": "Annulé par utilisateur",
            "dispatched_at": now - timedelta(days=8),
            "started_at": now - timedelta(days=8, minutes=-1),
            "completed_at": now - timedelta(days=8, minutes=-3),
        },
    ]


def main() -> None:
    db = SessionLocal()
    try:
        admin = _get_admin(db)
        print(f"[INFO] Admin: id={admin.id}, username={admin.username}")

        frameworks = db.query(Framework).filter(Framework.is_active.is_(True)).all()
        if not frameworks:
            print("[ERREUR] Aucun framework actif — démarrer le backend pour charger les YAML")
            sys.exit(1)
        print(f"[INFO] {len(frameworks)} framework(s) actif(s) trouvé(s)")

        # ─── Entreprise A : Acme Industries (industriel) ─────────────
        ent_a = _ensure_entreprise(
            db,
            owner_id=admin.id,
            nom="Acme Industries SAS",
            adresse="12 rue de l'Innovation, 75001 Paris",
            secteur_activite="Industrie manufacturière",
            siret="12345678900012",
            presentation_desc="PME industrielle, 250 collaborateurs, infra hybride.",
            contraintes_reglementaires="ISO 27001 visée pour 2026, RGPD",
        )
        _ensure_contact(
            db,
            entreprise_id=ent_a.id,
            nom="Jean Dupont",
            role="DSI",
            email="j.dupont@acme.fr",
            telephone="0145678901",
            is_main_contact=True,
        )
        _ensure_contact(
            db,
            entreprise_id=ent_a.id,
            nom="Marie Lefèvre",
            role="RSSI",
            email="m.lefevre@acme.fr",
            telephone="0145678902",
        )

        site_a1 = _ensure_site(
            db,
            entreprise_id=ent_a.id,
            nom="Siège Paris",
            description="Bureaux et datacenter principal",
            adresse="12 rue de l'Innovation, 75001 Paris",
        )
        site_a2 = _ensure_site(
            db,
            entreprise_id=ent_a.id,
            nom="Usine Lille",
            description="Site de production",
            adresse="45 avenue de l'Industrie, 59000 Lille",
        )

        eq_a_fw = _ensure_equipement(
            db,
            EquipementFirewall,
            site_id=site_a1.id,
            ip_address="192.168.10.1",
            hostname="fw-paris-01",
            fabricant="Fortinet",
            os_detected="FortiOS 7.4.2",
            license_status="active",
            vpn_users_count=45,
            rules_count=128,
            status_audit=EquipementAuditStatus.EN_COURS,
        )
        eq_a_sw = _ensure_equipement(
            db,
            EquipementSwitch,
            site_id=site_a1.id,
            ip_address="192.168.10.10",
            hostname="sw-paris-core",
            fabricant="Cisco",
            os_detected="IOS-XE 17.9",
            firmware_version="17.9.4a",
            status_audit=EquipementAuditStatus.A_AUDITER,
        )
        eq_a_srv = _ensure_equipement(
            db,
            EquipementServeur,
            site_id=site_a1.id,
            ip_address="192.168.10.50",
            hostname="srv-ad-01",
            fabricant="Dell",
            os_detected="Windows Server 2022",
            os_version_detail="Datacenter 21H2 build 20348",
            modele_materiel="PowerEdge R650",
            role_list={"roles": ["AD-DS", "DNS", "DHCP"]},
            status_audit=EquipementAuditStatus.CONFORME,
        )
        _ensure_equipement(
            db,
            EquipementHyperviseur,
            site_id=site_a1.id,
            ip_address="192.168.10.60",
            hostname="esx-paris-01",
            fabricant="VMware",
            os_detected="ESXi 8.0 U2",
            status_audit=EquipementAuditStatus.A_AUDITER,
        )
        _ensure_equipement(
            db,
            EquipementRouter,
            site_id=site_a2.id,
            ip_address="192.168.20.1",
            hostname="rtr-lille-01",
            fabricant="Juniper",
            os_detected="JunOS 22.4",
            firmware_version="22.4R3",
            status_audit=EquipementAuditStatus.A_AUDITER,
        )
        _ensure_equipement(
            db,
            EquipementAccessPoint,
            site_id=site_a2.id,
            ip_address="192.168.20.50",
            hostname="ap-lille-01",
            fabricant="Aruba",
            os_detected="ArubaOS 8.11",
            firmware_version="8.11.2.1",
            status_audit=EquipementAuditStatus.NON_CONFORME,
        )

        # ─── Entreprise B : Beta Services (cabinet conseil) ──────────
        ent_b = _ensure_entreprise(
            db,
            owner_id=admin.id,
            nom="Beta Services SARL",
            adresse="8 boulevard des Affaires, 69002 Lyon",
            secteur_activite="Services aux entreprises",
            siret="98765432100021",
            presentation_desc="Cabinet de conseil, 50 collaborateurs, 100% cloud.",
            contraintes_reglementaires="HDS pour clients santé",
        )
        _ensure_contact(
            db,
            entreprise_id=ent_b.id,
            nom="Sophie Martin",
            role="Directrice Opérationnelle",
            email="s.martin@beta-services.fr",
            telephone="0478123456",
            is_main_contact=True,
        )

        site_b1 = _ensure_site(
            db,
            entreprise_id=ent_b.id,
            nom="Bureau Lyon",
            description="Bureau unique",
            adresse="8 boulevard des Affaires, 69002 Lyon",
        )

        _ensure_equipement(
            db,
            EquipementFirewall,
            site_id=site_b1.id,
            ip_address="10.0.0.1",
            hostname="fw-lyon",
            fabricant="pfSense",
            os_detected="pfSense 2.7.2",
            license_status="community",
            vpn_users_count=12,
            rules_count=42,
            status_audit=EquipementAuditStatus.A_AUDITER,
        )

        # ─── Entreprise C : Gamma Healthcare (santé / HDS) ───────────
        ent_c = _ensure_entreprise(
            db,
            owner_id=admin.id,
            nom="Gamma Healthcare SAS",
            adresse="22 quai des Berges, 33000 Bordeaux",
            secteur_activite="Santé — Éditeur logiciel HDS",
            siret="55678912300033",
            presentation_desc="Éditeur de logiciels de gestion hospitalière, 80 collaborateurs.",
            contraintes_reglementaires="Certification HDS (ASIP Santé), RGPD article 9, ANSSI SecNumCloud",
        )
        _ensure_contact(
            db,
            entreprise_id=ent_c.id,
            nom="Pierre Bernard",
            role="DPO",
            email="dpo@gamma-health.fr",
            telephone="0556001122",
            is_main_contact=True,
        )
        _ensure_contact(
            db,
            entreprise_id=ent_c.id,
            nom="Claire Rousseau",
            role="RSSI",
            email="rssi@gamma-health.fr",
            telephone="0556001123",
        )

        site_c1 = _ensure_site(
            db,
            entreprise_id=ent_c.id,
            nom="Datacenter Bordeaux",
            description="Hébergement HDS — production",
            adresse="22 quai des Berges, 33000 Bordeaux",
        )

        eq_c_hv = _ensure_equipement(
            db,
            EquipementHyperviseur,
            site_id=site_c1.id,
            ip_address="10.20.10.1",
            hostname="hv-bdx-prod-01",
            fabricant="Proxmox",
            os_detected="Proxmox VE 8.1",
            status_audit=EquipementAuditStatus.EN_COURS,
        )
        eq_c_nas = _ensure_equipement(
            db,
            EquipementNAS,
            site_id=site_c1.id,
            ip_address="10.20.10.20",
            hostname="nas-bdx-01",
            fabricant="Synology",
            os_detected="DSM 7.2",
            status_audit=EquipementAuditStatus.A_AUDITER,
        )
        eq_c_srv = _ensure_equipement(
            db,
            EquipementServeur,
            site_id=site_c1.id,
            ip_address="10.20.10.30",
            hostname="srv-app-prod",
            fabricant="HPE",
            os_detected="Debian 12",
            os_version_detail="Bookworm 12.5",
            modele_materiel="ProLiant DL360 Gen11",
            role_list={"roles": ["app-server", "database"]},
            status_audit=EquipementAuditStatus.CONFORME,
        )
        eq_c_cam = _ensure_equipement(
            db,
            EquipementCamera,
            site_id=site_c1.id,
            ip_address="10.20.10.200",
            hostname="cam-entrance-01",
            fabricant="Hikvision",
            os_detected="Firmware 5.7.x",
            status_audit=EquipementAuditStatus.NON_CONFORME,
        )
        _ensure_equipement(
            db,
            EquipementIoT,
            site_id=site_c1.id,
            ip_address="10.20.10.210",
            hostname="probe-temp-01",
            fabricant="Bosch",
            os_detected="Custom firmware",
            status_audit=EquipementAuditStatus.A_AUDITER,
        )

        # ─── Entreprise D : Delta Collectivité (secteur public) ──────
        ent_d = _ensure_entreprise(
            db,
            owner_id=admin.id,
            nom="Delta Collectivité Territoriale",
            adresse="1 place de la République, 31000 Toulouse",
            secteur_activite="Secteur public — Collectivité",
            siret="20000123400044",
            presentation_desc="Collectivité de 600 agents, mairie + services techniques.",
            contraintes_reglementaires="RGS, RGPD, ANSSI référentiels Collectivités",
        )
        _ensure_contact(
            db,
            entreprise_id=ent_d.id,
            nom="Antoine Moreau",
            role="DSI",
            email="dsi@delta-mairie.fr",
            telephone="0561112233",
            is_main_contact=True,
        )

        site_d1 = _ensure_site(
            db,
            entreprise_id=ent_d.id,
            nom="Hôtel de Ville",
            description="Administration centrale",
            adresse="1 place de la République, 31000 Toulouse",
        )

        _ensure_equipement(
            db,
            EquipementFirewall,
            site_id=site_d1.id,
            ip_address="172.20.0.1",
            hostname="fw-mairie",
            fabricant="Stormshield",
            os_detected="SNS 4.7",
            license_status="active",
            vpn_users_count=120,
            rules_count=215,
            status_audit=EquipementAuditStatus.A_AUDITER,
        )
        _ensure_equipement(
            db,
            EquipementSwitch,
            site_id=site_d1.id,
            ip_address="172.20.0.10",
            hostname="sw-mairie-core",
            fabricant="HPE Aruba",
            os_detected="ArubaOS-CX 10.10",
            firmware_version="10.10.1010",
            status_audit=EquipementAuditStatus.A_AUDITER,
        )
        _ensure_equipement(
            db,
            EquipementServeur,
            site_id=site_d1.id,
            ip_address="172.20.0.50",
            hostname="srv-files-01",
            fabricant="Dell",
            os_detected="Ubuntu 22.04 LTS",
            os_version_detail="Jammy",
            modele_materiel="PowerEdge R450",
            role_list={"roles": ["file-server", "samba"]},
            status_audit=EquipementAuditStatus.A_AUDITER,
        )

        # ─── Audits ───────────────────────────────────────────────────
        audit_a = _ensure_audit(
            db,
            owner_id=admin.id,
            entreprise_id=ent_a.id,
            nom_projet="Audit annuel Acme 2026",
            status=AuditStatus.EN_COURS,
            date_debut=_utcnow() - timedelta(days=10),
            date_fin=_utcnow() + timedelta(days=20),
            objectifs="Évaluation conformité ISO 27001 sur le périmètre infra centrale",
            scope_covered="Firewall, AD, switching cœur",
            scope_excluded="Postes de travail, applicatif métier",
            audit_type="recurring",
            access_level="complete",
            client_contact_name="Marie Lefèvre",
            client_contact_email="m.lefevre@acme.fr",
            intervention_window="Lun-Ven 09h-18h",
        )
        audit_b = _ensure_audit(
            db,
            owner_id=admin.id,
            entreprise_id=ent_b.id,
            nom_projet="Audit initial Beta Services",
            status=AuditStatus.NOUVEAU,
            date_debut=_utcnow(),
            objectifs="État des lieux sécurité pour PME en croissance",
            audit_type="initial",
            access_level="partial",
            client_contact_name="Sophie Martin",
            client_contact_email="s.martin@beta-services.fr",
        )
        audit_a_prev = _ensure_audit(
            db,
            owner_id=admin.id,
            entreprise_id=ent_a.id,
            nom_projet="Audit annuel Acme 2025",
            status=AuditStatus.TERMINE,
            date_debut=_utcnow() - timedelta(days=400),
            date_fin=_utcnow() - timedelta(days=350),
            objectifs="Audit ISO 27001 — exercice précédent",
            audit_type="recurring",
            access_level="complete",
            client_contact_name="Marie Lefèvre",
            client_contact_email="m.lefevre@acme.fr",
        )
        audit_b_old = _ensure_audit(
            db,
            owner_id=admin.id,
            entreprise_id=ent_b.id,
            nom_projet="Pré-audit Beta 2024",
            status=AuditStatus.ARCHIVE,
            date_debut=_utcnow() - timedelta(days=600),
            date_fin=_utcnow() - timedelta(days=580),
            objectifs="Première prise de contact, archivé",
            audit_type="initial",
            access_level="partial",
        )
        audit_c = _ensure_audit(
            db,
            owner_id=admin.id,
            entreprise_id=ent_c.id,
            nom_projet="Audit HDS Gamma 2026",
            status=AuditStatus.EN_COURS,
            date_debut=_utcnow() - timedelta(days=5),
            date_fin=_utcnow() + timedelta(days=40),
            objectifs="Préparation à la recertification HDS",
            scope_covered="Hyperviseurs, NAS, serveurs applicatifs, vidéosurveillance",
            scope_excluded="Postes utilisateurs",
            audit_type="recurring",
            access_level="complete",
            client_contact_name="Claire Rousseau",
            client_contact_email="rssi@gamma-health.fr",
            intervention_window="Lun-Ven 08h-19h, hors créneaux maintenance",
        )
        audit_d = _ensure_audit(
            db,
            owner_id=admin.id,
            entreprise_id=ent_d.id,
            nom_projet="Audit RGS Delta",
            status=AuditStatus.NOUVEAU,
            date_debut=_utcnow() + timedelta(days=15),
            objectifs="Évaluation RGS niveau 2 sur l'infrastructure mairie",
            audit_type="initial",
            access_level="partial",
            client_contact_name="Antoine Moreau",
            client_contact_email="dsi@delta-mairie.fr",
        )

        # ─── Campagnes & Assessments ─────────────────────────────────
        fw_by_engine = {f.engine: f for f in frameworks if f.engine}
        default_fw = frameworks[0]
        nmap_fw = fw_by_engine.get("nmap") or default_fw

        campaign_a = _ensure_campaign(
            db,
            audit_id=audit_a.id,
            name="Campagne infra centrale Q2 2026",
            description="Évaluation des équipements critiques du siège",
            status=CampaignStatus.IN_PROGRESS,
            started_at=_utcnow() - timedelta(days=8),
        )

        total_results = 0
        total_findings = 0
        for eq in (eq_a_fw, eq_a_sw, eq_a_srv):
            assessment = _ensure_assessment(db, campaign_a.id, eq.id, nmap_fw.id)
            results = _seed_control_results(db, assessment, nmap_fw)
            total_results += len(results)
            total_findings += _seed_findings(db, assessment, results)

        _ensure_campaign(
            db,
            audit_id=audit_b.id,
            name="Pré-audit Beta",
            description="Première passe d'évaluation",
            status=CampaignStatus.DRAFT,
        )

        # Campagne TERMINÉE sur l'audit précédent Acme
        campaign_a_prev = _ensure_campaign(
            db,
            audit_id=audit_a_prev.id,
            name="Campagne ISO 27001 — 2025",
            description="Bilan complet de l'exercice 2025",
            status=CampaignStatus.COMPLETED,
            started_at=_utcnow() - timedelta(days=400),
            completed_at=_utcnow() - timedelta(days=355),
        )
        for eq in (eq_a_fw, eq_a_srv):
            assessment = _ensure_assessment(db, campaign_a_prev.id, eq.id, nmap_fw.id)
            results = _seed_control_results(db, assessment, nmap_fw)
            total_results += len(results)
            total_findings += _seed_findings(db, assessment, results)

        # Campagne ARCHIVÉE
        _ensure_campaign(
            db,
            audit_id=audit_b_old.id,
            name="Pré-audit Beta — 2024 (archivé)",
            description="Premiers entretiens, conservé pour historique",
            status=CampaignStatus.ARCHIVED,
            started_at=_utcnow() - timedelta(days=600),
            completed_at=_utcnow() - timedelta(days=580),
        )

        # Campagne EN REVIEW pour Gamma (HDS)
        campaign_c = _ensure_campaign(
            db,
            audit_id=audit_c.id,
            name="Campagne HDS — production",
            description="Évaluation des équipements de production HDS",
            status=CampaignStatus.REVIEW,
            started_at=_utcnow() - timedelta(days=4),
        )
        for eq in (eq_c_hv, eq_c_nas, eq_c_srv, eq_c_cam):
            assessment = _ensure_assessment(db, campaign_c.id, eq.id, nmap_fw.id)
            results = _seed_control_results(db, assessment, nmap_fw)
            total_results += len(results)
            total_findings += _seed_findings(db, assessment, results)

        # Campagne DRAFT pour Delta
        _ensure_campaign(
            db,
            audit_id=audit_d.id,
            name="Pré-cadrage RGS",
            description="Définition du périmètre",
            status=CampaignStatus.DRAFT,
        )

        # ─── Agents + tâches ─────────────────────────────────────────
        agent_a = _ensure_agent(
            db,
            owner_id=admin.id,
            name="Demo-Agent-Paris",
            agent_uuid="demo-agent-acme-paris-0001",
        )
        agent_b = _ensure_agent(
            db,
            owner_id=admin.id,
            name="Demo-Agent-Bordeaux",
            agent_uuid="demo-agent-gamma-bdx-0002",
            status="offline",
            last_seen=_utcnow() - timedelta(days=2),
            os_info="Ubuntu 22.04 LTS",
            agent_version="0.9.3",
            last_ip="10.20.10.99",
        )

        now = _utcnow()
        n_tasks_a = _seed_agent_tasks(
            db, agent_a, owner_id=admin.id, audit_id=audit_a.id, presets=_agent_a_presets(now)
        )
        n_tasks_b = _seed_agent_tasks(
            db, agent_b, owner_id=admin.id, audit_id=audit_c.id, presets=_agent_b_presets(now)
        )

        db.commit()

        print("[OK] Seed terminé")
        print(f"  • Entreprises    : 4 ({ent_a.nom}, {ent_b.nom}, {ent_c.nom}, {ent_d.nom})")
        print("  • Sites          : 5")
        print("  • Équipements    : 15")
        print("  • Audits         : 6 (2 EN_COURS, 2 NOUVEAU, 1 TERMINE, 1 ARCHIVE)")
        print("  • Campagnes      : 6 (1 IN_PROGRESS, 2 DRAFT, 1 COMPLETED, 1 ARCHIVED, 1 REVIEW)")
        print(f"  • ControlResults : {total_results}")
        print(f"  • Findings       : {total_findings}")
        print(f"  • Agents         : 2 ({agent_a.name} active, {agent_b.name} offline)")
        print(f"  • AgentTasks     : {n_tasks_a + n_tasks_b}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

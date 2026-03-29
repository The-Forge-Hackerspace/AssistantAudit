"""
Factory functions for creating test data with realistic defaults.
Provides utilities for building complex test scenarios quickly.
"""

import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    User,
    Entreprise,
    Contact,
    Site,
    Equipement,
    EquipementReseau,
    EquipementServeur,
    EquipementFirewall,
    Framework,
    FrameworkCategory,
    Control,
    ControlSeverity,
    CheckType,
    AssessmentCampaign,
    Assessment,
    ControlResult,
    ComplianceStatus,
    CampaignStatus,
    Audit,
    AuditStatus,
)


class UserFactory:
    """Factory for creating User objects"""
    
    @staticmethod
    def create(
        db: Session,
        username: str = "testuser",
        email: str = "test@example.com",
        password: str = "TestPass123!",
        full_name: str = "Test User",
        role: str = "auditeur",
        is_active: bool = True,
        **kwargs
    ) -> User:
        """Create a user with defaults"""
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=is_active,
            **kwargs
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def create_batch(db: Session, count: int = 5) -> list[User]:
        """Create multiple users"""
        users = []
        for i in range(count):
            user = UserFactory.create(
                db,
                username=f"user_{i}",
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                role=["admin", "auditeur", "lecteur"][i % 3],
            )
            users.append(user)
        return users


class EntrepriseFactory:
    """Factory for creating Entreprise objects"""
    
    @staticmethod
    def create(
        db: Session,
        nom: str = "Test Company",
        secteur_activite: str = "IT",
        adresse: str = "123 Main Street",
        siret: str = None,
        **kwargs
    ) -> Entreprise:
        """Create an entreprise with defaults"""
        if not siret:
            siret = f"123456789{str(uuid.uuid4())[:5]}"
        ent = Entreprise(
            nom=nom,
            secteur_activite=secteur_activite,
            adresse=adresse,
            siret=siret,
            **kwargs
        )
        db.add(ent)
        db.commit()
        db.refresh(ent)
        return ent
    
    @staticmethod
    def create_batch(db: Session, count: int = 3) -> list[Entreprise]:
        """Create multiple entreprises"""
        entreprises = []
        for i in range(count):
            ent = EntrepriseFactory.create(
                db,
                nom=f"Company {i+1} {str(uuid.uuid4())[:8]}",
                secteur_activite=["IT", "Finance", "Healthcare", "Retail"][i % 4],
            )
            entreprises.append(ent)
        return entreprises


class ContactFactory:
    """Factory for creating Contact objects"""
    
    @staticmethod
    def create(
        db: Session,
        entreprise_id: int,
        nom: str = "John Doe",
        role: str = "IT Manager",
        email: str = "john@example.com",
        telephone: str = "+33123456789",
        **kwargs
    ) -> Contact:
        """Create a contact with defaults"""
        contact = Contact(
            entreprise_id=entreprise_id,
            nom=nom,
            role=role,
            email=email,
            telephone=telephone,
            **kwargs
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact


class SiteFactory:
    """Factory for creating Site objects"""
    
    @staticmethod
    def create(
        db: Session,
        nom: str = "Test Site",
        entreprise_id: int = None,
        adresse: str = "456 Site Avenue",
        description: str = "Test site",
        **kwargs
    ) -> Site:
        """Create a site with defaults"""
        site = Site(
            nom=nom,
            entreprise_id=entreprise_id,
            adresse=adresse,
            description=description,
            **kwargs
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return site
    
    @staticmethod
    def create_batch(db: Session, entreprise_id: int, count: int = 3) -> list[Site]:
        """Create multiple sites for an entreprise"""
        sites = []
        for i in range(count):
            site = SiteFactory.create(
                db,
                nom=f"Site {i+1}",
                entreprise_id=entreprise_id,
                adresse=f"{100+i} Site Avenue",
            )
            sites.append(site)
        return sites


class EquipementFactory:
    """Factory for creating Equipement objects"""
    
    @staticmethod
    def create(
        db: Session,
        site_id: int = None,
        type_equipement: str = "serveur",
        ip_address: str = None,
        hostname: str = "test-host",
        mac_address: str = None,
        **kwargs
    ) -> Equipement:
        """Create an equipement with defaults"""
        if not ip_address:
            # Generate unique IP in 10.0.0.0/8 range
            import random
            ip_address = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        if not mac_address:
            import random
            mac_address = ":".join([f"{random.randint(0,255):02x}" for _ in range(6)])
        
        eq = Equipement(
            site_id=site_id,
            type_equipement=type_equipement,
            ip_address=ip_address,
            hostname=hostname,
            mac_address=mac_address,
            **kwargs
        )
        db.add(eq)
        db.commit()
        db.refresh(eq)
        return eq
    
    @staticmethod
    def create_batch(db: Session, site_id: int, count: int = 5) -> list[Equipement]:
        """Create multiple equipements"""
        equipements = []
        types = ["serveur", "firewall", "switch", "routeur"]
        for i in range(count):
            eq = EquipementFactory.create(
                db,
                site_id=site_id,
                type_equipement=types[i % len(types)],
                hostname=f"host-{i+1}",
            )
            equipements.append(eq)
        return equipements





# Skip EquipementReseauFactory as it's specific to network equipment


class AuditFactory:
    """Factory for creating Audit objects"""
    
    @staticmethod
    def create(
        db: Session,
        nom_projet: str = "Test Audit",
        entreprise_id: int = None,
        status: str = "NOUVEAU",
        **kwargs
    ) -> Audit:
        """Create an audit with defaults"""
        from app.models.audit import AuditStatus
        
        audit = Audit(
            nom_projet=nom_projet,
            entreprise_id=entreprise_id,
            status=AuditStatus(status),
            **kwargs
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit


class FrameworkFactory:
    """Factory for creating Framework objects"""
    
    @staticmethod
    def create(
        db: Session,
        ref_id: str = "FW_TEST",
        name: str = "Test Framework",
        description: str = "Test framework",
        version: str = "1.0",
        **kwargs
    ) -> Framework:
        """Create a framework with defaults"""
        fw = Framework(
            ref_id=ref_id,
            name=name,
            description=description,
            version=version,
            **kwargs
        )
        db.add(fw)
        db.commit()
        db.refresh(fw)
        return fw


class FrameworkCategoryFactory:
    """Factory for creating FrameworkCategory objects"""
    
    @staticmethod
    def create(
        db: Session,
        framework_id: int,
        name: str = "Test Category",
        description: str = "Test category",
        order: int = 1,
        **kwargs
    ) -> FrameworkCategory:
        """Create a framework category"""
        cat = FrameworkCategory(
            framework_id=framework_id,
            name=name,
            description=description,
            order=order,
            **kwargs
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat


class ControlFactory:
    """Factory for creating Control objects"""
    
    @staticmethod
    def create(
        db: Session,
        category_id: int,
        ref_id: str = "CTL_001",
        title: str = "Test Control",
        description: str = "Test control",
        severity: str = "medium",
        check_type: str = "manual",
        **kwargs
    ) -> Control:
        """Create a control with defaults"""
        from app.models.framework import ControlSeverity, CheckType
        
        control = Control(
            category_id=category_id,
            ref_id=ref_id,
            title=title,
            description=description,
            severity=ControlSeverity(severity),
            check_type=CheckType(check_type),
            **kwargs
        )
        db.add(control)
        db.commit()
        db.refresh(control)
        return control
    
    @staticmethod
    def create_batch(
        db: Session,
        category_id: int,
        count: int = 5
    ) -> list[Control]:
        """Create multiple controls"""
        from app.models.framework import ControlSeverity
        
        controls = []
        severities = ["low", "medium", "high", "critical"]
        for i in range(count):
            control = ControlFactory.create(
                db,
                category_id=category_id,
                ref_id=f"CTL_{i:03d}",
                title=f"Control {i+1}",
                severity=severities[i % len(severities)],
            )
            controls.append(control)
        return controls


class AssessmentCampaignFactory:
    """Factory for creating AssessmentCampaign objects"""
    
    @staticmethod
    def create(
        db: Session,
        audit_id: int,
        name: str = "Test Campaign",
        description: str = "Test campaign",
        status: str = "draft",
        **kwargs
    ) -> AssessmentCampaign:
        """Create an assessment campaign"""
        campaign = AssessmentCampaign(
            audit_id=audit_id,
            name=name,
            description=description,
            status=status,
            **kwargs
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign


class AssessmentFactory:
    """Factory for creating Assessment objects"""
    
    @staticmethod
    def create(
        db: Session,
        campaign_id: int,
        equipement_id: int,
        framework_id: int,
        notes: str = "",
        **kwargs
    ) -> Assessment:
        """Create an assessment"""
        assessment = Assessment(
            campaign_id=campaign_id,
            equipement_id=equipement_id,
            framework_id=framework_id,
            notes=notes,
            **kwargs
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment


class ControlResultFactory:
    """Factory for creating ControlResult objects"""
    
    @staticmethod
    def create(
        db: Session,
        assessment_id: int,
        control_id: int,
        status: str = "compliant",
        comment: str = "Test notes",
        **kwargs
    ) -> ControlResult:
        """Create a control result"""
        from app.models.assessment import ComplianceStatus
        
        result = ControlResult(
            assessment_id=assessment_id,
            control_id=control_id,
            status=ComplianceStatus(status),
            comment=comment,
            **kwargs
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result
    
    @staticmethod
    def create_batch(
        db: Session,
        assessment_id: int,
        control_ids: list[int],
    ) -> list[ControlResult]:
        """Create multiple control results"""
        from app.models.assessment import ComplianceStatus
        
        statuses = ["compliant", "non_compliant", "partially_compliant", "not_applicable"]
        results = []
        for i, control_id in enumerate(control_ids):
            result = ControlResultFactory.create(
                db,
                assessment_id=assessment_id,
                control_id=control_id,
                status=statuses[i % len(statuses)],
            )
            results.append(result)
        return results


# ────────────────────────────────────────────────────────────────────────
# Convenience test data builders
# ────────────────────────────────────────────────────────────────────────


def create_full_assessment_scenario(db: Session):
    """Create a complete assessment scenario with all related objects"""
    # Create users with unique emails
    unique_id = str(uuid.uuid4())[:8]
    admin = UserFactory.create(db, username=f"admin_{unique_id}", email=f"admin_{unique_id}@test.local", role="admin")
    auditeur = UserFactory.create(db, username=f"auditeur_{unique_id}", email=f"auditeur_{unique_id}@test.local", role="auditeur")
    
    # Create entreprise and site
    ent = EntrepriseFactory.create(db, nom=f"Test Corp {unique_id}")
    site = SiteFactory.create(db, nom="Main Site", entreprise_id=ent.id)
    
    # Create equipements (use keyword args that match model fields)
    eq1 = EquipementFactory.create(db, site_id=site.id, type_equipement="serveur", hostname="server-1")
    eq2 = EquipementFactory.create(db, site_id=site.id, type_equipement="firewall", hostname="fw-1")
    
    # Create framework with categories and controls
    fw = FrameworkFactory.create(db, ref_id=f"ISO27001_{unique_id}", name="ISO 27001")
    cat = FrameworkCategoryFactory.create(db, framework_id=fw.id, name="Access Control")
    controls = ControlFactory.create_batch(db, cat.id, count=5)
    
    # Create audit and campaign
    audit = AuditFactory.create(db, nom_projet="Q1 2026 Audit", entreprise_id=ent.id)
    campaign = AssessmentCampaignFactory.create(db, audit_id=audit.id)
    
    # Create assessments
    assess1 = AssessmentFactory.create(db, campaign_id=campaign.id, equipement_id=eq1.id, framework_id=fw.id)
    
    # Create control results
    control_ids = [c.id for c in controls]
    results = ControlResultFactory.create_batch(db, assess1.id, control_ids)
    
    return {
        "admin": admin,
        "auditeur": auditeur,
        "entreprise": ent,
        "site": site,
        "equipements": [eq1, eq2],
        "framework": fw,
        "category": cat,
        "controls": controls,
        "audit": audit,
        "campaign": campaign,
        "assessment": assess1,
        "results": results,
    }

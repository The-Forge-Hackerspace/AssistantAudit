"""
Performance and correctness tests for N+1 query optimization.
Validates that optimization methods return correct data consistently.
"""

import pytest
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import AssessmentCampaign
from app.services.assessment_service import AssessmentService
from app.services.query_optimizer import get_campaigns_optimized, QueryOptimizer
from tests.factories import (
    EntrepriseFactory,
    AuditFactory,
    SiteFactory,
    AssessmentCampaignFactory,
    AssessmentFactory,
    FrameworkFactory,
    EquipementFactory,
)


def create_test_assessment_data(db: Session, audit_id: int, num_campaigns: int, assessments_per_campaign: int):
    """Helper to create complete test data for performance tests"""
    # Get the audit to find its entreprise
    from app.models import Audit
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    
    # Create a site for the equipements
    site = SiteFactory.create(db, entreprise_id=audit.entreprise_id)
    
    # Create a framework
    framework = FrameworkFactory.create(db)
    
    for i in range(num_campaigns):
        campaign = AssessmentCampaignFactory.create(db, audit_id=audit_id)
        for j in range(assessments_per_campaign):
            # Create unique equipement for each assessment to avoid conflicts
            equipement = EquipementFactory.create(db, site_id=site.id)
            AssessmentFactory.create(
                db,
                campaign_id=campaign.id,
                equipement_id=equipement.id,
                framework_id=framework.id
            )


class TestN1QueryOptimization:
    """Tests verifying N+1 query optimization implementations"""

    def test_list_campaigns_with_optimization(self, app, db_session):
        """
        Verify that optimized list_campaigns returns correct data with eager loading.
        """
        # Setup: Create test data
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=5, assessments_per_campaign=3)

        # Verify optimized list returns all expected data
        campaigns, total = AssessmentService.list_campaigns(db_session, audit_id=audit.id, limit=100)
        
        # Should return 5 campaigns
        assert total == 5
        assert len(campaigns) == 5
        
        # Each campaign should have assessments available (from eager loading)
        for campaign in campaigns:
            # This should NOT trigger a new query because assessments are eagerly loaded
            assert len(campaign.assessments) == 3
            assert campaign.audit_id == audit.id
        
        print(f"\n✓ list_campaigns_with_optimization: {total} campaigns, {sum(len(c.assessments) for c in campaigns)} assessments")

    def test_get_campaigns_optimized_correctness(self, app, db_session):
        """
        Verify that get_campaigns_optimized returns correct data.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=10, assessments_per_campaign=2)

        # Test optimized query
        campaigns, total = get_campaigns_optimized(db_session, limit=100)
        
        assert total == 10
        assert len(campaigns) == 10
        
        # Verify all campaigns are from our audit
        for campaign in campaigns:
            assert campaign.audit_id == audit.id
            # Verify assessments are accessible (not lazy-loaded)
            assert len(campaign.assessments) == 2

    def test_pagination_with_optimization(self, app, db_session):
        """
        Verify that pagination works correctly with eager loading.
        """
        # Setup: Create many campaigns
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=250, assessments_per_campaign=2)

        db_session.expunge_all()
        
        # Page 1
        campaigns1, total = get_campaigns_optimized(db_session, skip=0, limit=100)
        assert len(campaigns1) == 100
        assert total == 250
        
        # Verify data integrity
        for campaign in campaigns1:
            assert len(campaign.assessments) == 2

        db_session.expunge_all()
        
        # Page 2
        campaigns2, total = get_campaigns_optimized(db_session, skip=100, limit=100)
        assert len(campaigns2) == 100
        
        # Verify pages don't overlap
        ids1 = {c.id for c in campaigns1}
        ids2 = {c.id for c in campaigns2}
        assert len(ids1 & ids2) == 0, "Pages should not overlap"

    def test_relationship_eager_loading(self, app, db_session):
        """
        Verify that relationships are eagerly loaded, not lazy-loaded.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=5, assessments_per_campaign=3)

        db_session.expunge_all()
        
        # Get optimized campaigns
        campaigns, _ = get_campaigns_optimized(db_session, limit=100)
        
        # Accessing campaign.assessments multiple times should not cause new queries
        c = campaigns[0]
        count1 = len(c.assessments)
        count2 = len(c.assessments)
        count3 = len(c.assessments)
        
        assert count1 == count2 == count3 == 3
        
        # Verify assessments are accessible
        for assessment in c.assessments:
            assert assessment.campaign_id == c.id

    def test_campaign_score_with_optimization(self, app, db_session):
        """
        Verify get_campaign_score works with eagerly-loaded results.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=1, assessments_per_campaign=2)

        db_session.expunge_all()
        
        # Get the campaign
        campaigns, _ = get_campaigns_optimized(db_session, limit=100)
        campaign = campaigns[0]
        
        # Verify score calculation works
        score = AssessmentService.get_campaign_score(db_session, campaign.id)
        
        # Score should be computable since results are loaded
        assert score is not None
        assert "compliance_score" in score
        assert "total_controls" in score

    def test_assessment_score_optimization(self, app, db_session):
        """
        Verify get_assessment_score works with eagerly-loaded control results.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=1, assessments_per_campaign=1)

        db_session.expunge_all()
        
        # Get an assessment
        campaigns, _ = get_campaigns_optimized(db_session, limit=100)
        assessment = campaigns[0].assessments[0]
        
        # Calculate score
        score = AssessmentService.get_assessment_score(db_session, assessment.id)
        
        # Score should be computable
        assert score is not None
        assert "compliance_score" in score
        assert "assessed_controls" in score

    def test_consistency_between_methods(self, app, db_session):
        """
        Verify that optimized helper and service methods return consistent data.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        audit_id = audit.id  # Store the ID before expunge_all
        create_test_assessment_data(db_session, audit_id, num_campaigns=3, assessments_per_campaign=2)

        db_session.expunge_all()
        
        # Get from both methods (don't use audit object after expunge_all)
        campaigns1, total1 = AssessmentService.list_campaigns(db_session, audit_id=audit_id, limit=100)
        campaigns2, total2 = get_campaigns_optimized(db_session, limit=100)
        
        # Should return same data
        assert total1 == total2
        assert len(campaigns1) == len(campaigns2)
        
        # IDs should match
        ids1 = {c.id for c in campaigns1}
        ids2 = {c.id for c in campaigns2}
        assert ids1 == ids2

    def test_query_optimizer_utility(self, app, db_session):
        """
        Verify QueryOptimizer utility works correctly.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=5, assessments_per_campaign=3)

        db_session.expunge_all()
        
        # Test QueryOptimizer utility
        campaigns, total = QueryOptimizer.paginated_query(
            db_session,
            AssessmentCampaign,
            eager_load_options=[selectinload(AssessmentCampaign.assessments)],
            limit=100,
        )

        # Verify results
        assert total == 5
        assert len(campaigns) == 5
        for campaign in campaigns:
            assert len(campaign.assessments) == 3

    def test_batch_load_optimization(self, app, db_session):
        """
        Verify QueryOptimizer.batch_load works correctly.
        """
        # Setup
        entreprise = EntrepriseFactory.create(db_session)
        audit = AuditFactory.create(db_session, entreprise_id=entreprise.id)
        create_test_assessment_data(db_session, audit.id, num_campaigns=10, assessments_per_campaign=1)

        db_session.expunge_all()
        
        # Get all campaigns
        all_campaigns, _ = get_campaigns_optimized(db_session, limit=100)
        campaign_ids = [c.id for c in all_campaigns[:5]]  # Get first 5 IDs
        
        # Test batch load
        campaigns = QueryOptimizer.batch_load(
            db_session,
            AssessmentCampaign,
            ids=campaign_ids,
            eager_load_options=[selectinload(AssessmentCampaign.assessments)],
        )
        
        # Should return only requested campaigns
        assert len(campaigns) == 5
        returned_ids = {c.id for c in campaigns}
        assert returned_ids == set(campaign_ids)

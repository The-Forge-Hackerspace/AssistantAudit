"""
N+1 Query Optimization utilities for SQLAlchemy.
Provides helper functions to eagerly load relationships efficiently.
"""

from typing import Any, List, Type, TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

ModelType = TypeVar("ModelType")


# ────────────────────────────────────────────────────────────────────────
# Query Optimization Helpers
# ────────────────────────────────────────────────────────────────────────


class QueryOptimizer:
    """Helper class for optimizing SQLAlchemy queries"""

    @staticmethod
    def paginated_query(
        db: Session,
        model: Type[ModelType],
        skip: int = 0,
        limit: int = 100,
        eager_load_options: List[Any] = None,
    ) -> tuple[List[ModelType], int]:
        """
        Execute a paginated query with eager loading.

        Args:
            db: Database session
            model: SQLAlchemy model class
            skip: Number of records to skip
            limit: Maximum records to return
            eager_load_options: List of selectinload() options

        Returns:
            Tuple of (results, total_count)
        """
        query = db.query(model)

        # Apply eager loading
        if eager_load_options:
            for option in eager_load_options:
                query = query.options(option)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        results = query.offset(skip).limit(limit).all()

        return results, total

    @staticmethod
    def optimized_get(
        db: Session,
        model: Type[ModelType],
        id: int,
        eager_load_options: List[Any] = None,
    ) -> ModelType | None:
        """
        Get a single record with eager loading.

        Args:
            db: Database session
            model: SQLAlchemy model class
            id: Record ID
            eager_load_options: List of selectinload() options

        Returns:
            Model instance or None
        """
        query = db.query(model)

        # Apply eager loading
        if eager_load_options:
            for option in eager_load_options:
                query = query.options(option)

        return query.filter(model.id == id).first()

    @staticmethod
    def batch_load(
        db: Session,
        model: Type[ModelType],
        ids: List[int],
        eager_load_options: List[Any] = None,
    ) -> List[ModelType]:
        """
        Load multiple records efficiently.

        Args:
            db: Database session
            model: SQLAlchemy model class
            ids: List of record IDs
            eager_load_options: List of selectinload() options

        Returns:
            List of model instances
        """
        if not ids:
            return []

        query = db.query(model)

        # Apply eager loading
        if eager_load_options:
            for option in eager_load_options:
                query = query.options(option)

        return query.filter(model.id.in_(ids)).all()


# ────────────────────────────────────────────────────────────────────────
# Pre-configured Query Builders for Top 5 Endpoints
# ────────────────────────────────────────────────────────────────────────


def get_campaigns_optimized(
    db: Session, skip: int = 0, limit: int = 100
) -> tuple[List["AssessmentCampaign"], int]:
    """
    Optimized query for listing assessment campaigns.
    Avoids N+1 by eager-loading assessments and audit.
    """
    from app.models import AssessmentCampaign

    query = db.query(AssessmentCampaign).options(
        selectinload(AssessmentCampaign.assessments),
        selectinload(AssessmentCampaign.audit),
    )

    total = query.count()
    results = query.offset(skip).limit(limit).all()
    return results, total


def get_audit_optimized(db: Session, audit_id: int) -> "Audit | None":
    """
    Optimized query for getting a single audit with all related data.
    Eagerly loads campaigns, sites, and their nested relationships.
    """
    from app.models import Audit, Assessment, Site

    result = (
        db.query(Audit)
        .options(
            selectinload(Audit.entreprise),
            selectinload(Audit.campaigns).selectinload(AssessmentCampaign.assessments),
            selectinload(Audit.sites).selectinload(Site.equipements),
        )
        .filter(Audit.id == audit_id)
        .first()
    )
    return result


def get_audits_list_optimized(
    db: Session, skip: int = 0, limit: int = 100
) -> tuple[List["Audit"], int]:
    """
    Optimized query for listing audits with pagination.
    Eagerly loads entreprise and campaigns.
    """
    from app.models import Audit

    query = db.query(Audit).options(
        selectinload(Audit.entreprise),
        selectinload(Audit.campaigns),
    )

    total = query.count()
    results = query.offset(skip).limit(limit).all()
    return results, total


def get_sites_optimized(
    db: Session, entreprise_id: int = None, skip: int = 0, limit: int = 100
) -> tuple[List["Site"], int]:
    """
    Optimized query for listing sites with pagination.
    Eagerly loads equipements and scans.
    """
    from app.models import Site

    query = db.query(Site).options(
        selectinload(Site.equipements),
        selectinload(Site.scans),
    )

    if entreprise_id:
        query = query.filter(Site.entreprise_id == entreprise_id)

    total = query.count()
    results = query.offset(skip).limit(limit).all()
    return results, total


def get_site_optimized(db: Session, site_id: int) -> "Site | None":
    """
    Optimized query for getting a single site with nested data.
    Eagerly loads equipements and their assessments.
    """
    from app.models import Site, Equipement

    result = (
        db.query(Site)
        .options(
            selectinload(Site.entreprise),
            selectinload(Site.equipements).selectinload(Equipement.assessments),
            selectinload(Site.scans),
        )
        .filter(Site.id == site_id)
        .first()
    )
    return result


# ────────────────────────────────────────────────────────────────────────
# Query Analysis & Debugging
# ────────────────────────────────────────────────────────────────────────


class QueryDebugger:
    """Helper for analyzing and debugging query performance"""

    def __init__(self, db: Session):
        self.db = db
        self.query_count = 0
        self.last_queries = []

    def count_queries(self, func_to_profile):
        """Decorator to count queries executed in a function"""

        def wrapper(*args, **kwargs):
            # This would require sqlalchemy event listeners
            # For now, just a placeholder
            return func_to_profile(*args, **kwargs)

        return wrapper

    @staticmethod
    def analyze_relationship_loading(model_instance, relationship_name: str) -> str:
        """
        Analyze whether a relationship is eagerly or lazily loaded.

        Args:
            model_instance: Instance of SQLAlchemy model
            relationship_name: Name of relationship attribute

        Returns:
            String describing the loading state
        """
        from sqlalchemy.orm import attributes

        # Check if attribute is loaded
        state = attributes.instance_state(model_instance)
        attr = getattr(model_instance.__class__, relationship_name)

        if attr.key in state.committed_state:
            return "EAGER_LOADED"
        elif attr.key in state.dict:
            try:
                state.dict[attr.key]
                return "LAZY_LOADED"
            except Exception:
                return "UNINITIALIZED"
        else:
            return "NOT_LOADED_YET"

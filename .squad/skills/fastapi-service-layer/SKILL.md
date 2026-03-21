# FastAPI Service Layer Pattern

## Purpose
Stateless service layer pattern for FastAPI applications using SQLAlchemy ORM.

## Pattern

### Service Class Structure
```python
from sqlalchemy.orm import Session
from typing import Optional

class EntityService:
    """Business logic for Entity operations"""
    
    @staticmethod
    def create_entity(db: Session, name: str, data: dict) -> Entity:
        """Create new entity"""
        entity = Entity(name=name, **data)
        db.add(entity)
        db.commit()
        db.refresh(entity)
        logger.info(f"Entity created: {entity.id}")
        return entity
    
    @staticmethod
    def get_entity(db: Session, entity_id: int) -> Optional[Entity]:
        """Get entity by ID"""
        return db.get(Entity, entity_id)
    
    @staticmethod
    def list_entities(
        db: Session, offset: int = 0, limit: int = 20
    ) -> tuple[list[Entity], int]:
        """List entities with pagination"""
        query = db.query(Entity)
        total = query.count()
        entities = query.offset(offset).limit(limit).all()
        return entities, total
    
    @staticmethod
    def update_entity(db: Session, entity_id: int, data: dict) -> Entity:
        """Update entity"""
        entity = db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        for key, value in data.items():
            setattr(entity, key, value)
        db.commit()
        db.refresh(entity)
        return entity
    
    @staticmethod
    def delete_entity(db: Session, entity_id: int) -> None:
        """Delete entity"""
        entity = db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        db.delete(entity)
        db.commit()
```

### API Route Integration
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.entity import EntityCreate, EntityRead
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()

@router.get("", response_model=PaginatedResponse[EntityRead])
async def list_entities(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List entities"""
    entities, total = EntityService.list_entities(
        db, offset=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse(
        items=entities,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )

@router.post("", response_model=EntityRead, status_code=status.HTTP_201_CREATED)
async def create_entity(
    body: EntityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Create entity"""
    entity = EntityService.create_entity(db, name=body.name, data=body.model_dump())
    return entity

@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get entity details"""
    entity = EntityService.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity
```

## Benefits
- **Separation of concerns**: Controllers delegate to services, services interact with DB
- **Reusability**: Services can be called from multiple routes or background tasks
- **Testability**: Services can be tested independently of FastAPI routes
- **Maintainability**: Business logic centralized, easier to refactor
- **Type safety**: Full type hints enforced by mypy

## Anti-Patterns to Avoid
- ❌ DB logic in API routes (tight coupling)
- ❌ Instance methods (services should be stateless)
- ❌ Services calling other services directly (use dependency injection)
- ❌ Services returning HTTP responses (let routes handle HTTP layer)

## Related Patterns
- Repository pattern (implicit via SQLAlchemy ORM)
- Dependency injection (FastAPI `Depends()`)
- Unit of Work (SQLAlchemy session)

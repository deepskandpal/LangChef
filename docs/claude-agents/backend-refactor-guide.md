# Backend Refactor Guide for Claude Code

This guide provides specific instructions for the `backend-fastapi-refactorer` agent when working with the LangChef backend.

## Architecture Principles

### Layer Enforcement
Maintain strict layering:
```
routers/ (HTTP handling) → services/ (business logic) → repositories/ (data access) → models/ (ORM)
```

### Key Patterns to Follow

#### 1. Route Structure
```python
# routes/example.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.example_service import ExampleService
from ..schemas.example import ExampleCreate, ExampleResponse

router = APIRouter(prefix="/api/example", tags=["example"])

@router.post("/", response_model=ExampleResponse)
async def create_example(
    example: ExampleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ExampleService(db)
    return await service.create_example(example, current_user.id)
```

#### 2. Service Layer
```python
# services/example_service.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.example import Example
from ..schemas.example import ExampleCreate, ExampleUpdate
from ..core.logging import get_logger

logger = get_logger(__name__)

class ExampleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_example(self, example_data: ExampleCreate, user_id: str) -> Example:
        try:
            db_example = Example(**example_data.dict(), user_id=user_id)
            self.db.add(db_example)
            await self.db.commit()
            await self.db.refresh(db_example)
            logger.info(f"Created example {db_example.id} for user {user_id}")
            return db_example
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create example: {str(e)}")
            raise
```

#### 3. Model Structure
```python
# models/example.py
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="examples")
```

## Refactoring Checklist

### ✅ Code Quality
- [ ] All functions have proper type hints
- [ ] Async/await used consistently
- [ ] Error handling with proper logging
- [ ] No print() statements (use logger)
- [ ] Proper exception handling
- [ ] SQLAlchemy best practices

### ✅ Architecture
- [ ] Routes only handle HTTP concerns
- [ ] Business logic in service layer
- [ ] Database operations in repositories/services
- [ ] Proper dependency injection
- [ ] Clear separation of concerns

### ✅ Configuration
- [ ] Environment variables in config.py
- [ ] No hardcoded values
- [ ] Proper validation of settings
- [ ] Secure defaults

### ✅ Database
- [ ] Async SQLAlchemy patterns
- [ ] Proper transaction handling
- [ ] Connection pooling configured
- [ ] Migrations follow best practices

## Common Refactoring Patterns

### 1. Route Simplification
**Before:**
```python
@router.post("/prompts/")
async def create_prompt(prompt: PromptCreate, db: Session = Depends(get_db)):
    # Business logic mixed with HTTP handling
    db_prompt = Prompt(**prompt.dict())
    db.add(db_prompt)
    db.commit()
    return db_prompt
```

**After:**
```python
@router.post("/prompts/", response_model=PromptResponse)
async def create_prompt(
    prompt: PromptCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PromptService(db)
    return await service.create_prompt(prompt, current_user.id)
```

### 2. Error Handling Standardization
**Before:**
```python
try:
    # operation
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**After:**
```python
try:
    logger.info("Starting operation")
    # operation
    logger.info("Operation completed successfully")
except ValidationError as e:
    logger.warning(f"Validation error: {str(e)}")
    raise HTTPException(status_code=400, detail="Invalid input data")
except NotFoundError as e:
    logger.warning(f"Resource not found: {str(e)}")
    raise HTTPException(status_code=404, detail="Resource not found")
except Exception as e:
    logger.error(f"Unexpected error in operation: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### 3. Configuration Management
**Before:**
```python
# Scattered configuration
SECRET_KEY = os.getenv("SECRET_KEY", "default-key")
DATABASE_URL = os.getenv("DATABASE_URL")
```

**After:**
```python
# config.py
class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set")
    
    class Config:
        env_file = ".env"
```

## File Organization

```
backend/
├── api/
│   ├── routes/          # HTTP route handlers
│   └── schemas/         # Pydantic schemas
├── services/            # Business logic layer
├── models/              # SQLAlchemy ORM models
├── core/                # Core utilities (logging, etc.)
├── config.py            # Configuration management
├── database.py          # Database setup
└── main.py              # FastAPI app creation
```

## Security Considerations

- Always validate input data with Pydantic schemas
- Use parameterized queries (SQLAlchemy handles this)
- Implement proper authentication on all endpoints
- Sanitize error messages for production
- Use HTTPS in production
- Implement rate limiting
- Validate file uploads thoroughly

## Performance Guidelines

- Use async/await for I/O operations
- Implement proper database connection pooling
- Add database indexes where needed
- Use pagination for large result sets
- Implement caching for frequently accessed data
- Monitor query performance

## Testing Guidelines

- Write unit tests for service layer
- Use pytest-asyncio for async tests
- Mock external dependencies
- Test error conditions
- Use factory patterns for test data
- Implement integration tests for critical paths
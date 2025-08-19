# Backend API Endpoints Security Audit

**Component**: FastAPI Route Handlers & Input Validation  
**Priority**: 🔴 CRITICAL  
**Agent Assignment**: `backend-fastapi-refactorer`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. SQL Injection Vulnerability (CRITICAL - 8.5/10)

**File**: `/backend/api/routes/datasets.py:155, 194, 218, 795`  
**Issue**: Extensive use of raw SQL with dynamic query construction

```python
# VULNERABLE CODE:
query = text(f"""
UPDATE datasets 
SET {", ".join(set_parts)}
WHERE id = :dataset_id
""")

# Another example:
sql_query = """
SELECT id, name, description, type, version, is_active, meta_data, examples, created_at, updated_at 
FROM datasets
WHERE ($1 IS NULL OR name ILIKE $1)
"""
```

**Risk**:
- SQL injection through crafted dataset names or parameters
- Database compromise through malicious queries
- Data exfiltration potential

**Affected Endpoints**:
- `POST /api/datasets/` - Dataset creation
- `PUT /api/datasets/{id}` - Dataset updates  
- `GET /api/datasets/` - Dataset filtering
- `POST /api/datasets/{id}/items/` - Dataset item creation

### 2. Missing Input Validation (HIGH - 7.5/10)

**File**: `/backend/api/routes/datasets.py:400-600`  
**Issue**: File upload endpoints lack comprehensive validation

```python
# VULNERABLE: No file type validation
@router.post("/{dataset_id}/upload")
async def upload_dataset_file(
    dataset_id: str,
    file: UploadFile = File(...),
    # No validation for file type, size, content
):
    content = await file.read()  # Reads entire file into memory
```

**Risk**:
- Malicious file uploads
- Server resource exhaustion
- Path traversal attacks
- Memory exhaustion from large files

### 3. Information Disclosure in Error Messages (MEDIUM - 6.0/10)

**Files**: Multiple route files  
**Issue**: Detailed error messages expose system information

```python
# VULNERABLE: Exposing internal details
except Exception as e:
    print(f"Error creating dataset: {str(e)}")  # Logs to console
    raise HTTPException(
        status_code=500, 
        detail=f"Database error: {str(e)}"  # Exposes internal error
    )
```

**Risk**:
- Database schema information leakage
- Internal system architecture exposure
- Potential for fingerprinting attacks

### 4. Missing Rate Limiting (HIGH - 8.0/10)

**Files**: All route files  
**Issue**: No rate limiting on any endpoints

```python
# MISSING: Rate limiting decorators
@router.post("/api/auth/login")
async def login():  # Vulnerable to brute force
    pass

@router.post("/api/datasets/")
async def create_dataset():  # Vulnerable to spam
    pass
```

**Risk**:
- Brute force attacks on authentication
- Resource exhaustion through API spam
- DoS attacks on expensive operations

### 5. Inconsistent Authentication (MEDIUM - 6.5/10)

**Files**: Various route files  
**Issue**: Some endpoints lack proper authentication checks

```python
# INCONSISTENT: Some endpoints unprotected
@router.get("/health")  # Should this require auth?
async def health_check():
    return {"status": "healthy"}

# vs properly protected:
@router.get("/datasets/")
async def get_datasets(current_user: User = Depends(get_current_user)):
    pass
```

**Risk**:
- Unauthorized access to sensitive data
- Information leakage through unprotected endpoints
- Inconsistent security posture

### 6. Missing Response Model Validation (MEDIUM - 5.5/10)

**Files**: Multiple route files  
**Issue**: API responses not properly validated

```python
# VULNERABLE: Raw dict responses without validation
@router.get("/datasets/", response_model=None)  # Should have proper model
async def get_datasets():
    return {"datasets": raw_data}  # No schema validation
```

**Risk**:
- Sensitive data leakage in responses
- Inconsistent API behavior
- Client-side vulnerabilities from unexpected data

## 🔧 Remediation Steps

### Fix 1: Eliminate SQL Injection Vulnerabilities

**Replace Raw SQL with ORM**:

```python
# BEFORE (vulnerable):
query = text(f"""
UPDATE datasets 
SET {", ".join(set_parts)}
WHERE id = :dataset_id
""")

# AFTER (secure):
from sqlalchemy import update

stmt = (
    update(Dataset)
    .where(Dataset.id == dataset_id)
    .values(**update_data)
)
result = await db.execute(stmt)
```

**For complex queries, use parameterized queries**:

```python
# SECURE: Properly parameterized
from sqlalchemy import text

query = text("""
    SELECT d.id, d.name, d.description 
    FROM datasets d 
    WHERE (:name_filter IS NULL OR d.name ILIKE :name_filter)
    AND d.user_id = :user_id
""")

result = await db.execute(query, {
    "name_filter": f"%{name}%" if name else None,
    "user_id": current_user.id
})
```

### Fix 2: Implement Comprehensive Input Validation

**File Upload Security**:

```python
from typing import List
import magic
from pathlib import Path

ALLOWED_EXTENSIONS = {'.csv', '.json', '.jsonl', '.txt'}
ALLOWED_MIME_TYPES = {
    'text/csv', 'application/json', 'text/plain', 
    'application/x-ndjson'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

async def validate_upload_file(file: UploadFile) -> None:
    """Comprehensive file validation"""
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"MIME type '{file.content_type}' not allowed"
        )
    
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size {file.size} exceeds maximum {MAX_FILE_SIZE} bytes"
        )
    
    # Validate file content (first few bytes)
    content_preview = await file.read(1024)
    await file.seek(0)  # Reset file pointer
    
    # Use python-magic for actual MIME type detection
    actual_mime = magic.from_buffer(content_preview, mime=True)
    if actual_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File content type '{actual_mime}' doesn't match expected types"
        )

@router.post("/{dataset_id}/upload")
async def upload_dataset_file(
    dataset_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file before processing
    await validate_upload_file(file)
    
    # Process file in chunks to avoid memory issues
    content = b""
    while chunk := await file.read(8192):  # Read 8KB chunks
        content += chunk
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, "File too large")
    
    # Rest of processing...
```

### Fix 3: Standardize Error Handling

**Create custom exception handler**:

```python
# backend/core/exceptions.py
class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class ValidationError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 400, details)

class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, 404)

class DatabaseError(AppException):
    def __init__(self, operation: str):
        super().__init__(f"Database error during {operation}", 500)

# backend/core/error_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.core.logging import get_logger

logger = get_logger(__name__)

async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions with appropriate logging"""
    
    # Log error with context
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    # Return sanitized error to client
    response_data = {"error": exc.message}
    
    # Only include details in development
    if settings.DEBUG and exc.details:
        response_data["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )

# In route handlers:
try:
    result = await db.execute(query)
except SQLAlchemyError as e:
    logger.error(f"Database error in get_datasets: {str(e)}")
    raise DatabaseError("fetching datasets")
except Exception as e:
    logger.error(f"Unexpected error in get_datasets: {str(e)}")
    raise AppException("An unexpected error occurred")
```

### Fix 4: Implement Rate Limiting

**Add rate limiting middleware**:

```python
# requirements: slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# In main.py:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In route handlers:
@router.post("/auth/login")
@limiter.limit("5/minute")  # 5 attempts per minute
async def login(request: Request, credentials: LoginRequest):
    pass

@router.post("/datasets/")
@limiter.limit("10/minute")  # 10 dataset creations per minute
async def create_dataset(request: Request, dataset: DatasetCreate):
    pass

@router.post("/datasets/{dataset_id}/upload")
@limiter.limit("3/minute")  # 3 uploads per minute
async def upload_file(request: Request, dataset_id: str, file: UploadFile):
    pass
```

### Fix 5: Standardize Authentication Requirements

**Create authentication audit**:

```python
# List all endpoints and their auth requirements
ENDPOINT_AUTH_MATRIX = {
    # Public endpoints (no auth required)
    "GET /health": False,
    "GET /docs": False,
    "POST /auth/login": False,
    "POST /auth/register": False,
    
    # Protected endpoints (auth required)  
    "GET /auth/me": True,
    "POST /auth/logout": True,
    "GET /datasets/": True,
    "POST /datasets/": True,
    "PUT /datasets/{id}": True,
    "DELETE /datasets/{id}": True,
    # ... all other endpoints
}

# Middleware to verify auth requirements
@app.middleware("http")
async def verify_auth_requirements(request: Request, call_next):
    path = request.url.path
    method = request.method
    endpoint = f"{method} {path}"
    
    # Check if endpoint requires authentication
    requires_auth = ENDPOINT_AUTH_MATRIX.get(endpoint, True)  # Default to auth required
    
    if requires_auth:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required"}
            )
    
    response = await call_next(request)
    return response
```

### Fix 6: Implement Proper Response Models

**Create comprehensive response schemas**:

```python
# backend/api/schemas/responses.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class BaseResponse(BaseModel):
    """Base response model with common fields"""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DatasetResponse(BaseResponse):
    """Dataset response with all fields validated"""
    id: str
    name: str
    description: Optional[str] = None
    type: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    
    class Config:
        from_attributes = True

class DatasetListResponse(BaseResponse):
    """Paginated dataset list response"""
    datasets: List[DatasetResponse]
    total: int
    page: int
    page_size: int
    has_next: bool

class ErrorResponse(BaseModel):
    """Standardized error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Update route handlers:
@router.get("/", response_model=DatasetListResponse)
async def get_datasets(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DatasetListResponse:
    # Implementation with proper response validation
    pass

@router.post("/", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    dataset: DatasetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DatasetResponse:
    # Implementation returns validated response
    pass
```

## ✅ Verification Methods

### Test SQL Injection Protection:
```bash
# Try SQL injection in dataset name
curl -X POST http://localhost:8000/api/datasets/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "test\"; DROP TABLE datasets; --", "type": "classification"}'

# Should be safely handled by ORM
```

### Test File Upload Validation:
```bash
# Test malicious file upload
echo "<?php system($_GET['cmd']); ?>" > malicious.php
curl -X POST http://localhost:8000/api/datasets/123/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@malicious.php"

# Should be rejected due to file type validation
```

### Test Rate Limiting:
```bash
# Rapid fire requests to test rate limiting
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "test", "password": "test"}'
done
# Should be rate limited after 5 attempts
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Eliminate SQL injection vulnerabilities
- [ ] **Fix 2**: Implement file upload validation
- [ ] **Fix 3**: Standardize error handling
- [ ] **Fix 4**: Add rate limiting to all endpoints
- [ ] **Fix 5**: Audit and standardize authentication
- [ ] **Fix 6**: Implement proper response models
- [ ] **Testing**: API security test suite
- [ ] **Documentation**: API security guidelines

## 🔗 Dependencies

- `slowapi` for rate limiting
- `python-magic` for file type detection
- Custom exception classes and handlers
- Comprehensive Pydantic response models
- Updated requirements.txt with security dependencies

## 🚨 Immediate Actions Required

1. **Replace all raw SQL queries with ORM/parameterized queries**
2. **Implement comprehensive file upload validation**
3. **Add rate limiting to authentication endpoints**
4. **Standardize error responses (no internal details in production)**
5. **Audit all endpoints for proper authentication requirements**
6. **Add comprehensive API security tests**
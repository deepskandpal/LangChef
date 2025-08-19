# Security Sweep Guide for Claude Code

This guide provides specific instructions for the `security-sweeper` agent when conducting security audits of the LangChef codebase.

## Security Audit Checklist

### 🔴 Critical Priority (P0)

#### 1. Secrets and Credential Exposure
```bash
# Search patterns for secrets
grep -r "api[_-]?key" --include="*.py" --include="*.js" --include="*.env*"
grep -r "secret[_-]?key" --include="*.py" --include="*.js" 
grep -r "password" --include="*.py" --include="*.js"
grep -r "token" --include="*.py" --include="*.js"

# Check for hardcoded credentials
grep -r "sk-" .  # OpenAI API keys
grep -r "AKIA" .  # AWS access keys
grep -r "eyJ" .   # JWT tokens
```

**Common Issues:**
- Hardcoded API keys in source code
- Default/placeholder secrets in production
- Credentials in git history
- Environment variables in committed files

**Remediation:**
```python
# BAD: Hardcoded secrets
OPENAI_API_KEY = "sk-1234567890abcdef"

# GOOD: Environment-based configuration
import os
from typing import Optional

class Settings:
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    def __init__(self):
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
```

#### 2. Authentication and Authorization Flaws

**JWT Token Security:**
```python
# Check JWT implementation
# backend/services/auth_service.py

# BAD: Weak or default secret
SECRET_KEY = "your-secret-key-for-jwt"  # Default/weak

# GOOD: Strong, environment-based secret
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be at least 32 characters")

# BAD: Long token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# GOOD: Reasonable expiration with refresh
ACCESS_TOKEN_EXPIRE_MINUTES = 60   # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7      # 1 week
```

**Route Protection:**
```python
# Ensure sensitive endpoints are protected
@router.get("/admin/users")  # BAD: No authentication
async def get_users():
    pass

@router.get("/admin/users")
async def get_users(current_user: User = Depends(get_current_user)):  # GOOD
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
```

### 🟡 High Priority (P1)

#### 3. Input Validation and Injection Attacks

**SQL Injection Prevention:**
```python
# BAD: Raw SQL with string formatting
query = f"SELECT * FROM users WHERE id = {user_id}"

# GOOD: Parameterized queries (SQLAlchemy handles this)
query = select(User).where(User.id == user_id)
```

**File Upload Security:**
```python
# File upload validation
ALLOWED_EXTENSIONS = {'.txt', '.csv', '.json', '.jsonl'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_upload(file: UploadFile):
    # Check file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {ext} not allowed")
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # Validate content type
    if file.content_type not in ['text/plain', 'text/csv', 'application/json']:
        raise HTTPException(400, "Invalid content type")
```

**Input Sanitization:**
```python
# Use Pydantic for validation
from pydantic import BaseModel, validator
import re

class PromptCreate(BaseModel):
    name: str
    content: str
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Name contains invalid characters')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        if len(v) > 10000:
            raise ValueError('Content too long')
        return v
```

#### 4. CORS and Headers Configuration

**CORS Security:**
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

# BAD: Wildcard origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Too permissive
    allow_credentials=True
)

# GOOD: Specific origins
allowed_origins = [
    "http://localhost:3000",  # Development
    "https://yourdomain.com", # Production
]

if settings.DEBUG:
    allowed_origins.extend(["http://localhost:*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)
```

**Security Headers:**
```python
# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:;"
    )
    return response
```

### 🟨 Medium Priority (P2)

#### 5. Frontend Security

**Token Storage:**
```javascript
// BAD: localStorage for sensitive tokens
localStorage.setItem('token', token);

// BETTER: sessionStorage with encryption
const encryptedToken = encrypt(token, userSession);
sessionStorage.setItem('auth_token', encryptedToken);

// BEST: httpOnly cookies (backend implementation needed)
// Set-Cookie: token=abc123; HttpOnly; Secure; SameSite=Strict
```

**XSS Prevention:**
```javascript
// BAD: Direct HTML insertion
document.getElementById('content').innerHTML = userInput;

// GOOD: Use React's built-in escaping
return <div>{userInput}</div>;

// For dynamic HTML, use DOMPurify
import DOMPurify from 'dompurify';
const cleanHTML = DOMPurify.sanitize(userInput);
```

#### 6. Error Handling and Information Disclosure

**Error Message Security:**
```python
# BAD: Detailed error messages in production
try:
    user = get_user(user_id)
except Exception as e:
    raise HTTPException(500, f"Database error: {str(e)}")  # Too detailed

# GOOD: Generic messages with proper logging
try:
    user = get_user(user_id)
except UserNotFoundError:
    logger.warning(f"User {user_id} not found")
    raise HTTPException(404, "User not found")
except Exception as e:
    logger.error(f"Unexpected error retrieving user {user_id}: {str(e)}")
    raise HTTPException(500, "Internal server error")
```

## Security Scanning Commands

### Dependency Vulnerabilities
```bash
# Python dependencies
pip install safety
safety check

# Node.js dependencies
npm audit
npm audit fix

# Check for outdated packages
npm outdated
pip list --outdated
```

### Secret Scanning
```bash
# Install truffleHog
pip install truffleHog

# Scan for secrets
trufflehog filesystem /path/to/repo

# Git history scan
trufflehog git file://path/to/repo
```

### SAST Tools
```bash
# Python static analysis
bandit -r backend/

# JavaScript/TypeScript analysis
npx eslint frontend/src --ext .js,.jsx,.ts,.tsx
```

## Common Vulnerability Patterns

### 1. Insecure Direct Object References
```python
# BAD: No authorization check
@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()

# GOOD: Ownership validation
@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    return dataset
```

### 2. Mass Assignment
```python
# BAD: Direct model creation from request data
@router.post("/users")
async def create_user(user_data: dict):
    user = User(**user_data)  # Could set admin=True
    
# GOOD: Use Pydantic schemas
@router.post("/users")
async def create_user(user_data: UserCreate):
    user = User(
        username=user_data.username,
        email=user_data.email,
        # Only allowed fields
    )
```

### 3. Insufficient Rate Limiting
```python
# Add rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    # Login logic with rate limiting
    pass
```

## Security Testing

### Unit Tests for Security
```python
# Test authentication
def test_protected_endpoint_requires_auth():
    response = client.get("/api/datasets")
    assert response.status_code == 401

# Test authorization
def test_user_cannot_access_others_data():
    token = get_user_token(user_id=1)
    response = client.get(
        "/api/datasets/user2-dataset-id",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [404, 403]

# Test input validation
def test_invalid_input_rejected():
    response = client.post("/api/prompts", json={
        "name": "../../../etc/passwd",  # Path traversal attempt
        "content": "test"
    })
    assert response.status_code == 400
```

## Remediation Priorities

### Immediate (P0)
1. **Remove hardcoded secrets** - Replace with environment variables
2. **Fix authentication bypasses** - Add proper route protection
3. **Update vulnerable dependencies** - Run npm audit fix, safety check

### Short-term (P1)
4. **Implement input validation** - Add Pydantic schemas
5. **Configure CORS properly** - Restrict to known origins
6. **Add security headers** - Implement CSP, HSTS, etc.

### Medium-term (P2)
7. **Implement rate limiting** - Protect against brute force
8. **Add audit logging** - Track security-relevant events
9. **Conduct penetration testing** - Third-party security assessment

## Security Monitoring

### Logging Security Events
```python
# Security event logging
import logging

security_logger = logging.getLogger('security')

def log_auth_failure(username: str, ip: str, reason: str):
    security_logger.warning(
        f"Authentication failure: user={username}, ip={ip}, reason={reason}"
    )

def log_unauthorized_access(user_id: str, resource: str, action: str):
    security_logger.error(
        f"Unauthorized access attempt: user={user_id}, resource={resource}, action={action}"
    )
```

### Alerting
```python
# Set up alerts for security events
def alert_on_security_event(event_type: str, details: dict):
    if event_type in ['multiple_auth_failures', 'admin_action', 'data_access_violation']:
        # Send to monitoring system (Slack, PagerDuty, etc.)
        send_security_alert(event_type, details)
```
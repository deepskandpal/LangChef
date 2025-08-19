# Critical Security Fixes Remediation Plan

**Priority**: 🔴 CRITICAL (P0)  
**Agent Assignment**: `security-sweeper`  
**Status**: ❌ Not Started  
**Estimated Time**: 4-6 hours  

## 🚨 Immediate Actions Required

These are the 9 critical security vulnerabilities that pose immediate risk to the application and must be addressed before any production deployment.

---

## 1. Fix Wildcard CORS Configuration (CRITICAL - 9.0/10)

**Issue**: `/backend/main.py:19-27` - Complete bypass of same-origin policy  
**Risk**: Credential theft from any website, CSRF attacks, data exfiltration  

### Immediate Fix Steps:

```bash
# Step 1: Back up current configuration
cp backend/main.py backend/main.py.backup

# Step 2: Replace CORS configuration
```

**Update `/backend/main.py`**:
```python
# REPLACE THIS VULNERABLE CODE:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # REMOVE THIS
    allow_credentials=True,  # DANGEROUS WITH WILDCARD
    allow_methods=["*"],  # REMOVE THIS
    allow_headers=["*"],   # REMOVE THIS
)

# WITH SECURE CONFIGURATION:
from backend.config import settings

# Environment-specific origins
def get_allowed_origins():
    if settings.ENVIRONMENT == "development":
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
    elif settings.ENVIRONMENT == "staging":
        return [
            "https://staging.langchef.com"
        ]
    elif settings.ENVIRONMENT == "production":
        return [
            "https://langchef.com",
            "https://app.langchef.com"
        ]
    return []

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),  # SPECIFIC ORIGINS ONLY
    allow_credentials=True,  # SAFE WITH SPECIFIC ORIGINS
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # SPECIFIC METHODS
    allow_headers=[  # SPECIFIC HEADERS
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With"
    ],
    max_age=3600,  # Cache preflight for 1 hour
)
```

### Verification:
```bash
# Test unauthorized origin (should fail)
curl -H "Origin: https://malicious.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8001/api/prompts
# Expected: 403 Forbidden

# Test authorized origin (should succeed)
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8001/api/prompts
# Expected: 200 with CORS headers
```

---

## 2. Fix Weak JWT Secret Key Validation (CRITICAL - 9.5/10)

**Issue**: `/backend/config.py:26-30` - Weak secret allows token forgery  
**Risk**: Complete authentication bypass, session hijacking  

### Immediate Fix Steps:

**Step 1: Generate strong secret key**
```bash
# Generate cryptographically secure key
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))" > .env.secret
```

**Step 2: Update config validation**
```python
# Update backend/config.py
SECRET_KEY: str = Field(validation_alias="SECRET_KEY")

@field_validator("SECRET_KEY")
@classmethod
def validate_secret_key(cls, v: str) -> str:
    if not v:
        raise ValueError("SECRET_KEY is required")
    
    # Check for weak default keys
    weak_keys = [
        "your-secret-key-here-change-in-production",
        "secret", "changeme", "password", "default", "test"
    ]
    
    if v.lower() in [key.lower() for key in weak_keys]:
        raise ValueError(f"Weak SECRET_KEY detected. Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'")
    
    # Minimum length check
    if len(v) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters")
    
    # Production requires 64+ characters with high entropy
    if settings.ENVIRONMENT == "production" and len(v) < 64:
        raise ValueError("Production SECRET_KEY must be at least 64 characters")
    
    return v
```

**Step 3: Deploy new secret**
```bash
# Add to .env file
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" >> .env

# Restart application to load new key
docker-compose restart backend
```

### Verification:
```bash
# Test with weak key (should fail)
SECRET_KEY=weak python -c "from backend.config import settings; print('Should fail')"

# Test with strong key (should succeed)
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))') python -c "from backend.config import settings; print('Strong key accepted')"
```

---

## 3. Fix Unencrypted AWS Credentials (CRITICAL - 9.0/10)

**Issue**: `/backend/config.py:43-47` - AWS credentials in plain text  
**Risk**: AWS account compromise, data exfiltration  

### Immediate Fix Steps:

**Step 1: Remove credentials from environment**
```bash
# Remove from any .env files
sed -i '/AWS_ACCESS_KEY_ID/d' .env*
sed -i '/AWS_SECRET_ACCESS_KEY/d' .env*
```

**Step 2: Use IAM roles (preferred) or encrypted storage**
```python
# Option A: Use IAM roles (RECOMMENDED for production)
import boto3
from botocore.exceptions import NoCredentialsError

def get_bedrock_client():
    try:
        # Use IAM role - no credentials needed
        return boto3.client('bedrock-runtime')
    except NoCredentialsError:
        logger.error("AWS credentials not configured. Use IAM roles in production.")
        return None

# Option B: Encrypted credential storage
from cryptography.fernet import Fernet

class AWSCredentialManager:
    def __init__(self):
        self.key = self._get_encryption_key()
        self.cipher = Fernet(self.key)
    
    def _get_encryption_key(self):
        key_file = Path(".secrets/aws.key")
        if not key_file.exists():
            key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(key)
            key_file.chmod(0o600)
            return key
        
        with open(key_file, "rb") as f:
            return f.read()
    
    def store_credentials(self, access_key: str, secret_key: str):
        encrypted_access = self.cipher.encrypt(access_key.encode())
        encrypted_secret = self.cipher.encrypt(secret_key.encode())
        
        creds_file = Path(".secrets/aws_creds.enc")
        with open(creds_file, "wb") as f:
            f.write(len(encrypted_access).to_bytes(4, 'big'))
            f.write(encrypted_access)
            f.write(encrypted_secret)
        
        creds_file.chmod(0o600)
```

**Step 3: Update application to use secure credentials**
```python
# Update backend/services/llm_service.py
def get_aws_credentials():
    # Try IAM role first
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            return credentials
    except:
        pass
    
    # Fallback to encrypted storage
    cred_manager = AWSCredentialManager()
    return cred_manager.get_credentials()
```

### Verification:
```bash
# Verify no credentials in environment
env | grep -i aws
# Should show no AWS credentials

# Test AWS connection with IAM role
python -c "import boto3; print(boto3.client('bedrock-runtime').describe_model_inference_jobs())"
```

---

## 4. Implement Missing Token Revocation (CRITICAL - 8.5/10)

**Issue**: No token revocation mechanism  
**Risk**: Compromised tokens remain valid indefinitely  

### Immediate Fix Steps:

**Step 1: Create token blacklist system**
```python
# backend/core/token_blacklist.py
import redis
from datetime import datetime, timedelta
from typing import Set
import jwt
from backend.config import settings

class TokenBlacklist:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST, 
            port=settings.REDIS_PORT,
            decode_responses=True
        )
    
    def revoke_token(self, token: str):
        """Add token to blacklist"""
        try:
            # Decode to get expiration
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get('exp')
            
            if exp:
                # Store until token would naturally expire
                ttl = exp - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    self.redis_client.setex(f"blacklist:{token}", ttl, "revoked")
        except:
            # If can't decode, blacklist for 24 hours
            self.redis_client.setex(f"blacklist:{token}", 86400, "revoked")
    
    def is_token_revoked(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return bool(self.redis_client.exists(f"blacklist:{token}"))

# Global instance
token_blacklist = TokenBlacklist()
```

**Step 2: Add revocation endpoint**
```python
# backend/api/routes/auth.py
@router.post("/revoke")
async def revoke_token(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Revoke current authentication token"""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    
    if token:
        token_blacklist.revoke_token(token)
        logger.info(f"Token revoked for user {current_user.id}")
    
    return {"message": "Token revoked successfully"}
```

**Step 3: Update authentication middleware**
```python
# backend/core/auth.py
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Check if token is blacklisted
    if token_blacklist.is_token_revoked(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )
    
    # Continue with normal token validation...
```

### Verification:
```bash
# Test token revocation
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' | jq -r '.access_token')

# Revoke token
curl -X POST http://localhost:8001/api/auth/revoke \
  -H "Authorization: Bearer $TOKEN"

# Test revoked token (should fail)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/prompts
# Expected: 401 Unauthorized
```

---

## 5. Fix SQL Injection in Dynamic Queries (CRITICAL - 8.0/10)

**Issue**: String concatenation in database queries  
**Risk**: Data breach, unauthorized data access  

### Immediate Fix Steps:

**Step 1: Replace string concatenation with parameterized queries**
```python
# VULNERABLE CODE TO REPLACE:
query = f"SELECT * FROM prompts WHERE name LIKE '%{search_term}%'"
result = await db.execute(query)

# SECURE REPLACEMENT:
from sqlalchemy import text

query = text("SELECT * FROM prompts WHERE name LIKE :search_term")
result = await db.execute(query, {"search_term": f"%{search_term}%"})
```

**Step 2: Update all database operations**
```python
# backend/api/routes/prompts.py - Fix search endpoint
@router.get("/search")
async def search_prompts(
    q: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db)
):
    # Sanitize input
    search_term = q.strip()
    if not search_term:
        raise HTTPException(status_code=400, detail="Search term required")
    
    # Use parameterized query
    query = text("""
        SELECT * FROM prompts 
        WHERE name ILIKE :search_term 
           OR description ILIKE :search_term
        ORDER BY created_at DESC
        LIMIT 50
    """)
    
    result = await db.execute(
        query, 
        {"search_term": f"%{search_term}%"}
    )
    
    return result.fetchall()
```

**Step 3: Add input validation middleware**
```python
# backend/middleware/input_validation.py
import re
from fastapi import HTTPException

class SQLInjectionProtection:
    @staticmethod
    def validate_user_input(value: str, field_name: str) -> str:
        if not value:
            return value
        
        # Check for SQL injection patterns
        dangerous_patterns = [
            r"('|(\\'))",           # SQL quotes
            r"(;|\|)",              # Statement separators  
            r"(\*|%)",              # SQL wildcards
            r"(exec|execute)",      # Command execution
            r"(union|select|insert|update|delete|drop|create)", # SQL keywords
            r"(script|javascript)", # Script injection
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value.lower()):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid characters detected in {field_name}"
                )
        
        return value[:1000]  # Limit length

# Apply to all string inputs
def validate_string_input(value: str, field_name: str = "input") -> str:
    return SQLInjectionProtection.validate_user_input(value, field_name)
```

### Verification:
```bash
# Test SQL injection protection
curl "http://localhost:8001/api/prompts/search?q=test'; DROP TABLE prompts; --"
# Expected: 400 Bad Request with validation error

# Test normal search
curl "http://localhost:8001/api/prompts/search?q=customer"
# Expected: 200 with search results
```

---

## 6. Fix Insecure Token Storage (CRITICAL - 7.5/10)

**Issue**: JWT tokens in localStorage vulnerable to XSS  
**Risk**: Token theft via cross-site scripting  

### Immediate Fix Steps:

**Step 1: Create secure token storage**
```javascript
// frontend/src/utils/secureStorage.js
import CryptoJS from 'crypto-js';

class SecureTokenStorage {
    constructor() {
        this.encryptionKey = this.getOrCreateSessionKey();
    }
    
    getOrCreateSessionKey() {
        let key = sessionStorage.getItem('session_key');
        if (!key) {
            key = CryptoJS.lib.WordArray.random(256/8).toString();
            sessionStorage.setItem('session_key', key);
        }
        return key;
    }
    
    storeToken(token) {
        if (!token) return;
        
        const encrypted = CryptoJS.AES.encrypt(token, this.encryptionKey).toString();
        
        // Use sessionStorage instead of localStorage
        sessionStorage.setItem('auth_token_enc', encrypted);
        
        // Set expiration
        const expirationTime = Date.now() + (60 * 60 * 1000);
        sessionStorage.setItem('auth_token_exp', expirationTime.toString());
    }
    
    getToken() {
        const encrypted = sessionStorage.getItem('auth_token_enc');
        const expiration = sessionStorage.getItem('auth_token_exp');
        
        if (!encrypted || !expiration) {
            return null;
        }
        
        // Check expiration
        if (Date.now() > parseInt(expiration)) {
            this.clearToken();
            return null;
        }
        
        try {
            const decrypted = CryptoJS.AES.decrypt(encrypted, this.encryptionKey);
            return decrypted.toString(CryptoJS.enc.Utf8);
        } catch (error) {
            this.clearToken();
            return null;
        }
    }
    
    clearToken() {
        sessionStorage.removeItem('auth_token_enc');
        sessionStorage.removeItem('auth_token_exp');
    }
}

export const tokenStorage = new SecureTokenStorage();
```

**Step 2: Update AuthContext**
```javascript
// frontend/src/contexts/AuthContext.js
import { tokenStorage } from '../utils/secureStorage';

// REPLACE:
localStorage.setItem('token', response.data.access_token);
// WITH:
tokenStorage.storeToken(response.data.access_token);

// REPLACE:
const token = localStorage.getItem('token');
// WITH:
const token = tokenStorage.getToken();

// REPLACE:
localStorage.removeItem('token');
// WITH:
tokenStorage.clearToken();
```

### Verification:
```javascript
// Test secure token storage
import { tokenStorage } from './utils/secureStorage';

// Store token
tokenStorage.storeToken('test-jwt-token');

// Verify it's encrypted in storage
const encrypted = sessionStorage.getItem('auth_token_enc');
console.assert(encrypted !== 'test-jwt-token', 'Token should be encrypted');

// Verify decryption works
const decrypted = tokenStorage.getToken();
console.assert(decrypted === 'test-jwt-token', 'Token should decrypt correctly');
```

---

## 7. Fix Unvalidated File Uploads (HIGH - 7.5/10)

**Issue**: No file type or size validation  
**Risk**: Malicious file uploads, DoS attacks  

### Immediate Fix Steps:

**Step 1: Add file validation**
```python
# backend/core/file_validator.py
from typing import List, Optional
from fastapi import UploadFile, HTTPException
import magic
import hashlib

class FileValidator:
    ALLOWED_TYPES = {
        'text/csv': ['.csv'],
        'application/json': ['.json'],
        'text/plain': ['.txt']
    }
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    @classmethod
    def validate_upload_file(cls, file: UploadFile) -> bool:
        # Check file size
        if hasattr(file.file, 'seek'):
            file.file.seek(0, 2)  # Seek to end
            size = file.file.tell()
            file.file.seek(0)  # Seek back to start
            
            if size > cls.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {cls.MAX_FILE_SIZE / (1024*1024):.1f}MB"
                )
        
        # Check file extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        # Validate MIME type
        content = file.file.read(1024)  # Read first 1KB for MIME detection
        file.file.seek(0)  # Reset file pointer
        
        detected_type = magic.from_buffer(content, mime=True)
        
        if detected_type not in cls.ALLOWED_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File type not allowed. Allowed: {list(cls.ALLOWED_TYPES.keys())}"
            )
        
        allowed_extensions = cls.ALLOWED_TYPES[detected_type]
        if f".{file_ext}" not in allowed_extensions:
            raise HTTPException(
                status_code=415,
                detail=f"File extension '{file_ext}' doesn't match content type '{detected_type}'"
            )
        
        return True
```

**Step 2: Update upload endpoint**
```python
# backend/api/routes/datasets.py
from backend.core.file_validator import FileValidator

@router.post("/upload/file")
async def upload_dataset_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file
    FileValidator.validate_upload_file(file)
    
    # Continue with secure file processing...
```

### Verification:
```bash
# Test file size limit
dd if=/dev/zero of=large_file.csv bs=1M count=100  # Create 100MB file
curl -F "file=@large_file.csv" http://localhost:8001/api/datasets/upload/file
# Expected: 413 Payload Too Large

# Test file type validation
echo "malicious content" > malicious.exe
curl -F "file=@malicious.exe" http://localhost:8001/api/datasets/upload/file
# Expected: 415 Unsupported Media Type
```

---

## 8. Fix Missing Input Validation (HIGH - 7.0/10)

**Issue**: No validation on API endpoints  
**Risk**: Data corruption, injection attacks  

### Immediate Fix Steps:

**Step 1: Add comprehensive input validation**
```python
# backend/core/validators.py
from pydantic import BaseModel, Field, validator
import re
from typing import Optional

class SecurePromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v.strip() if v else None
    
    @validator('content')
    def validate_content(cls, v):
        # Check for dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Content contains potentially dangerous code')
        
        return v.strip()

class SecureDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
```

**Step 2: Apply validation to endpoints**
```python
# backend/api/routes/prompts.py
from backend.core.validators import SecurePromptCreate

@router.post("/", response_model=PromptResponse)
async def create_prompt(
    prompt_data: SecurePromptCreate,  # Use secure validator
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Input is now validated and sanitized
    prompt = Prompt(
        name=prompt_data.name,
        description=prompt_data.description,
        content=prompt_data.content,
        user_id=current_user.id
    )
    
    db.add(prompt)
    await db.commit()
    return prompt
```

### Verification:
```bash
# Test input validation
curl -X POST http://localhost:8001/api/prompts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"<script>alert(1)</script>","content":"test"}'
# Expected: 422 Validation Error

# Test valid input
curl -X POST http://localhost:8001/api/prompts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Valid Prompt","content":"This is valid content"}'
# Expected: 201 Created
```

---

## 9. Fix Debug Information Exposure (HIGH - 6.5/10)

**Issue**: Debug code and sensitive information in production  
**Risk**: Information disclosure, attack surface expansion  

### Immediate Fix Steps:

**Step 1: Remove debug code**
```python
# backend/main.py - Remove debug information
# REMOVE THESE LINES:
# import uvicorn
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# REPLACE debug middleware with production-ready version:
if settings.ENVIRONMENT != "production":
    # Only add debug middleware in non-production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Dev only
    )
```

**Step 2: Secure error handling**
```python
# backend/core/error_handlers.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

async def production_exception_handler(request: Request, exc: Exception):
    """Handle exceptions securely in production"""
    
    if settings.ENVIRONMENT == "production":
        # Generic error message for production
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        # Detailed errors for development
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )

# Add to main.py
app.add_exception_handler(Exception, production_exception_handler)
```

**Step 3: Remove frontend debug code**
```javascript
// frontend/src/contexts/AuthContext.js - REMOVE:
window.debugAuthToken = localStorage.getItem('token');
document.body.setAttribute('data-has-token', !!localStorage.getItem('token'));
```

### Verification:
```bash
# Test error handling in production
ENVIRONMENT=production curl http://localhost:8001/api/nonexistent
# Should return generic error, not stack trace

# Verify no debug attributes in DOM
curl -s http://localhost:3000 | grep -i debug
# Should return no results
```

---

## 🔍 Critical Fixes Validation Checklist

After implementing all critical fixes, verify each one:

- [ ] **CORS**: ✅ Wildcard origins removed, specific origins configured
- [ ] **JWT Secret**: ✅ Strong secret key generated and deployed
- [ ] **AWS Credentials**: ✅ Moved to encrypted storage or IAM roles
- [ ] **Token Revocation**: ✅ Blacklist system implemented and tested
- [ ] **SQL Injection**: ✅ All queries use parameterized statements
- [ ] **Token Storage**: ✅ Encrypted sessionStorage replaces localStorage
- [ ] **File Uploads**: ✅ Type, size, and content validation added
- [ ] **Input Validation**: ✅ All API endpoints validate input data
- [ ] **Debug Exposure**: ✅ Debug code removed from production

## 📊 Success Metrics

- **Security Score**: Target 95%+ on security scanners
- **Vulnerability Count**: 0 critical, <3 high priority
- **Test Coverage**: 100% of security fixes covered by tests
- **Performance Impact**: <5% degradation from security measures

## 🚨 Emergency Rollback Plan

If critical fixes cause system instability:

1. **Immediate rollback**: `git checkout HEAD~1 && docker-compose restart`
2. **Gradual deployment**: Apply fixes one by one with testing
3. **Monitoring**: Check error rates and performance metrics
4. **Communication**: Notify stakeholders of security vs. stability trade-offs

---

**Next Steps**: After completing critical fixes, proceed to [High Priority Fixes](high-priority.md) for remaining security improvements.
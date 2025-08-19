# Backend Authentication Security Audit

**Component**: JWT Authentication & Session Management  
**Priority**: 🔴 CRITICAL  
**Agent Assignment**: `backend-fastapi-refactorer`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Weak JWT Secret Key Validation (CRITICAL - 9.5/10)

**File**: `/backend/config.py:26-30`  
**Issue**: SECRET_KEY validation only catches specific placeholder value, not empty strings or weak keys

```python
# VULNERABLE CODE:
def model_post_init(self, __context) -> None:
    if self.SECRET_KEY == "your-secret-key-for-jwt":  # Only validates placeholder
        raise ValueError("SECRET_KEY must be set to a secure random value")
```

**Risk**: 
- JWT tokens can be forged with predictable keys
- Authentication bypass vulnerability
- Session hijacking potential

**Impact**: Complete authentication system compromise

### 2. Missing Token Revocation System (CRITICAL - 9.0/10)

**File**: `/backend/services/auth_service.py`  
**Issue**: No token blacklist or revocation mechanism

```python
# MISSING: Token revocation endpoint and blacklist system
# Frontend expects /revoke endpoint but doesn't exist
```

**Risk**:
- Compromised tokens remain valid for full 24-hour period
- No way to invalidate sessions on logout
- Extended impact window for token theft

### 3. Excessive Token Expiration Time (HIGH - 7.0/10)

**File**: `/backend/config.py:26`  
**Issue**: 24-hour JWT token expiration too long

```python
# VULNERABLE:
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
```

**Risk**:
- Increased attack window for stolen tokens
- No refresh token strategy
- Sessions persist too long

### 4. AWS Credentials Stored Unencrypted (CRITICAL - 9.8/10)

**File**: `/backend/models/user.py`  
**Issue**: AWS credentials stored in plaintext in database

```python
# VULNERABLE: Plaintext credential storage
aws_access_key_id = Column(String, nullable=True)
aws_secret_access_key = Column(String, nullable=True)
aws_session_token = Column(Text, nullable=True)
```

**Risk**:
- Database compromise exposes all user AWS accounts
- Credentials visible in database dumps
- Insider threat vulnerability

### 5. Inconsistent Authentication Patterns (MEDIUM - 5.0/10)

**Files**: Various routes in `/backend/api/routes/`  
**Issue**: Mixed authentication requirements across endpoints

```python
# Some endpoints missing authentication:
@router.get("/health")  # Should this be authenticated?
async def health_check():
    pass

# Inconsistent dependency injection:
current_user: User = Depends(get_current_user)  # Good
# vs manual token extraction in some places
```

## 🔧 Remediation Steps

### Fix 1: Strengthen SECRET_KEY Validation

**Target File**: `/backend/config.py`

```python
def model_post_init(self, __context) -> None:
    if not self.SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set")
    
    if self.SECRET_KEY in ["your-secret-key-for-jwt", "secret", "key"]:
        raise ValueError("SECRET_KEY cannot be a default or common value")
    
    if len(self.SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")
    
    # Check for sufficient entropy (basic check)
    if len(set(self.SECRET_KEY)) < 10:
        raise ValueError("SECRET_KEY must have sufficient entropy (varied characters)")
```

### Fix 2: Implement Token Revocation System

**New File**: `/backend/services/token_blacklist.py`

```python
from datetime import datetime, timedelta
from typing import Set
import redis
from backend.config import settings

class TokenBlacklist:
    def __init__(self):
        # Use Redis for production, in-memory for development
        self.redis_client = redis.Redis.from_url(
            settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else None
        ) if settings.REDIS_URL else None
        self._memory_blacklist: Set[str] = set()
    
    async def revoke_token(self, jti: str, exp: datetime) -> None:
        """Add token to blacklist until expiration"""
        if self.redis_client:
            ttl = int((exp - datetime.utcnow()).total_seconds())
            await self.redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
        else:
            self._memory_blacklist.add(jti)
    
    async def is_revoked(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        if self.redis_client:
            return await self.redis_client.exists(f"blacklist:{jti}")
        return jti in self._memory_blacklist

blacklist = TokenBlacklist()
```

**Add to auth_service.py**:

```python
# Add JTI to JWT tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Add unique JTI for revocation
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Update token validation
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        
        if username is None or jti is None:
            raise credentials_exception
        
        # Check if token is revoked
        if await blacklist.is_revoked(jti):
            raise credentials_exception
            
        # ... rest of validation
```

**New Route**: `/backend/api/routes/auth.py`

```python
@router.post("/revoke")
async def revoke_token(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user)
):
    """Revoke the current JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = datetime.fromtimestamp(payload.get("exp"))
        
        await blacklist.revoke_token(jti, exp)
        
        return {"message": "Token revoked successfully"}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

### Fix 3: Reduce Token Expiration and Add Refresh Tokens

**Update config.py**:

```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # 1 week
```

### Fix 4: Encrypt AWS Credentials in Database

**Update user model**:

```python
from cryptography.fernet import Fernet
from backend.config import settings

def encrypt_credential(credential: str) -> str:
    """Encrypt credential using application key"""
    if not credential:
        return None
    
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return fernet.encrypt(credential.encode()).decode()

def decrypt_credential(encrypted_credential: str) -> str:
    """Decrypt credential using application key"""
    if not encrypted_credential:
        return None
    
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return fernet.decrypt(encrypted_credential.encode()).decode()

class User(Base):
    __tablename__ = "users"
    
    # Store encrypted credentials
    _aws_access_key_id = Column("aws_access_key_id", String, nullable=True)
    _aws_secret_access_key = Column("aws_secret_access_key", String, nullable=True)
    _aws_session_token = Column("aws_session_token", Text, nullable=True)
    
    @property
    def aws_access_key_id(self) -> Optional[str]:
        return decrypt_credential(self._aws_access_key_id)
    
    @aws_access_key_id.setter
    def aws_access_key_id(self, value: Optional[str]):
        self._aws_access_key_id = encrypt_credential(value)
    
    # Similar for other credentials...
```

**Add to config.py**:

```python
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY")

def model_post_init(self, __context) -> None:
    # ... existing validation ...
    
    if not self.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY must be set for credential encryption")
    
    if len(self.ENCRYPTION_KEY) != 44:  # Fernet key length
        raise ValueError("ENCRYPTION_KEY must be a valid Fernet key (44 characters)")
```

## ✅ Verification Methods

### Test SECRET_KEY Validation:
```bash
# Should fail with weak keys
export SECRET_KEY="weak"
python -c "from backend.config import settings"

# Should pass with strong key
export SECRET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
python -c "from backend.config import settings; print('Strong key accepted')"
```

### Test Token Revocation:
```bash
# Test revocation endpoint
curl -X POST http://localhost:8000/api/auth/revoke \
  -H "Authorization: Bearer YOUR_TOKEN"

# Verify token is rejected
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer REVOKED_TOKEN"
```

### Test Credential Encryption:
```python
from backend.models.user import User
from backend.database import get_db

# Create user with AWS credentials
user = User(username="test", aws_access_key_id="AKIA123456789")
# Verify credentials are encrypted in database
assert user._aws_access_key_id != "AKIA123456789"
# Verify decryption works
assert user.aws_access_key_id == "AKIA123456789"
```

## 📊 Progress Tracking

- [ ] **Fix 1**: SECRET_KEY validation strengthening
- [ ] **Fix 2**: Token revocation system implementation  
- [ ] **Fix 3**: Reduce token expiration times
- [ ] **Fix 4**: AWS credential encryption
- [ ] **Fix 5**: Standardize authentication patterns
- [ ] **Testing**: Comprehensive authentication tests
- [ ] **Documentation**: Update security documentation

## 🔗 Dependencies

- `cryptography` library for credential encryption
- `redis` or alternative for token blacklist (optional)
- Environment variables for ENCRYPTION_KEY
- Database migration for credential encryption

## 🚨 Critical Actions Required Before Production

1. Generate and set strong SECRET_KEY (32+ characters)
2. Generate and set ENCRYPTION_KEY for credentials
3. Implement token revocation system
4. Encrypt existing AWS credentials in database
5. Set up Redis for production token blacklist
6. Add comprehensive authentication tests
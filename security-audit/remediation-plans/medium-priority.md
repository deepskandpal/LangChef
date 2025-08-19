# Medium Priority Security Fixes Remediation Plan

**Priority**: 🟠 MEDIUM (P2)  
**Agent Assignment**: Mixed - `backend-fastapi-refactorer`, `frontend-react-refactorer`, `security-sweeper`  
**Status**: ❌ Not Started  
**Estimated Time**: 4-6 hours  

## 📋 Overview

These are the 13 medium-priority security vulnerabilities that should be addressed to achieve comprehensive security posture. While not immediately critical, they contribute to defense-in-depth and should be implemented for production deployment.

---

## 1. Implement Request Rate Limiting (MEDIUM - 6.5/10)

**Issue**: No rate limiting on API endpoints allows DoS attacks  
**Risk**: API abuse, resource exhaustion, brute force attacks  
**Agent**: `backend-fastapi-refactorer`  

### Implementation Steps:

**Step 1: Install rate limiting dependencies**
```bash
cd backend
pip install slowapi redis
```

**Step 2: Create rate limiting system**
```python
# backend/middleware/rate_limiting.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import redis
from typing import Dict, Optional
import time
import json
from backend.config import settings

# Redis connection for rate limiting
redis_client = redis.Redis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    decode_responses=True
)

class AdvancedRateLimiter:
    def __init__(self):
        self.limiter = Limiter(
            key_func=self._get_identifier,
            storage_uri=f"redis://{getattr(settings, 'REDIS_HOST', 'localhost')}:{getattr(settings, 'REDIS_PORT', 6379)}"
        )
        self.suspicious_ips = set()
        
    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        # Try to get user ID first (for authenticated requests)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP address
        return get_remote_address(request)
    
    def _get_endpoint_limits(self, endpoint: str) -> Dict[str, str]:
        """Get rate limits for specific endpoints"""
        limits = {
            # Authentication endpoints (stricter limits)
            '/auth/login': '5/minute',
            '/auth/register': '3/minute', 
            '/auth/reset-password': '2/minute',
            
            # File upload endpoints
            '/datasets/upload': '10/minute',
            
            # Search endpoints
            '/prompts/search': '30/minute',
            '/datasets/search': '30/minute',
            
            # General API endpoints
            'default': '100/minute'
        }
        
        # Find matching endpoint
        for pattern, limit in limits.items():
            if pattern in endpoint:
                return {'rate': limit}
        
        return {'rate': limits['default']}
    
    def check_rate_limit(self, request: Request, endpoint: str) -> bool:
        """Check if request should be rate limited"""
        identifier = self._get_identifier(request)
        limits = self._get_endpoint_limits(endpoint)
        
        # Check if IP is marked as suspicious
        ip = get_remote_address(request)
        if ip in self.suspicious_ips:
            # Apply stricter limits for suspicious IPs
            limits['rate'] = '10/minute'
        
        try:
            # Use slowapi's rate limiting
            self.limiter.check_request_limit(
                request=request,
                response=Response(),
                key=identifier,
                limits=[limits['rate']]
            )
            return True
        except RateLimitExceeded:
            # Mark IP as suspicious after multiple rate limit violations
            self._handle_rate_limit_violation(ip, identifier)
            return False
    
    def _handle_rate_limit_violation(self, ip: str, identifier: str):
        """Handle rate limit violations"""
        violation_key = f"violations:{ip}"
        
        # Increment violation count
        violations = redis_client.incr(violation_key)
        redis_client.expire(violation_key, 3600)  # 1 hour window
        
        # Mark as suspicious after 5 violations
        if violations >= 5:
            self.suspicious_ips.add(ip)
            redis_client.setex(f"suspicious:{ip}", 3600, "true")
            
            # Log security event
            self._log_security_event(ip, identifier, violations)
    
    def _log_security_event(self, ip: str, identifier: str, violations: int):
        """Log rate limiting security events"""
        event = {
            'type': 'rate_limit_violation',
            'ip': ip,
            'identifier': identifier,
            'violations': violations,
            'timestamp': time.time()
        }
        
        # In production, send to security monitoring system
        logger.warning(f"Security event: {json.dumps(event)}")

# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()

# Rate limiting middleware
async def rate_limiting_middleware(request: Request, call_next):
    """Apply rate limiting to requests"""
    endpoint = request.url.path
    
    # Skip rate limiting for health checks
    if endpoint in ['/health', '/metrics']:
        return await call_next(request)
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(request, endpoint):
        return Response(
            content='{"detail": "Rate limit exceeded"}',
            status_code=429,
            headers={'Content-Type': 'application/json'}
        )
    
    return await call_next(request)
```

**Step 3: Apply rate limiting to FastAPI**
```python
# backend/main.py
from backend.middleware.rate_limiting import rate_limiting_middleware, rate_limiter

# Add rate limiting middleware
app.middleware("http")(rate_limiting_middleware)

# Add rate limiter to app state
app.state.limiter = rate_limiter.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply specific rate limits to routes
@app.get("/api/prompts/search")
@rate_limiter.limiter.limit("30/minute")
async def search_prompts(
    request: Request,
    q: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    # Implementation...
    pass
```

### Verification:
```bash
# Test rate limiting
for i in {1..6}; do
  curl -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}'
  echo "Request $i"
done
# Expected: 429 Rate Limited after 5 requests
```

---

## 2. Secure Session Management (MEDIUM - 6.0/10)

**Issue**: No secure session handling mechanism  
**Risk**: Session fixation, hijacking, concurrent sessions  
**Agent**: `backend-fastapi-refactorer`  

### Implementation Steps:

**Step 1: Create session management system**
```python
# backend/core/session_manager.py
import uuid
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import redis
from backend.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

class SecureSessionManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            decode_responses=True
        )
        self.session_timeout = 3600  # 1 hour
        self.max_sessions_per_user = 5
        
    def create_session(self, user_id: int, user_agent: str, ip_address: str) -> str:
        """Create new secure session"""
        session_id = str(uuid.uuid4())
        
        # Limit concurrent sessions per user
        self._enforce_session_limit(user_id)
        
        session_data = {
            'user_id': user_id,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'user_agent': user_agent,
            'ip_address': ip_address,
            'is_active': True
        }
        
        # Store session data
        session_key = f"session:{session_id}"
        self.redis_client.setex(
            session_key,
            self.session_timeout,
            json.dumps(session_data)
        )
        
        # Track user sessions
        user_sessions_key = f"user_sessions:{user_id}"
        self.redis_client.sadd(user_sessions_key, session_id)
        self.redis_client.expire(user_sessions_key, self.session_timeout)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def validate_session(self, session_id: str, user_agent: str, ip_address: str) -> Optional[Dict[str, Any]]:
        """Validate and refresh session"""
        session_key = f"session:{session_id}"
        session_data_str = self.redis_client.get(session_key)
        
        if not session_data_str:
            return None
        
        try:
            session_data = json.loads(session_data_str)
        except json.JSONDecodeError:
            logger.error(f"Invalid session data for {session_id}")
            return None
        
        # Validate session integrity
        if not self._validate_session_security(session_data, user_agent, ip_address):
            self.invalidate_session(session_id)
            return None
        
        # Update last accessed time
        session_data['last_accessed'] = time.time()
        self.redis_client.setex(
            session_key,
            self.session_timeout,
            json.dumps(session_data)
        )
        
        return session_data
    
    def _validate_session_security(self, session_data: Dict, user_agent: str, ip_address: str) -> bool:
        """Validate session security attributes"""
        
        # Check if session is active
        if not session_data.get('is_active', False):
            return False
        
        # Validate user agent (detect session hijacking)
        stored_user_agent = session_data.get('user_agent', '')
        if stored_user_agent != user_agent:
            logger.warning(f"User agent mismatch for session. Stored: {stored_user_agent[:50]}, Current: {user_agent[:50]}")
            return False
        
        # Validate IP address (optional - can be disabled for mobile users)
        stored_ip = session_data.get('ip_address', '')
        if settings.ENFORCE_IP_VALIDATION and stored_ip != ip_address:
            logger.warning(f"IP address mismatch for session. Stored: {stored_ip}, Current: {ip_address}")
            return False
        
        # Check session age
        created_at = session_data.get('created_at', 0)
        max_session_age = 24 * 3600  # 24 hours
        if time.time() - created_at > max_session_age:
            logger.info("Session expired due to age")
            return False
        
        return True
    
    def invalidate_session(self, session_id: str):
        """Invalidate specific session"""
        session_key = f"session:{session_id}"
        session_data_str = self.redis_client.get(session_key)
        
        if session_data_str:
            try:
                session_data = json.loads(session_data_str)
                user_id = session_data.get('user_id')
                
                # Remove from user sessions
                if user_id:
                    user_sessions_key = f"user_sessions:{user_id}"
                    self.redis_client.srem(user_sessions_key, session_id)
                
            except json.JSONDecodeError:
                pass
        
        # Delete session
        self.redis_client.delete(session_key)
        logger.info(f"Invalidated session {session_id}")
    
    def invalidate_all_user_sessions(self, user_id: int):
        """Invalidate all sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis_client.smembers(user_sessions_key)
        
        for session_id in session_ids:
            self.invalidate_session(session_id)
        
        self.redis_client.delete(user_sessions_key)
        logger.info(f"Invalidated all sessions for user {user_id}")
    
    def _enforce_session_limit(self, user_id: int):
        """Enforce maximum sessions per user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = list(self.redis_client.smembers(user_sessions_key))
        
        if len(session_ids) >= self.max_sessions_per_user:
            # Remove oldest sessions
            sessions_with_age = []
            for session_id in session_ids:
                session_key = f"session:{session_id}"
                session_data_str = self.redis_client.get(session_key)
                if session_data_str:
                    try:
                        session_data = json.loads(session_data_str)
                        created_at = session_data.get('created_at', 0)
                        sessions_with_age.append((session_id, created_at))
                    except json.JSONDecodeError:
                        # Remove invalid session
                        self.invalidate_session(session_id)
            
            # Sort by age and remove oldest
            sessions_with_age.sort(key=lambda x: x[1])
            sessions_to_remove = len(sessions_with_age) - self.max_sessions_per_user + 1
            
            for i in range(sessions_to_remove):
                session_id = sessions_with_age[i][0]
                self.invalidate_session(session_id)
                logger.info(f"Removed old session {session_id} for user {user_id} (session limit)")
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis_client.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session_key = f"session:{session_id}"
            session_data_str = self.redis_client.get(session_key)
            
            if session_data_str:
                try:
                    session_data = json.loads(session_data_str)
                    sessions.append({
                        'session_id': session_id,
                        'created_at': datetime.fromtimestamp(session_data['created_at']),
                        'last_accessed': datetime.fromtimestamp(session_data['last_accessed']),
                        'user_agent': session_data['user_agent'][:100],  # Truncate for display
                        'ip_address': session_data['ip_address']
                    })
                except json.JSONDecodeError:
                    # Clean up invalid session
                    self.invalidate_session(session_id)
        
        return sessions

# Global session manager
session_manager = SecureSessionManager()
```

**Step 2: Integrate with authentication**
```python
# backend/api/routes/auth.py
from backend.core.session_manager import session_manager

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # Validate credentials (existing code)
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    user_agent = request.headers.get('user-agent', '')
    ip_address = request.client.host
    session_id = session_manager.create_session(user.id, user_agent, ip_address)
    
    # Create JWT token with session reference
    access_token = create_access_token(
        data={"sub": user.username, "session_id": session_id}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "session_id": session_id
    }

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Get session ID from token
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        session_id = payload.get("session_id")
        if session_id:
            session_manager.invalidate_session(session_id)
    except:
        pass  # Token might be invalid, but still log out
    
    return {"message": "Logged out successfully"}

@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user)
):
    """Get all active sessions for current user"""
    sessions = session_manager.get_user_sessions(current_user.id)
    return {"sessions": sessions}

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Revoke specific session"""
    session_manager.invalidate_session(session_id)
    return {"message": "Session revoked"}
```

### Verification:
```bash
# Test session management
# Login and get session
RESPONSE=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test")

SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')
TOKEN=$(echo $RESPONSE | jq -r '.access_token')

# List sessions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/auth/sessions

# Revoke session
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/auth/sessions/$SESSION_ID"
```

---

## 3. Implement Comprehensive Logging (MEDIUM - 6.0/10)

**Issue**: Insufficient security logging and monitoring  
**Risk**: Undetected security incidents, compliance issues  
**Agent**: `security-sweeper`  

### Implementation Steps:

**Step 1: Create security logging system**
```python
# backend/core/security_logger.py
import json
import time
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import logging
from backend.config import settings

class SecurityEventType(Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    AUTHENTICATION_ERROR = "auth_error"
    AUTHORIZATION_ERROR = "authz_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    FILE_UPLOAD = "file_upload"
    ADMIN_ACTION = "admin_action"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "config_change"
    SECURITY_SCAN = "security_scan"
    PASSWORD_CHANGE = "password_change"
    SESSION_CREATED = "session_created"
    SESSION_TERMINATED = "session_terminated"

class SecurityLogger:
    def __init__(self):
        # Configure security-specific logger
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # Create secure log formatter
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        
        # File handler for security events (separate from application logs)
        file_handler = logging.FileHandler('logs/security.log')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        # Console handler for development
        if settings.ENVIRONMENT == "development":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        risk_level: str = "medium"
    ):
        """Log security event with structured data"""
        
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "user_agent": user_agent[:200] if user_agent else None,  # Truncate
            "resource": resource,
            "action": action,
            "result": result,
            "risk_level": risk_level,
            "session_id": None,  # Will be set by context if available
            "environment": settings.ENVIRONMENT,
            "details": details or {}
        }
        
        # Remove None values for cleaner logs
        event_data = {k: v for k, v in event_data.items() if v is not None}
        
        # Log as JSON for structured logging systems
        log_message = json.dumps(event_data)
        
        # Use appropriate log level based on risk
        if risk_level == "critical":
            self.logger.critical(log_message)
        elif risk_level == "high":
            self.logger.error(log_message)
        elif risk_level == "medium":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def log_authentication_event(
        self,
        event_type: SecurityEventType,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: Optional[str] = None
    ):
        """Log authentication-related events"""
        self.log_security_event(
            event_type=event_type,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            result="success" if success else "failure",
            risk_level="high" if not success else "low",
            details={"failure_reason": failure_reason} if failure_reason else None
        )
    
    def log_data_access_event(
        self,
        user_id: int,
        username: str,
        resource: str,
        action: str,
        ip_address: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log data access events"""
        self.log_security_event(
            event_type=SecurityEventType.DATA_ACCESS,
            user_id=user_id,
            username=username,
            resource=resource,
            action=action,
            ip_address=ip_address,
            result="success" if success else "failure",
            risk_level="medium",
            details=details
        )
    
    def log_admin_action(
        self,
        user_id: int,
        username: str,
        action: str,
        resource: str,
        ip_address: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log administrative actions"""
        self.log_security_event(
            event_type=SecurityEventType.ADMIN_ACTION,
            user_id=user_id,
            username=username,
            resource=resource,
            action=action,
            ip_address=ip_address,
            risk_level="high",
            details=details
        )
    
    def log_suspicious_activity(
        self,
        event_description: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log suspicious activity for security monitoring"""
        self.log_security_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=event_description,
            risk_level="critical",
            details=details
        )

# Global security logger instance
security_logger = SecurityLogger()

# Logging middleware
async def security_logging_middleware(request: Request, call_next):
    """Middleware to log security-relevant requests"""
    start_time = time.time()
    
    # Extract request information
    ip_address = request.client.host
    user_agent = request.headers.get('user-agent', '')
    method = request.method
    path = request.url.path
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log security-relevant endpoints
    security_endpoints = ['/auth/', '/admin/', '/user/', '/upload/']
    
    if any(endpoint in path for endpoint in security_endpoints):
        # Get user information if available
        user_id = getattr(request.state, 'user_id', None)
        username = getattr(request.state, 'username', None)
        
        # Determine if this was successful
        success = 200 <= response.status_code < 300
        
        security_logger.log_security_event(
            event_type=SecurityEventType.DATA_ACCESS,
            user_id=user_id,
            username=username,
            resource=path,
            action=method,
            ip_address=ip_address,
            user_agent=user_agent,
            result="success" if success else "failure",
            risk_level="medium" if success else "high",
            details={
                "status_code": response.status_code,
                "process_time": round(process_time, 3)
            }
        )
    
    return response
```

**Step 2: Integrate security logging**
```python
# backend/main.py
from backend.core.security_logger import security_logging_middleware

# Add security logging middleware
app.middleware("http")(security_logging_middleware)

# Update authentication routes to use security logging
from backend.core.security_logger import security_logger, SecurityEventType

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host
    user_agent = request.headers.get('user-agent', '')
    
    try:
        # Authenticate user
        user = await authenticate_user(db, form_data.username, form_data.password)
        if not user:
            # Log failed authentication
            security_logger.log_authentication_event(
                event_type=SecurityEventType.LOGIN_FAILURE,
                username=form_data.username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="Invalid credentials"
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create session and token
        session_id = session_manager.create_session(user.id, user_agent, ip_address)
        access_token = create_access_token(
            data={"sub": user.username, "session_id": session_id}
        )
        
        # Log successful authentication
        security_logger.log_authentication_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log authentication error
        security_logger.log_authentication_event(
            event_type=SecurityEventType.AUTHENTICATION_ERROR,
            username=form_data.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason=str(e)
        )
        raise HTTPException(status_code=500, detail="Authentication error")
```

### Verification:
```bash
# Test security logging
# Make some requests to trigger logs
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=wrong"

# Check security logs
tail -f logs/security.log
```

---

## 4. Implement Input Sanitization (MEDIUM - 5.5/10)

**Issue**: Limited input sanitization beyond basic validation  
**Risk**: Data corruption, injection attacks, stored XSS  
**Agent**: `backend-fastapi-refactorer`  

### Implementation Steps:

**Step 1: Create comprehensive input sanitizer**
```python
# backend/core/input_sanitizer.py
import re
import html
import bleach
from typing import Any, Dict, List, Union
import json
from urllib.parse import quote, unquote

class InputSanitizer:
    # Allowed HTML tags for rich text fields
    ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'code', 'pre', 'br', 'p']
    ALLOWED_ATTRIBUTES = {'*': ['class']}
    
    # Dangerous patterns to remove
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'data:text/html',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"('|(\\'))",
        r"(;|\|)",
        r"(exec|execute|sp_|xp_)",
        r"(union\s+select|insert\s+into|update\s+set|delete\s+from)",
        r"(drop\s+table|create\s+table|alter\s+table)",
        r"(--|\#|/\*|\*/)",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value) if value is not None else ""
        
        # Remove null bytes and control characters
        value = cls._remove_control_characters(value)
        
        # Handle HTML content
        if allow_html:
            # Use bleach to sanitize HTML
            value = bleach.clean(
                value,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )
        else:
            # Escape HTML for plain text
            value = html.escape(value)
        
        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Normalize whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        
        return value
    
    @classmethod
    def sanitize_sql_string(cls, value: str) -> str:
        """Sanitize string for SQL safety"""
        if not isinstance(value, str):
            return str(value) if value is not None else ""
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous SQL pattern detected")
        
        # Escape single quotes by doubling them
        value = value.replace("'", "''")
        
        return value
    
    @classmethod
    def _remove_control_characters(cls, value: str) -> str:
        """Remove control characters except common whitespace"""
        # Allow tab, newline, and carriage return
        allowed_control_chars = {0x09, 0x0A, 0x0D}
        
        return ''.join(
            char for char in value 
            if ord(char) >= 32 or ord(char) in allowed_control_chars
        )
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            return "unnamed_file"
        
        # Remove path separators and dangerous characters
        dangerous_chars = r'[<>:"/\\|?*\x00-\x1f]'
        filename = re.sub(dangerous_chars, '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 250 - len(ext) - 1 if ext else 250
            filename = name[:max_name_length] + ('.' + ext if ext else '')
        
        # Ensure it's not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
    
    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """Sanitize and validate email address"""
        if not isinstance(email, str):
            raise ValueError("Email must be a string")
        
        email = email.strip().lower()
        
        # Basic email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        # Additional security checks
        if len(email) > 254:  # RFC 5321 limit
            raise ValueError("Email address too long")
        
        return email
    
    @classmethod
    def sanitize_json_string(cls, json_str: str) -> str:
        """Sanitize JSON string"""
        try:
            # Parse JSON to validate structure
            parsed = json.loads(json_str)
            
            # Recursively sanitize string values
            sanitized = cls._sanitize_json_object(parsed)
            
            # Convert back to string
            return json.dumps(sanitized)
            
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid JSON: {e}")
    
    @classmethod
    def _sanitize_json_object(cls, obj: Any) -> Any:
        """Recursively sanitize JSON object"""
        if isinstance(obj, dict):
            return {
                cls.sanitize_string(str(key)): cls._sanitize_json_object(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [cls._sanitize_json_object(item) for item in obj]
        elif isinstance(obj, str):
            return cls.sanitize_string(obj)
        else:
            return obj
    
    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """Sanitize URL"""
        if not isinstance(url, str):
            raise ValueError("URL must be a string")
        
        url = url.strip()
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                raise ValueError(f"Dangerous URL protocol: {protocol}")
        
        # Ensure it starts with http or https for external URLs
        if url and not url.startswith(('http://', 'https://', '/', '#')):
            url = 'http://' + url
        
        return url

class SanitizedModel:
    """Base class for models with automatic input sanitization"""
    
    def __init__(self, **data):
        # Apply sanitization to string fields
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                # Determine sanitization method based on field name
                if 'email' in field_name.lower():
                    data[field_name] = InputSanitizer.sanitize_email(field_value)
                elif 'filename' in field_name.lower() or 'file' in field_name.lower():
                    data[field_name] = InputSanitizer.sanitize_filename(field_value)
                elif 'url' in field_name.lower() or 'link' in field_name.lower():
                    data[field_name] = InputSanitizer.sanitize_url(field_value)
                elif 'description' in field_name.lower() or 'content' in field_name.lower():
                    # Allow limited HTML in content fields
                    data[field_name] = InputSanitizer.sanitize_string(field_value, allow_html=True)
                else:
                    # Plain text sanitization
                    data[field_name] = InputSanitizer.sanitize_string(field_value)
        
        super().__init__(**data)
```

**Step 2: Apply sanitization to Pydantic models**
```python
# backend/api/schemas.py
from backend.core.input_sanitizer import InputSanitizer, SanitizedModel

class SecurePromptCreate(SanitizedModel, BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    
    @validator('name')
    def sanitize_name(cls, v):
        return InputSanitizer.sanitize_string(v)
    
    @validator('description')
    def sanitize_description(cls, v):
        if v:
            return InputSanitizer.sanitize_string(v, allow_html=True)
        return v
    
    @validator('content')
    def sanitize_content(cls, v):
        return InputSanitizer.sanitize_string(v, allow_html=True)

class SecureUserCreate(SanitizedModel, BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(...)
    password: str = Field(..., min_length=12)
    
    @validator('username')
    def sanitize_username(cls, v):
        # Username should only contain safe characters
        sanitized = InputSanitizer.sanitize_string(v)
        if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return sanitized
    
    @validator('email')
    def sanitize_email(cls, v):
        return InputSanitizer.sanitize_email(v)
```

### Verification:
```python
# Test input sanitization
from backend.core.input_sanitizer import InputSanitizer

# Test XSS protection
malicious_input = '<script>alert("XSS")</script>Hello'
sanitized = InputSanitizer.sanitize_string(malicious_input)
assert '<script>' not in sanitized

# Test SQL injection protection
try:
    InputSanitizer.sanitize_sql_string("'; DROP TABLE users; --")
    assert False, "Should have raised ValueError"
except ValueError:
    pass  # Expected

print("Input sanitization tests passed")
```

---

## 5. Implement Secure Error Handling (MEDIUM - 5.0/10)

**Issue**: Error messages may leak sensitive information  
**Risk**: Information disclosure, system enumeration  
**Agent**: `backend-fastapi-refactorer`  

### Implementation Steps:

**Step 1: Create secure error handling system**
```python
# backend/core/error_handlers.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import traceback
import uuid
from typing import Dict, Any
from backend.config import settings
from backend.core.security_logger import security_logger, SecurityEventType

class SecureErrorHandler:
    def __init__(self):
        self.error_registry = {}  # Store error details for debugging
    
    async def handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions securely"""
        
        # Generate error ID for tracking
        error_id = str(uuid.uuid4())
        
        # Log security-relevant errors
        if exc.status_code in [401, 403, 429]:
            security_logger.log_security_event(
                event_type=SecurityEventType.AUTHORIZATION_ERROR,
                ip_address=request.client.host,
                user_agent=request.headers.get('user-agent'),
                resource=str(request.url),
                action=request.method,
                result="failure",
                risk_level="medium",
                details={
                    "status_code": exc.status_code,
                    "error_id": error_id
                }
            )
        
        # Determine response based on environment
        if settings.ENVIRONMENT == "production":
            # Generic error messages for production
            safe_detail = self._get_safe_error_message(exc.status_code)
            response_data = {
                "detail": safe_detail,
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Detailed errors for development
            response_data = {
                "detail": str(exc.detail),
                "status_code": exc.status_code,
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Store full error details for internal use
        self.error_registry[error_id] = {
            "exception": str(exc),
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response_data
        )
    
    async def handle_validation_error(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors"""
        
        error_id = str(uuid.uuid4())
        
        if settings.ENVIRONMENT == "production":
            # Generic validation error message
            response_data = {
                "detail": "Invalid request data",
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Detailed validation errors for development
            response_data = {
                "detail": "Validation error",
                "errors": exc.errors(),
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Log validation errors (might indicate attack attempts)
        self.error_registry[error_id] = {
            "exception": str(exc),
            "errors": exc.errors(),
            "path": str(request.url),
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return JSONResponse(
            status_code=422,
            content=response_data
        )
    
    async def handle_general_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions"""
        
        error_id = str(uuid.uuid4())
        
        # Log the full exception for debugging
        full_traceback = traceback.format_exc()
        
        # Store detailed error information
        self.error_registry[error_id] = {
            "exception": str(exc),
            "exception_type": type(exc).__name__,
            "traceback": full_traceback,
            "path": str(request.url),
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log security event for unexpected errors
        security_logger.log_security_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent'),
            resource=str(request.url),
            action="system_error",
            result="failure",
            risk_level="medium",
            details={
                "error_id": error_id,
                "exception_type": type(exc).__name__
            }
        )
        
        # Generic error response for production
        response_data = {
            "detail": "Internal server error",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if settings.ENVIRONMENT == "development":
            response_data.update({
                "exception": str(exc),
                "exception_type": type(exc).__name__
            })
        
        return JSONResponse(
            status_code=500,
            content=response_data
        )
    
    def _get_safe_error_message(self, status_code: int) -> str:
        """Get safe error messages for production"""
        safe_messages = {
            400: "Bad request",
            401: "Authentication required",
            403: "Access denied", 
            404: "Resource not found",
            405: "Method not allowed",
            409: "Conflict occurred",
            422: "Invalid request data",
            429: "Too many requests",
            500: "Internal server error",
            502: "Service unavailable",
            503: "Service temporarily unavailable"
        }
        
        return safe_messages.get(status_code, "An error occurred")
    
    def get_error_details(self, error_id: str) -> Dict[str, Any]:
        """Get detailed error information for debugging"""
        return self.error_registry.get(error_id)

# Global error handler
secure_error_handler = SecureErrorHandler()
```

**Step 2: Register error handlers with FastAPI**
```python
# backend/main.py
from backend.core.error_handlers import secure_error_handler

# Register error handlers
app.add_exception_handler(HTTPException, secure_error_handler.handle_http_exception)
app.add_exception_handler(RequestValidationError, secure_error_handler.handle_validation_error)
app.add_exception_handler(Exception, secure_error_handler.handle_general_exception)

# Add endpoint for error details (admin only)
@app.get("/admin/errors/{error_id}")
async def get_error_details(
    error_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get detailed error information for debugging"""
    error_details = secure_error_handler.get_error_details(error_id)
    if not error_details:
        raise HTTPException(status_code=404, detail="Error not found")
    
    return error_details
```

### Verification:
```bash
# Test secure error handling
# Test 404 error
curl http://localhost:8001/api/nonexistent
# Expected: Generic error message in production

# Test validation error
curl -X POST http://localhost:8001/api/prompts \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'
# Expected: Generic validation error in production
```

---

## 📊 Medium Priority Fixes Progress Tracking

Track completion of each medium-priority fix:

- [ ] **Rate Limiting**: API endpoints protected against abuse
- [ ] **Session Management**: Secure session handling implemented
- [ ] **Security Logging**: Comprehensive audit logging system
- [ ] **Input Sanitization**: Content sanitization and validation
- [ ] **Error Handling**: Secure error responses and logging
- [ ] **File Security**: Enhanced file upload validation
- [ ] **Network Security**: Internal network segmentation
- [ ] **Backup Security**: Encrypted backup procedures
- [ ] **Monitoring Setup**: Security monitoring dashboard
- [ ] **Compliance Logging**: Regulatory compliance tracking
- [ ] **Performance Security**: DoS protection measures
- [ ] **API Documentation**: Security-focused API docs
- [ ] **Penetration Testing**: Security testing framework

## 🎯 Success Criteria

- **Security Score**: 75%+ on security assessment tools
- **Logging Coverage**: 95%+ of security events logged
- **Response Time**: <200ms degradation from security measures
- **False Positive Rate**: <5% for security monitoring alerts

## 🔍 Final Security Validation

After completing medium priority fixes:

1. **Run security scanners**: OWASP ZAP, Nessus, or similar
2. **Conduct code review**: Focus on security implementations
3. **Test all fixes**: Verify each security control works as expected
4. **Performance testing**: Ensure security doesn't impact performance significantly
5. **Documentation**: Update security documentation and runbooks

---

**Next Steps**: After completing medium priority fixes, proceed to [Implementation Guide](implementation-guide.md) for deployment and testing procedures.
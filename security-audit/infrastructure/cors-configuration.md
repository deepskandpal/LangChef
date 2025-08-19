# Infrastructure CORS Configuration Security Audit

**Component**: Cross-Origin Resource Sharing (CORS) Security  
**Priority**: 🔴 CRITICAL  
**Agent Assignment**: `backend-fastapi-refactorer`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Overly Permissive CORS Configuration (CRITICAL - 9.0/10)

**File**: `/backend/main.py:19-27`  
**Issue**: Wildcard CORS configuration allows all origins in production

```python
# CRITICAL VULNERABILITY:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows ALL origins - critical security flaw
    allow_credentials=True,  # With credentials + wildcard = security breach
    allow_methods=["*"],  # All HTTP methods allowed
    allow_headers=["*"],   # All headers allowed
)
```

**Risk**:
- Complete bypass of same-origin policy protection
- Enables credential theft from any malicious website
- CSRF attacks from any origin with full credential access
- Data exfiltration to unauthorized domains
- Session hijacking through cross-origin requests

### 2. CORS Credentials with Wildcard Origins (CRITICAL - 9.5/10)

**File**: `/backend/main.py:22`  
**Issue**: `allow_credentials=True` combined with `allow_origins=["*"]` is forbidden by CORS spec

```python
# FORBIDDEN COMBINATION:
allow_origins=["*"],      # Wildcard origins
allow_credentials=True,   # Allow credentials
# This combination is rejected by modern browsers but creates security vulnerabilities
```

**Risk**:
- Violates CORS specification security model
- Potential for credential theft in older browsers
- Circumvention of browser security protections
- Complete exposure of authenticated API endpoints

### 3. Unrestricted HTTP Methods (HIGH - 7.5/10)

**File**: `/backend/main.py:24`  
**Issue**: All HTTP methods allowed without restriction

```python
# SECURITY ISSUE:
allow_methods=["*"],  # Allows dangerous methods like PUT, DELETE, PATCH
```

**Risk**:
- Unrestricted access to destructive operations (DELETE, PUT)
- Potential for data manipulation from unauthorized origins
- Admin operations accessible cross-origin
- No method-based access control

### 4. Unrestricted Headers (HIGH - 7.0/10)

**File**: `/backend/main.py:25`  
**Issue**: All headers allowed without validation

```python
# SECURITY ISSUE:
allow_headers=["*"],  # Allows any custom headers
```

**Risk**:
- Custom authentication headers from malicious sites
- Bypassing of security headers validation
- Header injection attacks
- Information disclosure through custom headers

### 5. No Origin Validation or Allowlisting (HIGH - 8.0/10)

**File**: `/backend/main.py` (missing origin validation)  
**Issue**: No mechanism to validate or restrict specific origins

```python
# MISSING SECURITY MEASURES:
# - No environment-based origin configuration
# - No origin validation logic
# - No subdomain restrictions
# - No protocol restrictions (HTTP vs HTTPS)
```

**Risk**:
- Any website can make requests to the API
- No differentiation between development and production origins
- Subdomain takeover attacks can bypass restrictions
- Mixed content attacks (HTTP to HTTPS)

### 6. Missing Preflight Request Handling (MEDIUM - 6.0/10)

**File**: `/backend/main.py` (incomplete CORS configuration)  
**Issue**: No specific handling for preflight requests or custom headers

```python
# MISSING CONFIGURATIONS:
# - max_age for preflight caching
# - Specific exposed headers
# - Preflight request validation
# - Custom origin verification
```

**Risk**:
- Unnecessary preflight requests impact performance
- Potential for race conditions in preflight handling
- Missing security validations in OPTIONS requests

## 🔧 Remediation Steps

### Fix 1: Implement Environment-Specific CORS Configuration

**Update backend/main.py with secure CORS**:

```python
# main.py (Updated with secure CORS)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from urllib.parse import urlparse

from backend.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="LangChef API", version="1.0.0")

class SecureCORSManager:
    def __init__(self):
        self.allowed_origins = self._get_allowed_origins()
        self.allowed_methods = self._get_allowed_methods()
        self.allowed_headers = self._get_allowed_headers()
        self.expose_headers = self._get_expose_headers()
        
    def _get_allowed_origins(self) -> List[str]:
        """Get allowed origins based on environment"""
        origins = []
        
        if settings.ENVIRONMENT == "development":
            # Development origins
            origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001"
            ]
            
        elif settings.ENVIRONMENT == "staging":
            # Staging origins
            origins = [
                "https://staging.langchef.com",
                "https://staging-app.langchef.com"
            ]
            
        elif settings.ENVIRONMENT == "production":
            # Production origins - strictly controlled
            origins = [
                "https://langchef.com",
                "https://app.langchef.com",
                "https://www.langchef.com"
            ]
            
        # Add custom origins from environment
        custom_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        for origin in custom_origins:
            origin = origin.strip()
            if origin and self._validate_origin(origin):
                origins.append(origin)
                
        logger.info(f"CORS allowed origins: {origins}")
        return origins
    
    def _validate_origin(self, origin: str) -> bool:
        """Validate origin URL format and security"""
        try:
            parsed = urlparse(origin)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"Invalid origin format: {origin}")
                return False
                
            # Production must use HTTPS
            if settings.ENVIRONMENT == "production" and parsed.scheme != "https":
                logger.warning(f"Production origin must use HTTPS: {origin}")
                return False
                
            # Check for suspicious patterns
            suspicious_patterns = [
                "javascript:",
                "data:",
                "file:",
                "ftp:",
                "localhost" if settings.ENVIRONMENT == "production" else None
            ]
            
            for pattern in suspicious_patterns:
                if pattern and pattern in origin.lower():
                    logger.warning(f"Suspicious origin blocked: {origin}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Origin validation error for {origin}: {e}")
            return False
    
    def _get_allowed_methods(self) -> List[str]:
        """Get allowed HTTP methods"""
        if settings.ENVIRONMENT == "development":
            return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
        else:
            # Restrict methods in production
            return ["GET", "POST", "PUT", "OPTIONS", "HEAD"]
    
    def _get_allowed_headers(self) -> List[str]:
        """Get allowed headers"""
        return [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRFToken",
            "Cache-Control"
        ]
    
    def _get_expose_headers(self) -> List[str]:
        """Get headers to expose to client"""
        return [
            "Content-Length",
            "Content-Type",
            "X-Total-Count",
            "X-RateLimit-Remaining"
        ]
    
    def validate_request_origin(self, origin: str) -> bool:
        """Validate incoming request origin"""
        if not origin:
            return False
            
        # Check against allowed origins
        if origin in self.allowed_origins:
            return True
            
        # Log suspicious origin attempts
        logger.warning(f"Request from unauthorized origin blocked: {origin}")
        return False

# Initialize CORS manager
cors_manager = SecureCORSManager()

# Configure CORS middleware with security
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_manager.allowed_origins,  # Specific origins only
    allow_credentials=True,  # Safe with specific origins
    allow_methods=cors_manager.allowed_methods,  # Limited methods
    allow_headers=cors_manager.allowed_headers,  # Specific headers only
    expose_headers=cors_manager.expose_headers,  # Limited exposed headers
    max_age=3600,  # Cache preflight for 1 hour
)

# Add origin validation middleware
from fastapi import Request, HTTPException

@app.middleware("http")
async def validate_cors_origin(request: Request, call_next):
    """Additional CORS origin validation"""
    origin = request.headers.get("origin")
    
    # Skip validation for same-origin requests
    if not origin:
        return await call_next(request)
    
    # Validate origin for CORS requests
    if not cors_manager.validate_request_origin(origin):
        logger.warning(f"CORS request blocked from unauthorized origin: {origin}")
        raise HTTPException(
            status_code=403,
            detail="Origin not allowed"
        )
    
    response = await call_next(request)
    
    # Add additional security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY" 
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response
```

### Fix 2: Implement Dynamic Origin Configuration

**Create CORS configuration management**:

```python
# backend/core/cors_config.py
from typing import List, Dict, Set
import re
import os
from urllib.parse import urlparse
from backend.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

class DynamicCORSConfig:
    def __init__(self):
        self.allowed_origin_patterns: List[re.Pattern] = []
        self.blocked_origins: Set[str] = set()
        self.origin_cache: Dict[str, bool] = {}
        self.max_cache_size = 1000
        
        self._load_configuration()
    
    def _load_configuration(self):
        """Load CORS configuration from environment and files"""
        
        # Load allowed origin patterns
        patterns = self._get_origin_patterns()
        self.allowed_origin_patterns = [
            re.compile(pattern) for pattern in patterns
        ]
        
        # Load blocked origins
        self.blocked_origins = self._get_blocked_origins()
        
        logger.info(f"Loaded {len(self.allowed_origin_patterns)} origin patterns")
        logger.info(f"Loaded {len(self.blocked_origins)} blocked origins")
    
    def _get_origin_patterns(self) -> List[str]:
        """Get allowed origin regex patterns"""
        patterns = []
        
        if settings.ENVIRONMENT == "development":
            patterns = [
                r"^http://localhost:\d+$",
                r"^http://127\.0\.0\.1:\d+$",
                r"^http://.*\.localhost:\d+$"
            ]
        elif settings.ENVIRONMENT == "staging":
            patterns = [
                r"^https://.*\.staging\.langchef\.com$",
                r"^https://staging\.langchef\.com$"
            ]
        elif settings.ENVIRONMENT == "production":
            patterns = [
                r"^https://langchef\.com$",
                r"^https://app\.langchef\.com$",
                r"^https://www\.langchef\.com$",
                r"^https://.*\.langchef\.com$"  # Subdomains (be careful with this)
            ]
        
        # Add custom patterns from environment
        custom_patterns = os.getenv("CORS_ORIGIN_PATTERNS", "").split(",")
        for pattern in custom_patterns:
            pattern = pattern.strip()
            if pattern:
                patterns.append(pattern)
        
        return patterns
    
    def _get_blocked_origins(self) -> Set[str]:
        """Get explicitly blocked origins"""
        blocked = set()
        
        # Common malicious or problematic origins
        default_blocked = [
            "null",
            "file://",
            "data:",
            "javascript:",
            "vbscript:",
        ]
        blocked.update(default_blocked)
        
        # Add custom blocked origins
        custom_blocked = os.getenv("CORS_BLOCKED_ORIGINS", "").split(",")
        for origin in custom_blocked:
            origin = origin.strip()
            if origin:
                blocked.add(origin)
        
        return blocked
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed with caching"""
        
        if not origin:
            return False
        
        # Check cache first
        if origin in self.origin_cache:
            return self.origin_cache[origin]
        
        # Check blocked origins
        if origin in self.blocked_origins:
            self._cache_result(origin, False)
            return False
        
        # Validate origin format
        if not self._validate_origin_format(origin):
            self._cache_result(origin, False)
            return False
        
        # Check against patterns
        allowed = any(
            pattern.match(origin) for pattern in self.allowed_origin_patterns
        )
        
        self._cache_result(origin, allowed)
        
        if not allowed:
            logger.warning(f"Origin rejected: {origin}")
        
        return allowed
    
    def _validate_origin_format(self, origin: str) -> bool:
        """Validate origin URL format"""
        try:
            parsed = urlparse(origin)
            
            # Must have valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check scheme
            allowed_schemes = ["http", "https"]
            if parsed.scheme not in allowed_schemes:
                return False
            
            # Production must use HTTPS (except localhost)
            if (settings.ENVIRONMENT == "production" and 
                parsed.scheme == "http" and 
                "localhost" not in parsed.netloc and
                "127.0.0.1" not in parsed.netloc):
                return False
            
            # Check for suspicious characters
            if any(char in origin for char in ["<", ">", '"', "'", "&"]):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _cache_result(self, origin: str, allowed: bool):
        """Cache origin validation result"""
        # Prevent cache from growing too large
        if len(self.origin_cache) >= self.max_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self.origin_cache.keys())[:100]
            for key in oldest_keys:
                del self.origin_cache[key]
        
        self.origin_cache[origin] = allowed
    
    def add_allowed_origin(self, origin: str):
        """Dynamically add an allowed origin"""
        if self._validate_origin_format(origin):
            pattern = re.escape(origin) + "$"
            self.allowed_origin_patterns.append(re.compile(f"^{pattern}"))
            self.origin_cache[origin] = True
            logger.info(f"Added allowed origin: {origin}")
    
    def block_origin(self, origin: str):
        """Dynamically block an origin"""
        self.blocked_origins.add(origin)
        self.origin_cache[origin] = False
        logger.info(f"Blocked origin: {origin}")
    
    def get_stats(self) -> Dict:
        """Get CORS statistics"""
        return {
            "allowed_patterns": len(self.allowed_origin_patterns),
            "blocked_origins": len(self.blocked_origins),
            "cache_size": len(self.origin_cache),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        # This would require tracking cache hits/misses
        # Simplified implementation
        return 0.0

# Global instance
dynamic_cors = DynamicCORSConfig()
```

### Fix 3: Implement CORS Security Monitoring

```python
# backend/core/cors_monitor.py
from typing import Dict, List
import time
from collections import defaultdict, deque
from backend.core.logging import get_logger

logger = get_logger(__name__)

class CORSSecurityMonitor:
    def __init__(self):
        self.request_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_attempts: Dict[str, int] = defaultdict(int)
        self.suspicious_patterns: List[str] = [
            "script", "eval", "javascript:", "data:", "vbscript:"
        ]
        self.alert_threshold = 10  # Alert after 10 blocked attempts
        
    def log_cors_request(self, origin: str, allowed: bool, request_path: str):
        """Log CORS request for monitoring"""
        timestamp = time.time()
        
        self.request_counts[origin].append({
            "timestamp": timestamp,
            "allowed": allowed,
            "path": request_path
        })
        
        if not allowed:
            self.blocked_attempts[origin] += 1
            
            # Check for suspicious patterns
            if any(pattern in origin.lower() for pattern in self.suspicious_patterns):
                logger.warning(f"Suspicious CORS origin detected: {origin}")
                self._trigger_security_alert(origin, "suspicious_pattern")
            
            # Check for repeated attempts
            if self.blocked_attempts[origin] >= self.alert_threshold:
                logger.error(f"Multiple CORS blocks from origin: {origin}")
                self._trigger_security_alert(origin, "repeated_attempts")
    
    def _trigger_security_alert(self, origin: str, alert_type: str):
        """Trigger security alert for suspicious CORS activity"""
        alert_data = {
            "type": "cors_security_alert",
            "alert_subtype": alert_type,
            "origin": origin,
            "blocked_count": self.blocked_attempts[origin],
            "timestamp": time.time()
        }
        
        logger.error(f"CORS Security Alert: {alert_data}")
        
        # In production, send to monitoring service
        # monitoring_service.send_alert(alert_data)
    
    def get_origin_stats(self, origin: str, time_window: int = 3600) -> Dict:
        """Get statistics for a specific origin"""
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        requests = self.request_counts[origin]
        recent_requests = [
            req for req in requests 
            if req["timestamp"] > cutoff_time
        ]
        
        allowed_count = sum(1 for req in recent_requests if req["allowed"])
        blocked_count = sum(1 for req in recent_requests if not req["allowed"])
        
        return {
            "origin": origin,
            "time_window": time_window,
            "total_requests": len(recent_requests),
            "allowed_requests": allowed_count,
            "blocked_requests": blocked_count,
            "block_ratio": blocked_count / len(recent_requests) if recent_requests else 0
        }

# Global monitor instance
cors_monitor = CORSSecurityMonitor()

# Integration with FastAPI middleware
@app.middleware("http")
async def cors_monitoring_middleware(request: Request, call_next):
    """Monitor CORS requests for security"""
    origin = request.headers.get("origin")
    
    if origin:
        allowed = dynamic_cors.is_origin_allowed(origin)
        cors_monitor.log_cors_request(origin, allowed, request.url.path)
        
        if not allowed:
            raise HTTPException(status_code=403, detail="Origin not allowed")
    
    return await call_next(request)
```

### Fix 4: Environment-Specific Configuration

**Create environment configuration files**:

```bash
# .env.development
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ORIGIN_PATTERNS=^http://localhost:\d+$,^http://127\.0\.0\.1:\d+$
CORS_BLOCKED_ORIGINS=
ENVIRONMENT=development

# .env.staging  
CORS_ALLOWED_ORIGINS=https://staging.langchef.com
CORS_ORIGIN_PATTERNS=^https://.*\.staging\.langchef\.com$
CORS_BLOCKED_ORIGINS=
ENVIRONMENT=staging

# .env.production
CORS_ALLOWED_ORIGINS=https://langchef.com,https://app.langchef.com
CORS_ORIGIN_PATTERNS=^https://langchef\.com$,^https://app\.langchef\.com$
CORS_BLOCKED_ORIGINS=
ENVIRONMENT=production
```

## ✅ Verification Methods

### Test CORS Configuration:
```bash
# Test unauthorized origin
curl -H "Origin: https://malicious.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8001/api/prompts

# Should return 403 Forbidden

# Test authorized origin
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8001/api/prompts

# Should return 200 with CORS headers
```

### Browser Testing:
```javascript
// Test from browser console
fetch('http://localhost:8001/api/prompts', {
    method: 'GET',
    credentials: 'include'
}).then(response => {
    console.log('CORS test successful:', response.status);
}).catch(error => {
    console.log('CORS test failed:', error);
});
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Replace wildcard CORS with environment-specific origins
- [ ] **Fix 2**: Implement dynamic origin validation and caching
- [ ] **Fix 3**: Add CORS security monitoring and alerting
- [ ] **Fix 4**: Create environment-based configuration system
- [ ] **Fix 5**: Add origin pattern matching for subdomains
- [ ] **Fix 6**: Implement CORS request rate limiting
- [ ] **Testing**: CORS security test suite
- [ ] **Documentation**: CORS configuration guidelines

## 🔗 Dependencies

- Environment configuration system
- Security monitoring and alerting
- Request logging and analytics
- Rate limiting implementation

## 🚨 Critical Actions Required

1. **Remove wildcard CORS origins immediately - critical security flaw**
2. **Implement environment-specific origin allowlisting**
3. **Add origin validation and security monitoring**
4. **Test CORS configuration against common attack vectors**
5. **Set up alerting for suspicious CORS activity**
6. **Document approved origins for each environment**
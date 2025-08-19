# Infrastructure Security Headers Audit

**Component**: HTTP Security Headers Configuration  
**Priority**: 🟡 HIGH  
**Agent Assignment**: `security-sweeper`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Missing Critical Security Headers (HIGH - 8.0/10)

**Files**: Backend and Frontend HTTP responses (observed from application behavior)  
**Issue**: No security headers implemented to protect against common attacks

```http
# MISSING SECURITY HEADERS:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# Content-Security-Policy: [comprehensive policy]
# Referrer-Policy: strict-origin-when-cross-origin
# Permissions-Policy: [feature restrictions]
```

**Risk**:
- MIME type confusion attacks
- Clickjacking and frame embedding attacks  
- Cross-site scripting in older browsers
- Insecure HTTP connections to sensitive resources
- Information leakage through referrer headers
- Unauthorized access to browser features

### 2. No Content Security Policy (CSP) Implementation (HIGH - 8.5/10)

**Files**: Missing CSP headers in all responses  
**Issue**: No CSP to prevent XSS, code injection, and unauthorized resource loading

```http
# MISSING CSP HEADER:
Content-Security-Policy: default-src 'self'; 
                        script-src 'self' 'unsafe-inline';
                        style-src 'self' 'unsafe-inline';
                        [... comprehensive policy needed]
```

**Risk**:
- Cross-site scripting attacks
- Code injection from external sources
- Unauthorized data exfiltration
- Malicious script execution
- Inline script and style vulnerabilities

### 3. Missing HSTS (HTTP Strict Transport Security) (HIGH - 7.5/10)

**Files**: HTTPS configuration missing HSTS headers  
**Issue**: No enforcement of HTTPS connections

```http
# MISSING HSTS HEADER:
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Risk**:
- Man-in-the-middle attacks on first visit
- Protocol downgrade attacks
- Cookie theft over insecure connections
- Session hijacking via HTTP

### 4. Insecure Cookie Configuration (HIGH - 7.0/10)

**Files**: Session and authentication cookie settings  
**Issue**: Cookies lack security attributes

```python
# INSECURE COOKIE PATTERNS:
# Set-Cookie: session_id=abc123
# MISSING: Secure flag for HTTPS
# MISSING: HttpOnly flag to prevent XSS
# MISSING: SameSite attribute for CSRF protection
# MISSING: proper Domain and Path restrictions
```

**Risk**:
- Session cookies transmitted over HTTP
- XSS attacks can steal authentication cookies
- CSRF attacks via cross-site cookie inclusion
- Cookie theft through insecure domains

### 5. Missing Permissions Policy (MEDIUM - 6.0/10)

**Files**: No Permissions Policy (Feature Policy) headers  
**Issue**: No restrictions on browser feature access

```http
# MISSING PERMISSIONS POLICY:
Permissions-Policy: camera=(), microphone=(), geolocation=(), 
                   payment=(), usb=(), magnetometer=(),
                   gyroscope=(), accelerometer=()
```

**Risk**:
- Unauthorized access to device features
- Malicious scripts accessing camera/microphone
- Privacy violations through sensor access
- Resource abuse through unrestricted API access

### 6. Information Disclosure Headers (MEDIUM - 5.5/10)

**Files**: Server and framework headers potentially exposed  
**Issue**: Headers reveal internal technology stack

```http
# INFORMATION DISCLOSURE:
Server: uvicorn/0.23.2
X-Powered-By: FastAPI
# These headers reveal technology versions and frameworks
```

**Risk**:
- Technology stack enumeration for attackers
- Version-specific vulnerability targeting
- Framework-specific attack vectors
- Infrastructure reconnaissance assistance

### 7. Missing Cache Control Security (LOW - 4.5/10)

**Files**: API responses without proper cache control  
**Issue**: Sensitive data may be cached inappropriately

```http
# INSECURE CACHE PATTERNS:
# No Cache-Control headers on sensitive endpoints
# No Pragma: no-cache for legacy browsers
# No Expires header for explicit cache prevention
```

**Risk**:
- Sensitive data cached in browser/proxy
- Authentication tokens cached locally
- Personal information in browser cache
- Data persistence after logout

## 🔧 Remediation Steps

### Fix 1: Implement Comprehensive Security Headers Middleware

**Create security headers middleware**:

```python
# backend/middleware/security_headers.py
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import time
from backend.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

class SecurityHeadersMiddleware:
    def __init__(self):
        self.security_headers = self._build_security_headers()
        self.csp_policy = self._build_csp_policy()
        
    def _build_security_headers(self) -> Dict[str, str]:
        """Build comprehensive security headers"""
        headers = {}
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable XSS filtering (legacy browsers)
        headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy: Control referrer information
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # X-DNS-Prefetch-Control: Disable DNS prefetching
        headers["X-DNS-Prefetch-Control"] = "off"
        
        # X-Download-Options: Prevent file download exploits (IE)
        headers["X-Download-Options"] = "noopen"
        
        # X-Permitted-Cross-Domain-Policies: Restrict cross-domain access
        headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Content Security Policy
        headers["Content-Security-Policy"] = self._build_csp_policy()
        
        # Permissions Policy (Feature Policy)
        headers["Permissions-Policy"] = self._build_permissions_policy()
        
        # HSTS (only for HTTPS)
        if settings.ENVIRONMENT == "production":
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Remove information disclosure headers
        headers["Server"] = "LangChef"  # Generic server name
        
        return headers
    
    def _build_csp_policy(self) -> str:
        """Build Content Security Policy"""
        if settings.ENVIRONMENT == "development":
            # Relaxed policy for development
            policy_parts = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* 127.0.0.1:*",
                "style-src 'self' 'unsafe-inline' fonts.googleapis.com",
                "font-src 'self' fonts.gstatic.com",
                "img-src 'self' data: https:",
                "connect-src 'self' localhost:* 127.0.0.1:* ws://localhost:* ws://127.0.0.1:*",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "upgrade-insecure-requests"
            ]
        else:
            # Strict policy for production
            policy_parts = [
                "default-src 'self'",
                "script-src 'self' https://fonts.googleapis.com",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https:",
                "connect-src 'self' https://api.langchef.com wss://api.langchef.com",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "upgrade-insecure-requests",
                "block-all-mixed-content"
            ]
        
        return "; ".join(policy_parts)
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy to restrict browser features"""
        permissions = [
            "camera=()",  # Disable camera access
            "microphone=()",  # Disable microphone access
            "geolocation=()",  # Disable location access
            "payment=()",  # Disable payment API
            "usb=()",  # Disable USB API
            "magnetometer=()",  # Disable magnetometer
            "gyroscope=()",  # Disable gyroscope
            "accelerometer=()",  # Disable accelerometer
            "autoplay=()",  # Disable autoplay
            "encrypted-media=()",  # Disable encrypted media
            "fullscreen=(self)",  # Allow fullscreen only for same origin
            "picture-in-picture=()"  # Disable picture-in-picture
        ]
        
        return ", ".join(permissions)
    
    def get_cache_control_headers(self, endpoint: str, is_sensitive: bool = False) -> Dict[str, str]:
        """Get appropriate cache control headers"""
        headers = {}
        
        if is_sensitive or any(path in endpoint for path in ["/auth", "/user", "/profile"]):
            # Sensitive endpoints - no caching
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            })
        elif "/api/" in endpoint:
            # API endpoints - limited caching
            headers.update({
                "Cache-Control": "private, max-age=300",  # 5 minutes
                "Vary": "Authorization, Accept-Encoding"
            })
        else:
            # Static resources - longer caching
            headers.update({
                "Cache-Control": "public, max-age=3600",  # 1 hour
                "Vary": "Accept-Encoding"
            })
        
        return headers

# Middleware function for FastAPI
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    security_middleware = SecurityHeadersMiddleware()
    
    response = await call_next(request)
    
    # Add security headers
    for header, value in security_middleware.security_headers.items():
        response.headers[header] = value
    
    # Add cache control headers
    cache_headers = security_middleware.get_cache_control_headers(
        str(request.url.path)
    )
    for header, value in cache_headers.items():
        response.headers[header] = value
    
    # Log security headers for monitoring
    if settings.ENVIRONMENT == "development":
        logger.debug(f"Security headers applied to {request.url.path}")
    
    return response

# Add to main.py
from backend.middleware.security_headers import add_security_headers

app.middleware("http")(add_security_headers)
```

### Fix 2: Implement Secure Cookie Configuration

```python
# backend/core/secure_cookies.py
from fastapi import Response, Request
from typing import Optional, Dict, Any
import secrets
from datetime import datetime, timedelta
from backend.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

class SecureCookieManager:
    def __init__(self):
        self.cookie_config = self._get_cookie_config()
    
    def _get_cookie_config(self) -> Dict[str, Any]:
        """Get secure cookie configuration"""
        config = {
            "httponly": True,  # Prevent XSS access
            "secure": settings.ENVIRONMENT != "development",  # HTTPS only in prod
            "samesite": "lax",  # CSRF protection
            "max_age": 3600,  # 1 hour default
            "domain": self._get_cookie_domain(),
            "path": "/"
        }
        
        return config
    
    def _get_cookie_domain(self) -> Optional[str]:
        """Get appropriate cookie domain"""
        if settings.ENVIRONMENT == "production":
            return ".langchef.com"  # Subdomains allowed
        elif settings.ENVIRONMENT == "staging":
            return ".staging.langchef.com"
        else:
            return None  # Localhost for development
    
    def set_secure_cookie(
        self, 
        response: Response, 
        name: str, 
        value: str,
        max_age: Optional[int] = None,
        sensitive: bool = False
    ):
        """Set a secure cookie with appropriate security flags"""
        
        config = self.cookie_config.copy()
        
        if max_age is not None:
            config["max_age"] = max_age
        
        # Extra security for sensitive cookies
        if sensitive:
            config["samesite"] = "strict"  # Stricter CSRF protection
            config["secure"] = True  # Always require HTTPS for sensitive cookies
        
        response.set_cookie(name, value, **config)
        
        logger.debug(f"Set secure cookie: {name} (sensitive: {sensitive})")
    
    def set_session_cookie(self, response: Response, session_id: str):
        """Set session cookie with security"""
        self.set_secure_cookie(
            response, 
            "session_id", 
            session_id,
            max_age=3600,  # 1 hour session
            sensitive=True
        )
    
    def set_csrf_token(self, response: Response) -> str:
        """Set CSRF token cookie and return token"""
        csrf_token = secrets.token_urlsafe(32)
        
        self.set_secure_cookie(
            response,
            "csrf_token",
            csrf_token,
            max_age=3600,
            sensitive=True
        )
        
        return csrf_token
    
    def clear_cookie(self, response: Response, name: str):
        """Securely clear a cookie"""
        config = self.cookie_config.copy()
        config["max_age"] = 0
        config["expires"] = datetime.utcnow() - timedelta(days=1)
        
        response.set_cookie(name, "", **config)
        
        logger.debug(f"Cleared cookie: {name}")
    
    def validate_cookie_security(self, request: Request) -> Dict[str, Any]:
        """Validate security of incoming cookies"""
        cookies = request.cookies
        security_report = {
            "secure_cookies": 0,
            "insecure_cookies": 0,
            "issues": []
        }
        
        for cookie_name, cookie_value in cookies.items():
            # Check for potential security issues
            if len(cookie_value) > 4096:  # Cookie too large
                security_report["issues"].append(f"Cookie {cookie_name} too large")
            
            if any(char in cookie_value for char in [";", "\n", "\r"]):
                security_report["issues"].append(f"Cookie {cookie_name} contains dangerous characters")
        
        return security_report

# Global instance
secure_cookies = SecureCookieManager()
```

### Fix 3: Frontend Security Headers Configuration

```javascript
// frontend/nginx/default.conf
server {
    listen 3000;
    server_name localhost;
    
    # Security Headers
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-DNS-Prefetch-Control off always;
    add_header X-Download-Options noopen always;
    add_header X-Permitted-Cross-Domain-Policies none always;
    
    # Content Security Policy
    set $csp_policy "default-src 'self'; ";
    set $csp_policy "${csp_policy}script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; ";
    set $csp_policy "${csp_policy}style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; ";
    set $csp_policy "${csp_policy}font-src 'self' https://fonts.gstatic.com; ";
    set $csp_policy "${csp_policy}img-src 'self' data: https:; ";
    set $csp_policy "${csp_policy}connect-src 'self' https://api.langchef.com wss://api.langchef.com; ";
    set $csp_policy "${csp_policy}object-src 'none'; ";
    set $csp_policy "${csp_policy}base-uri 'self'; ";
    set $csp_policy "${csp_policy}form-action 'self'; ";
    set $csp_policy "${csp_policy}frame-ancestors 'none'; ";
    set $csp_policy "${csp_policy}upgrade-insecure-requests; ";
    set $csp_policy "${csp_policy}block-all-mixed-content";
    
    add_header Content-Security-Policy $csp_policy always;
    
    # Permissions Policy
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=(), autoplay=(), encrypted-media=(), fullscreen=(self), picture-in-picture=()" always;
    
    # HSTS (production only)
    if ($server_name != "localhost") {
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    }
    
    # Hide server information
    server_tokens off;
    
    # Security configurations
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
        
        # Cache control for HTML files
        if ($uri ~* \.(html|htm)$) {
            add_header Cache-Control "no-cache, no-store, must-revalidate";
            add_header Pragma "no-cache";
            add_header Expires "0";
        }
        
        # Cache control for static assets
        if ($uri ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$) {
            add_header Cache-Control "public, max-age=31536000, immutable";
        }
    }
    
    # API proxy with security headers
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Additional security headers for API
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
    }
    
    # Security for file uploads
    location /api/upload/ {
        client_max_body_size 100M;
        proxy_pass http://backend:8000/api/upload/;
        proxy_request_buffering off;
        
        # File upload security headers
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "no-cache" always;
    }
    
    # Block access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ \.(ini|conf|config|log)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

### Fix 4: Security Headers Monitoring and Testing

```python
# backend/core/security_monitor.py
from typing import Dict, List, Set
from fastapi import Request, Response
import time
from backend.core.logging import get_logger

logger = get_logger(__name__)

class SecurityHeadersMonitor:
    def __init__(self):
        self.required_headers = {
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
            "Permissions-Policy"
        }
        self.production_headers = {
            "Strict-Transport-Security"
        }
        self.missing_headers_count = {}
        
    def validate_response_headers(self, response: Response, request_path: str) -> Dict[str, Any]:
        """Validate that security headers are present"""
        missing_headers = set()
        present_headers = set()
        
        # Check required headers
        for header in self.required_headers:
            if header.lower() in [h.lower() for h in response.headers.keys()]:
                present_headers.add(header)
            else:
                missing_headers.add(header)
        
        # Check production-only headers in production
        if settings.ENVIRONMENT == "production":
            for header in self.production_headers:
                if header.lower() not in [h.lower() for h in response.headers.keys()]:
                    missing_headers.add(header)
        
        # Log missing headers
        if missing_headers:
            logger.warning(f"Missing security headers for {request_path}: {missing_headers}")
            
            # Track missing headers
            for header in missing_headers:
                self.missing_headers_count[header] = self.missing_headers_count.get(header, 0) + 1
        
        return {
            "path": request_path,
            "present_headers": list(present_headers),
            "missing_headers": list(missing_headers),
            "security_score": len(present_headers) / len(self.required_headers) * 100
        }
    
    def get_security_report(self) -> Dict[str, Any]:
        """Get security headers report"""
        return {
            "required_headers": list(self.required_headers),
            "production_headers": list(self.production_headers),
            "missing_headers_count": self.missing_headers_count,
            "most_missing_header": max(
                self.missing_headers_count.items(), 
                key=lambda x: x[1]
            )[0] if self.missing_headers_count else None
        }

# Testing utilities
class SecurityHeadersTester:
    @staticmethod
    def test_csp_policy(policy: str) -> List[str]:
        """Test CSP policy for common issues"""
        issues = []
        
        # Check for unsafe directives
        unsafe_patterns = ["'unsafe-inline'", "'unsafe-eval'", "data:", "javascript:"]
        for pattern in unsafe_patterns:
            if pattern in policy:
                issues.append(f"Potentially unsafe CSP directive: {pattern}")
        
        # Check for missing directives
        required_directives = ["default-src", "script-src", "object-src"]
        for directive in required_directives:
            if directive not in policy:
                issues.append(f"Missing CSP directive: {directive}")
        
        # Check for overly permissive policies
        if "'self' *" in policy or "* 'self'" in policy:
            issues.append("Overly permissive CSP policy detected")
        
        return issues
    
    @staticmethod
    def test_hsts_header(hsts_value: str) -> List[str]:
        """Test HSTS header configuration"""
        issues = []
        
        # Parse max-age
        if "max-age=" not in hsts_value:
            issues.append("HSTS missing max-age directive")
        else:
            max_age_str = hsts_value.split("max-age=")[1].split(";")[0]
            try:
                max_age = int(max_age_str)
                if max_age < 31536000:  # Less than 1 year
                    issues.append(f"HSTS max-age too short: {max_age} seconds")
            except ValueError:
                issues.append("Invalid HSTS max-age value")
        
        # Check for includeSubDomains
        if "includeSubDomains" not in hsts_value:
            issues.append("HSTS missing includeSubDomains directive")
        
        return issues

# Global instances
security_monitor = SecurityHeadersMonitor()
security_tester = SecurityHeadersTester()
```

## ✅ Verification Methods

### Test Security Headers:
```bash
# Test security headers
curl -I http://localhost:8001/api/health
# Should include all security headers

# Test CSP
curl -H "Content-Security-Policy-Report-Only: default-src 'self'" \
     http://localhost:8001/api/prompts

# Test HSTS (production)
curl -I https://api.langchef.com/health
# Should include HSTS header
```

### Browser Testing:
```javascript
// Check security headers in browser
fetch('/api/health', {method: 'HEAD'})
    .then(response => {
        console.log('Security Headers:');
        for (let [name, value] of response.headers) {
            if (name.toLowerCase().includes('security') || 
                name.toLowerCase().startsWith('x-') ||
                name.toLowerCase().includes('content-security-policy')) {
                console.log(`${name}: ${value}`);
            }
        }
    });
```

### Security Scanner Testing:
```bash
# Use online security scanner
# https://securityheaders.com/
# https://observatory.mozilla.org/

# Or use automated tools
npm install -g security-headers-check
security-headers-check http://localhost:3000
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Implement comprehensive security headers middleware
- [ ] **Fix 2**: Configure secure cookie management
- [ ] **Fix 3**: Add frontend nginx security headers configuration
- [ ] **Fix 4**: Implement Content Security Policy
- [ ] **Fix 5**: Add HSTS and secure transport configuration
- [ ] **Fix 6**: Create security headers monitoring and testing
- [ ] **Testing**: Security headers test suite
- [ ] **Documentation**: Security headers configuration guide

## 🔗 Dependencies

- Environment configuration system
- Security monitoring and logging
- HTTPS/TLS certificate configuration
- Content Security Policy implementation

## 🚨 Critical Actions Required

1. **Implement security headers middleware immediately**
2. **Configure Content Security Policy to prevent XSS**
3. **Add HSTS headers for HTTPS enforcement**
4. **Secure all cookie configurations with proper flags**
5. **Set up security headers monitoring and alerting**
6. **Test headers configuration against security scanners**
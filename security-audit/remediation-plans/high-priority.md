# High Priority Security Fixes Remediation Plan

**Priority**: 🟡 HIGH (P1)  
**Agent Assignment**: `backend-fastapi-refactorer` + `frontend-react-refactorer`  
**Status**: ❌ Not Started  
**Estimated Time**: 6-8 hours  

## 📋 Overview

These are the 13 high-priority security vulnerabilities that should be addressed after critical fixes are complete. While not immediately exploitable, they create significant security risks that could lead to data breaches or system compromise.

---

## 1. Implement Comprehensive Security Headers (HIGH - 8.0/10)

**Issue**: Missing security headers leave application vulnerable to various attacks  
**Risk**: XSS, clickjacking, MIME confusion, protocol downgrade attacks  
**Agent**: `security-sweeper`  

### Implementation Steps:

**Step 1: Create security headers middleware**
```python
# backend/middleware/security_headers.py
from fastapi import Request, Response
from typing import Dict

class SecurityHeadersMiddleware:
    def __init__(self):
        self.headers = self._build_security_headers()
    
    def _build_security_headers(self) -> Dict[str, str]:
        return {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # XSS protection for legacy browsers
            "X-XSS-Protection": "1; mode=block",
            
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Prevent DNS prefetching
            "X-DNS-Prefetch-Control": "off",
            
            # Content Security Policy
            "Content-Security-Policy": self._build_csp(),
            
            # HSTS for production
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Permissions Policy
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
            
            # Hide server information
            "Server": "LangChef"
        }
    
    def _build_csp(self) -> str:
        """Build Content Security Policy"""
        return "; ".join([
            "default-src 'self'",
            "script-src 'self' https://fonts.googleapis.com", 
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ])

# Add to main.py
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    security_middleware = SecurityHeadersMiddleware()
    for header, value in security_middleware.headers.items():
        response.headers[header] = value
    
    return response

app.middleware("http")(add_security_headers)
```

### Verification:
```bash
# Test security headers
curl -I http://localhost:8001/api/health | grep -E "(X-|Content-Security|Strict-Transport)"
```

---

## 2. Fix Authentication Password Security (HIGH - 7.5/10)

**Issue**: Weak password validation and insecure storage  
**Risk**: Brute force attacks, credential stuffing, password compromise  
**Agent**: `backend-fastapi-refactorer`  

### Implementation Steps:

**Step 1: Implement secure password handling**
```python
# backend/core/password_security.py
import bcrypt
import re
from typing import Dict, List
from datetime import datetime, timedelta

class PasswordSecurity:
    MIN_LENGTH = 12
    MAX_LENGTH = 128
    
    # Password strength requirements
    REQUIREMENTS = {
        'min_length': MIN_LENGTH,
        'require_uppercase': True,
        'require_lowercase': True, 
        'require_digits': True,
        'require_special': True,
        'min_special_chars': 1
    }
    
    # Common weak passwords (should be loaded from file)
    WEAK_PASSWORDS = {
        'password123', 'admin123', 'welcome123', 'changeme',
        'password!', '123456789', 'qwerty123', 'letmein'
    }
    
    @classmethod
    def validate_password_strength(cls, password: str) -> Dict[str, any]:
        """Validate password meets security requirements"""
        issues = []
        
        if len(password) < cls.MIN_LENGTH:
            issues.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        
        if len(password) > cls.MAX_LENGTH:
            issues.append(f"Password must be less than {cls.MAX_LENGTH} characters")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain uppercase letters")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain lowercase letters")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain numbers")
        
        special_chars = re.findall(r'[!@#$%^&*(),.?":{}|<>]', password)
        if len(special_chars) < cls.REQUIREMENTS['min_special_chars']:
            issues.append("Password must contain special characters")
        
        # Check against common weak passwords
        if password.lower() in cls.WEAK_PASSWORDS:
            issues.append("Password is too common")
        
        # Check for repeated characters
        if cls._has_repeated_chars(password):
            issues.append("Password contains too many repeated characters")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'strength_score': cls._calculate_strength_score(password)
        }
    
    @classmethod
    def _has_repeated_chars(cls, password: str) -> bool:
        """Check for excessive character repetition"""
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        return False
    
    @classmethod
    def _calculate_strength_score(cls, password: str) -> int:
        """Calculate password strength score (0-100)"""
        score = 0
        
        # Length bonus
        score += min(25, len(password) * 2)
        
        # Character variety bonus
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        
        # Complexity bonus
        unique_chars = len(set(password))
        if unique_chars >= 8:
            score += 15
        
        # Pattern penalty
        if cls._has_common_patterns(password):
            score -= 20
        
        return max(0, min(100, score))
    
    @classmethod
    def _has_common_patterns(cls, password: str) -> bool:
        """Check for common patterns like 123, abc, qwerty"""
        patterns = [
            '123456789', 'abcdefgh', 'qwertyuiop',
            '987654321', 'zyxwvuts', '0987654321'
        ]
        
        password_lower = password.lower()
        for pattern in patterns:
            for i in range(len(pattern) - 3):
                if pattern[i:i+4] in password_lower:
                    return True
        return False
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using bcrypt"""
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=12)  # Increase rounds for security
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

class PasswordPolicy:
    def __init__(self):
        self.failed_attempts = {}  # In production, use Redis
        self.lockout_threshold = 5
        self.lockout_duration = timedelta(minutes=15)
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is rate limited"""
        if user_id not in self.failed_attempts:
            return True
        
        attempts, last_attempt = self.failed_attempts[user_id]
        
        # Reset if lockout period has passed
        if datetime.utcnow() - last_attempt > self.lockout_duration:
            del self.failed_attempts[user_id]
            return True
        
        return attempts < self.lockout_threshold
    
    def record_failed_attempt(self, user_id: str):
        """Record a failed login attempt"""
        now = datetime.utcnow()
        
        if user_id in self.failed_attempts:
            attempts, _ = self.failed_attempts[user_id]
            self.failed_attempts[user_id] = (attempts + 1, now)
        else:
            self.failed_attempts[user_id] = (1, now)
    
    def reset_failed_attempts(self, user_id: str):
        """Reset failed attempts on successful login"""
        if user_id in self.failed_attempts:
            del self.failed_attempts[user_id]
```

**Step 2: Update user registration and login**
```python
# backend/api/routes/auth.py
from backend.core.password_security import PasswordSecurity, PasswordPolicy

password_policy = PasswordPolicy()

@router.post("/register")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Validate password strength
    password_check = PasswordSecurity.validate_password_strength(user_data.password)
    if not password_check['is_valid']:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Password does not meet security requirements",
                "issues": password_check['issues'],
                "strength_score": password_check['strength_score']
            }
        )
    
    # Hash password securely
    hashed_password = PasswordSecurity.hash_password(user_data.password)
    
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    await db.commit()
    return user

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # Check rate limiting
    if not password_policy.check_rate_limit(form_data.username):
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Account locked temporarily."
        )
    
    # Verify user exists
    user = await get_user_by_username(db, form_data.username)
    if not user:
        password_policy.record_failed_attempt(form_data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not PasswordSecurity.verify_password(form_data.password, user.hashed_password):
        password_policy.record_failed_attempt(form_data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Reset failed attempts on successful login
    password_policy.reset_failed_attempts(form_data.username)
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
```

### Verification:
```bash
# Test weak password rejection
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"weak"}'
# Expected: 400 with password requirements

# Test rate limiting
for i in {1..6}; do
  curl -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test&password=wrong"
done
# Expected: 429 Too Many Requests after 5 attempts
```

---

## 3. Fix XSS Prevention in Frontend (HIGH - 7.5/10)

**Issue**: Unescaped user content rendering  
**Risk**: Cross-site scripting attacks, session hijacking  
**Agent**: `frontend-react-refactorer`  

### Implementation Steps:

**Step 1: Install and configure DOMPurify**
```bash
cd frontend
npm install dompurify
npm install @types/dompurify  # For TypeScript
```

**Step 2: Create sanitization utilities**
```javascript
// frontend/src/utils/sanitizer.js
import DOMPurify from 'dompurify';

class ContentSanitizer {
    constructor() {
        // Configure DOMPurify for strict sanitization
        this.config = {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'code', 'pre', 'br'],
            ALLOWED_ATTR: ['class'],
            ALLOW_DATA_ATTR: false,
            ALLOW_UNKNOWN_PROTOCOLS: false,
            RETURN_DOM: false,
            RETURN_DOM_FRAGMENT: false
        };
    }

    sanitizeText(text) {
        if (!text || typeof text !== 'string') {
            return '';
        }
        return DOMPurify.sanitize(text, { 
            ...this.config, 
            ALLOWED_TAGS: [] // No HTML tags for plain text
        });
    }

    sanitizeRichContent(content) {
        if (!content || typeof content !== 'string') {
            return '';
        }
        return DOMPurify.sanitize(content, this.config);
    }

    sanitizeJSON(jsonString) {
        try {
            if (!jsonString || typeof jsonString !== 'string') {
                return {};
            }

            const parsed = JSON.parse(jsonString);
            return this.sanitizeObjectValues(parsed);
        } catch (error) {
            console.error('Invalid JSON provided for sanitization:', error);
            return {};
        }
    }

    sanitizeObjectValues(obj) {
        if (obj === null || obj === undefined) {
            return obj;
        }

        if (typeof obj === 'string') {
            return this.sanitizeText(obj);
        }

        if (typeof obj === 'number' || typeof obj === 'boolean') {
            return obj;
        }

        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeObjectValues(item));
        }

        if (typeof obj === 'object') {
            const sanitized = {};
            for (const [key, value] of Object.entries(obj)) {
                const cleanKey = this.sanitizeText(key);
                sanitized[cleanKey] = this.sanitizeObjectValues(value);
            }
            return sanitized;
        }

        return obj;
    }

    validateInput(input, maxLength = 1000) {
        if (!input || typeof input !== 'string') {
            return { isValid: false, error: 'Input must be a non-empty string' };
        }

        if (input.length > maxLength) {
            return { 
                isValid: false, 
                error: `Input exceeds maximum length of ${maxLength} characters` 
            };
        }

        // Check for suspicious patterns
        const suspiciousPatterns = [
            /<script[^>]*>/i,
            /javascript:/i,
            /on\w+\s*=/i,
            /data:text\/html/i,
            /vbscript:/i
        ];

        for (const pattern of suspiciousPatterns) {
            if (pattern.test(input)) {
                return { 
                    isValid: false, 
                    error: 'Input contains potentially malicious content' 
                };
            }
        }

        return { isValid: true };
    }
}

export const contentSanitizer = new ContentSanitizer();
```

**Step 3: Create safe display components**
```javascript
// frontend/src/components/SafeDisplay.js
import React from 'react';
import { Typography } from '@mui/material';
import { contentSanitizer } from '../utils/sanitizer';

// Safe text display component
export const SafeTextDisplay = ({ text, variant = "body2", ...props }) => {
    const sanitizedText = contentSanitizer.sanitizeText(text || '');
    
    return (
        <Typography variant={variant} {...props}>
            {sanitizedText}
        </Typography>
    );
};

// Safe JSON display component
export const SafeJSONDisplay = ({ jsonString }) => {
    const [sanitizedJson, setSanitizedJson] = React.useState('');
    const [jsonError, setJsonError] = React.useState('');

    React.useEffect(() => {
        try {
            const sanitized = contentSanitizer.sanitizeJSON(jsonString);
            setSanitizedJson(JSON.stringify(sanitized, null, 2));
            setJsonError('');
        } catch (error) {
            setJsonError('Invalid JSON format');
            setSanitizedJson('');
        }
    }, [jsonString]);

    if (jsonError) {
        return (
            <Typography variant="body2" color="error">
                {jsonError}
            </Typography>
        );
    }

    return (
        <Typography 
            variant="body2" 
            component="pre" 
            sx={{ 
                backgroundColor: 'background.paper', 
                p: 1, 
                borderRadius: 1,
                overflow: 'auto',
                fontFamily: 'monospace'
            }}
        >
            {sanitizedJson}
        </Typography>
    );
};

// Safe input component with validation
export const SafeTextField = ({
    value,
    onChange,
    maxLength = 1000,
    sanitize = true,
    ...props
}) => {
    const [error, setError] = React.useState('');

    const handleChange = React.useCallback((event) => {
        const newValue = event.target.value;

        // Validate input
        const validation = contentSanitizer.validateInput(newValue, maxLength);
        if (!validation.isValid) {
            setError(validation.error);
            return;
        }

        setError('');

        // Sanitize if requested
        const finalValue = sanitize ? contentSanitizer.sanitizeText(newValue) : newValue;
        
        onChange({
            ...event,
            target: {
                ...event.target,
                value: finalValue
            }
        });
    }, [onChange, maxLength, sanitize]);

    return (
        <TextField
            {...props}
            value={value}
            onChange={handleChange}
            error={!!error}
            helperText={error || props.helperText}
            inputProps={{
                ...props.inputProps,
                maxLength: maxLength
            }}
        />
    );
};
```

**Step 4: Update components to use safe display**
```javascript
// frontend/src/pages/TraceDetail.js (Update existing code)
import { SafeTextDisplay, SafeJSONDisplay } from '../components/SafeDisplay';

// REPLACE unsafe displays:
<Typography variant="h6">{span.name}</Typography>
// WITH:
<SafeTextDisplay text={span.name} variant="h6" />

// REPLACE unsafe JSON display:
<Typography variant="body2" component="pre">
    {JSON.stringify(JSON.parse(span.metadata), null, 2)}
</Typography>
// WITH:
<SafeJSONDisplay jsonString={span.metadata} />
```

### Verification:
```javascript
// Test XSS prevention
import { contentSanitizer } from './utils/sanitizer';

// Test malicious inputs
const xssPayloads = [
    '<script>alert("XSS")</script>',
    'javascript:alert("XSS")',
    '<img src=x onerror=alert("XSS")>'
];

xssPayloads.forEach(payload => {
    const sanitized = contentSanitizer.sanitizeText(payload);
    console.assert(!sanitized.includes('<script'), 'XSS payload neutralized');
});
```

---

## 4. Implement API Client Security (HIGH - 7.5/10)

**Issue**: Insecure API client configuration  
**Risk**: Token theft, request interception, API abuse  
**Agent**: `frontend-react-refactorer`  

### Implementation Steps:

**Step 1: Create secure API client**
```javascript
// frontend/src/services/secureApi.js
import axios from 'axios';
import { tokenStorage } from '../utils/secureStorage';
import { contentSanitizer } from '../utils/sanitizer';

class SecureApiClient {
    constructor() {
        this.baseURL = this.getSecureBaseURL();
        this.client = this.createSecureClient();
        this.setupInterceptors();
    }

    getSecureBaseURL() {
        const apiUrl = process.env.REACT_APP_API_URL;
        
        // Enforce HTTPS in production
        if (process.env.NODE_ENV === 'production') {
            if (!apiUrl || !apiUrl.startsWith('https://')) {
                console.error('Production API URL must use HTTPS');
                return 'https://api.langchef.com';
            }
        }

        return apiUrl || 'http://localhost:8001';
    }

    createSecureClient() {
        return axios.create({
            baseURL: this.baseURL,
            timeout: 30000,
            maxRedirects: 3,
            maxContentLength: 10 * 1024 * 1024,  // 10MB
            maxBodyLength: 10 * 1024 * 1024,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',  // CSRF protection
            },
            validateStatus: (status) => status >= 200 && status < 300,
        });
    }

    setupInterceptors() {
        // Request interceptor
        this.client.interceptors.request.use(
            (config) => {
                // Add authentication
                const token = tokenStorage.getToken();
                if (token && tokenStorage.isTokenValid()) {
                    config.headers.Authorization = `Bearer ${token}`;
                }

                // Add security headers
                config.headers['X-Content-Type-Options'] = 'nosniff';

                // Sanitize request data
                if (config.data && typeof config.data === 'object') {
                    config.data = this.sanitizeRequestData(config.data);
                }

                return config;
            },
            (error) => {
                console.error('Request error:', error.message);
                return Promise.reject(error);
            }
        );

        // Response interceptor
        this.client.interceptors.response.use(
            (response) => {
                // Validate and sanitize response
                return this.validateResponse(response);
            },
            async (error) => {
                return this.handleResponseError(error);
            }
        );
    }

    sanitizeRequestData(data) {
        if (Array.isArray(data)) {
            return data.map(item => this.sanitizeRequestData(item));
        }

        if (typeof data === 'object' && data !== null) {
            const sanitized = {};
            for (const [key, value] of Object.entries(data)) {
                if (typeof value === 'string') {
                    sanitized[key] = contentSanitizer.sanitizeText(value);
                } else if (typeof value === 'object') {
                    sanitized[key] = this.sanitizeRequestData(value);
                } else {
                    sanitized[key] = value;
                }
            }
            return sanitized;
        }

        return data;
    }

    validateResponse(response) {
        // Sanitize response data
        if (response.data && typeof response.data === 'object') {
            response.data = this.sanitizeResponseData(response.data);
        }

        return response;
    }

    sanitizeResponseData(data) {
        if (Array.isArray(data)) {
            return data.map(item => this.sanitizeResponseData(item));
        }

        if (typeof data === 'object' && data !== null) {
            const sanitized = {};
            for (const [key, value] of Object.entries(data)) {
                if (typeof value === 'string' && 
                    ['name', 'description', 'input', 'output'].includes(key)) {
                    sanitized[key] = contentSanitizer.sanitizeText(value);
                } else if (typeof value === 'object') {
                    sanitized[key] = this.sanitizeResponseData(value);
                } else {
                    sanitized[key] = value;
                }
            }
            return sanitized;
        }

        return data;
    }

    async handleResponseError(error) {
        const originalRequest = error.config;

        // Handle 401 errors with token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshed = await this.refreshAuthToken();
                if (refreshed) {
                    const token = tokenStorage.getToken();
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                    return this.client(originalRequest);
                }
            } catch (refreshError) {
                this.handleAuthFailure();
                return Promise.reject(refreshError);
            }
        }

        // Handle rate limiting with backoff
        if (error.response?.status === 429) {
            if (!originalRequest._retryCount) {
                originalRequest._retryCount = 0;
            }
            
            if (originalRequest._retryCount < 3) {
                originalRequest._retryCount++;
                const delay = Math.pow(2, originalRequest._retryCount) * 1000;
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.client(originalRequest);
            }
        }

        return Promise.reject(this.sanitizeError(error));
    }

    async refreshAuthToken() {
        try {
            const currentToken = tokenStorage.getToken();
            if (!currentToken) return false;

            const response = await axios.post(`${this.baseURL}/auth/refresh`, {}, {
                headers: { Authorization: `Bearer ${currentToken}` },
                timeout: 10000
            });

            tokenStorage.storeToken(response.data.access_token);
            return true;
        } catch (error) {
            return false;
        }
    }

    handleAuthFailure() {
        tokenStorage.clearToken();
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }

    sanitizeError(error) {
        return {
            message: error.response?.data?.message || 'An error occurred',
            status: error.response?.status,
            code: error.code
        };
    }
}

export const secureApi = new SecureApiClient();
```

### Verification:
```javascript
// Test secure API configuration
console.assert(
    secureApi.baseURL.startsWith('https://') || process.env.NODE_ENV !== 'production',
    'Production API must use HTTPS'
);

// Test request sanitization
const testData = { name: '<script>alert("xss")</script>' };
const sanitized = secureApi.sanitizeRequestData(testData);
console.assert(!sanitized.name.includes('<script'), 'Request data sanitized');
```

---

## 5. Fix Database Security Configuration (HIGH - 8.0/10)

**Issue**: Insecure database configuration and connection  
**Risk**: Database compromise, credential theft, data breaches  
**Agent**: `backend-fastapi-refactorer`  

### Implementation Steps:

**Step 1: Secure database configuration**
```python
# backend/core/database_security.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import asyncpg
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class SecureDatabaseConfig:
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._setup_secure_engine()
    
    def _setup_secure_engine(self):
        """Setup secure database engine with security configurations"""
        
        # Build secure connection URL
        db_url = self._build_secure_db_url()
        
        # Security-focused engine configuration
        self.engine = create_async_engine(
            db_url,
            echo=settings.ENVIRONMENT == "development",  # Only log SQL in dev
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,  # Recycle connections every hour
            poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
            connect_args={
                "server_settings": {
                    "application_name": "langchef_backend",
                    "jit": "off",  # Disable JIT compilation for security
                },
                "ssl": "require" if settings.ENVIRONMENT == "production" else "prefer",
                "command_timeout": 60,  # Query timeout
            }
        )
        
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    def _build_secure_db_url(self) -> str:
        """Build database URL with security validations"""
        base_url = settings.DATABASE_URL
        
        if not base_url:
            raise ValueError("DATABASE_URL is required")
        
        # Validate production database security
        if settings.ENVIRONMENT == "production":
            if "localhost" in base_url or "127.0.0.1" in base_url:
                raise ValueError("Production database cannot use localhost")
            
            if "sslmode=disable" in base_url:
                raise ValueError("Production database must use SSL")
            
            # Ensure SSL mode is set
            if "sslmode=" not in base_url:
                separator = "&" if "?" in base_url else "?"
                base_url += f"{separator}sslmode=require"
        
        return base_url
    
    async def validate_connection_security(self):
        """Validate database connection security"""
        try:
            async with self.engine.begin() as conn:
                # Check SSL status
                result = await conn.execute("SHOW ssl")
                ssl_status = result.scalar()
                
                if settings.ENVIRONMENT == "production" and ssl_status != "on":
                    logger.warning("Database SSL not enabled in production")
                
                # Check connection encryption
                result = await conn.execute(
                    "SELECT * FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
                )
                ssl_info = result.fetchone()
                
                if ssl_info:
                    logger.info(f"Database SSL: {ssl_info.ssl}, Cipher: {ssl_info.cipher}")
                else:
                    logger.warning("No SSL information available")
                
                # Validate user permissions (should not be superuser)
                result = await conn.execute("SELECT current_user, usesuper FROM pg_user WHERE usename = current_user")
                user_info = result.fetchone()
                
                if user_info and user_info.usesuper:
                    logger.warning("Database user has superuser privileges - security risk")
                
                return True
        
        except Exception as e:
            logger.error(f"Database security validation failed: {e}")
            return False

# Database session management with security
class SecureDatabaseSession:
    def __init__(self, db_config: SecureDatabaseConfig):
        self.db_config = db_config
        self.active_sessions = set()
    
    async def get_session(self) -> AsyncSession:
        """Get secure database session"""
        session = self.db_config.session_factory()
        
        # Track active sessions for security monitoring
        self.active_sessions.add(id(session))
        
        # Set session-level security parameters
        await session.execute("SET statement_timeout = '60s'")
        await session.execute("SET idle_in_transaction_session_timeout = '300s'")
        
        return session
    
    async def close_session(self, session: AsyncSession):
        """Securely close database session"""
        try:
            await session.close()
            self.active_sessions.discard(id(session))
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active database sessions for monitoring"""
        return len(self.active_sessions)

# Global secure database configuration
secure_db = SecureDatabaseConfig()
db_session_manager = SecureDatabaseSession(secure_db)

async def get_secure_db():
    """Dependency for getting secure database session"""
    session = await db_session_manager.get_session()
    try:
        yield session
    finally:
        await db_session_manager.close_session(session)
```

**Step 2: Implement database query security**
```python
# backend/core/query_security.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import re

class QuerySecurityManager:
    # SQL injection patterns to detect
    DANGEROUS_PATTERNS = [
        r"('|(\\'))",           # SQL quotes
        r"(;|\|)",              # Statement separators  
        r"(\*|%)",              # SQL wildcards
        r"(exec|execute)",      # Command execution
        r"(union|select|insert|update|delete|drop|create|alter)", # SQL keywords
        r"(script|javascript)", # Script injection
        r"(--|\#|/\*|\*/)",     # SQL comments
    ]
    
    @classmethod
    def validate_query_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize query parameters"""
        safe_params = {}
        
        for key, value in params.items():
            # Validate parameter name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid parameter name: {key}")
            
            # Sanitize string values
            if isinstance(value, str):
                safe_value = cls._sanitize_string_param(value)
                safe_params[key] = safe_value
            elif isinstance(value, (int, float, bool)):
                safe_params[key] = value
            elif value is None:
                safe_params[key] = None
            else:
                raise ValueError(f"Unsupported parameter type: {type(value)}")
        
        return safe_params
    
    @classmethod
    def _sanitize_string_param(cls, value: str) -> str:
        """Sanitize string parameter for SQL safety"""
        if not value:
            return value
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value.lower()):
                raise ValueError(f"Potentially dangerous content in parameter: {value[:50]}...")
        
        # Limit string length
        if len(value) > 1000:
            raise ValueError("Parameter value too long")
        
        return value
    
    @classmethod
    async def execute_safe_query(
        cls, 
        session: AsyncSession, 
        query: str, 
        params: Dict[str, Any] = None
    ):
        """Execute query with security validations"""
        
        # Validate parameters
        safe_params = cls.validate_query_params(params or {})
        
        # Ensure query uses parameterized format
        if "%" in query or "{" in query:
            raise ValueError("Query must use parameterized format (:param_name)")
        
        # Execute with bound parameters
        result = await session.execute(text(query), safe_params)
        return result

# Secure repository base class
class SecureRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.query_manager = QuerySecurityManager()
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None):
        """Execute query securely"""
        return await self.query_manager.execute_safe_query(
            self.session, query, params
        )
    
    async def find_by_id(self, model_class, id_value: int):
        """Secure find by ID"""
        query = "SELECT * FROM {} WHERE id = :id".format(model_class.__tablename__)
        result = await self.execute_query(query, {"id": id_value})
        return result.first()
    
    async def search(self, model_class, field: str, value: str, limit: int = 50):
        """Secure search with ILIKE"""
        if limit > 100:
            limit = 100  # Prevent large result sets
        
        query = """
            SELECT * FROM {} 
            WHERE {} ILIKE :search_term 
            ORDER BY created_at DESC 
            LIMIT :limit
        """.format(model_class.__tablename__, field)
        
        result = await self.execute_query(
            query, 
            {"search_term": f"%{value}%", "limit": limit}
        )
        return result.fetchall()
```

### Verification:
```python
# Test database security
async def test_database_security():
    # Test connection security
    assert await secure_db.validate_connection_security()
    
    # Test query parameter validation
    try:
        QuerySecurityManager.validate_query_params({"malicious": "'; DROP TABLE users; --"})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    print("Database security tests passed")
```

---

## 6. Implement Container Security (HIGH - 7.5/10)

**Issue**: Insecure Docker configuration  
**Risk**: Container escape, privilege escalation, resource abuse  
**Agent**: `security-sweeper`  

### Implementation Steps:

**Step 1: Create secure Dockerfiles**
```dockerfile
# backend/Dockerfile.secure
FROM python:3.11.4-alpine3.18 AS base

# Security: Install security updates
RUN apk update && apk upgrade && \
    apk add --no-cache dumb-init tini && \
    addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# Build stage
FROM base AS builder
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /root/.local /home/appuser/.local

WORKDIR /app
COPY --chown=appuser:appgroup . .

# Security: Set permissions and remove build artifacts
RUN chmod -R 755 /app && \
    rm -rf /var/cache/apk/* /tmp/* /root/.cache

# Security: Create directories for non-root user
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appgroup /app/logs /app/tmp

# Security: Switch to non-root user
USER appuser

# Security: Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Create secure docker-compose.yml**
```yaml
# docker-compose.secure.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.secure
    user: "1000:1000"  # Non-root user
    read_only: true    # Read-only filesystem
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    networks:
      - backend-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.secure
    user: "1001:1001"
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=50m
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    networks:
      - frontend-network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  db:
    image: postgres:15.3-alpine
    user: "postgres"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - SETUID
      - SETGID
      - DAC_OVERRIDE
    environment:
      POSTGRES_DB: langchef
      POSTGRES_USER: langchef_user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data:Z
    networks:
      - backend-network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

networks:
  backend-network:
    driver: bridge
    internal: true
  frontend-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### Verification:
```bash
# Test container security
docker run --rm langchef-backend:latest whoami
# Should output: appuser (not root)

# Test security options
docker inspect langchef-backend:latest | jq '.[0].HostConfig.SecurityOpt'
# Should show security configurations
```

---

## 📊 High Priority Fixes Progress Tracking

Track completion of each high-priority fix:

- [ ] **Security Headers**: Comprehensive HTTP security headers implemented
- [ ] **Password Security**: Strong password validation and hashing 
- [ ] **XSS Prevention**: Content sanitization and safe rendering
- [ ] **API Client Security**: Secure API communication and validation
- [ ] **Database Security**: Encrypted connections and query protection
- [ ] **Container Security**: Hardened Docker configuration
- [ ] **File Upload Security**: Type and size validation
- [ ] **Rate Limiting**: API abuse protection
- [ ] **Session Management**: Secure session handling
- [ ] **Error Handling**: Production-safe error responses
- [ ] **Logging Security**: Secure audit logging
- [ ] **Network Security**: Firewall and network isolation
- [ ] **Backup Security**: Encrypted backup procedures

## 🎯 Success Criteria

- **Security Score**: 85%+ on automated security scanners
- **Vulnerability Count**: 0 high priority vulnerabilities
- **Performance Impact**: <10% degradation from security measures
- **Test Coverage**: 90%+ of security fixes covered by automated tests

---

**Next Steps**: After completing high priority fixes, proceed to [Medium Priority Fixes](medium-priority.md) for additional security improvements.
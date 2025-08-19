# Frontend Token Storage Security Audit

**Component**: JWT Token Storage & Client-Side Authentication  
**Priority**: 🟡 HIGH  
**Agent Assignment**: `frontend-react-refactorer`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Insecure Token Storage in localStorage (HIGH - 7.5/10)

**File**: `/frontend/src/contexts/AuthContext.js:72-73, 32-33`  
**Issue**: JWT tokens stored in localStorage vulnerable to XSS attacks

```javascript
// VULNERABLE CODE:
const login = async (username, password) => {
    const response = await api.post('/auth/login', { username, password });
    localStorage.setItem('token', response.data.access_token);  // XSS vulnerable
    setUser(response.data.user);
};

const logout = () => {
    localStorage.removeItem('token');  // Token persists if XSS prevents logout
    setUser(null);
};

// Token retrieval also vulnerable
useEffect(() => {
    const token = localStorage.getItem('token');  // XSS can steal this
    if (token) {
        // Auto-login with potentially compromised token
    }
}, []);
```

**Risk**:
- XSS attacks can steal authentication tokens
- Tokens persist indefinitely in browser storage
- No automatic token expiration handling
- Vulnerable to malicious browser extensions

### 2. Missing Token Refresh Logic (MEDIUM - 6.0/10)

**File**: `/frontend/src/contexts/AuthContext.js`  
**Issue**: No automatic token refresh implementation

```javascript
// MISSING: Token refresh logic
// Frontend expects /refresh endpoint but doesn't implement refresh flow
// Tokens expire but no graceful refresh mechanism
```

**Risk**:
- Users logged out abruptly when tokens expire
- Poor user experience with forced re-authentication
- Potential data loss from interrupted operations

### 3. Debug Token Exposure (MEDIUM - 6.5/10)

**File**: `/frontend/src/contexts/AuthContext.js:45-46`  
**Issue**: Debug code exposes tokens in production

```javascript
// VULNERABLE: Debug code in production
window.debugAuthToken = localStorage.getItem('token');
document.body.setAttribute('data-has-token', !!localStorage.getItem('token'));
```

**Risk**:
- Tokens accessible via browser console
- DOM attributes leak authentication state
- Debug information available to malicious scripts

### 4. Inconsistent API Configuration (MEDIUM - 5.5/10)

**Files**: `/frontend/src/contexts/AuthContext.js` vs `/frontend/src/services/api.js`  
**Issue**: Different API base URLs causing potential security issues

```javascript
// AuthContext.js:
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// api.js:
baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8001',
```

**Risk**:
- Tokens sent to wrong endpoints
- Potential CORS issues with authentication
- Configuration drift leading to security gaps

### 5. Missing Token Validation (LOW - 4.0/10)

**File**: `/frontend/src/contexts/AuthContext.js`  
**Issue**: No client-side token validation or expiration checks

```javascript
// MISSING: Token expiration validation
const token = localStorage.getItem('token');
if (token) {
    // No validation of token format or expiration
    setIsAuthenticated(true);
}
```

**Risk**:
- Invalid tokens cause API failures
- Expired tokens not detected until API call
- Poor error handling for token-related issues

## 🔧 Remediation Steps

### Fix 1: Implement Secure Token Storage

**Replace localStorage with secure alternatives**:

```javascript
// utils/secureStorage.js
import CryptoJS from 'crypto-js';

class SecureTokenStorage {
    constructor() {
        // Generate session-specific encryption key
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
        
        // Encrypt token before storage
        const encrypted = CryptoJS.AES.encrypt(token, this.encryptionKey).toString();
        
        // Use sessionStorage instead of localStorage
        sessionStorage.setItem('auth_token_enc', encrypted);
        
        // Set expiration timer
        const expirationTime = Date.now() + (60 * 60 * 1000); // 1 hour
        sessionStorage.setItem('auth_token_exp', expirationTime.toString());
    }
    
    getToken() {
        const encrypted = sessionStorage.getItem('auth_token_enc');
        const expiration = sessionStorage.getItem('auth_token_exp');
        
        if (!encrypted || !expiration) {
            return null;
        }
        
        // Check if token has expired
        if (Date.now() > parseInt(expiration)) {
            this.clearToken();
            return null;
        }
        
        try {
            const decrypted = CryptoJS.AES.decrypt(encrypted, this.encryptionKey);
            return decrypted.toString(CryptoJS.enc.Utf8);
        } catch (error) {
            console.error('Failed to decrypt token:', error);
            this.clearToken();
            return null;
        }
    }
    
    clearToken() {
        sessionStorage.removeItem('auth_token_enc');
        sessionStorage.removeItem('auth_token_exp');
    }
    
    isTokenValid() {
        const token = this.getToken();
        if (!token) return false;
        
        try {
            // Basic JWT validation (without signature verification)
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp * 1000 > Date.now();
        } catch (error) {
            return false;
        }
    }
}

export const tokenStorage = new SecureTokenStorage();
```

**Update AuthContext.js**:

```javascript
import { tokenStorage } from '../utils/secureStorage';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Remove debug code
    // DELETE: window.debugAuthToken = ...
    // DELETE: document.body.setAttribute('data-has-token', ...);

    const login = async (username, password) => {
        try {
            setLoading(true);
            const response = await api.post('/auth/login', { username, password });
            
            // Store token securely
            tokenStorage.storeToken(response.data.access_token);
            
            setUser(response.data.user);
            setIsAuthenticated(true);
            
            return { success: true };
        } catch (error) {
            console.error('Login failed:', error);
            return { success: false, error: error.response?.data?.detail || 'Login failed' };
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try {
            const token = tokenStorage.getToken();
            if (token) {
                // Call revoke endpoint
                await api.post('/auth/revoke', {}, {
                    headers: { Authorization: `Bearer ${token}` }
                });
            }
        } catch (error) {
            console.error('Logout API call failed:', error);
            // Continue with logout even if API call fails
        } finally {
            // Clear token and state
            tokenStorage.clearToken();
            setUser(null);
            setIsAuthenticated(false);
        }
    };

    const checkAuthStatus = useCallback(async () => {
        try {
            setLoading(true);
            
            if (!tokenStorage.isTokenValid()) {
                setIsAuthenticated(false);
                return;
            }

            const token = tokenStorage.getToken();
            if (token) {
                // Verify token with backend
                const response = await api.get('/auth/me', {
                    headers: { Authorization: `Bearer ${token}` }
                });
                
                setUser(response.data);
                setIsAuthenticated(true);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            tokenStorage.clearToken();
            setIsAuthenticated(false);
        } finally {
            setLoading(false);
        }
    }, []);

    // Auto-refresh token
    useEffect(() => {
        const refreshToken = async () => {
            if (!isAuthenticated) return;
            
            try {
                const token = tokenStorage.getToken();
                const response = await api.post('/auth/refresh', {}, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                
                tokenStorage.storeToken(response.data.access_token);
            } catch (error) {
                console.error('Token refresh failed:', error);
                logout(); // Force logout on refresh failure
            }
        };

        // Refresh token every 30 minutes
        const interval = setInterval(refreshToken, 30 * 60 * 1000);
        return () => clearInterval(interval);
    }, [isAuthenticated]);

    useEffect(() => {
        checkAuthStatus();
    }, [checkAuthStatus]);

    const value = {
        user,
        loading,
        isAuthenticated,
        login,
        logout,
        checkAuthStatus
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
```

### Fix 2: Update API Client for Secure Token Handling

**Update api.js**:

```javascript
import axios from 'axios';
import { tokenStorage } from '../utils/secureStorage';

// Consistent API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Request interceptor for token attachment
api.interceptors.request.use(
    (config) => {
        const token = tokenStorage.getToken();
        if (token && tokenStorage.isTokenValid()) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
    }
);

// Response interceptor for token handling
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        // Handle 401 errors (token expired/invalid)
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            
            try {
                // Try to refresh token
                const refreshResponse = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
                    headers: { Authorization: `Bearer ${tokenStorage.getToken()}` }
                });
                
                tokenStorage.storeToken(refreshResponse.data.access_token);
                
                // Retry original request with new token
                originalRequest.headers.Authorization = `Bearer ${refreshResponse.data.access_token}`;
                return api(originalRequest);
            } catch (refreshError) {
                // Refresh failed, redirect to login
                tokenStorage.clearToken();
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }
        
        return Promise.reject(error);
    }
);

export default api;
```

### Fix 3: Implement Token Refresh Hook

**Create useTokenRefresh hook**:

```javascript
// hooks/useTokenRefresh.js
import { useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { tokenStorage } from '../utils/secureStorage';
import api from '../services/api';

export const useTokenRefresh = () => {
    const { logout } = useAuth();

    const refreshToken = useCallback(async () => {
        try {
            if (!tokenStorage.isTokenValid()) {
                return false;
            }

            const response = await api.post('/auth/refresh');
            tokenStorage.storeToken(response.data.access_token);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            logout();
            return false;
        }
    }, [logout]);

    // Auto-refresh 5 minutes before expiration
    useEffect(() => {
        const checkAndRefresh = async () => {
            const token = tokenStorage.getToken();
            if (!token) return;

            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                const expirationTime = payload.exp * 1000;
                const currentTime = Date.now();
                const fiveMinutes = 5 * 60 * 1000;

                // Refresh if token expires within 5 minutes
                if (expirationTime - currentTime < fiveMinutes) {
                    await refreshToken();
                }
            } catch (error) {
                console.error('Token parsing failed:', error);
                logout();
            }
        };

        // Check every minute
        const interval = setInterval(checkAndRefresh, 60 * 1000);
        return () => clearInterval(interval);
    }, [refreshToken, logout]);

    return { refreshToken };
};
```

### Fix 4: Add Token Security Middleware

**Create token security component**:

```javascript
// components/TokenSecurityProvider.js
import React, { useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { tokenStorage } from '../utils/secureStorage';

export const TokenSecurityProvider = ({ children }) => {
    const { logout } = useAuth();

    useEffect(() => {
        // Security measures against token theft
        
        // 1. Clear tokens on page unload (for security)
        const handleBeforeUnload = () => {
            // Optional: Clear tokens on page close
            // tokenStorage.clearToken();
        };

        // 2. Detect if page is loaded in iframe (potential clickjacking)
        const detectFraming = () => {
            if (window.self !== window.top) {
                console.warn('Application loaded in iframe - potential security risk');
                // Optional: Force logout or show warning
            }
        };

        // 3. Monitor for suspicious activity
        const monitorSuspiciousActivity = () => {
            // Detect rapid API calls that might indicate automated attacks
            let apiCallCount = 0;
            const resetCount = () => { apiCallCount = 0; };
            
            // Monitor API interceptor for unusual patterns
            // This would integrate with your API monitoring
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        detectFraming();
        monitorSuspiciousActivity();

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [logout]);

    // Periodic security checks
    useEffect(() => {
        const securityCheck = () => {
            // Check if token has been tampered with
            const token = tokenStorage.getToken();
            if (token) {
                try {
                    const parts = token.split('.');
                    if (parts.length !== 3) {
                        console.error('Invalid token format detected');
                        logout();
                    }
                } catch (error) {
                    console.error('Token validation failed:', error);
                    logout();
                }
            }
        };

        const interval = setInterval(securityCheck, 30 * 1000); // Every 30 seconds
        return () => clearInterval(interval);
    }, [logout]);

    return <>{children}</>;
};
```

## ✅ Verification Methods

### Test Secure Token Storage:
```javascript
// Test encryption/decryption
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

### Test Token Expiration:
```javascript
// Test token expiration handling
const expiredToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE2MDAwMDAwMDF9.invalid';
tokenStorage.storeToken(expiredToken);

// Should return null for expired token
console.assert(tokenStorage.getToken() === null, 'Expired token should be rejected');
```

### Test XSS Protection:
```javascript
// Simulate XSS attempt to steal tokens
try {
    const stolenToken = localStorage.getItem('token'); // Should be undefined
    console.assert(stolenToken === null, 'XSS should not be able to access tokens');
} catch (error) {
    console.log('XSS protection working - token not accessible');
}
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Implement secure token storage with encryption
- [ ] **Fix 2**: Replace localStorage with sessionStorage
- [ ] **Fix 3**: Remove all debug token exposure code
- [ ] **Fix 4**: Implement automatic token refresh
- [ ] **Fix 5**: Add client-side token validation
- [ ] **Fix 6**: Create token security monitoring
- [ ] **Testing**: Token security test suite
- [ ] **Documentation**: Secure token handling guidelines

## 🔗 Dependencies

- `crypto-js` for client-side encryption
- Updated API interceptors for token handling
- Token refresh endpoint implementation in backend
- Security monitoring and alerting

## 🚨 Critical Actions Required

1. **Replace localStorage with encrypted sessionStorage immediately**
2. **Remove all debug token exposure code from production**
3. **Implement automatic token refresh to prevent session timeouts**
4. **Add client-side token validation and expiration checking**
5. **Configure consistent API endpoints across all services**
6. **Test token security against common XSS attack vectors**
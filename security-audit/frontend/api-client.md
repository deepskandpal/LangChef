# Frontend API Client Security Audit

**Component**: API Client & HTTP Communication Security  
**Priority**: 🟡 HIGH  
**Agent Assignment**: `frontend-react-refactorer`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Insecure Token Handling in Request Interceptor (HIGH - 7.5/10)

**File**: `/frontend/src/services/api.js:14-20`  
**Issue**: Unsafe token retrieval and formatting logic

```javascript
// VULNERABLE CODE:
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');  // XSS vulnerable storage
    
    if (token) {
      // Unsafe token formatting - may double-prefix Bearer
      const formattedToken = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
      config.headers['Authorization'] = formattedToken;
    }
    
    return config;
  },
```

**Risk**:
- Token retrieved from XSS-vulnerable localStorage
- No validation of token format or content
- Potential token corruption with double Bearer prefix
- Tokens sent to all API endpoints without validation

### 2. Missing Request/Response Security Validation (HIGH - 7.0/10)

**File**: `/frontend/src/services/api.js` (entire file)  
**Issue**: No security validation of requests or responses

```javascript
// MISSING SECURITY MEASURES:
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8001',
  headers: {
    'Content-Type': 'application/json',
  },
  // MISSING: timeout configuration
  // MISSING: request size limits
  // MISSING: response validation
  // MISSING: HTTPS enforcement
});
```

**Risk**:
- No timeout protection against slowloris attacks
- No request size limits (potential DoS)
- HTTPS not enforced for production
- No response content validation
- No rate limiting protection

### 3. Information Disclosure in Error Handling (MEDIUM - 6.5/10)

**File**: `/frontend/src/services/api.js:36-44`  
**Issue**: Detailed error information exposed to console

```javascript
// INFORMATION DISCLOSURE:
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (process.env.NODE_ENV === 'development') {
      console.error('API Response Error:', 
        error.response?.status,     // Status code exposed
        error.config?.url,          // API endpoint exposed  
        error.message               // Error details exposed
      );
    }
    return Promise.reject(error);
  }
);
```

**Risk**:
- Internal API structure exposed in errors
- Authentication errors reveal sensitive information
- Error messages may contain stack traces
- Debug information accessible in production builds

### 4. Unsafe File Upload Configuration (MEDIUM - 6.0/10)

**Files**: `/frontend/src/services/api.js:84-97`  
**Issue**: File uploads lack security validation

```javascript
// INSECURE FILE UPLOADS:
upload: (formData) => {
  return api.post('/api/datasets/upload/file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'  // No file type validation
    }
    // MISSING: file size limits
    // MISSING: file type validation
    // MISSING: virus scanning
  });
},

uploadCSV: (formData) => {
  return api.post('/api/datasets/upload/csv', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'  // CSV-specific but no validation
    }
    // MISSING: CSV format validation
    // MISSING: malicious content detection
  });
},
```

**Risk**:
- No file size limits (potential DoS)
- No file type validation (malicious file uploads)
- No virus or malware scanning
- CSV files could contain malicious formulas

### 5. Insecure API Configuration Inconsistencies (MEDIUM - 5.5/10)

**Files**: Multiple API configurations across the application  
**Issue**: Inconsistent security configurations between different API calls

```javascript
// CONFIGURATION INCONSISTENCIES:
// Default API base URL
baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8001',

// But AuthContext uses different URL:
// 'http://localhost:8000' (from AuthContext.js)

// No consistent HTTPS enforcement
// No consistent timeout settings
// No consistent retry policies
```

**Risk**:
- Tokens sent to wrong endpoints
- Mixed HTTP/HTTPS communications
- Inconsistent security policies across API calls
- Potential for security configuration drift

### 6. Missing CSRF Protection (MEDIUM - 5.0/10)

**File**: `/frontend/src/services/api.js` (missing CSRF configuration)  
**Issue**: No Cross-Site Request Forgery protection

```javascript
// MISSING CSRF PROTECTION:
const api = axios.create({
  // No CSRF token configuration
  // No SameSite cookie settings
  // No X-Requested-With headers
});
```

**Risk**:
- Vulnerable to CSRF attacks
- No protection against unauthorized cross-origin requests
- State-changing operations can be triggered by malicious sites

### 7. Insufficient Response Data Validation (LOW - 4.5/10)

**Files**: All API service methods  
**Issue**: No validation of API response data structure

```javascript
// NO RESPONSE VALIDATION:
export const tracesApi = {
  getAll: (params) => api.get('/api/traces', { params }),  // Raw response
  getById: (id) => api.get(`/api/traces/${id}`),          // No validation
  create: (data) => api.post('/api/traces', data),        // No sanitization
};
```

**Risk**:
- Malicious API responses can inject unexpected data
- Application crashes from unexpected response formats
- No protection against API response manipulation
- Client-side code assumes trusted data structure

## 🔧 Remediation Steps

### Fix 1: Implement Secure API Client Configuration

**Create secure API configuration**:

```javascript
// services/secureApi.js
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
                throw new Error('Production API URL must use HTTPS');
            }
        }

        return apiUrl || (
            process.env.NODE_ENV === 'production' 
                ? 'https://api.langchef.com'  // Production default
                : 'http://localhost:8001'     // Development default
        );
    }

    createSecureClient() {
        return axios.create({
            baseURL: this.baseURL,
            timeout: 30000,  // 30 second timeout
            maxRedirects: 3,
            maxContentLength: 10 * 1024 * 1024,  // 10MB limit
            maxBodyLength: 10 * 1024 * 1024,     // 10MB limit
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',  // CSRF protection
            },
            validateStatus: (status) => {
                // Only accept expected status codes
                return status >= 200 && status < 300;
            }
        });
    }

    setupInterceptors() {
        // Secure request interceptor
        this.client.interceptors.request.use(
            (config) => {
                // Add authentication if available
                const token = tokenStorage.getToken();
                if (token && tokenStorage.isTokenValid()) {
                    config.headers.Authorization = `Bearer ${token}`;
                }

                // Add security headers
                config.headers['X-Content-Type-Options'] = 'nosniff';
                config.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';

                // Validate request data
                if (config.data && typeof config.data === 'object') {
                    config.data = this.sanitizeRequestData(config.data);
                }

                // Log request for monitoring (without sensitive data)
                this.logRequest(config);

                return config;
            },
            (error) => {
                console.error('Request configuration error:', error.message);
                return Promise.reject(error);
            }
        );

        // Secure response interceptor
        this.client.interceptors.response.use(
            (response) => {
                // Validate response structure
                const validatedResponse = this.validateResponse(response);
                
                // Log successful response for monitoring
                this.logResponse(response);

                return validatedResponse;
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
        // Basic response structure validation
        if (!response || typeof response !== 'object') {
            throw new Error('Invalid response structure');
        }

        // Validate response headers
        const contentType = response.headers['content-type'];
        if (contentType && !contentType.includes('application/json') && !contentType.includes('text/')) {
            console.warn('Unexpected content type:', contentType);
        }

        // Sanitize response data if it contains strings
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
                if (typeof value === 'string') {
                    // Only sanitize user-generated content, not system fields
                    if (['name', 'description', 'input', 'output'].includes(key)) {
                        sanitized[key] = contentSanitizer.sanitizeText(value);
                    } else {
                        sanitized[key] = value;
                    }
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

        // Handle authentication errors
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                // Attempt token refresh
                const refreshed = await this.refreshAuthToken();
                if (refreshed) {
                    // Retry original request with new token
                    const token = tokenStorage.getToken();
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                    return this.client(originalRequest);
                }
            } catch (refreshError) {
                // Refresh failed, redirect to login
                this.handleAuthFailure();
                return Promise.reject(refreshError);
            }
        }

        // Handle rate limiting
        if (error.response?.status === 429) {
            const retryAfter = error.response.headers['retry-after'] || 60;
            console.warn(`Rate limited. Retry after ${retryAfter} seconds`);
            
            // Implement exponential backoff for retry
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

        // Log error securely (without sensitive information)
        this.logError(error);

        return Promise.reject(this.sanitizeError(error));
    }

    async refreshAuthToken() {
        try {
            const currentToken = tokenStorage.getToken();
            if (!currentToken) {
                return false;
            }

            const response = await axios.post(`${this.baseURL}/auth/refresh`, {}, {
                headers: { Authorization: `Bearer ${currentToken}` },
                timeout: 10000
            });

            tokenStorage.storeToken(response.data.access_token);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error.message);
            return false;
        }
    }

    handleAuthFailure() {
        tokenStorage.clearToken();
        
        // Redirect to login page
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }

    sanitizeError(error) {
        // Create safe error object without sensitive information
        return {
            message: error.response?.data?.message || 'An error occurred',
            status: error.response?.status,
            code: error.code,
            // Don't include full config or response data
        };
    }

    logRequest(config) {
        if (process.env.NODE_ENV === 'development') {
            console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        }
    }

    logResponse(response) {
        if (process.env.NODE_ENV === 'development') {
            console.log(`API Response: ${response.status} ${response.config.url}`);
        }
    }

    logError(error) {
        const safeError = {
            status: error.response?.status,
            message: error.message,
            url: error.config?.url,
            method: error.config?.method
        };
        
        console.error('API Error:', safeError);

        // In production, send to monitoring service
        if (process.env.NODE_ENV === 'production') {
            // monitoringService.reportError(safeError);
        }
    }

    // Secure file upload with validation
    async uploadFile(endpoint, file, options = {}) {
        // Validate file before upload
        const validation = this.validateFile(file, options);
        if (!validation.isValid) {
            throw new Error(validation.error);
        }

        const formData = new FormData();
        formData.append('file', file);

        // Add additional security headers for file uploads
        const config = {
            headers: {
                'Content-Type': 'multipart/form-data',
                'X-File-Upload': 'true',
            },
            timeout: 300000, // 5 minutes for file uploads
            onUploadProgress: options.onProgress
        };

        return this.client.post(endpoint, formData, config);
    }

    validateFile(file, options = {}) {
        const maxSize = options.maxSize || 10 * 1024 * 1024; // 10MB default
        const allowedTypes = options.allowedTypes || ['text/csv', 'application/json'];

        if (!file) {
            return { isValid: false, error: 'No file provided' };
        }

        if (file.size > maxSize) {
            return { 
                isValid: false, 
                error: `File size exceeds ${maxSize / (1024 * 1024)}MB limit` 
            };
        }

        if (!allowedTypes.includes(file.type)) {
            return { 
                isValid: false, 
                error: `File type ${file.type} not allowed` 
            };
        }

        // Check file name for suspicious patterns
        const dangerousPatterns = [
            /\.exe$/i, /\.bat$/i, /\.sh$/i, /\.php$/i, /\.asp$/i
        ];

        if (dangerousPatterns.some(pattern => pattern.test(file.name))) {
            return { 
                isValid: false, 
                error: 'File type potentially dangerous' 
            };
        }

        return { isValid: true };
    }
}

// Export singleton instance
export const secureApi = new SecureApiClient();
```

### Fix 2: Update API Service Methods with Security

```javascript
// services/api.js (Updated with security)
import { secureApi } from './secureApi';

// Secure API services with validation
export const tracesApi = {
    async getAll(params = {}) {
        const response = await secureApi.client.get('/api/traces', { params });
        
        // Validate response structure
        if (!Array.isArray(response.data)) {
            throw new Error('Invalid traces response format');
        }

        return response;
    },

    async getById(id) {
        if (!id || typeof id !== 'string' && typeof id !== 'number') {
            throw new Error('Invalid trace ID provided');
        }

        const response = await secureApi.client.get(`/api/traces/${encodeURIComponent(id)}`);
        
        // Validate response structure
        if (!response.data || typeof response.data !== 'object') {
            throw new Error('Invalid trace response format');
        }

        return response;
    },

    async create(data) {
        // Validate input data
        if (!data || !data.name) {
            throw new Error('Trace name is required');
        }

        const validation = contentSanitizer.validateInput(data.name, 100);
        if (!validation.isValid) {
            throw new Error(`Invalid name: ${validation.error}`);
        }

        return secureApi.client.post('/api/traces', data);
    },

    async update(id, data) {
        if (!id || typeof id !== 'string' && typeof id !== 'number') {
            throw new Error('Invalid trace ID provided');
        }

        if (!data || typeof data !== 'object') {
            throw new Error('Invalid update data provided');
        }

        return secureApi.client.put(`/api/traces/${encodeURIComponent(id)}`, data);
    },

    async delete(id) {
        if (!id || typeof id !== 'string' && typeof id !== 'number') {
            throw new Error('Invalid trace ID provided');
        }

        return secureApi.client.delete(`/api/traces/${encodeURIComponent(id)}`);
    }
};

// Secure datasets API with file upload validation
export const datasetsApi = {
    // ... other methods ...

    async upload(file, options = {}) {
        return secureApi.uploadFile('/api/datasets/upload/file', file, {
            maxSize: 50 * 1024 * 1024, // 50MB for datasets
            allowedTypes: ['text/csv', 'application/json', 'text/plain'],
            ...options
        });
    },

    async uploadCSV(file, options = {}) {
        return secureApi.uploadFile('/api/datasets/upload/csv', file, {
            maxSize: 100 * 1024 * 1024, // 100MB for CSV files
            allowedTypes: ['text/csv'],
            ...options
        });
    }
};

// Export secure API client as default
export default {
    traces: tracesApi,
    datasets: datasetsApi,
    // ... other APIs
};
```

### Fix 3: Implement API Security Monitoring

```javascript
// hooks/useApiSecurity.js
import { useEffect, useCallback, useRef } from 'react';

export const useApiSecurity = () => {
    const requestCount = useRef(0);
    const lastRequestTime = useRef(Date.now());
    const suspiciousActivity = useRef(false);

    // Monitor API request patterns
    const monitorRequestPattern = useCallback(() => {
        const now = Date.now();
        const timeDiff = now - lastRequestTime.current;
        
        // Reset counter every minute
        if (timeDiff > 60000) {
            requestCount.current = 0;
            lastRequestTime.current = now;
        }
        
        requestCount.current++;
        
        // Flag suspicious activity (more than 100 requests per minute)
        if (requestCount.current > 100) {
            suspiciousActivity.current = true;
            console.warn('Suspicious API activity detected - rate limiting recommended');
        }
    }, []);

    // Validate API responses for security
    const validateApiResponse = useCallback((response) => {
        // Check for suspicious response patterns
        if (response.headers['x-powered-by']) {
            console.warn('Server exposes technology stack in headers');
        }

        // Check for potential information disclosure
        if (response.data && typeof response.data === 'object') {
            const stringified = JSON.stringify(response.data);
            
            const sensitivePatterns = [
                /password/i,
                /secret/i,
                /token/i,
                /key/i,
                /credential/i
            ];

            sensitivePatterns.forEach(pattern => {
                if (pattern.test(stringified)) {
                    console.warn('API response may contain sensitive information');
                }
            });
        }

        return response;
    }, []);

    return {
        monitorRequestPattern,
        validateApiResponse,
        isSuspicious: () => suspiciousActivity.current
    };
};
```

## ✅ Verification Methods

### Test Secure API Configuration:
```javascript
// Test HTTPS enforcement
if (process.env.NODE_ENV === 'production') {
    console.assert(
        secureApi.baseURL.startsWith('https://'),
        'Production API must use HTTPS'
    );
}

// Test request sanitization
const testData = { name: '<script>alert("xss")</script>' };
const sanitized = secureApi.sanitizeRequestData(testData);
console.assert(
    !sanitized.name.includes('<script'),
    'Request data should be sanitized'
);
```

### Test File Upload Security:
```javascript
// Test file validation
const maliciousFile = new File(['malicious'], 'virus.exe', { type: 'application/exe' });
const validation = secureApi.validateFile(maliciousFile);
console.assert(!validation.isValid, 'Malicious files should be rejected');
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Implement SecureApiClient with comprehensive security
- [ ] **Fix 2**: Update all API service methods with validation
- [ ] **Fix 3**: Add secure file upload functionality
- [ ] **Fix 4**: Implement API security monitoring hooks
- [ ] **Fix 5**: Add CSRF protection headers
- [ ] **Fix 6**: Configure proper timeout and retry policies
- [ ] **Testing**: API security test suite
- [ ] **Documentation**: Secure API client usage guidelines

## 🔗 Dependencies

- Secure token storage system
- Content sanitization utilities
- Response validation library
- API monitoring and alerting system

## 🚨 Critical Actions Required

1. **Replace current API client with secure implementation immediately**
2. **Add file upload validation to prevent malicious uploads**
3. **Implement proper request/response sanitization**
4. **Add CSRF protection headers to all requests**
5. **Configure HTTPS enforcement for production**
6. **Add API security monitoring and alerting**
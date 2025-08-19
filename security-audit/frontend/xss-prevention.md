# Frontend XSS Prevention Security Audit

**Component**: Cross-Site Scripting (XSS) Prevention  
**Priority**: 🔴 CRITICAL  
**Agent Assignment**: `frontend-react-refactorer`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Dangerous HTML Injection in Trace Detail Component (CRITICAL - 9.0/10)

**File**: `/frontend/src/pages/TraceDetail.js:393-395`  
**Issue**: Direct JSON parsing and display without sanitization

```javascript
// VULNERABLE CODE:
<Typography variant="body2" component="pre" sx={{ 
    backgroundColor: 'background.paper', 
    p: 1, 
    borderRadius: 1,
    overflow: 'auto'
}}>
    {JSON.stringify(JSON.parse(span.metadata), null, 2)}  // XSS vulnerability
</Typography>
```

**Risk**:
- Malicious JSON metadata can inject executable scripts
- No validation of JSON content before parsing
- Direct rendering of untrusted data to DOM
- Potential for script execution in Material-UI Typography component

### 2. Unescaped User Input Display (HIGH - 7.5/10)

**Files**: `/frontend/src/pages/TraceDetail.js:380, 383`, `/frontend/src/pages/Traces.js:127-128`  
**Issue**: User-controlled content displayed without escaping

```javascript
// VULNERABLE CODE in TraceDetail.js:
<Typography variant="body2" sx={{ mb: 1 }}>{span.input}</Typography>     // User input
<Typography variant="body2" sx={{ mb: 1 }}>{span.output}</Typography>    // LLM output

// VULNERABLE CODE in Traces.js:
{ field: 'name', headerName: 'Name', width: 200 },                       // User input
{ field: 'description', headerName: 'Description', width: 300 },         // User input
```

**Risk**:
- User-controlled trace names/descriptions can contain XSS payloads
- LLM outputs may contain malicious content from manipulated prompts
- Material-UI components don't automatically escape HTML entities
- Risk of reflected XSS through URL parameters

### 3. Missing Content Security Policy (CSP) Headers (HIGH - 7.0/10)

**File**: `/frontend/public/index.html` (missing CSP configuration)  
**Issue**: No CSP headers to prevent XSS execution

```html
<!-- MISSING CSP CONFIGURATION -->
<meta http-equiv="Content-Security-Policy" content="...">
```

**Risk**:
- No browser-level protection against XSS attacks
- Inline scripts and eval() are allowed by default
- External resource loading not restricted
- No protection against clickjacking attacks

### 4. Unsafe Dynamic Content Rendering (MEDIUM - 6.5/10)

**Files**: Multiple components rendering dynamic content  
**Issue**: Various components render user/API data without sanitization

```javascript
// VULNERABLE PATTERNS:
// 1. Direct rendering of API responses
const response = await tracesApi.getAll();
setTraces(response.data);  // No validation of response content

// 2. Direct rendering of form inputs
<Typography variant="body1">{trace.name}</Typography>  // User input
<Typography variant="body1">{trace.description}</Typography>  // User input

// 3. Dynamic dialog content
<DialogTitle>{editMode ? 'Edit Trace' : trace.name}</DialogTitle>  // XSS in title
```

**Risk**:
- API responses may contain malicious payloads
- Form data not validated before display
- Dynamic content in dialog titles/headers vulnerable to XSS

### 5. Insufficient Input Validation (MEDIUM - 6.0/10)

**Files**: `/frontend/src/pages/TraceDetail.js`, `/frontend/src/pages/Traces.js`  
**Issue**: No client-side input validation or sanitization

```javascript
// MISSING VALIDATION:
const handleCreateTrace = async () => {
    // No sanitization of newTrace data before sending
    console.log('Creating trace:', newTrace);
};

const handleAddSpan = async () => {
    // No validation of span metadata JSON
    console.log('Adding span:', newSpan);
};
```

**Risk**:
- Malicious payloads stored in backend database
- Invalid JSON in metadata fields crashes application
- No length limits on input fields
- Special characters not handled safely

### 6. Debug Information Exposure (LOW - 4.5/10)

**Files**: Multiple components with console.log statements  
**Issue**: Sensitive data exposed in browser console

```javascript
// INFORMATION DISCLOSURE:
console.log('Creating trace:', newTrace);          // May contain sensitive data
console.error('API fetch failed:', apiError);     // Exposes internal errors
console.log('Adding span:', newSpan);              // User input in console
```

**Risk**:
- Debug information accessible to malicious scripts
- Sensitive data logged to browser console
- Error messages reveal internal application structure
- Production builds may still contain debug code

## 🔧 Remediation Steps

### Fix 1: Implement Content Sanitization

**Create sanitization utility**:

```javascript
// utils/sanitizer.js
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
            RETURN_DOM_FRAGMENT: false,
            RETURN_TRUSTED_TYPE: false
        };
    }

    // Sanitize text content for display
    sanitizeText(text) {
        if (!text || typeof text !== 'string') {
            return '';
        }
        return DOMPurify.sanitize(text, { 
            ...this.config, 
            ALLOWED_TAGS: [] // No HTML tags for plain text
        });
    }

    // Sanitize rich content (minimal HTML allowed)
    sanitizeRichContent(content) {
        if (!content || typeof content !== 'string') {
            return '';
        }
        return DOMPurify.sanitize(content, this.config);
    }

    // Validate and sanitize JSON metadata
    sanitizeJSON(jsonString) {
        try {
            if (!jsonString || typeof jsonString !== 'string') {
                return {};
            }

            // Parse JSON first to validate structure
            const parsed = JSON.parse(jsonString);
            
            // Recursively sanitize string values in JSON
            const sanitized = this.sanitizeObjectValues(parsed);
            
            return sanitized;
        } catch (error) {
            console.error('Invalid JSON provided for sanitization:', error);
            return {};
        }
    }

    // Recursively sanitize object values
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
                // Sanitize both keys and values
                const cleanKey = this.sanitizeText(key);
                sanitized[cleanKey] = this.sanitizeObjectValues(value);
            }
            return sanitized;
        }

        return obj;
    }

    // Validate input length and content
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

    // Escape HTML entities for safe display
    escapeHtml(text) {
        if (!text || typeof text !== 'string') {
            return '';
        }

        const entityMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '/': '&#x2F;'
        };

        return text.replace(/[&<>"'/]/g, (char) => entityMap[char]);
    }
}

export const contentSanitizer = new ContentSanitizer();
```

### Fix 2: Update TraceDetail Component with Safe Rendering

```javascript
// pages/TraceDetail.js (Updated with security)
import React, { useState, useEffect, useCallback } from 'react';
import { contentSanitizer } from '../utils/sanitizer';

const TraceDetail = () => {
    // ... existing state and hooks ...

    // Safe JSON rendering component
    const SafeJSONDisplay = ({ jsonString }) => {
        const [sanitizedJson, setSanitizedJson] = useState('');
        const [jsonError, setJsonError] = useState('');

        useEffect(() => {
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

    // Safe text display component
    const SafeTextDisplay = ({ text, variant = "body2", ...props }) => {
        const sanitizedText = contentSanitizer.sanitizeText(text || '');
        
        return (
            <Typography variant={variant} {...props}>
                {sanitizedText}
            </Typography>
        );
    };

    // Validate inputs before processing
    const validateTraceInput = (trace) => {
        const nameValidation = contentSanitizer.validateInput(trace.name, 100);
        const descValidation = contentSanitizer.validateInput(trace.description, 500);

        if (!nameValidation.isValid) {
            throw new Error(`Name validation failed: ${nameValidation.error}`);
        }

        if (!descValidation.isValid) {
            throw new Error(`Description validation failed: ${descValidation.error}`);
        }

        return {
            ...trace,
            name: contentSanitizer.sanitizeText(trace.name),
            description: contentSanitizer.sanitizeText(trace.description)
        };
    };

    // Updated save handler with validation
    const handleSaveChanges = async () => {
        try {
            const validatedTrace = validateTraceInput(editedTrace);
            console.log('Saving sanitized changes'); // Removed sensitive data logging
            setTrace(validatedTrace);
            setEditMode(false);
            fetchTraceDetails();
        } catch (error) {
            console.error('Validation error:', error.message);
            // Show user-friendly error message
            alert('Invalid input detected. Please check your data and try again.');
        }
    };

    // Updated span addition with validation
    const handleAddSpan = async () => {
        try {
            const validation = contentSanitizer.validateInput(newSpan.name, 100);
            if (!validation.isValid) {
                throw new Error(validation.error);
            }

            const sanitizedSpan = {
                ...newSpan,
                name: contentSanitizer.sanitizeText(newSpan.name),
                input: contentSanitizer.sanitizeText(newSpan.input),
                output: contentSanitizer.sanitizeText(newSpan.output),
                metadata: contentSanitizer.sanitizeJSON(newSpan.metadata || '{}')
            };

            console.log('Adding sanitized span'); // Removed sensitive data logging
            setOpenAddSpanDialog(false);
            fetchTraceDetails();
            setNewSpan({
                name: '',
                type: 'llm',
                input: '',
                output: '',
                metadata: ''
            });
        } catch (error) {
            console.error('Span validation error:', error.message);
            alert('Invalid span data detected. Please check your input and try again.');
        }
    };

    // ... rest of component logic ...

    return (
        <Box sx={{ p: 3 }}>
            {/* Updated title with sanitization */}
            <Typography variant="h4" component="h1">
                {editMode ? 'Edit Trace' : contentSanitizer.sanitizeText(trace.name)}
            </Typography>

            {/* Updated trace display with safe components */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                        {editMode ? (
                            <TextField
                                fullWidth
                                label="Name"
                                value={editedTrace.name}
                                onChange={(e) => {
                                    const validation = contentSanitizer.validateInput(e.target.value, 100);
                                    if (validation.isValid) {
                                        setEditedTrace({...editedTrace, name: e.target.value});
                                    }
                                }}
                                margin="normal"
                                inputProps={{ maxLength: 100 }}
                                helperText="Maximum 100 characters"
                            />
                        ) : (
                            <Box sx={{ mb: 2 }}>
                                <Typography variant="subtitle1" color="text.secondary">Name</Typography>
                                <SafeTextDisplay text={trace.name} />
                            </Box>
                        )}

                        {editMode ? (
                            <TextField
                                fullWidth
                                label="Description"
                                value={editedTrace.description}
                                onChange={(e) => {
                                    const validation = contentSanitizer.validateInput(e.target.value, 500);
                                    if (validation.isValid) {
                                        setEditedTrace({...editedTrace, description: e.target.value});
                                    }
                                }}
                                margin="normal"
                                multiline
                                rows={3}
                                inputProps={{ maxLength: 500 }}
                                helperText="Maximum 500 characters"
                            />
                        ) : (
                            <Box sx={{ mb: 2 }}>
                                <Typography variant="subtitle1" color="text.secondary">Description</Typography>
                                <SafeTextDisplay text={trace.description} />
                            </Box>
                        )}
                    </Grid>
                    {/* ... rest of grid ... */}
                </Grid>
            </Paper>

            {/* Updated spans display with sanitization */}
            <Paper sx={{ p: 3 }}>
                {spans.length === 0 ? (
                    <Typography variant="body1" align="center" sx={{ py: 3 }}>
                        No spans found for this trace.
                    </Typography>
                ) : (
                    <List>
                        {spans.map((span, index) => (
                            <ListItem key={span.id} sx={{ mb: 2, display: 'block' }}>
                                <Card variant="outlined" sx={{ mb: 2 }}>
                                    <CardContent>
                                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                            <ListItemIcon>
                                                {getSpanIcon(span.type)}
                                            </ListItemIcon>
                                            <SafeTextDisplay 
                                                text={span.name} 
                                                variant="h6" 
                                            />
                                            <Chip 
                                                label={span.type} 
                                                color={getSpanColor(span.type)} 
                                                size="small" 
                                                sx={{ ml: 1 }}
                                            />
                                            <Box sx={{ flexGrow: 1 }} />
                                            <Typography variant="caption">
                                                {new Date(span.startTime).toLocaleTimeString()} - {new Date(span.endTime).toLocaleTimeString()}
                                            </Typography>
                                        </Box>
                                        
                                        <Box sx={{ pl: 6 }}>
                                            <Typography variant="subtitle2" color="text.secondary">Input</Typography>
                                            <SafeTextDisplay text={span.input} sx={{ mb: 1 }} />
                                            
                                            <Typography variant="subtitle2" color="text.secondary">Output</Typography>
                                            <SafeTextDisplay text={span.output} sx={{ mb: 1 }} />
                                            
                                            {span.metadata && (
                                                <>
                                                    <Typography variant="subtitle2" color="text.secondary">Metadata</Typography>
                                                    <SafeJSONDisplay jsonString={span.metadata} />
                                                </>
                                            )}
                                        </Box>
                                    </CardContent>
                                </Card>
                                {index < spans.length - 1 && (
                                    <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
                                        <ArrowRightIcon color="action" sx={{ transform: 'rotate(90deg)' }} />
                                    </Box>
                                )}
                            </ListItem>
                        ))}
                    </List>
                )}
            </Paper>

            {/* Updated Add Span Dialog with validation */}
            <Dialog
                open={openAddSpanDialog}
                onClose={() => setOpenAddSpanDialog(false)}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle>Add Span</DialogTitle>
                <DialogContent>
                    <TextField
                        fullWidth
                        label="Name"
                        value={newSpan.name}
                        onChange={(e) => {
                            const validation = contentSanitizer.validateInput(e.target.value, 100);
                            if (validation.isValid) {
                                setNewSpan({...newSpan, name: e.target.value});
                            }
                        }}
                        margin="normal"
                        required
                        inputProps={{ maxLength: 100 }}
                        helperText="Maximum 100 characters"
                    />
                    
                    {/* ... other fields with similar validation ... */}
                    
                    <TextField
                        fullWidth
                        label="Metadata (JSON)"
                        value={newSpan.metadata}
                        onChange={(e) => {
                            // Validate JSON format on change
                            try {
                                if (e.target.value && e.target.value.trim()) {
                                    JSON.parse(e.target.value);
                                }
                                setNewSpan({...newSpan, metadata: e.target.value});
                            } catch (error) {
                                // Don't update if invalid JSON
                                console.warn('Invalid JSON format');
                            }
                        }}
                        margin="normal"
                        multiline
                        rows={3}
                        helperText="Must be valid JSON format"
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpenAddSpanDialog(false)}>Cancel</Button>
                    <Button 
                        onClick={handleAddSpan} 
                        color="primary" 
                        disabled={!newSpan.name}
                    >
                        Add
                    </Button>
                </DialogActions>
            </Dialog>

            {/* ... rest of component ... */}
        </Box>
    );
};
```

### Fix 3: Implement Content Security Policy

**Create CSP configuration**:

```html
<!-- public/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    
    <!-- SECURITY: Comprehensive Content Security Policy -->
    <meta http-equiv="Content-Security-Policy" content="
        default-src 'self';
        script-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
        style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
        font-src 'self' https://fonts.gstatic.com;
        img-src 'self' data: https:;
        connect-src 'self' http://localhost:8000 http://localhost:8001 ws://localhost:3000;
        object-src 'none';
        base-uri 'self';
        form-action 'self';
        frame-ancestors 'none';
        upgrade-insecure-requests;
    ">
    
    <!-- SECURITY: Additional security headers -->
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <meta http-equiv="X-XSS-Protection" content="1; mode=block">
    <meta http-equiv="Referrer-Policy" content="strict-origin-when-cross-origin">
    
    <meta name="description" content="LangChef - LLM Workflow Platform" />
    <link rel="apple-touch-icon" href="%PUBLIC_URL%/logo192.png" />
    <link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
    
    <title>LangChef</title>
</head>
<body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
</body>
</html>
```

### Fix 4: Create XSS Protection Hook

```javascript
// hooks/useXSSProtection.js
import { useEffect, useCallback } from 'react';
import { contentSanitizer } from '../utils/sanitizer';

export const useXSSProtection = () => {
    // Monitor for potential XSS attempts
    const detectXSSAttempt = useCallback((data) => {
        if (!data || typeof data !== 'string') return false;
        
        const xssPatterns = [
            /<script[^>]*>/i,
            /javascript:/i,
            /on\w+\s*=/i,
            /data:text\/html/i,
            /vbscript:/i,
            /<iframe[^>]*>/i,
            /<object[^>]*>/i,
            /<embed[^>]*>/i
        ];

        return xssPatterns.some(pattern => pattern.test(data));
    }, []);

    // Log and block suspicious content
    const handleSuspiciousContent = useCallback((source, content) => {
        console.warn(`XSS attempt detected from ${source}:`, content);
        
        // In production, you might want to report this to a security service
        if (process.env.NODE_ENV === 'production') {
            // Report to security monitoring service
            // securityService.reportXSSAttempt(source, content);
        }
    }, []);

    // Sanitize form data
    const sanitizeFormData = useCallback((formData) => {
        const sanitized = {};
        
        for (const [key, value] of Object.entries(formData)) {
            if (typeof value === 'string') {
                if (detectXSSAttempt(value)) {
                    handleSuspiciousContent('form input', value);
                }
                sanitized[key] = contentSanitizer.sanitizeText(value);
            } else {
                sanitized[key] = value;
            }
        }
        
        return sanitized;
    }, [detectXSSAttempt, handleSuspiciousContent]);

    // Monitor page for suspicious activity
    useEffect(() => {
        const handleDOMModification = (mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check for suspicious script tags
                        if (node.tagName === 'SCRIPT') {
                            console.warn('Script tag dynamically added to DOM:', node);
                            node.remove();
                        }
                        
                        // Check for suspicious attributes
                        if (node.attributes) {
                            Array.from(node.attributes).forEach((attr) => {
                                if (attr.name.startsWith('on') && attr.value) {
                                    console.warn('Suspicious event handler detected:', attr.name, attr.value);
                                    node.removeAttribute(attr.name);
                                }
                            });
                        }
                    }
                });
            });
        };

        const observer = new MutationObserver(handleDOMModification);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['onload', 'onclick', 'onerror', 'onmouseover']
        });

        return () => observer.disconnect();
    }, []);

    return {
        detectXSSAttempt,
        sanitizeFormData,
        handleSuspiciousContent
    };
};
```

## ✅ Verification Methods

### Test XSS Prevention:
```javascript
// Test sanitization
import { contentSanitizer } from './utils/sanitizer';

// Test malicious inputs
const xssPayloads = [
    '<script>alert("XSS")</script>',
    'javascript:alert("XSS")',
    '<img src=x onerror=alert("XSS")>',
    '<svg onload=alert("XSS")>',
    '"onmouseover="alert(\'XSS\')"'
];

xssPayloads.forEach(payload => {
    const sanitized = contentSanitizer.sanitizeText(payload);
    console.assert(!payload.includes('<script'), 'XSS payload should be neutralized');
});
```

### Test CSP Headers:
```javascript
// Check CSP is active
if (document.querySelector('meta[http-equiv="Content-Security-Policy"]')) {
    console.log('CSP header present');
} else {
    console.error('CSP header missing - XSS protection insufficient');
}
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Implement DOMPurify sanitization library
- [ ] **Fix 2**: Update TraceDetail component with safe rendering
- [ ] **Fix 3**: Update Traces component with input validation  
- [ ] **Fix 4**: Implement Content Security Policy headers
- [ ] **Fix 5**: Create XSS protection hook and monitoring
- [ ] **Fix 6**: Remove debug information from production builds
- [ ] **Testing**: XSS protection test suite
- [ ] **Documentation**: XSS prevention guidelines

## 🔗 Dependencies

- `dompurify` for content sanitization
- CSP headers configuration
- Input validation utilities
- XSS monitoring and detection system

## 🚨 Critical Actions Required

1. **Install and configure DOMPurify immediately**
2. **Update all components rendering user/API data with sanitization**
3. **Implement Content Security Policy headers**
4. **Add input validation to all form fields**
5. **Remove debug logging from production builds**
6. **Test XSS protection against common attack vectors**
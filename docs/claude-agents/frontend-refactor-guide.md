# Frontend Refactor Guide for Claude Code

This guide provides specific instructions for the `frontend-react-refactorer` agent when working with the LangChef React frontend.

## React Best Practices

### Component Architecture
Follow these patterns for clean, maintainable React components:

```javascript
// Component structure
import React, { useState, useCallback, useMemo } from 'react';
import { Box, Typography, Button } from '@mui/material';
import PropTypes from 'prop-types';

// Clean component with proper separation
const ExampleComponent = React.memo(({ data, onAction, loading = false }) => {
  // State management
  const [localState, setLocalState] = useState('');
  
  // Memoized computations
  const processedData = useMemo(() => {
    return data?.map(item => ({ ...item, processed: true }));
  }, [data]);
  
  // Event handlers with useCallback
  const handleAction = useCallback((value) => {
    setLocalState(value);
    onAction?.(value);
  }, [onAction]);
  
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6">Example Component</Typography>
      {/* Component JSX */}
    </Box>
  );
});

// PropTypes for runtime type checking
ExampleComponent.propTypes = {
  data: PropTypes.array,
  onAction: PropTypes.func,
  loading: PropTypes.bool
};

export default ExampleComponent;
```

### State Management Patterns

#### Context Usage
```javascript
// Separate contexts by domain
// contexts/AuthContext.js - Authentication only
// contexts/SessionContext.js - Session management
// contexts/ThemeContext.js - UI theming

// Clean context implementation
const AuthContext = createContext({
  isAuthenticated: false,
  user: null,
  login: () => {},
  logout: () => {}
});

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const login = useCallback(async (credentials) => {
    // Login logic
  }, []);
  
  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('token');
  }, []);
  
  const value = useMemo(() => ({
    user,
    isAuthenticated: !!user,
    login,
    logout,
    loading
  }), [user, login, logout, loading]);
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
```

#### Custom Hooks
```javascript
// hooks/useAuth.js - Replace direct context usage
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// hooks/useApi.js - API call patterns
export const useApi = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const execute = useCallback(async (apiCall) => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { execute, loading, error };
};
```

## Component Refactoring Patterns

### 1. Large Component Breakdown
**Before:**
```javascript
// Playground.js (1592 lines)
const Playground = () => {
  // Massive component with everything
  return (
    <Box>
      {/* Chat history sidebar */}
      {/* Model configuration */}
      {/* Chat interface */}
      {/* Input area */}
    </Box>
  );
};
```

**After:**
```javascript
// Playground.js (main layout - ~150 lines)
const Playground = () => {
  return (
    <Box display="flex" height="100vh">
      <PlaygroundSidebar />
      <PlaygroundMain />
    </Box>
  );
};

// components/Playground/PlaygroundSidebar.js
// components/Playground/PlaygroundMain.js
// components/Playground/ChatInterface.js
// components/Playground/ModelConfig.js
```

### 2. Props Drilling Elimination
**Before:**
```javascript
// Props passed through multiple levels
<Parent user={user} settings={settings} onUpdate={onUpdate}>
  <Child user={user} settings={settings} onUpdate={onUpdate}>
    <GrandChild user={user} onUpdate={onUpdate} />
  </Child>
</Parent>
```

**After:**
```javascript
// Use context or component composition
<UserProvider>
  <SettingsProvider>
    <Parent>
      <Child>
        <GrandChild />
      </Child>
    </Parent>
  </SettingsProvider>
</UserProvider>
```

### 3. API Layer Consolidation
**Before:**
```javascript
// Scattered API calls
const response1 = await axios.post('/api/prompts', data);
const response2 = await fetch('/api/models', { method: 'POST' });
const response3 = await modelsApi.create(data);
```

**After:**
```javascript
// Unified API client
const response1 = await apiClient.prompts.create(data);
const response2 = await apiClient.models.create(data);
const response3 = await apiClient.experiments.run(config);
```

## Material-UI Best Practices

### Theme Usage
```javascript
// Use theme consistently
const useStyles = makeStyles((theme) => ({
  root: {
    padding: theme.spacing(2),
    backgroundColor: theme.palette.background.paper
  }
}));

// Or with sx prop
<Box sx={{ 
  p: 2, 
  bgcolor: 'background.paper',
  borderRadius: 1 
}}>
```

### Component Consistency
```javascript
// Consistent Material-UI usage
const FormComponent = () => {
  return (
    <Paper elevation={1} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Form Title
      </Typography>
      <TextField
        fullWidth
        variant="outlined"
        margin="normal"
        // ... props
      />
      <Button
        variant="contained"
        color="primary"
        sx={{ mt: 2 }}
      >
        Submit
      </Button>
    </Paper>
  );
};
```

## Performance Optimization

### Memoization Strategy
```javascript
// Component memoization
const ExpensiveComponent = React.memo(({ data, onAction }) => {
  // Heavy computations
  const processedData = useMemo(() => {
    return heavyProcessing(data);
  }, [data]);
  
  // Event handler memoization
  const handleClick = useCallback((id) => {
    onAction(id);
  }, [onAction]);
  
  return (
    <div>
      {processedData.map(item => (
        <ItemComponent 
          key={item.id} 
          item={item} 
          onClick={handleClick} 
        />
      ))}
    </div>
  );
});
```

### Code Splitting
```javascript
// Lazy loading for large components
const Playground = lazy(() => import('./pages/Playground'));
const Dashboard = lazy(() => import('./pages/Dashboard'));

// In routing
<Suspense fallback={<CircularProgress />}>
  <Routes>
    <Route path="/playground" element={<Playground />} />
    <Route path="/dashboard" element={<Dashboard />} />
  </Routes>
</Suspense>
```

## Error Handling

### Error Boundaries
```javascript
// components/ErrorBoundary.js
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <Box p={3} textAlign="center">
          <Typography variant="h6" color="error">
            Something went wrong
          </Typography>
          <Button 
            onClick={() => this.setState({ hasError: false })}
            sx={{ mt: 2 }}
          >
            Try Again
          </Button>
        </Box>
      );
    }
    
    return this.props.children;
  }
}
```

## File Organization

```
src/
├── components/           # Reusable UI components
│   ├── common/          # Generic components (Button, Modal, etc.)
│   ├── forms/           # Form-specific components
│   └── layout/          # Layout components (Header, Sidebar)
├── pages/               # Route-level components
├── hooks/               # Custom React hooks
├── contexts/            # React context providers
├── services/            # API and external services
├── utils/               # Pure utility functions
├── constants/           # Application constants
└── types/              # TypeScript type definitions (future)
```

## Refactoring Checklist

### ✅ Component Quality
- [ ] Components under 200 lines
- [ ] Single responsibility principle
- [ ] Proper PropTypes or TypeScript
- [ ] Memoization where appropriate
- [ ] Clean JSX with proper formatting

### ✅ State Management
- [ ] Context separation by domain
- [ ] Custom hooks for reusable logic
- [ ] No props drilling
- [ ] Proper state updates (immutable)

### ✅ Performance
- [ ] React.memo for pure components
- [ ] useCallback for event handlers
- [ ] useMemo for expensive computations
- [ ] Code splitting for large routes

### ✅ Material-UI
- [ ] Consistent theme usage
- [ ] Proper sx prop usage
- [ ] Accessible components
- [ ] Responsive design patterns

### ✅ Error Handling
- [ ] Error boundaries in place
- [ ] Proper loading states
- [ ] User-friendly error messages
- [ ] Graceful degradation
import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  CircularProgress,
  Container,
  Alert,
  Divider,
  Stack
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const { isAuthenticated, login, loginWithAWS, loading } = useAuth();
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get the redirect path from location state or default to '/'
  const from = location.state?.from?.pathname || '/';
  
  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);
  
  const handleLogin = async () => {
    setError(null);
    try {
      const success = await login();
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError('Login failed. Please try again.');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('An unexpected error occurred. Please try again.');
    }
  };
  
  const handleAWSLogin = async () => {
    setError(null);
    try {
      const success = await loginWithAWS();
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError('AWS login failed. Please check that AWS credentials are properly configured on the server.');
      }
    } catch (err) {
      console.error('AWS login error:', err);
      setError('An unexpected error occurred. Please try again.');
    }
  };
  
  return (
    <Container maxWidth="sm">
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        py: 4
      }}>
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography variant="h4" component="h1" align="center" gutterBottom>
            LLM Workflow Platform
          </Typography>
          
          <Typography variant="h6" align="center" color="text.secondary" sx={{ mb: 4 }}>
            Sign in to continue
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}
          
          {location.state?.sessionExpired && (
            <Alert severity="warning" sx={{ mb: 3 }}>
              Your session has expired. Please sign in again.
            </Alert>
          )}
          
          <Stack spacing={2} sx={{ mb: 3 }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleLogin}
              disabled={loading}
              sx={{ 
                py: 1.5, 
                px: 4,
                backgroundColor: '#232F3E', // AWS color
                '&:hover': {
                  backgroundColor: '#1A2530',
                },
              }}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
              ) : (
                <>Sign in with AWS SSO</>
              )}
            </Button>
            
            <Divider sx={{ my: 2 }}>OR</Divider>
            
            <Button
              variant="outlined"
              size="large"
              onClick={handleAWSLogin}
              disabled={loading}
              sx={{ 
                py: 1.5, 
                px: 4,
                borderColor: '#232F3E',
                color: '#232F3E',
                '&:hover': {
                  borderColor: '#1A2530',
                  backgroundColor: 'rgba(35, 47, 62, 0.04)',
                },
              }}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
              ) : (
                <>Use AWS Credentials</>
              )}
            </Button>
          </Stack>
          
          <Typography variant="body2" align="center" sx={{ mt: 4, color: 'text.secondary' }}>
            This application uses AWS authentication for secure access.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default Login; 
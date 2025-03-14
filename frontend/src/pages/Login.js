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
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Link
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const { isAuthenticated, login, loginWithAWS, loading, awsSSOState, error: authError } = useAuth();
  const [error, setError] = useState(null);
  const [showVerificationDialog, setShowVerificationDialog] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get the redirect path from location state or default to '/'
  const from = location.state?.from?.pathname || '/';
  
  // Redirect if already authenticated
  useEffect(() => {
    console.log('Login - Authentication state:', { 
      isAuthenticated, 
      from,
      awsSSOState,
      loading
    });
    
    // Only redirect if not loading and authenticated
    if (!loading && isAuthenticated) {
      console.log('Login - Already authenticated, redirecting to:', from);
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from, awsSSOState, loading]);

  // Show verification dialog when AWS SSO state is updated
  useEffect(() => {
    console.log('Login - AWS SSO state updated:', awsSSOState);
    if (awsSSOState && awsSSOState.device_code) {
      // We have an active AWS SSO authentication flow
      setShowVerificationDialog(true);
      // Clear any error if we're in polling state
      setError(null);
    } else {
      setShowVerificationDialog(false);
    }
  }, [awsSSOState]);
  
  // Handle auth errors
  useEffect(() => {
    if (authError && !awsSSOState) {
      // Only set error if we're not in polling state (authorization_pending is expected)
      setError(authError);
    } else if (awsSSOState) {
      // Clear any errors when we're in polling state
      setError(null);
    }
  }, [authError, awsSSOState]);
  
  const handleLogin = async () => {
    setError(null);
    try {
      await login();
      // No need to set error here - we'll get it from the auth context if needed
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

  const handleCloseVerificationDialog = () => {
    setShowVerificationDialog(false);
  };
  
  // Show a different message when we're in SSO polling state
  const isPolling = awsSSOState && awsSSOState.device_code;
  
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
          
          {error && !isPolling && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}
          
          {isPolling && (
            <Alert severity="info" sx={{ mb: 3 }}>
              AWS SSO authentication in progress. Please complete the verification in the opened browser window.
              This process may take a few moments. Do not close this page or refresh until authentication is complete.
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
              disabled={loading || isPolling}
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
              disabled={loading || isPolling}
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

      {/* AWS SSO Verification Dialog */}
      <Dialog 
        open={showVerificationDialog} 
        onClose={handleCloseVerificationDialog}
        maxWidth="sm"
        fullWidth
        disableEscapeKeyDown // Prevent closing with ESC key
      >
        <DialogTitle>
          <Typography variant="h6" component="div" align="center">
            AWS SSO Verification
          </Typography>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <Typography variant="body1" gutterBottom>
              Please enter the following code at the AWS SSO verification page:
            </Typography>
            
            <TextField
              variant="outlined"
              value={awsSSOState?.user_code || ''}
              fullWidth
              InputProps={{
                readOnly: true,
                sx: { 
                  fontSize: '24px', 
                  textAlign: 'center',
                  letterSpacing: '0.5em',
                  fontWeight: 'bold'
                }
              }}
              sx={{ my: 3 }}
            />
            
            <Typography variant="body2" color="text.secondary" gutterBottom>
              If the AWS SSO verification page didn't open automatically, please click the link below:
            </Typography>
            
            <Link 
              href={awsSSOState?.verification_uri_complete || '#'} 
              target="_blank"
              rel="noopener noreferrer"
              sx={{ display: 'inline-block', mt: 1 }}
            >
              Open AWS SSO Verification Page
            </Link>
            
            <Box sx={{ mt: 4 }}>
              <CircularProgress size={24} sx={{ mr: 2 }} />
              <Typography variant="body2" color="text.secondary" display="inline">
                Waiting for verification... Please complete the authentication in the browser window.
              </Typography>
            </Box>

            <Box sx={{ mt: 3, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Authentication will expire in {awsSSOState ? Math.round((new Date(awsSSOState.expiresAt) - new Date()) / 60000) : 0} minutes if not completed
              </Typography>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseVerificationDialog} color="primary">
            Cancel Authentication
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Login; 
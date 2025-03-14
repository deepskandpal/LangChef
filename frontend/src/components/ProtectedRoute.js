import React, { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Spinner, Alert, Button } from 'react-bootstrap';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = () => {
  const { isAuthenticated, loading, awsSSOState, user, error, login } = useAuth();
  const location = useLocation();
  const [authRetryCount, setAuthRetryCount] = useState(0);
  const [showRetryOption, setShowRetryOption] = useState(false);
  const [authError, setAuthError] = useState(null);
  
  // Added comprehensive logging for debug purposes
  useEffect(() => {
    console.log('ProtectedRoute - Auth state changed:', { 
      path: location.pathname,
      isAuthenticated, 
      loading, 
      isPolling: !!awsSSOState,
      hasUser: !!user,
      user: user ? `${user.username} (${user.email})` : 'none',
      error,
      retryCount: authRetryCount
    });
  }, [isAuthenticated, loading, awsSSOState, user, location.pathname, error, authRetryCount]);

  // Show retry option after 30 seconds if still in polling state
  useEffect(() => {
    let timer;
    if (awsSSOState && !showRetryOption) {
      timer = setTimeout(() => {
        setShowRetryOption(true);
      }, 30000); // Show retry option after 30 seconds
    } else if (!awsSSOState) {
      setShowRetryOption(false);
    }
    
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [awsSSOState, showRetryOption]);

  // Handle error updates
  useEffect(() => {
    if (error) {
      setAuthError(error);
    } else {
      setAuthError(null);
    }
  }, [error]);

  // Handler for manual retry of authentication
  const handleRetryAuth = async () => {
    setAuthRetryCount(prev => prev + 1);
    setShowRetryOption(false);
    setAuthError(null);
    
    try {
      const success = await login(); // Attempt to restart the authentication flow
      
      if (!success) {
        setAuthError("Failed to restart authentication. Please try again or refresh the page.");
      }
    } catch (err) {
      console.error("Error restarting authentication:", err);
      setAuthError("An unexpected error occurred. Please refresh the page and try again.");
    }
  };

  // Helper to open the verification URI in a new window
  const openVerificationPage = () => {
    if (awsSSOState && awsSSOState.verification_uri_complete) {
      window.open(awsSSOState.verification_uri_complete, '_blank');
    }
  };

  // Show loading spinner while checking auth state
  if (loading && !awsSSOState) {
    console.log('ProtectedRoute - Still loading authentication state');
    return (
      <div className="d-flex justify-content-center align-items-center flex-column" style={{ minHeight: '100vh' }}>
        <Spinner animation="border" role="status" className="mb-3">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
        <div className="ms-2">Verifying authentication...</div>
      </div>
    );
  }

  // If authentication is in progress (polling for AWS SSO token), show loading indicator
  // but maintain the current URL to prevent navigation issues
  if (awsSSOState) {
    console.log('ProtectedRoute - AWS SSO authentication in progress');
    
    // Calculate remaining time
    const expiryTime = new Date(awsSSOState.expiresAt);
    const now = new Date();
    const remainingMinutes = Math.max(0, Math.round((expiryTime - now) / 60000));
    const remainingSeconds = Math.max(0, Math.round((expiryTime - now) / 1000) % 60);
    
    // Format time remaining
    let timeRemaining = "";
    if (remainingMinutes > 0) {
      timeRemaining = `${remainingMinutes} minute${remainingMinutes !== 1 ? 's' : ''}`;
      if (remainingSeconds > 0) {
        timeRemaining += ` and ${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''}`;
      }
    } else if (remainingSeconds > 0) {
      timeRemaining = `${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''}`;
    } else {
      timeRemaining = "less than a second";
    }
    
    return (
      <div className="d-flex justify-content-center align-items-center flex-column" style={{ minHeight: '100vh', padding: '2rem' }}>
        <Spinner animation="border" role="status" className="mb-3">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
        
        <h4 className="mb-3">AWS SSO Authentication</h4>
        
        <Alert variant="info" className="mb-3 text-center">
          <div className="mb-2">Waiting for AWS SSO authentication to complete...</div>
          <div className="text-muted">
            Please complete the authentication in the browser window that opened.
          </div>
          {remainingMinutes > 0 || remainingSeconds > 0 ? (
            <div className="mt-2 small">
              <strong>Time remaining:</strong> {timeRemaining}
            </div>
          ) : (
            <div className="mt-2 small text-danger">
              <strong>Authentication is about to expire!</strong>
            </div>
          )}
        </Alert>
        
        <div className="text-center mb-3">
          <div className="fw-bold mb-2">Verification Code</div>
          <div 
            className="badge bg-light text-dark p-3 mb-2" 
            style={{ fontSize: '1.2rem', letterSpacing: '0.2rem' }}
          >
            {awsSSOState.user_code}
          </div>
          <div>
            <Button 
              variant="link" 
              size="sm" 
              onClick={openVerificationPage}
              className="text-decoration-none"
            >
              Open verification page
            </Button>
          </div>
        </div>
        
        {showRetryOption && (
          <div className="mt-3 text-center">
            <div className="mb-2 text-muted">
              It's taking longer than expected. Do you want to restart the authentication process?
            </div>
            <Button variant="outline-primary" onClick={handleRetryAuth}>
              Restart Authentication
            </Button>
          </div>
        )}
        
        {authError && (
          <Alert variant="warning" className="mt-3">
            {authError}
          </Alert>
        )}
      </div>
    );
  }

  // If not authenticated and not in polling state, redirect to login
  if (!isAuthenticated) {
    console.log('ProtectedRoute - User not authenticated, redirecting to login');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If authenticated, render the child routes
  console.log('ProtectedRoute - User authenticated, rendering child routes');
  return <Outlet />;
};

export default ProtectedRoute; 
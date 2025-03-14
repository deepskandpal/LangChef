import React, { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Spinner, Alert, Button, Badge } from 'react-bootstrap';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = () => {
  const { 
    isAuthenticated, 
    loading, 
    awsSSOState, 
    user, 
    error, 
    login, 
    refreshSession,
    sessionExpiry
  } = useAuth();
  const location = useLocation();
  const [authRetryCount, setAuthRetryCount] = useState(0);
  const [showRetryOption, setShowRetryOption] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState('');
  const [timerId, setTimerId] = useState(null);
  
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
      retryCount: authRetryCount,
      sessionExpiry: sessionExpiry ? new Date(sessionExpiry).toISOString() : null
    });
  }, [isAuthenticated, loading, awsSSOState, user, location.pathname, error, authRetryCount, sessionExpiry]);

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

  // Update time remaining for AWS SSO authentication
  useEffect(() => {
    if (!awsSSOState) {
      if (timerId) {
        clearInterval(timerId);
        setTimerId(null);
      }
      return;
    }
    
    // Function to update time remaining
    const updateTimeRemaining = () => {
      if (!awsSSOState) return;
      
      // Calculate remaining time
      const expiryTime = new Date(awsSSOState.expiresAt);
      const now = new Date();
      const remainingMinutes = Math.max(0, Math.round((expiryTime - now) / 60000));
      const remainingSeconds = Math.max(0, Math.round((expiryTime - now) / 1000) % 60);
      
      // Format time remaining
      let formattedTime = "";
      if (remainingMinutes > 0) {
        formattedTime = `${remainingMinutes} minute${remainingMinutes !== 1 ? 's' : ''}`;
        if (remainingSeconds > 0) {
          formattedTime += ` and ${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''}`;
        }
      } else if (remainingSeconds > 0) {
        formattedTime = `${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''}`;
      } else {
        formattedTime = "less than a second";
      }
      
      setTimeRemaining(formattedTime);
    };
    
    // Update immediately
    updateTimeRemaining();
    
    // Set up interval for regular updates
    const timer = setInterval(updateTimeRemaining, 1000);
    setTimerId(timer);
    
    return () => {
      clearInterval(timer);
    };
  }, [awsSSOState]);

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

  // Handler for manual session refresh
  const handleManualRefresh = async () => {
    setAuthError(null);
    
    try {
      const success = await refreshSession();
      
      if (success) {
        // Show success message briefly
        setAuthError({
          type: 'success',
          message: 'Session refreshed successfully.'
        });
        
        // Clear the message after 3 seconds
        setTimeout(() => {
          setAuthError(null);
        }, 3000);
      } else {
        setAuthError({
          type: 'warning',
          message: 'Failed to refresh session. Please try again or log out and back in.'
        });
      }
    } catch (err) {
      console.error("Error refreshing session:", err);
      setAuthError({
        type: 'danger',
        message: 'An error occurred while refreshing your session.'
      });
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
  if (awsSSOState) {
    console.log('ProtectedRoute - AWS SSO authentication in progress');
    
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
          {timeRemaining ? (
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
          <Alert variant={authError.type || "warning"} className="mt-3">
            {authError.message || authError}
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

  // Session status display for authenticated users
  const renderSessionStatus = () => {
    if (!sessionExpiry) return null;
    
    const now = new Date();
    const expiry = new Date(sessionExpiry);
    const timeToExpiry = expiry - now;
    const hoursRemaining = Math.floor(timeToExpiry / (1000 * 60 * 60));
    
    let variant = "success";
    if (hoursRemaining < 1) {
      variant = "danger";
    } else if (hoursRemaining < 3) {
      variant = "warning";
    }
    
    return (
      <div className="position-fixed bottom-0 end-0 m-3">
        <div className="d-flex align-items-center p-2 bg-light rounded shadow-sm">
          <Badge bg={variant} className="me-2">
            {hoursRemaining < 1 ? 'Session expiring soon' : `${hoursRemaining}h remaining`}
          </Badge>
          <Button 
            size="sm" 
            variant="outline-secondary" 
            onClick={handleManualRefresh}
          >
            Refresh
          </Button>
        </div>
      </div>
    );
  };

  // If authenticated, render the child routes
  console.log('ProtectedRoute - User authenticated, rendering child routes');
  return (
    <>
      <Outlet />
      {renderSessionStatus()}
    </>
  );
};

export default ProtectedRoute; 
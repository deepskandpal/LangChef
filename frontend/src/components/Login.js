import React, { useEffect, useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import { Button, Card, Form, Alert, Spinner } from 'react-bootstrap';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const { isAuthenticated, login, loading, error, awsSSOState } = useAuth();
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState(null);
  const location = useLocation();

  // Get the redirect path from location state or default to dashboard
  const from = location.state?.from?.pathname || '/dashboard';
  
  // Track if we're currently in the polling state
  const isPolling = !!awsSSOState;

  useEffect(() => {
    // Log the authentication state for debugging
    console.log('Login component - Auth state:', { 
      isAuthenticated, 
      loading, 
      isPolling,
      error,
      redirectTo: from
    });
  }, [isAuthenticated, loading, isPolling, error, from]);

  // If authenticated and not loading, redirect to the intended destination
  if (isAuthenticated && !loading) {
    console.log(`Login component - User is authenticated, redirecting to ${from}`);
    return <Navigate to={from} replace />;
  }

  const handleAWSLogin = async (e) => {
    e.preventDefault();
    setLocalLoading(true);
    setLocalError(null);
    
    try {
      console.log('Login component - Starting AWS SSO login flow');
      await login();
    } catch (err) {
      console.error('Login component - Login error:', err);
      setLocalError('Failed to start login process. Please try again.');
    } finally {
      setLocalLoading(false);
    }
  };

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
      <Card style={{ width: '400px' }}>
        <Card.Body>
          <Card.Title className="text-center mb-4">
            <h2>Login to LangChef</h2>
          </Card.Title>
          
          {error && <Alert variant="danger">{error}</Alert>}
          {localError && <Alert variant="danger">{localError}</Alert>}
          
          {isPolling && (
            <Alert variant="info" className="d-flex align-items-center">
              <Spinner animation="border" size="sm" className="me-2" />
              <div>
                Please complete the AWS SSO authentication in the new window. Waiting for approval...
              </div>
            </Alert>
          )}
          
          <Form>
            <div className="d-grid gap-2">
              <Button 
                variant="primary" 
                onClick={handleAWSLogin}
                disabled={loading || localLoading || isPolling}
              >
                {(loading || localLoading) && !isPolling ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    Signing in...
                  </>
                ) : isPolling ? (
                  'Waiting for AWS SSO...'
                ) : (
                  'Sign in with AWS SSO'
                )}
              </Button>
            </div>
          </Form>
          
          <div className="w-100 text-center mt-3">
            <Link to="/forgot-password">Forgot Password?</Link>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default Login; 
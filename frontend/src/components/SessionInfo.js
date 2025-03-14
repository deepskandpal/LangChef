import React, { useState, useEffect } from 'react';
import { Card, ListGroup, Badge, Button, Spinner, Alert } from 'react-bootstrap';
import { useAuth } from '../contexts/AuthContext';

const SessionInfo = () => {
  const { 
    user, 
    sessionExpiry, 
    refreshSession, 
    logout,
    isSessionRefreshing
  } = useAuth();
  
  const [timeRemaining, setTimeRemaining] = useState('');
  const [timerId, setTimerId] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [refreshStatus, setRefreshStatus] = useState(null);
  
  // Format the session expiry time
  useEffect(() => {
    if (!sessionExpiry) {
      setTimeRemaining('Unknown');
      return;
    }
    
    const updateTimeRemaining = () => {
      const now = new Date();
      const expiry = new Date(sessionExpiry);
      const diff = expiry - now;
      
      if (diff <= 0) {
        setTimeRemaining('Expired');
        return;
      }
      
      // Format differently based on how much time is left
      if (diff > 24 * 60 * 60 * 1000) {
        // More than a day
        const days = Math.floor(diff / (24 * 60 * 60 * 1000));
        const hours = Math.floor((diff % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
        setTimeRemaining(`${days}d ${hours}h`);
      } else if (diff > 60 * 60 * 1000) {
        // More than an hour
        const hours = Math.floor(diff / (60 * 60 * 1000));
        const minutes = Math.floor((diff % (60 * 60 * 1000)) / (60 * 1000));
        setTimeRemaining(`${hours}h ${minutes}m`);
      } else if (diff > 60 * 1000) {
        // More than a minute
        const minutes = Math.floor(diff / (60 * 1000));
        const seconds = Math.floor((diff % (60 * 1000)) / 1000);
        setTimeRemaining(`${minutes}m ${seconds}s`);
      } else {
        // Less than a minute
        const seconds = Math.floor(diff / 1000);
        setTimeRemaining(`${seconds}s`);
      }
    };
    
    // Update immediately
    updateTimeRemaining();
    
    // Set up interval for updates
    const timer = setInterval(updateTimeRemaining, 1000);
    setTimerId(timer);
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [sessionExpiry]);
  
  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (timerId) clearInterval(timerId);
    };
  }, [timerId]);
  
  // Handle manual session refresh
  const handleRefreshSession = async () => {
    setRefreshStatus({ type: 'info', message: 'Refreshing session...' });
    
    try {
      const success = await refreshSession();
      
      if (success) {
        setLastRefreshed(new Date());
        setRefreshStatus({ type: 'success', message: 'Session refreshed successfully.' });
        
        // Clear the success message after 3 seconds
        setTimeout(() => {
          setRefreshStatus(null);
        }, 3000);
      } else {
        setRefreshStatus({ type: 'warning', message: 'Failed to refresh session. Please try again or log out and back in.' });
      }
    } catch (error) {
      console.error('Error refreshing session:', error);
      setRefreshStatus({ type: 'danger', message: 'An error occurred while refreshing your session.' });
    }
  };
  
  // Calculate session status color
  const getSessionStatusVariant = () => {
    if (!sessionExpiry) return 'secondary';
    
    const now = new Date();
    const expiry = new Date(sessionExpiry);
    const hoursRemaining = (expiry - now) / (1000 * 60 * 60);
    
    if (hoursRemaining <= 0) return 'danger';
    if (hoursRemaining < 1) return 'danger';
    if (hoursRemaining < 3) return 'warning';
    return 'success';
  };
  
  // Format date with native JavaScript
  const formatDate = (date) => {
    if (!date) return 'N/A';
    
    const d = new Date(date);
    
    // Format: MMM DD, YYYY HH:MM:SS
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[d.getMonth()];
    const day = d.getDate();
    const year = d.getFullYear();
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    const seconds = d.getSeconds().toString().padStart(2, '0');
    
    return `${month} ${day}, ${year} ${hours}:${minutes}:${seconds}`;
  };
  
  if (!user) {
    return (
      <Card className="shadow-sm">
        <Card.Body className="text-center p-4">
          <div className="text-muted">No active session information available</div>
        </Card.Body>
      </Card>
    );
  }
  
  return (
    <Card className="shadow-sm mb-4">
      <Card.Header className="bg-light d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Session Information</h5>
        <Badge bg={getSessionStatusVariant()}>
          {sessionExpiry ? 'Active' : 'Unknown'}
        </Badge>
      </Card.Header>
      
      <ListGroup variant="flush">
        <ListGroup.Item>
          <div className="d-flex justify-content-between">
            <span className="text-muted">User:</span>
            <span className="fw-semibold">{user.username}</span>
          </div>
        </ListGroup.Item>
        
        <ListGroup.Item>
          <div className="d-flex justify-content-between">
            <span className="text-muted">Email:</span>
            <span>{user.email || 'N/A'}</span>
          </div>
        </ListGroup.Item>
        
        <ListGroup.Item>
          <div className="d-flex justify-content-between">
            <span className="text-muted">Session Expires:</span>
            <span className={`${getSessionStatusVariant() === 'danger' ? 'text-danger' : ''}`}>
              {sessionExpiry ? formatDate(sessionExpiry) : 'Unknown'}
            </span>
          </div>
        </ListGroup.Item>
        
        <ListGroup.Item>
          <div className="d-flex justify-content-between">
            <span className="text-muted">Time Remaining:</span>
            <span className={`${getSessionStatusVariant() === 'danger' ? 'text-danger fw-bold' : ''}`}>
              {timeRemaining}
            </span>
          </div>
        </ListGroup.Item>
        
        {lastRefreshed && (
          <ListGroup.Item>
            <div className="d-flex justify-content-between">
              <span className="text-muted">Last Refreshed:</span>
              <span>{formatDate(lastRefreshed)}</span>
            </div>
          </ListGroup.Item>
        )}
      </ListGroup>
      
      <Card.Body>
        {refreshStatus && (
          <Alert variant={refreshStatus.type} className="mb-3">
            {refreshStatus.message}
          </Alert>
        )}
        
        <div className="d-grid gap-2">
          <Button 
            variant="outline-primary" 
            onClick={handleRefreshSession}
            disabled={isSessionRefreshing}
          >
            {isSessionRefreshing ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Refreshing Session...
              </>
            ) : (
              'Refresh Session'
            )}
          </Button>
          
          <Button 
            variant="outline-danger" 
            onClick={logout}
          >
            Sign Out
          </Button>
        </div>
        
        <div className="mt-3 small text-muted">
          <p className="mb-1">
            Your session will automatically refresh in the background before expiration.
            Manual refresh is available if needed.
          </p>
        </div>
      </Card.Body>
    </Card>
  );
};

export default SessionInfo; 
import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  Typography, 
  Box,
  LinearProgress,
  Alert
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const SessionExpiryAlert = () => {
  const { sessionExpiry, refreshSession, logout, timeUntilExpiry } = useAuth();
  const [open, setOpen] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // Show alert when session is about to expire (30 minutes before)
  useEffect(() => {
    if (!sessionExpiry) return;

    const checkInterval = setInterval(() => {
      const timeRemaining = timeUntilExpiry();
      const thirtyMinutes = 30 * 60 * 1000; // 30 minutes in milliseconds
      
      setTimeLeft(timeRemaining);
      
      if (timeRemaining > 0 && timeRemaining <= thirtyMinutes) {
        setOpen(true);
      } else if (timeRemaining <= 0) {
        setOpen(false);
        logout();
      }
    }, 1000); // Check every second
    
    return () => clearInterval(checkInterval);
  }, [sessionExpiry, timeUntilExpiry, logout]);

  const handleRefresh = async () => {
    setError(null);
    setRefreshing(true);
    
    try {
      const success = await refreshSession();
      if (success) {
        setOpen(false);
      } else {
        setError('Failed to refresh session. Please try again or log out and log back in.');
      }
    } catch (err) {
      console.error('Session refresh error:', err);
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleLogout = () => {
    setOpen(false);
    logout();
  };

  // Format time remaining as mm:ss
  const formatTimeRemaining = () => {
    if (!timeLeft) return '00:00';
    
    const minutes = Math.floor(timeLeft / 60000);
    const seconds = Math.floor((timeLeft % 60000) / 1000);
    
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  // Calculate progress value (0-100)
  const calculateProgress = () => {
    if (!timeLeft) return 0;
    
    const thirtyMinutes = 30 * 60 * 1000; // 30 minutes in milliseconds
    return (timeLeft / thirtyMinutes) * 100;
  };

  return (
    <Dialog
      open={open}
      onClose={() => {}}
      aria-labelledby="session-expiry-dialog-title"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle id="session-expiry-dialog-title">
        Session Expiring Soon
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        <Typography variant="body1" gutterBottom>
          Your session will expire in:
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="div" sx={{ mr: 2, fontFamily: 'monospace' }}>
            {formatTimeRemaining()}
          </Typography>
          <Box sx={{ width: '100%' }}>
            <LinearProgress 
              variant="determinate" 
              value={calculateProgress()} 
              color={timeLeft < 5 * 60 * 1000 ? 'error' : 'warning'} 
              sx={{ height: 10, borderRadius: 5 }}
            />
          </Box>
        </Box>
        
        <Typography variant="body2" color="text.secondary">
          For security reasons, your session will expire after 24 hours of inactivity. 
          Would you like to extend your session?
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleLogout} color="error">
          Log Out
        </Button>
        <Button 
          onClick={handleRefresh} 
          variant="contained" 
          color="primary"
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Extend Session'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SessionExpiryAlert; 
import React, { useState } from 'react';
import { 
  Box, 
  Avatar, 
  Menu, 
  MenuItem, 
  ListItemIcon, 
  Divider, 
  IconButton, 
  Tooltip, 
  Typography,
  Badge
} from '@mui/material';
import { 
  Logout as LogoutIcon,
  AccountCircle as AccountCircleIcon,
  Refresh as RefreshIcon,
  AccessTime as AccessTimeIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const UserProfile = () => {
  const { user, logout, refreshSession, sessionExpiry } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const open = Boolean(anchorEl);
  
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleClose = () => {
    setAnchorEl(null);
  };
  
  const handleLogout = () => {
    handleClose();
    logout();
  };
  
  const handleRefreshSession = async () => {
    setRefreshing(true);
    await refreshSession();
    setRefreshing(false);
    handleClose();
  };
  
  // Format session expiry time
  const formatSessionExpiry = () => {
    if (!sessionExpiry) return 'Unknown';
    
    const now = new Date();
    const expiry = new Date(sessionExpiry);
    
    // If expiry is today, show time only
    if (now.toDateString() === expiry.toDateString()) {
      return `Today at ${expiry.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    
    // If expiry is tomorrow, show "Tomorrow at time"
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    if (tomorrow.toDateString() === expiry.toDateString()) {
      return `Tomorrow at ${expiry.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    
    // Otherwise show full date and time
    return expiry.toLocaleString([], { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  // Calculate time until session expiry
  const getTimeUntilExpiry = () => {
    if (!sessionExpiry) return null;
    
    const now = new Date();
    const expiry = new Date(sessionExpiry);
    const diff = expiry - now;
    
    // If less than 1 hour, show minutes
    if (diff < 60 * 60 * 1000) {
      const minutes = Math.floor(diff / (60 * 1000));
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
    
    // If less than 1 day, show hours
    if (diff < 24 * 60 * 60 * 1000) {
      const hours = Math.floor(diff / (60 * 60 * 1000));
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    }
    
    // Otherwise show days
    const days = Math.floor(diff / (24 * 60 * 60 * 1000));
    return `${days} day${days !== 1 ? 's' : ''}`;
  };
  
  // Determine badge color based on time until expiry
  const getBadgeColor = () => {
    if (!sessionExpiry) return 'error';
    
    const now = new Date();
    const expiry = new Date(sessionExpiry);
    const diff = expiry - now;
    
    // If less than 1 hour, show red
    if (diff < 60 * 60 * 1000) {
      return 'error';
    }
    
    // If less than 4 hours, show warning
    if (diff < 4 * 60 * 60 * 1000) {
      return 'warning';
    }
    
    // Otherwise show success
    return 'success';
  };
  
  // Get the display name from user object with fallbacks
  const getDisplayName = () => {
    if (!user) return 'User';
    return user.full_name || user.name || user.username || user.email?.split('@')[0] || 'User';
  };
  
  // Get the first letter of the display name for the avatar
  const getAvatarInitial = () => {
    const displayName = getDisplayName();
    return displayName.charAt(0).toUpperCase();
  };
  
  if (!user) return null;
  
  return (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', textAlign: 'center' }}>
        <Tooltip title="Account settings">
          <IconButton
            onClick={handleClick}
            size="small"
            sx={{ ml: 2 }}
            aria-controls={open ? 'account-menu' : undefined}
            aria-haspopup="true"
            aria-expanded={open ? 'true' : undefined}
          >
            <Badge
              overlap="circular"
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              variant="dot"
              color={getBadgeColor()}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                {getAvatarInitial()}
              </Avatar>
            </Badge>
          </IconButton>
        </Tooltip>
      </Box>
      <Menu
        anchorEl={anchorEl}
        id="account-menu"
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        PaperProps={{
          elevation: 0,
          sx: {
            overflow: 'visible',
            filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.32))',
            mt: 1.5,
            width: 320,
            '& .MuiAvatar-root': {
              width: 32,
              height: 32,
              ml: -0.5,
              mr: 1,
            },
            '&:before': {
              content: '""',
              display: 'block',
              position: 'absolute',
              top: 0,
              right: 14,
              width: 10,
              height: 10,
              bgcolor: 'background.paper',
              transform: 'translateY(-50%) rotate(45deg)',
              zIndex: 0,
            },
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="subtitle1" noWrap>
            {getDisplayName()}
          </Typography>
          <Typography variant="body2" color="text.secondary" noWrap>
            {user.email || 'No email available'}
          </Typography>
        </Box>
        
        <Divider />
        
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Session expires:
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <AccessTimeIcon fontSize="small" color={getBadgeColor()} sx={{ mr: 0.5 }} />
            <Typography variant="body2">
              {formatSessionExpiry()} ({getTimeUntilExpiry()} remaining)
            </Typography>
          </Box>
        </Box>
        
        <Divider />
        
        <MenuItem onClick={handleRefreshSession} disabled={refreshing}>
          <ListItemIcon>
            <RefreshIcon fontSize="small" />
          </ListItemIcon>
          {refreshing ? 'Refreshing session...' : 'Refresh session'}
        </MenuItem>
        
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Logout
        </MenuItem>
      </Menu>
    </>
  );
};

export default UserProfile; 
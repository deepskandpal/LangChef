import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SessionExpiryAlert from './SessionExpiryAlert';

const ProtectedRoute = () => {
  const { isAuthenticated, isSessionExpired } = useAuth();
  const location = useLocation();

  // If not authenticated, redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If session is expired, redirect to login with sessionExpired flag
  if (isSessionExpired()) {
    return <Navigate to="/login" state={{ from: location, sessionExpired: true }} replace />;
  }

  // If authenticated and session is valid, render the protected content
  return (
    <>
      <SessionExpiryAlert />
      <Outlet />
    </>
  );
};

export default ProtectedRoute; 
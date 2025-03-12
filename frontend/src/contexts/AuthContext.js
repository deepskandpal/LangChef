import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create the context
const AuthContext = createContext({
  isAuthenticated: false,
  user: null,
  sessionExpiry: null,
  login: () => {},
  loginWithAWS: () => {},
  logout: () => {},
  refreshSession: () => {},
  isSessionExpired: () => false,
  timeUntilExpiry: () => 0,
});

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);

// Auth provider component
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [sessionExpiry, setSessionExpiry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [awsSSOState, setAwsSSOState] = useState({
    clientId: null,
    clientSecret: null,
    deviceCode: null,
    verificationUri: null,
    userCode: null,
    pollingInterval: null,
    isPolling: false,
  });

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedExpiry = localStorage.getItem('sessionExpiry');
    const token = localStorage.getItem('token');
    
    if (storedUser && storedExpiry && token && new Date(storedExpiry) > new Date()) {
      setUser(JSON.parse(storedUser));
      setSessionExpiry(new Date(storedExpiry));
      setIsAuthenticated(true);
      
      // Set default auth header for all requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      // Clear any expired session data
      localStorage.removeItem('user');
      localStorage.removeItem('sessionExpiry');
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
      
      setIsAuthenticated(false);
      setUser(null);
      setSessionExpiry(null);
    }
    
    setLoading(false);
  }, []);

  // Check session expiry periodically
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const checkInterval = setInterval(() => {
      if (sessionExpiry && new Date() > sessionExpiry) {
        logout();
      }
    }, 60000); // Check every minute
    
    return () => clearInterval(checkInterval);
  }, [isAuthenticated, sessionExpiry]);

  // Poll for token when device authorization is in progress
  useEffect(() => {
    if (!awsSSOState.isPolling || !awsSSOState.clientId || !awsSSOState.clientSecret || !awsSSOState.deviceCode) {
      return;
    }

    const pollForToken = async () => {
      try {
        const response = await axios.post(`${API_BASE_URL}/api/auth/token`, {
          client_id: awsSSOState.clientId,
          client_secret: awsSSOState.clientSecret,
          device_code: awsSSOState.deviceCode,
        });

        if (response.status === 200 && response.data) {
          const { access_token, user: userData } = response.data;
          
          // Calculate expiry from JWT token (assuming it's valid for 24 hours)
          const expiry = new Date();
          expiry.setHours(expiry.getHours() + 24);
          
          // Save user data
          const userInfo = {
            id: userData.username,
            name: userData.full_name,
            email: userData.email,
            roles: ['user'], // Default role
          };
          
          // Set auth header for future requests
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          // Save to state and localStorage
          setUser(userInfo);
          setSessionExpiry(expiry);
          setIsAuthenticated(true);
          
          localStorage.setItem('user', JSON.stringify(userInfo));
          localStorage.setItem('sessionExpiry', expiry.toISOString());
          localStorage.setItem('token', access_token);
          
          // Reset polling state
          setAwsSSOState(prev => ({
            ...prev,
            isPolling: false,
          }));
        }
      } catch (error) {
        if (error.response && error.response.status === 408) {
          // Authorization timed out
          setAwsSSOState(prev => ({
            ...prev,
            isPolling: false,
          }));
        } else if (error.response && error.response.status !== 500) {
          // Continue polling for non-server errors (like authorization pending)
          setTimeout(pollForToken, awsSSOState.pollingInterval * 1000);
        } else {
          // Stop polling on server errors
          setAwsSSOState(prev => ({
            ...prev,
            isPolling: false,
          }));
        }
      }
    };

    // Start polling
    pollForToken();

    // Cleanup function
    return () => {
      setAwsSSOState(prev => ({
        ...prev,
        isPolling: false,
      }));
    };
  }, [awsSSOState]);

  // AWS SSO login function
  const login = async () => {
    try {
      setLoading(true);
      
      // Step 1: Register client with AWS SSO OIDC
      const registerResponse = await axios.post(`${API_BASE_URL}/api/auth/register-client`);
      
      if (registerResponse.status !== 200 || !registerResponse.data) {
        throw new Error('Failed to register client with AWS SSO');
      }
      
      const { client_id, client_secret } = registerResponse.data;
      
      // Step 2: Start device authorization
      const authResponse = await axios.post(`${API_BASE_URL}/api/auth/device-authorization`, {
        client_id,
        client_secret,
      });
      
      if (authResponse.status !== 200 || !authResponse.data) {
        throw new Error('Failed to start device authorization');
      }
      
      const { 
        device_code, 
        user_code, 
        verification_uri, 
        verification_uri_complete,
        interval 
      } = authResponse.data;
      
      // Step 3: Open the verification URI in a new window
      window.open(verification_uri_complete, '_blank');
      
      // Step 4: Set state for polling
      setAwsSSOState({
        clientId: client_id,
        clientSecret: client_secret,
        deviceCode: device_code,
        verificationUri: verification_uri,
        userCode: user_code,
        pollingInterval: interval || 5,
        isPolling: true,
      });
      
      return true;
    } catch (error) {
      console.error('AWS SSO login error:', error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // AWS Credentials login function
  const loginWithAWS = async () => {
    try {
      setLoading(true);
      
      // Call the AWS login endpoint
      const response = await axios.post(`${API_BASE_URL}/api/auth/aws-login`);
      
      if (response.status === 200 && response.data) {
        const { access_token, user: userData } = response.data;
        
        // Calculate expiry from JWT token (assuming it's valid for 24 hours)
        const expiry = new Date();
        expiry.setHours(expiry.getHours() + 24);
        
        // Save user data
        const userInfo = {
          id: userData.username,
          name: userData.full_name,
          email: userData.email,
          roles: ['user'], // Default role
        };
        
        // Set auth header for future requests
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        
        // Save to state and localStorage
        setUser(userInfo);
        setSessionExpiry(expiry);
        setIsAuthenticated(true);
        
        localStorage.setItem('user', JSON.stringify(userInfo));
        localStorage.setItem('sessionExpiry', expiry.toISOString());
        localStorage.setItem('token', access_token);
        
        return true;
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('AWS login error:', error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    // Clear auth state
    setIsAuthenticated(false);
    setUser(null);
    setSessionExpiry(null);
    
    // Clear localStorage
    localStorage.removeItem('user');
    localStorage.removeItem('sessionExpiry');
    localStorage.removeItem('token');
    
    // Clear auth header
    delete axios.defaults.headers.common['Authorization'];
  };

  // Refresh session function
  const refreshSession = async () => {
    try {
      setLoading(true);
      
      // Get the stored token
      const token = localStorage.getItem('token');
      
      if (!token) {
        throw new Error('No token available');
      }
      
      // Call the refresh token endpoint
      const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 200 && response.data) {
        const { access_token } = response.data;
        
        // Set new session expiry to 24 hours from now
        const expiry = new Date();
        expiry.setHours(expiry.getHours() + 24);
        
        // Update auth header
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        
        // Update session expiry and token
        setSessionExpiry(expiry);
        localStorage.setItem('sessionExpiry', expiry.toISOString());
        localStorage.setItem('token', access_token);
        
        return true;
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Session refresh error:', error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Check if session is expired
  const isSessionExpired = () => {
    if (!sessionExpiry) return true;
    return new Date() > sessionExpiry;
  };

  // Calculate time until session expiry in milliseconds
  const timeUntilExpiry = () => {
    if (!sessionExpiry) return 0;
    return Math.max(0, sessionExpiry.getTime() - new Date().getTime());
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        sessionExpiry,
        login,
        loginWithAWS,
        logout,
        refreshSession,
        isSessionExpired,
        timeUntilExpiry,
        loading,
        awsSSOState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}; 
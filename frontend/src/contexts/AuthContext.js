import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';

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
  const [error, setError] = useState(null);
  const [awsSSOState, setAwsSSOState] = useState(null);
  const [pollingTimerId, setPollingTimerId] = useState(null);
  
  const navigate = useNavigate();
  const location = useLocation();

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedExpiry = localStorage.getItem('sessionExpiry');
    const token = localStorage.getItem('token');
    
    console.log('AuthContext - Initializing auth state from localStorage:', {
      hasStoredUser: !!storedUser,
      hasStoredExpiry: !!storedExpiry,
      hasToken: !!token,
      isExpired: storedExpiry ? new Date(storedExpiry) <= new Date() : true
    });
    
    if (storedUser && storedExpiry && token && new Date(storedExpiry) > new Date()) {
      const parsedUser = JSON.parse(storedUser);
      console.log('AuthContext - Valid stored credentials found, setting authenticated state', parsedUser);
      
      setUser(parsedUser);
      setSessionExpiry(new Date(storedExpiry));
      setIsAuthenticated(true);
      
      // Set default auth header for all requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      // Clear any expired session data
      console.log('AuthContext - No valid stored credentials found, clearing session data');
      
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

  // Load user from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    const savedToken = localStorage.getItem('token');
    
    if (savedUser && savedToken) {
      try {
        setUser(JSON.parse(savedUser));
        setIsAuthenticated(true);
        console.log('User loaded from localStorage', savedUser);
        axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
      } catch (err) {
        console.error('Failed to parse user from localStorage', err);
        localStorage.removeItem('user');
        localStorage.removeItem('token');
      }
    }
    
    setLoading(false);
    
    // Check if we have a saved polling state in localStorage
    const savedPollingState = localStorage.getItem('awsSSOPollingState');
    if (savedPollingState) {
      try {
        const parsedState = JSON.parse(savedPollingState);
        // Check if the polling state is still valid (not expired)
        if (parsedState && new Date(parsedState.expiresAt) > new Date()) {
          console.log('Resuming AWS SSO polling from saved state', parsedState);
          setAwsSSOState(parsedState);
          startPolling(parsedState);
        } else {
          // Clear expired polling state
          console.log('Clearing expired AWS SSO polling state');
          localStorage.removeItem('awsSSOPollingState');
        }
      } catch (err) {
        console.error('Failed to parse AWS SSO polling state from localStorage', err);
        localStorage.removeItem('awsSSOPollingState');
      }
    }
  }, []);

  // Start polling for token with improved error handling and exponential backoff
  const startPolling = (state) => {
    console.log('Starting to poll for AWS SSO token...', state);
    let pollCount = 0;
    let currentInterval = state.interval || 5; // Default to 5 seconds if not provided
    let consecutiveErrors = 0;
    let consecutivePending = 0;
    const MAX_CONSECUTIVE_ERRORS = 3;
    const MAX_CONSECUTIVE_PENDING = 20; // After this many consecutive pending responses, increase interval
    
    // Clear any existing polling
    if (pollingTimerId) {
      clearInterval(pollingTimerId);
      setPollingTimerId(null);
    }

    // Create a polling function to encapsulate the poll logic
    const pollForToken = async () => {
      try {
        // Increment poll count
        pollCount++;
        
        // Check if we've exceeded the maximum polling time
        const elapsedTimeMs = new Date() - new Date(state.startedAt);
        const maxPollingTimeMs = 10 * 60 * 1000; // 10 minutes
        
        console.log(`Polling status - attempt: ${pollCount}, elapsed: ${Math.round(elapsedTimeMs/1000)}s, max: ${Math.round(maxPollingTimeMs/1000)}s, interval: ${currentInterval}s`);
        
        if (elapsedTimeMs > maxPollingTimeMs) {
          console.log('Polling timeout reached. Stopping polling.');
          clearTimeout(pollingTimerId);
          setPollingTimerId(null);
          setLoading(false);
          setError('Authentication timed out. Please try again.');
          localStorage.removeItem('awsSSOPollingState');
          setAwsSSOState(null);
          return;
        }
        
        console.log(`Polling for token (attempt ${pollCount})...`);
        
        const tokenResponse = await axios.post(`${API_BASE_URL}/api/auth/token`, {
          client_id: state.client_id,
          client_secret: state.client_secret,
          device_code: state.device_code,
        });
        
        // Reset error counter on success
        consecutiveErrors = 0;
        
        // If we get here, we have a token
        console.log('Successfully got token:', tokenResponse.data);
        
        // Clear timeout for polling
        clearTimeout(pollingTimerId);
        setPollingTimerId(null);
        
        // Clear polling state from localStorage
        localStorage.removeItem('awsSSOPollingState');
        setAwsSSOState(null);
        
        // Set user and token
        const { access_token, user: userData, expires_in } = tokenResponse.data;
        setUser(userData);
        setIsAuthenticated(true);
        
        // Calculate expiry time (default to 24 hours if not provided)
        const expiryTime = new Date();
        expiryTime.setSeconds(expiryTime.getSeconds() + (expires_in || 24 * 60 * 60));
        setSessionExpiry(expiryTime);
        
        // Store in localStorage
        localStorage.setItem('user', JSON.stringify(userData));
        localStorage.setItem('token', access_token);
        localStorage.setItem('sessionExpiry', expiryTime.toISOString());
        
        // Set authorization header
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        
        // Set loading to false
        setLoading(false);
        
        // Navigate to dashboard
        console.log('Authentication successful, redirecting to dashboard');
        navigate('/dashboard');
        
      } catch (err) {
        // Check if we have a response from the server
        if (err.response) {
          const { status, data } = err.response;
          
          // Log for debugging
          console.log('Token polling error:', { status, detail: data.detail });
          
          // Handle authorization_pending (user hasn't approved yet) - this is expected
          if ((status === 400 && data.detail === "authorization_pending") || 
              (status === 500 && data.detail && data.detail.includes("InvalidGrantException"))) {
            console.log('Authorization pending, continuing to poll...');
            
            // Track consecutive pending responses to potentially increase interval
            consecutivePending++;
            
            // If we've received too many consecutive pending responses, implement a gradual backoff
            if (consecutivePending >= MAX_CONSECUTIVE_PENDING) {
              // Implement an incremental backoff - increase interval by 20%
              const newInterval = Math.min(currentInterval * 1.2, 15); // Cap at 15 seconds
              if (newInterval > currentInterval) {
                console.log(`Increasing polling interval from ${currentInterval}s to ${newInterval.toFixed(1)}s due to consecutive pending responses`);
                currentInterval = newInterval;
                
                // Update state with new interval
                const updatedState = { 
                  ...state, 
                  interval: currentInterval
                };
                setAwsSSOState(updatedState);
                localStorage.setItem('awsSSOPollingState', JSON.stringify(updatedState));
                
                // Reset counter after adjusting
                consecutivePending = 0;
              }
            }
            
            // Reset consecutive error counter since this is an expected status
            consecutiveErrors = 0;
            
            // Schedule next poll
            schedulePoll();
            return;
          }
          
          // Handle slow_down error (polling too fast) - RFC 8628 requirement
          if (status === 429 || (status === 400 && data.detail === 'slow_down')) {
            console.log('Polling too fast, slowing down...');
            
            // Increase polling interval by at least 5 seconds per RFC 8628
            currentInterval = Math.max(currentInterval + 5, currentInterval * 1.5);
            
            // Update state with increased interval
            const updatedState = { 
              ...state, 
              interval: currentInterval
            };
            setAwsSSOState(updatedState);
            localStorage.setItem('awsSSOPollingState', JSON.stringify(updatedState));
            
            // Reset consecutive counters
            consecutiveErrors = 0;
            consecutivePending = 0;
            
            // Schedule next poll with increased interval
            schedulePoll();
            return;
          }
          
          // Handle expired_token
          if (status === 400 && data.detail === 'expired_token') {
            console.log('Token expired, stopping polling');
            clearTimeout(pollingTimerId);
            setPollingTimerId(null);
            setLoading(false);
            setError('Authentication session expired. Please try again.');
            localStorage.removeItem('awsSSOPollingState');
            setAwsSSOState(null);
            return;
          }
          
          // Handle access_denied
          if (status === 400 && data.detail === 'access_denied') {
            console.log('Access denied, stopping polling');
            clearTimeout(pollingTimerId);
            setPollingTimerId(null);
            setLoading(false);
            setError('Authentication was denied. Please try again.');
            localStorage.removeItem('awsSSOPollingState');
            setAwsSSOState(null);
            return;
          }
        }
        
        // For other errors, track and handle
        console.error('Error polling for token:', err);
        if (err.response) {
          console.error('Response data:', err.response.data);
        }
        
        // Increment consecutive error counter
        consecutiveErrors++;
        
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          // Implement exponential backoff for connection issues - RFC 8628 recommendation
          console.log(`Too many consecutive errors (${consecutiveErrors}), implementing exponential backoff`);
          
          // Double the interval with a max of 30 seconds
          currentInterval = Math.min(currentInterval * 2, 30);
          
          console.log(`New polling interval: ${currentInterval}s`);
          
          // Update state with new interval
          const updatedState = { 
            ...state, 
            interval: currentInterval
          };
          setAwsSSOState(updatedState);
          localStorage.setItem('awsSSOPollingState', JSON.stringify(updatedState));
          
          // Reset counter after adjusting
          consecutiveErrors = 0;
        }
        
        // Continue polling with possibly adjusted interval
        schedulePoll();
      }
    };
    
    // Function to schedule the next poll
    const schedulePoll = () => {
      // Clear any existing timer first
      if (pollingTimerId) {
        clearTimeout(pollingTimerId);
      }
      
      // Schedule next poll
      const timerId = setTimeout(pollForToken, currentInterval * 1000);
      setPollingTimerId(timerId);
    };
    
    // Start first poll immediately
    pollForToken();
  };

  // Function to resume authentication if it was interrupted
  const resumeAuthentication = () => {
    const savedPollingState = localStorage.getItem('awsSSOPollingState');
    if (savedPollingState) {
      try {
        const parsedState = JSON.parse(savedPollingState);
        // Check if the polling state is still valid (not expired)
        if (parsedState && new Date(parsedState.expiresAt) > new Date()) {
          console.log('Resuming AWS SSO polling from saved state', parsedState);
          setAwsSSOState(parsedState);
          startPolling(parsedState);
          return true;
        } else {
          // Clear expired polling state
          console.log('Clearing expired AWS SSO polling state');
          localStorage.removeItem('awsSSOPollingState');
        }
      } catch (err) {
        console.error('Failed to parse AWS SSO polling state from localStorage', err);
        localStorage.removeItem('awsSSOPollingState');
      }
    }
    return false;
  };

  // Handle login
  const login = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Check if we can resume an in-progress authentication
      if (resumeAuthentication()) {
        console.log('Resumed an in-progress authentication session');
        return true;
      }
      
      // Clear any existing polling
      if (pollingTimerId) {
        clearTimeout(pollingTimerId);
        setPollingTimerId(null);
      }
      
      // Clear any existing polling state
      localStorage.removeItem('awsSSOPollingState');
      setAwsSSOState(null);
      
      // Register client
      const registerResponse = await axios.post(`${API_BASE_URL}/api/auth/register-client`);
      const { client_id, client_secret } = registerResponse.data;
      
      // Get device authorization
      const deviceAuthResponse = await axios.post(`${API_BASE_URL}/api/auth/device-authorization`, {
        client_id,
        client_secret,
      });
      
      const { 
        device_code, 
        user_code, 
        verification_uri,
        verification_uri_complete, 
        expires_in,
        interval
      } = deviceAuthResponse.data;
      
      // Calculate expiry time (current time + expires_in seconds)
      const expiresAt = new Date(new Date().getTime() + expires_in * 1000).toISOString();
      
      // Open AWS SSO login page
      const authWindow = window.open(verification_uri_complete, '_blank');
      
      // Make sure the window was successfully opened
      if (!authWindow || authWindow.closed || typeof authWindow.closed === 'undefined') {
        console.error('AuthContext - Failed to open AWS SSO authentication window');
        // Provide fallback option for users
        const manualConfirm = window.confirm(
          `Failed to open the AWS SSO authentication window automatically. ` +
          `Would you like to open it manually? If you click OK, we'll copy the verification code "${user_code}" to your clipboard.`
        );
        
        if (manualConfirm) {
          try {
            // Try to copy the code to clipboard
            navigator.clipboard.writeText(user_code).then(
              () => {
                alert(`Code "${user_code}" copied to clipboard. Please enter this code at: ${verification_uri}`);
                window.open(verification_uri, '_blank');
              },
              () => {
                // Clipboard write failed
                alert(`Please enter this code: "${user_code}" at: ${verification_uri}`);
                window.open(verification_uri, '_blank');
              }
            );
          } catch (e) {
            // Navigator clipboard not available
            alert(`Please enter this code: "${user_code}" at: ${verification_uri}`);
            window.open(verification_uri, '_blank');
          }
        } else {
          // User declined to continue
          setLoading(false);
          setError('Authentication cancelled. Please try again.');
          return false;
        }
      }
      
      // Set state for polling
      const ssoState = { 
        client_id, 
        client_secret, 
        device_code,
        user_code,
        verification_uri,
        verification_uri_complete,
        interval: interval || 5, // Default to 5 seconds if not provided
        startedAt: new Date().toISOString(),
        expiresAt,
        maxPollCount: Math.floor(expires_in / (interval || 5)), // Calculate max poll count
        inProgress: true  // Add this flag to track authentication in progress
      };
      
      setAwsSSOState(ssoState);
      
      // Save polling state to localStorage
      localStorage.setItem('awsSSOPollingState', JSON.stringify(ssoState));
      
      console.log('AWS SSO authentication initiated, polling will start');
      
      // Start polling - with a slight delay to allow auth window to open
      setTimeout(() => {
        startPolling(ssoState);
      }, 1000);
      
      return true;
    } catch (err) {
      console.error('Login failed:', err);
      setError(err.message || 'Login failed. Please try again.');
      setLoading(false);
      return false;
    }
  };

  // Add an alias for the login function to match the context declaration
  const loginWithAWS = login;

  // Handle logout with improved cleanup
  const logout = () => {
    // Clear local storage
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.removeItem('sessionExpiry');
    localStorage.removeItem('awsSSOPollingState');
    
    // Clear auth state
    setUser(null);
    setIsAuthenticated(false);
    setSessionExpiry(null);
    
    // Clear polling state
    if (pollingTimerId) {
      clearTimeout(pollingTimerId);
      setPollingTimerId(null);
    }
    setAwsSSOState(null);
    
    // Clear authorization header
    delete axios.defaults.headers.common['Authorization'];
    
    // Navigate to login page
    navigate('/login');
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
        error,
        awsSSOState,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}; 
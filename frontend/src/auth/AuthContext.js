// src/auth/AuthContext.js
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

// Backend API URL
// for local testing: const API_URL = 'http://localhost:8000/api/auth'; 
// To environment variable with fallback:
const API_URL = process.env.REACT_APP_API_URL || 'https://baduanjin-backend-docker.azurewebsites.net';

console.log('Environment REACT_APP_API_URL:', process.env.REACT_APP_API_URL);
console.log('Final API_URL being used:', API_URL);

// Add timeout for API requests
axios.defaults.timeout = 10000; // 10 seconds timeout

// Create context
const AuthContext = createContext();

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);

// Provider component
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const navigate = useNavigate();
  
  // Use useRef to break circular dependencies
  const logoutRef = useRef();
  
  // Define logout function first
  const logout = useCallback(() => {
    console.log('Logging out user');
    // Clear user and token
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    
    // Use navigate to redirect after logout
    navigate('/login');
  }, [navigate]);
  
  // Assign to ref so it's accessible before definition
  logoutRef.current = logout;
  
  // Now define refreshUserData, using the ref to logout
  const refreshUserData = useCallback(async () => {
    try {
      console.log('Refreshing user data...');
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
      
      const response = await axios.get(`${API_URL}/api/auth/me`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      console.log('User data fetched successfully:', response.data);
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      if (error.name === 'AbortError') {
        console.error('Request timed out');
        setError('Request timed out while fetching user data');
      }
      if (error.response?.status === 401) {
        // Token expired or invalid - use the ref version of logout
        logoutRef.current();
      }
      throw error;
    }
  }, []);  // No need to include logoutRef as a dependency
  
  // Check if user is logged in on initial load
  useEffect(() => {
    // IMPORTANT: Do not set loading to false here!
    console.log('Auth check starting...');
    const checkLoggedIn = async () => {
      const storedToken = localStorage.getItem('token');
      
      if (storedToken) {
        try {
          console.log('Token found, setting auth header');
          // Set auth header
          axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
          setToken(storedToken);
          
          // Get current user info
          await refreshUserData();
        } catch (error) {
          console.error('Auth check failed:', error);
          // Clear invalid token
          localStorage.removeItem('token');
          delete axios.defaults.headers.common['Authorization'];
          setToken(null);
          setUser(null);
        } finally {
          console.log('Auth check complete');
          setLoading(false);
        }
      } else {
        console.log('No token found');
        setLoading(false);
      }
    };
    
    checkLoggedIn();
  }, [refreshUserData]); 
  
  // Login function
  const login = async (emailOrUsername, password) => {
    try {
      setError(null);
      console.log('Attempting login for:', emailOrUsername);
      
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        email: emailOrUsername,
        password
      });
      
      console.log('Login response received:', response.data);
      
      // Check if agreement is required
      if (response.data.user.agreement_required) {
        console.log('User agreement required');
        // Store temporary user data for agreement screen
        sessionStorage.setItem('temp_user', JSON.stringify(response.data.user));
        sessionStorage.setItem('temp_password', password);
        
        // Redirect to agreement page
        console.log('Navigating to agreement page');
        window.location.href = '/agreement';
        return { success: true, agreementRequired: true, user: response.data.user };
      }
      
      // Save token
      console.log('Saving token and user data');
      localStorage.setItem('token', response.data.access_token);
      
      // Set auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
      
      // Set user and token state
      setUser(response.data.user);
      setToken(response.data.access_token);
      
      // Redirect to videos
      console.log('Attempting to navigate to videos');
      navigate('/videos');
      console.log('Navigation function called');
      
      return { success: true, user: response.data.user };
    } catch (error) {
      console.error('Login failed:', error);
      setError(error.response?.data?.detail || 'Login failed');
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Login failed'
      };
    }
  };
  
  // Accept user agreement
  const acceptAgreement = async () => {
    try {
      console.log('Starting agreement acceptance process');
      // Get temp user from session storage
      const tempUser = JSON.parse(sessionStorage.getItem('temp_user'));
      
      if (!tempUser) {
        console.error('No temporary user data found');
        throw new Error('No temporary user data found');
      }
      
      console.log('Temporary user data retrieved:', tempUser.email);
      
      // Important change: Don't try to login again to get a token
      // Instead, make a special agreement request directly
      console.log('Sending direct agreement acceptance request');
      
      // First create a temporary axios instance without auth headers
      const tempAxios = axios.create();
      delete tempAxios.defaults.headers.common['Authorization'];
      
      // Send the agreement acceptance with user ID in the request body
      const response = await tempAxios.post(
        `${API_URL}/api/auth/agreement/accept-initial`, // New endpoint needed on backend
        { 
          user_id: tempUser.id,
          email: tempUser.email,
          password: sessionStorage.getItem('temp_password'),
          agreement_accepted: true 
        }
      );
      
      // Now we should get a token in the response
      if (!response.data.access_token) {
        console.error('No token received from agreement acceptance');
        throw new Error('Failed to obtain authentication token');
      }
      
      // Set the token and user data
      localStorage.setItem('token', response.data.access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
      setToken(response.data.access_token);
      setUser(response.data.user);
      
      // Clear temp data
      sessionStorage.removeItem('temp_user');
      sessionStorage.removeItem('temp_password');
      
      // Navigate to videos
      console.log('Agreement accepted, navigating to videos');
      window.location.href = '/videos';
      
      return { success: true };
    } catch (error) {
      console.error('Failed to accept agreement:', error);
      return { 
        success: false, 
        message: error.message || 'Failed to accept agreement'
      };
    }
  };
  
  // Register function
  const register = async (username, email, password, role = 'learner', name = username) => {
    try {
      const response = await axios.post(`${API_URL}/api/auth/register`, {
        username,
        email,
        password,
        name,
        role
      });
      
      // Redirect to login page after successful registration
      navigate('/login');
      
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Registration error:', error);
      // Properly handle different error formats
      if (error.response) {
        // The server responded with an error status
        return { 
          success: false, 
          message: error.response.data
        };
      } else if (error.request) {
        // The request was made but no response received
        return {
          success: false,
          message: 'No response from server. Please try again later.'
        };
      } else {
        // Something else happened in setting up the request
        return { 
          success: false, 
          message: error.message || 'Registration failed'
        };
      }
    }
  };
  
  // Check if user is a master
  const isMaster = () => {
    return user?.role === 'master';
  };
  
  // Check if user is a learner
  const isLearner = () => {
    return user?.role === 'learner';
  };
  
  // Get user role
  const getUserRole = () => {
    return user?.role || null;
  };
  
  // Check if user is authenticated
  const isAuthenticated = () => {
    return !!user;
  };
  
  // Provide auth context to components
  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      token,
      error,
      login, 
      logout, 
      register,
      refreshUserData,
      acceptAgreement,
      isMaster,
      isLearner,
      getUserRole,
      isAuthenticated
    }}>
      {children}
    </AuthContext.Provider>
  );
}

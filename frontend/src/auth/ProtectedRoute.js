// src/auth/ProtectedRoute.js
// This component will prevent unauthorized access to routes that require authentication:

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  // Show loading indicator if auth state is still being determined
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <p>Verifying authentication...</p>
      </div>
    );
  }
  
  // Redirect to login if not authenticated
  if (!isAuthenticated()) {
    return <Navigate to="/login" />;
  }
  
  // Render children if authenticated
  return children;
};

export default ProtectedRoute;
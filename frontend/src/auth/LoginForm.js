// src/auth/LoginForm.js
// Create basic authentication forms

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import './auth.css';

const LoginForm = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const result = await login(email, password);
      
      if (result.success) {
        // Redirect to videos on successful login
        navigate('/videos'); 
      } else {
        setError(result.message);
      }
      } catch (err) {
        setError('An error occurred during login. Please try again.');
        console.error('Login error:', err);
      }
  };
  
  return (
    <div className="login-container">
      <div className="login-card">
        <h2>Sign In to Baduanjin Analyzer</h2>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="login-button">Sign In</button>
        </form>
        
        <div className="auth-footer">
          Don't have an account? <a href="/register">Register</a>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;
// src/auth/RegisterForm.js
// Create a registration form

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from './AuthContext';
import './auth.css';

function RegisterForm() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('learner');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Form validation
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }
    
    setLoading(true);
    
    try {
      // Use the name if provided, otherwise use username
      const displayName = name.trim() ? name : username;
      
      const result = await register(username, email, password, role, displayName);
      
      if (result.success) {
        // Registration successful, navigate to login
        navigate('/login');
      } else {
        // Handle error message properly - this is crucial
        if (typeof result.message === 'object') {
          // If message is an object (likely a FastAPI validation error)
          if (result.message.detail && Array.isArray(result.message.detail)) {
            // Extract validation error messages
            const errorMessages = result.message.detail.map(err => `${err.msg} (${err.loc.join('.')})`);
            setError(errorMessages.join('. '));
          } else {
            // Fallback for unknown object structure
            setError('Validation error. Please check your input.');
          }
        } else {
          // If message is a string, use it directly
          setError(result.message);
        }
      }
    } catch (err) {
      console.error('Registration error:', err);
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="login-container">
      <div className="login-card">
        <h2>Register for Baduanjin Analysis</h2>
        <h4>Select the role: Learner or Master before registeration</h4>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="name">Full Name (Optional)</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="role">Role</label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="learner">Learner</option>
              <option value="master">Master</option>
            </select>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="login-button"
          >
            {loading ? 'Registering...' : 'Register'}
          </button>
          
          <div className="auth-footer">
            Already have an account? <Link to="/login">Sign In</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RegisterForm;
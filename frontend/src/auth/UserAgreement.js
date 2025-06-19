// src/auth/UserAgreement.js

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

function UserAgreement() {
  const [accepted, setAccepted] = useState(false);
  const { acceptAgreement } = useAuth();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleAccept = async () => {
    if (!accepted) {
      setError('You must accept the agreement to continue.');
      return;
    }
  
    setIsSubmitting(true);
    setError(null);
    console.log('Agreement accepted, calling acceptAgreement function');
  
    try {
      const result = await acceptAgreement();
      console.log('Agreement acceptance result:', result);
      
      if (result.success) {
        console.log('Agreement acceptance successful, should redirect to videos');
        // The navigation should happen in the acceptAgreement function
      } else {
        console.error('Agreement acceptance failed:', result.message);
        setError(result.message || 'Failed to accept agreement. Please try again.');
      }
    } catch (err) {
      console.error('Agreement acceptance error:', err);
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    // Clear temporary session storage data
    sessionStorage.removeItem('temp_user');
    sessionStorage.removeItem('temp_password');
    
    // Redirect to login
    navigate('/login');
  };

  return (
    <div className="user-agreement-container" style={{ 
      maxWidth: '700px', 
      margin: '50px auto', 
      padding: '20px', 
      backgroundColor: '#f8f9fa',
      borderRadius: '8px',
      boxShadow: '0 4px 8px rgba(0,0,0,0.1)'
    }}>
      <h2>Baduanjin Analysis Application - User Agreement</h2>
      
      <div className="agreement-content" style={{ 
        height: '300px', 
        overflowY: 'auto', 
        border: '1px solid #ddd',
        padding: '15px',
        marginBottom: '20px',
        borderRadius: '4px',
        backgroundColor: 'white'
      }}>
        <h3>Terms of Service</h3>
        <p>
          Welcome to the Baduanjin Analysis Application. This application is designed for educational
          and research purposes to analyze and improve Baduanjin exercise techniques.
        </p>
        
        <h4>1. Data Collection and Privacy</h4>
        <p>
          By using this application, you agree that we may collect video data of your Baduanjin exercises
          for analysis purposes. This data will be stored securely and will only be accessible to you and
          any masters you explicitly grant access to.
        </p>
        
        <h4>2. User Responsibilities</h4>
        <p>
          You agree to use this application responsibly and not to upload any inappropriate or offensive content.
          The application should be used in a safe environment with adequate space for exercise movements.
        </p>
        
        <h4>3. Master-Learner Relationships</h4>
        <p>
          When you establish a master-learner relationship, you are granting the master user permission to
          view and analyze your exercise videos. You may terminate this relationship at any time.
        </p>
        
        <h4>4. Disclaimer</h4>
        <p>
          This application is not a substitute for professional medical advice. Always consult with a healthcare
          professional before beginning any exercise program, especially if you have any health concerns.
        </p>
      </div>
      
      <div className="agreement-checkbox" style={{ marginBottom: '20px' }}>
        <label style={{ display: 'flex', alignItems: 'center' }}>
          <input 
            type="checkbox" 
            checked={accepted} 
            onChange={() => setAccepted(!accepted)}
            style={{ marginRight: '10px' }}
          />
          I have read and accept the terms of this agreement
        </label>
      </div>
      
      {error && (
        <div className="error-message" style={{ 
          color: 'red', 
          marginBottom: '15px',
          padding: '10px',
          backgroundColor: 'rgba(255,0,0,0.05)',
          borderRadius: '4px'
        }}>
          {error}
        </div>
      )}
      
      <div className="button-container" style={{ display: 'flex', gap: '15px' }}>
        <button 
          onClick={handleCancel}
          style={{
            padding: '10px 20px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            backgroundColor: '#f8f9fa',
            cursor: 'pointer'
          }}
        >
          Cancel
        </button>
        
        <button 
          onClick={handleAccept}
          disabled={isSubmitting}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '4px',
            backgroundColor: '#007bff',
            color: 'white',
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            opacity: isSubmitting ? 0.7 : 1
          }}
        >
          {isSubmitting ? 'Processing...' : 'Accept & Continue'}
        </button>
      </div>
    </div>
  );
}

export default UserAgreement;
// frontend/src/components/UserAgreement/UserAgreementForm.js

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';


const UserAgreementForm = () => {
  const [accepted, setAccepted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { token, refreshUserData } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!accepted) {
      setError('You must accept the agreement to continue');
      return;
    }
    
    setIsSubmitting(true);
    setError('');
    
    try {
      await axios.post('/api/auth/agreement', 
        { agreement_accepted: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Update user data and redirect to dashboard
      await refreshUserData();
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit agreement');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="agreement-container">
      <div className="agreement-content">
        <h2>Baduanjin Analysis User Agreement</h2>
        
        {error && <div className="agreement-error">{error}</div>}
        
        <div className="agreement-text">
          <h3>Data Collection and Privacy Policy</h3>
          
          <p>Welcome to the Baduanjin Analysis application. Before you proceed, please read and accept the following user agreement regarding data collection and privacy:</p>
          
          <h4>Data We Collect</h4>
          <p>The Baduanjin Analysis application collects the following personal data:</p>
          <ul>
            <li>Account information (name, email, username)</li>
            <li>Profile information that you voluntarily provide</li>
            <li>Video recordings of your Baduanjin exercises</li>
            <li>Motion analysis data derived from your videos</li>
            <li>Exercise performance metrics and statistics</li>
          </ul>
          
          <h4>How We Use Your Data</h4>
          <p>We use your data for the following purposes:</p>
          <ul>
            <li>To provide you with exercise analysis and feedback</li>
            <li>To improve your Baduanjin practice through personalized recommendations</li>
            <li>If you are a learner, to share your exercise data with your authorized master(s)</li>
            <li>To improve our analysis algorithms and application functionality</li>
          </ul>
          
          <h4>Data Protection</h4>
          <p>We take your privacy seriously and implement the following measures:</p>
          <ul>
            <li>All data is stored securely on encrypted servers</li>
            <li>Your videos and personal information are not shared with unauthorized third parties</li>
            <li>You maintain control over your data and can delete it at any time</li>
            <li>If you are a learner, you control which masters can access your exercise data</li>
          </ul>
          
          <h4>Your Rights</h4>
          <p>You have the following rights regarding your data:</p>
          <ul>
            <li>Right to access your personal data</li>
            <li>Right to correct inaccurate data</li>
            <li>Right to delete your data</li>
            <li>Right to withdraw consent at any time</li>
          </ul>
        </div>
        
        <div className="agreement-checkbox">
          <input 
            type="checkbox" 
            id="accept-agreement" 
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
          />
          <label htmlFor="accept-agreement">
            I have read and agree to the data collection and privacy terms
          </label>
        </div>
        
        <div className="agreement-actions">
          <button 
            className="agreement-button decline-button"
            onClick={() => navigate('/login')}
          >
            Decline and Logout
          </button>
          
          <button 
            className="agreement-button accept-button"
            onClick={handleSubmit}
            disabled={!accepted || isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Accept and Continue'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserAgreementForm;
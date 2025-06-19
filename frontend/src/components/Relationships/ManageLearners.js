// frontend/src/components/Relationships/ManageLearners.js

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';


const ManageLearners = () => {
  const [learners, setLearners] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { token } = useAuth();

  // Define functions with useCallback before useEffect
  const fetchLearners = useCallback(async () => {
    try {
      const response = await axios.get('/api/relationships/learners', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setLearners(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load learners');
      setLoading(false);
    }
  }, [token]);

  const fetchPendingRequests = useCallback(async () => {
    try {
      const response = await axios.get('/api/relationships/my-requests', {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Filter to only pending requests
      setPendingRequests(response.data.filter(req => req.status === 'pending'));
    } catch (err) {
      console.error('Failed to load pending requests', err);
    }
  }, [token]);

  // Now use the memoized functions in useEffect
  useEffect(() => {
    fetchLearners();
    fetchPendingRequests();
  }, [fetchLearners, fetchPendingRequests]);

  const searchLearners = async () => {
    if (!searchTerm.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await axios.get(`/api/users/search?role=learner&query=${searchTerm}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSearchResults(response.data);
    } catch (err) {
      setError('Failed to search for learners');
    } finally {
      setIsSearching(false);
    }
  };

  const sendRequest = async (learnerId) => {
    try {
      await axios.post(`/api/relationships/request/${learnerId}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Remove from search results and refresh pending requests
      setSearchResults(searchResults.filter(learner => learner.id !== learnerId));
      fetchPendingRequests();
    } catch (err) {
      setError('Failed to send request');
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="relationships-container">
      <h2>Manage Learners</h2>
      
      {error && <div className="relationships-error">{error}</div>}
      
      <div className="search-section">
        <h3>Find New Learners</h3>
        <div className="search-box">
          <input
            type="text"
            placeholder="Search by username or name"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button onClick={searchLearners} disabled={isSearching}>
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </div>
        
        {searchResults.length > 0 && (
          <div className="search-results">
            <h4>Search Results</h4>
            <ul className="user-list">
              {searchResults.map(learner => (
                <li key={learner.id} className="user-item">
                  <div className="user-info">
                    <span className="user-name">{learner.name}</span>
                    <span className="user-username">@{learner.username}</span>
                  </div>
                  <button 
                    className="request-button"
                    onClick={() => sendRequest(learner.id)}
                  >
                    Send Request
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      
      {pendingRequests.length > 0 && (
        <div className="pending-requests">
          <h3>Pending Requests</h3>
          <ul className="user-list">
            {pendingRequests.map(request => (
              <li key={request.id} className="user-item">
                <div className="user-info">
                  <span className="user-name">{request.related_user.name}</span>
                  <span className="user-username">@{request.related_user.username}</span>
                </div>
                <span className="request-status pending">Pending</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      <div className="my-learners">
        <h3>My Learners</h3>
        {learners.length === 0 ? (
          <p className="no-results">You don't have any learners yet.</p>
        ) : (
          <ul className="user-list">
            {learners.map(learner => (
              <li key={learner.learner_id} className="user-item">
                <div className="user-info">
                  <span className="user-name">{learner.name}</span>
                  <span className="user-username">@{learner.username}</span>
                </div>
                <button 
                  className="view-button"
                  onClick={() => window.location.href = `/learner/${learner.learner_id}`}
                >
                  View Progress
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ManageLearners;
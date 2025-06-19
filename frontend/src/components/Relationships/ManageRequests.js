// frontend/src/components/Relationships/ManageRequests.js (for learners)

import React, { useState, useEffect, useCallback  } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';


const ManageRequests = () => {
  const [requests, setRequests] = useState([]);
  const [masters, setMasters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { token } = useAuth();

  // Memoize the fetchRequests function with useCallback
  const fetchRequests = useCallback(async () => {
    try {
      const response = await axios.get('/api/relationships/my-requests', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Separate into pending requests and accepted masters
      const pendingReqs = response.data.filter(req => req.status === 'pending');
      const acceptedMasters = response.data.filter(req => req.status === 'accepted');
      
      setRequests(pendingReqs);
      setMasters(acceptedMasters);
      setLoading(false);
    } catch (err) {
      setError('Failed to load relationship requests');
      setLoading(false);
    }
  }, [token]); 

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]); 

  const respondToRequest = async (requestId, status) => {
    try {
      await axios.post(`/api/relationships/${requestId}/respond?status=${status}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Refresh requests
      fetchRequests();
    } catch (err) {
      setError(`Failed to ${status} request`);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="relationships-container">
      <h2>Master Requests</h2>
      
      {error && <div className="relationships-error">{error}</div>}
      
      {requests.length > 0 ? (
        <div className="pending-requests">
          <h3>Pending Requests</h3>
          <ul className="user-list">
            {requests.map(request => (
              <li key={request.id} className="user-item">
                <div className="user-info">
                  <span className="user-name">{request.related_user.name}</span>
                  <span className="user-username">@{request.related_user.username}</span>
                </div>
                <div className="request-actions">
                  <button 
                    className="accept-button"
                    onClick={() => respondToRequest(request.id, 'accepted')}
                  >
                    Accept
                  </button>
                  <button 
                    className="reject-button"
                    onClick={() => respondToRequest(request.id, 'rejected')}
                  >
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="no-results">You don't have any pending requests.</p>
      )}
      
      <div className="my-masters">
        <h3>My Masters</h3>
        {masters.length === 0 ? (
          <p className="no-results">You don't have any masters yet.</p>
        ) : (
          <ul className="user-list">
            {masters.map(master => (
              <li key={master.id} className="user-item">
                <div className="user-info">
                  <span className="user-name">{master.related_user.name}</span>
                  <span className="user-username">@{master.related_user.username}</span>
                </div>
                <span className="master-badge">Your Master</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ManageRequests;
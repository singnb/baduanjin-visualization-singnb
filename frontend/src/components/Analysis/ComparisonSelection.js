// src/components/Analysis/ComparisonSelection.js

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import './ComparisonSelection.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

const ComparisonSelection = () => {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  
  const [masters, setMasters] = useState([]);
  const [selectedMaster, setSelectedMaster] = useState(null);
  const [masterVideos, setMasterVideos] = useState([]);
  const [selectedMasterVideo, setSelectedMasterVideo] = useState(null);
  const [userVideos, setUserVideos] = useState([]);
  const [selectedUserVideo, setSelectedUserVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingVideoCounts, setLoadingVideoCounts] = useState(false);

  // FIXED: Fetch masters with actual video counts
  const fetchMastersWithVideoCounts = async (mastersList) => {
    setLoadingVideoCounts(true);
    try {
      // Fetch video counts for each master
      const mastersWithCounts = await Promise.all(
        mastersList.map(async (master) => {
          try {
            const response = await axios.get(
              `${BACKEND_URL}/api/analysis-master/master-extracted-videos/${master.id}`,
              {
                headers: { 'Authorization': `Bearer ${token}` }
              }
            );
            
            return {
              ...master,
              video_count: response.data.length || 0
            };
          } catch (error) {
            console.error(`Error fetching video count for master ${master.id}:`, error);
            return {
              ...master,
              video_count: 0
            };
          }
        })
      );
      
      console.log('Masters with video counts:', mastersWithCounts);
      setMasters(mastersWithCounts);
    } catch (error) {
      console.error('Error fetching masters with video counts:', error);
      setMasters(mastersList); // Use original list without counts if fetch fails
    } finally {
      setLoadingVideoCounts(false);
    }
  };

  // Fetch available masters
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Get masters
        const mastersResponse = await axios.get(`${BACKEND_URL}/api/relationships/masters`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        console.log('Fetched masters:', mastersResponse.data);
        
        // Get user's own videos with extracted JSON
        const userVideosResponse = await axios.get(`${BACKEND_URL}/api/analysis-master/user-extracted-videos`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        console.log('Fetched user videos:', userVideosResponse.data);
        setUserVideos(userVideosResponse.data);
        
        // Fetch video counts for masters
        await fetchMastersWithVideoCounts(mastersResponse.data);
        
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [token]);

  // Fetch master's videos when a master is selected
  const handleMasterSelect = async (master) => {
    setSelectedMaster(master);
    setSelectedMasterVideo(null);
    
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/analysis-master/master-extracted-videos/${master.id}`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      console.log(`Fetched videos for master ${master.id}:`, response.data);
      setMasterVideos(response.data);
    } catch (err) {
      console.error('Error fetching master videos:', err);
      alert('Failed to load master videos');
    }
  };

  // Handle comparison
  const handleCompare = () => {
    if (!selectedUserVideo || !selectedMasterVideo) {
      alert('Please select both your video and a master video to compare');
      return;
    }
    
    // Navigate to comparison view
    navigate(`/comparison/${selectedUserVideo.id}/${selectedMasterVideo.id}`);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading comparison data...</p>
      </div>
    );
  }

  if (error) {
    return <div className="error-container">{error}</div>;
  }

  return (
    <div className="comparison-selection-container">
      <div className="section-header">
        <h1>Select Videos for Comparison</h1>
        <p>Choose your exercise video and a master's video to compare</p>
      </div>

      <div className="selection-grid">
        {/* User's Videos Section */}
        <div className="selection-section">
          <h2>Your Videos ({userVideos.length})</h2>
          <div className="video-list">
            {userVideos.length === 0 ? (
              <p className="empty-message">No videos with extracted data found. Please extract analysis data first.</p>
            ) : (
              userVideos.map(video => (
                <div 
                  key={video.id} 
                  className={`video-card ${selectedUserVideo?.id === video.id ? 'selected' : ''}`}
                  onClick={() => setSelectedUserVideo(video)}
                >
                  <h4>{video.title}</h4>
                  <p>Type: {video.brocade_type}</p>
                  <p>Date: {new Date(video.upload_timestamp).toLocaleDateString()}</p>
                  <div className="status-badge extracted">Data Extracted</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Masters Section */}
        <div className="selection-section">
          <h2>Select a Master</h2>
          {loadingVideoCounts && (
            <div className="loading-info">
              <small>Loading video counts...</small>
            </div>
          )}
          <div className="master-list">
            {masters.length === 0 ? (
              <p className="empty-message">No masters available</p>
            ) : (
              masters.map(master => (
                <div 
                  key={master.id} 
                  className={`master-card ${selectedMaster?.id === master.id ? 'selected' : ''}`}
                  onClick={() => handleMasterSelect(master)}
                >
                  <div className="master-avatar">
                    {master.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="master-info">
                    <h4>{master.name}</h4>
                    {/* FIXED: Show actual video count or loading state */}
                    <p>
                      {loadingVideoCounts ? (
                        <span className="loading-text">Loading...</span>
                      ) : (
                        `${master.video_count || 0} videos`
                      )}
                    </p>
                    {/* Add master ID for debugging */}
                    {process.env.NODE_ENV === 'development' && (
                      <small style={{ color: '#666' }}>ID: {master.id}</small>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Master's Videos Section */}
        <div className="selection-section">
          <h2>Master's Videos</h2>
          {!selectedMaster ? (
            <p className="empty-message">Select a master to view their videos</p>
          ) : (
            <div className="video-list">
              {masterVideos.length === 0 ? (
                <p className="empty-message">No videos with extracted data found for this master</p>
              ) : (
                masterVideos.map(video => (
                  <div 
                    key={video.id} 
                    className={`video-card ${selectedMasterVideo?.id === video.id ? 'selected' : ''}`}
                    onClick={() => setSelectedMasterVideo(video)}
                  >
                    <h4>{video.title}</h4>
                    <p>Type: {video.brocade_type}</p>
                    <p>Date: {new Date(video.upload_timestamp).toLocaleDateString()}</p>
                    <div className="status-badge extracted">Data Extracted</div>
                    {/* Add video ID for debugging */}
                    {process.env.NODE_ENV === 'development' && (
                      <small style={{ color: '#666' }}>Video ID: {video.id}</small>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        <button 
          className="btn btn-primary"
          onClick={handleCompare}
          disabled={!selectedUserVideo || !selectedMasterVideo}
        >
          Compare Videos
        </button>
        <button 
          className="btn btn-secondary"
          onClick={() => navigate('/videos')}
        >
          Back to Videos Management
        </button>
      </div>

      {/* Selection Summary */}
      {(selectedUserVideo || selectedMasterVideo) && (
        <div className="selection-summary">
          <h3>Selected for Comparison:</h3>
          <div className="summary-content">
            {selectedUserVideo && (
              <div className="summary-item">
                <strong>Your Video:</strong> {selectedUserVideo.title} ({selectedUserVideo.brocade_type})
                {process.env.NODE_ENV === 'development' && (
                  <small style={{ display: 'block', color: '#666' }}>ID: {selectedUserVideo.id}</small>
                )}
              </div>
            )}
            {selectedMasterVideo && (
              <div className="summary-item">
                <strong>Master Video:</strong> {selectedMasterVideo.title} ({selectedMasterVideo.brocade_type})
                {process.env.NODE_ENV === 'development' && (
                  <small style={{ display: 'block', color: '#666' }}>ID: {selectedMasterVideo.id}</small>
                )}
              </div>
            )}
          </div>
          {selectedUserVideo && selectedMasterVideo && 
           selectedUserVideo.brocade_type !== selectedMasterVideo.brocade_type && (
            <div className="warning-message">
              Warning: You're comparing different exercise types. Results may not be meaningful.
            </div>
          )}
        </div>
      )}

      {/* Debug Information */}
      {process.env.NODE_ENV === 'development' && (
        <div className="debug-section" style={{ 
          marginTop: '20px', 
          padding: '15px', 
          background: '#f5f5f5', 
          borderRadius: '4px',
          fontSize: '12px'
        }}>
          <h4>Debug Information:</h4>
          <p>Total Masters: {masters.length}</p>
          <p>User Videos: {userVideos.length}</p>
          <p>Selected User Video ID: {selectedUserVideo?.id || 'None'}</p>
          <p>Selected Master ID: {selectedMaster?.id || 'None'}</p>
          <p>Selected Master Video ID: {selectedMasterVideo?.id || 'None'}</p>
          <p>Master Videos for Selected Master: {masterVideos.length}</p>
        </div>
      )}
    </div>
  );
};

export default ComparisonSelection;

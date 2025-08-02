/* eslint-disable react-hooks/exhaustive-deps */
// src/components/Analysis/ComparisonSelection.js

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import './ComparisonSelection.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

// Create axios instance with custom timeout
const apiClient = axios.create({
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json'
  }
});

const ComparisonSelection = () => {
  const { token } = useAuth();
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
  const [videoCountErrors, setVideoCountErrors] = useState(new Set());

  // IMPROVED: Fetch masters with video counts (with better error handling)
  const fetchMastersWithVideoCounts = async (mastersList) => {
    setLoadingVideoCounts(true);
    setVideoCountErrors(new Set());
    
    try {
      // Process masters in smaller batches to avoid overwhelming the server
      const batchSize = 3;
      const batches = [];
      
      for (let i = 0; i < mastersList.length; i += batchSize) {
        batches.push(mastersList.slice(i, i + batchSize));
      }
      
      let mastersWithCounts = [...mastersList];
      const errors = new Set();
      
      // Process each batch with delay
      for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
        const batch = batches[batchIndex];
        
        console.log(`Processing batch ${batchIndex + 1}/${batches.length} with ${batch.length} masters`);
        
        // Process batch in parallel
        const batchResults = await Promise.allSettled(
          batch.map(async (master) => {
            try {
              console.log(`Fetching video count for master ${master.id} (${master.name})`);
              
              const controller = new AbortController();
              const timeoutId = setTimeout(() => controller.abort(), 25000); // 25s timeout per request
              
              const response = await apiClient.get(
                `${BACKEND_URL}/api/analysis-master/master-extracted-videos/${master.id}`,
                {
                  headers: { 'Authorization': `Bearer ${token}` },
                  signal: controller.signal
                }
              );
              
              clearTimeout(timeoutId);
              
              const videoCount = response.data.length || 0;
              console.log(`✅ Master ${master.id} has ${videoCount} videos`);
              
              return {
                ...master,
                video_count: videoCount,
                video_count_loaded: true
              };
            } catch (error) {
              console.error(`❌ Error fetching video count for master ${master.id}:`, error.message);
              errors.add(master.id);
              
              return {
                ...master,
                video_count: 0,
                video_count_loaded: false,
                video_count_error: error.code === 'ECONNABORTED' ? 'Timeout' : 'Error'
              };
            }
          })
        );
        
        // Update results from this batch
        batchResults.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            const masterIndex = mastersWithCounts.findIndex(m => m.id === batch[index].id);
            if (masterIndex !== -1) {
              mastersWithCounts[masterIndex] = result.value;
            }
          }
        });
        
        // Update state with current progress
        setMasters([...mastersWithCounts]);
        setVideoCountErrors(new Set(errors));
        
        // Small delay between batches to avoid overwhelming server
        if (batchIndex < batches.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      console.log('✅ Finished loading video counts for all masters');
      
    } catch (error) {
      console.error('Error in fetchMastersWithVideoCounts:', error);
      // Keep the original masters list if batch processing fails
      setMasters(mastersList.map(master => ({ ...master, video_count: '?', video_count_loaded: false })));
    } finally {
      setLoadingVideoCounts(false);
    }
  };

  // IMPROVED: Fetch master videos with timeout handling
  const fetchMasterVideos = async (masterId) => {
    try {
      console.log(`Fetching videos for master ${masterId}`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
      
      const response = await apiClient.get(
        `${BACKEND_URL}/api/analysis-master/master-extracted-videos/${masterId}`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
          signal: controller.signal
        }
      );
      
      clearTimeout(timeoutId);
      
      console.log(`✅ Fetched ${response.data.length} videos for master ${masterId}`);
      return response.data;
      
    } catch (error) {
      console.error(`❌ Error fetching videos for master ${masterId}:`, error);
      
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timed out. The master may have many videos to process.');
      } else if (error.response?.status === 404) {
        throw new Error('Master not found');
      } else if (error.response?.status >= 500) {
        throw new Error('Server error. Please try again later.');
      } else {
        throw new Error('Failed to load master videos. Please try again.');
      }
    }
  };

  // Fetch available masters and user videos
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        console.log('🔄 Fetching masters and user videos...');
        
        // Get masters and user videos in parallel
        const [mastersResponse, userVideosResponse] = await Promise.all([
          apiClient.get(`${BACKEND_URL}/api/relationships/masters`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          apiClient.get(`${BACKEND_URL}/api/analysis-master/user-extracted-videos`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);
        
        console.log('✅ Fetched masters:', mastersResponse.data.length);
        console.log('✅ Fetched user videos:', userVideosResponse.data.length);
        
        setUserVideos(userVideosResponse.data);
        
        // Set masters initially without video counts
        const mastersWithoutCounts = mastersResponse.data.map(master => ({
          ...master,
          video_count: '...',
          video_count_loaded: false
        }));
        setMasters(mastersWithoutCounts);
        
        // Then fetch video counts in background
        if (mastersResponse.data.length > 0) {
          console.log('🔄 Starting background fetch of video counts...');
          await fetchMastersWithVideoCounts(mastersResponse.data);
        }
        
      } catch (err) {
        console.error('❌ Error fetching initial data:', err);
        setError('Failed to load data. Please refresh the page.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [token]);

  // Handle master selection with improved loading
  const handleMasterSelect = async (master) => {
    setSelectedMaster(master);
    setSelectedMasterVideo(null);
    setMasterVideos([]);
    
    try {
      const videos = await fetchMasterVideos(master.id);
      setMasterVideos(videos);
    } catch (err) {
      alert(`Failed to load videos for ${master.name}: ${err.message}`);
      setMasterVideos([]);
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
    return (
      <div className="error-container">
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="comparison-selection-container">
      <div className="section-header">
        <h1>Select Videos for Comparison</h1>
        <p>Choose your exercise video and a master's video to compare</p>
        {loadingVideoCounts && (
          <div className="loading-banner" style={{ 
            background: '#e3f2fd', 
            padding: '8px 16px', 
            borderRadius: '4px', 
            marginTop: '10px',
            color: '#1976d2'
          }}>
            🔄 Loading video counts in background... This may take a moment.
          </div>
        )}
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
                    <p>
                      {!master.video_count_loaded ? (
                        <span className="loading-text">
                          {videoCountErrors.has(master.id) ? (
                            <span style={{ color: '#f44336' }}>
                              ⚠️ {master.video_count_error || 'Error loading'}
                            </span>
                          ) : (
                            <span style={{ color: '#ff9800' }}>
                              ⏳ Loading...
                            </span>
                          )}
                        </span>
                      ) : (
                        `${master.video_count || 0} videos`
                      )}
                    </p>
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

      {/* Performance Tips */}
      {videoCountErrors.size > 0 && (
        <div className="performance-tips" style={{
          marginTop: '20px',
          padding: '15px',
          background: '#fff3cd',
          border: '1px solid #ffeaa7',
          borderRadius: '4px'
        }}>
          <h4>🔧 Performance Notice</h4>
          <p>Some masters have many videos to process, causing timeouts. Video counts will load when you select individual masters.</p>
          <p>Affected masters: {Array.from(videoCountErrors).join(', ')}</p>
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
          <p>Loading Video Counts: {loadingVideoCounts ? 'Yes' : 'No'}</p>
          <p>Video Count Errors: {Array.from(videoCountErrors).join(', ') || 'None'}</p>
        </div>
      )}
    </div>
  );
};

export default ComparisonSelection;
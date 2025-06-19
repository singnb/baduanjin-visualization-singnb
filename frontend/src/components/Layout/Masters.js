// src/components/Layout/Masters.js

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './PageStyles.css';
import './Masters.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

function Masters() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [masters, setMasters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [followStatus, setFollowStatus] = useState({});
  const [selectedMaster, setSelectedMaster] = useState(null);
  const [masterVideos, setMasterVideos] = useState([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [hasEnglishAudio, setHasEnglishAudio] = useState(false);

  // Fetch all masters from backend
  useEffect(() => {
    const fetchMasters = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${BACKEND_URL}/api/relationships/masters`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.data && response.data.length > 0) {
          setMasters(response.data);
          
          // Check follow status for each master
          const statusPromises = response.data.map(master => 
            checkFollowStatus(master.id)
          );
          
          await Promise.all(statusPromises);
        } else {
          setError("No masters found in the system.");
        }
      } catch (err) {
        console.error("Error fetching masters data:", err);
        setError("Failed to load masters information. Please try again later.");
      } finally {
        setLoading(false);
      }
    };
    
    fetchMasters();
  }, [token]);

  // Check if user is following a specific master
  const checkFollowStatus = async (masterId) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/relationships/status/${masterId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      setFollowStatus(prev => ({
        ...prev,
        [masterId]: response.data.is_following
      }));
    } catch (err) {
      console.error("Error checking follow status:", err);
      setFollowStatus(prev => ({
        ...prev,
        [masterId]: false
      }));
    }
  };

  // Handle follow/unfollow action
  const handleFollowToggle = async (masterId) => {
    const isCurrentlyFollowing = followStatus[masterId];
    
    try {
      if (isCurrentlyFollowing) {
        // Unfollow API call
        await axios.post(`${BACKEND_URL}/api/relationships/unfollow/${masterId}`, {}, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        setFollowStatus(prev => ({
          ...prev,
          [masterId]: false
        }));
      } else {
        // Follow API call
        await axios.post(`${BACKEND_URL}/api/relationships/follow/${masterId}`, {}, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        setFollowStatus(prev => ({
          ...prev,
          [masterId]: true
        }));
      }
    } catch (err) {
      console.error("Error updating follow status:", err);
      alert("There was an error updating your relationship with this master. Please try again.");
    }
  };

  // FIXED: Fetch and display master's videos that are ready for analysis
  const fetchMasterVideos = async (masterId) => {
    setVideosLoading(true);
    try {
      console.log(`Fetching videos for master ${masterId}`);
      
      // FIXED: Use the correct endpoint that matches ComparisonSelection.js
      const response = await axios.get(
        `${BACKEND_URL}/api/analysis-master/master-extracted-videos/${masterId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      console.log('Master videos response:', response.data);
      console.log('Number of videos found:', response.data.length);
      
      setMasterVideos(response.data);
      setSelectedMaster(masters.find(m => m.id === masterId));
    } catch (err) {
      console.error('Error fetching master videos:', err);
      console.error('Error details:', err.response?.data);
      
      // More specific error message
      if (err.response?.status === 404) {
        alert('No videos found for this master or master not found.');
      } else if (err.response?.status === 403) {
        alert('Access denied. You may not have permission to view this master\'s videos.');
      } else {
        alert(`Error loading master videos: ${err.response?.data?.detail || err.message}`);
      }
      
      setMasterVideos([]);
    } finally {
      setVideosLoading(false);
    }
  };

  // ENHANCED: View a specific video with improved English audio detection
  const viewVideo = async (video) => {
    setSelectedVideo(video);
    
    // ENHANCED: Check if this video has an English audio version with fallback logic
    try {
      // Method 1: Try the backend endpoint first
      const response = await axios.get(
        `${BACKEND_URL}/api/videos/${video.id}/has-english-audio`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      console.log(`English audio check for video ${video.id}:`, response.data);
      
      let hasEnglish = response.data.has_english_audio;
      
      // Method 2: If backend says no English audio, try to verify by attempting to access the file
      if (!hasEnglish) {
        console.log(`Backend says no English audio for video ${video.id}, trying fallback check...`);
        
        try {
          // Try to access the English audio stream endpoint to see if it exists
          const englishStreamUrl = `${BACKEND_URL}/api/videos/${video.id}/stream-video?type=english&token=${encodeURIComponent(token)}`;
          
          // Make a HEAD request to check if the file exists without downloading it
          const headResponse = await axios.head(englishStreamUrl, {
            timeout: 5000 // 5 second timeout
          });
          
          if (headResponse.status === 200) {
            console.log(`Fallback check: English audio found for video ${video.id}`);
            hasEnglish = true;
          }
        } catch (fallbackError) {
          console.log(`Fallback check failed for video ${video.id}:`, fallbackError.response?.status);
          // If we get 404 or other errors, English audio probably doesn't exist
          hasEnglish = false;
        }
      }
      
      console.log(`Final English audio status for video ${video.id}: ${hasEnglish}`);
      setHasEnglishAudio(hasEnglish);
      
    } catch (err) {
      console.error('Error checking for English audio version:', err);
      // If the check fails entirely, try the fallback method
      try {
        console.log('Primary check failed, trying direct stream check...');
        const englishStreamUrl = `${BACKEND_URL}/api/videos/${video.id}/stream-video?type=english&token=${encodeURIComponent(token)}`;
        
        const headResponse = await axios.head(englishStreamUrl, {
          timeout: 5000
        });
        
        if (headResponse.status === 200) {
          console.log(`Direct stream check: English audio found for video ${video.id}`);
          setHasEnglishAudio(true);
        } else {
          setHasEnglishAudio(false);
        }
      } catch (directError) {
        console.log('Direct stream check also failed, assuming no English audio');
        setHasEnglishAudio(false);
      }
    }
    
    setShowVideoModal(true);
  };

  const closeVideoModal = () => {
    setShowVideoModal(false);
    setSelectedVideo(null);
    setHasEnglishAudio(false);
  };

  // Updated to use the new stream-video endpoint
  const getStreamingUrl = (videoId, type = 'original') => {
    return `${BACKEND_URL}/api/videos/${videoId}/stream-video?type=${type}&token=${encodeURIComponent(token)}`;
  };

  // Debug button to help troubleshoot video paths
  const debugVideoPaths = async (videoId) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/videos/${videoId}/debug-paths`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      console.log("Available video paths:", response.data);
      alert("Video paths logged to console. Please check browser developer tools.");
    } catch (err) {
      console.error("Error checking video paths:", err);
      alert("Error checking video paths. See console for details.");
    }
  };

  // Navigate to comparison selection with this master pre-selected
  const handleCompareWithMaster = (masterId, masterVideoId) => {
    // Navigate to comparison selection page
    // The user can then select their own video to compare
    navigate(`/comparison-selection?master=${masterId}&masterVideo=${masterVideoId}`);
  };

  // ENHANCED: Navigate to analysis page with this master and video
  const handleAnalyzeWithMaster = async (masterId, masterVideoId) => {
    try {
      console.log(`Preparing analysis for master ${masterId}, video ${masterVideoId}`);
      
      // Extract JSON files for comparison if not already done
      const extractResponse = await axios.post(
        `${BACKEND_URL}/api/analysis-master/extract/${masterVideoId}`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      console.log('Extract response:', extractResponse.data);
      
      if (extractResponse.data.status === 'success' || extractResponse.data.status === 'already_exists') {
        // Navigate to comparison selection with pre-selected master video
        navigate(`/comparison-selection?masterVideo=${masterVideoId}`);
      } else {
        alert('Failed to prepare analysis data. Please try again.');
      }
    } catch (err) {
      console.error('Error preparing analysis:', err);
      console.error('Error details:', err.response?.data);
      
      if (err.response && err.response.data && err.response.data.detail) {
        alert(`Error: ${err.response.data.detail}`);
      } else {
        alert('Error preparing analysis. Please check the console for details.');
      }
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-spinner">Loading masters information...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  return (
    <div className="page-container masters-page">
      <div className="page-content">
        <h2>Baduanjin Masters</h2>
        <p className="page-intro">
          Browse registered masters and view their analyzed videos. Follow a master to compare your exercises with their techniques.
        </p>
        
        {/* Masters List */}
        <div className="masters-grid">
          {masters.map(master => (
            <div key={master.id} className="master-card">
              <div className="master-header">
                <div className="master-image-placeholder">
                  {master.name.charAt(0)}
                </div>
                <div className="master-basic-info">
                  <h3>{master.name}</h3>
                  <p className="master-username">@{master.username}</p>
                  <p className="master-role">Baduanjin Master</p>
                  {/* Add master ID for debugging */}
                  {process.env.NODE_ENV === 'development' && (
                    <small style={{ color: '#666' }}>Master ID: {master.id}</small>
                  )}
                </div>
              </div>
              
              {master.profile && master.profile.bio && (
                <div className="master-bio">
                  <p>{master.profile.bio}</p>
                </div>
              )}
              
              <div className="master-stats">
                <div className="stat-item">
                  <span className="stat-value">{master.videos_count || 0}</span>
                  <span className="stat-label">Videos</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">{master.followers_count || 0}</span>
                  <span className="stat-label">Followers</span>
                </div>
              </div>
              
              <div className="master-actions">
                <button 
                  className={`btn ${followStatus[master.id] ? 'btn-success' : 'btn-primary'}`}
                  onClick={() => handleFollowToggle(master.id)}
                >
                  {followStatus[master.id] ? 'Following' : 'Follow Master'}
                </button>
                
                <button 
                  className="btn btn-secondary"
                  onClick={() => fetchMasterVideos(master.id)}
                >
                  View Videos
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Selected Master's Videos */}
        {selectedMaster && (
          <div className="master-videos-section">
            <h3>{selectedMaster.name}'s Analyzed Videos</h3>
            
            {videosLoading ? (
              <div className="loading-spinner">Loading videos...</div>
            ) : masterVideos.length > 0 ? (
              <div className="videos-grid">
                {masterVideos.map(video => (
                  <div key={video.id} className="video-card">
                    <div className="video-info">
                      <h4>{video.title}</h4>
                      <p className="video-description">{video.description}</p>
                      <p className="video-type">Type: {video.brocade_type}</p>
                      <p className="video-status">Status: {video.processing_status}</p>
                      <p className="video-date">
                        Uploaded: {new Date(video.upload_timestamp).toLocaleDateString()}
                      </p>
                      {/* Add video ID for debugging */}
                      {process.env.NODE_ENV === 'development' && (
                        <small style={{ color: '#666' }}>Video ID: {video.id}</small>
                      )}
                      
                      <div className="video-actions">
                        <button 
                          className="btn btn-primary"
                          onClick={() => viewVideo(video)}
                        >
                          View Video
                        </button>
                        
                        {/* Add comparison button for all users */}
                        <button 
                          className="btn btn-success"
                          onClick={() => handleCompareWithMaster(selectedMaster.id, video.id)}
                        >
                          Compare With This
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-videos-message">
                <p>This master has no analyzed videos ready for comparison.</p>
                <small>Videos must be fully processed and have extracted analysis data to appear here.</small>
              </div>
            )}
          </div>
        )}

        {/* Enhanced Video Modal with Better English Audio Handling */}
        {showVideoModal && selectedVideo && (
          <div className="video-modal-overlay" onClick={closeVideoModal}>
            <div className="video-modal" onClick={(e) => e.stopPropagation()}>
              <div className="video-modal-header">
                <h3>{selectedVideo.title}</h3>
                <button className="close-btn" onClick={closeVideoModal}>×</button>
              </div>
              <div className="video-modal-content">
                {/* Original Video */}
                <div className="video-player-container">
                  <h4>Original Video</h4>
                  <div className="video-player-wrapper">
                    <video 
                      controls 
                      className="modal-video-player"
                      src={getStreamingUrl(selectedVideo.id, 'original')}
                      onError={(e) => {
                        console.error('Error loading original video:', e);
                        console.log('Video URL:', getStreamingUrl(selectedVideo.id, 'original'));
                      }}
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>
                </div>

                {/* English Version Video - Enhanced with better detection */}
                {hasEnglishAudio && (
                  <div className="video-player-container">
                    <h4>English Version Video</h4>
                    <div className="video-player-wrapper">
                      <video 
                        controls 
                        className="modal-video-player"
                        src={getStreamingUrl(selectedVideo.id, 'english')}
                        onError={(e) => {
                          console.error('Error loading English video:', e);
                          console.log('English Video URL:', getStreamingUrl(selectedVideo.id, 'english'));
                          // If English video fails to load, hide this section
                          setHasEnglishAudio(false);
                        }}
                        onLoadStart={() => {
                          console.log('English video started loading successfully');
                        }}
                      >
                        Your browser does not support the video tag.
                      </video>
                    </div>
                  </div>
                )}

                {/* Manual English Audio Test Button - for debugging */}
                {process.env.NODE_ENV === 'development' && (
                  <div className="debug-controls" style={{ margin: '10px 0', padding: '10px', background: '#f0f0f0', borderRadius: '4px' }}>
                    <h5>Debug Controls:</h5>
                    <button 
                      className="btn btn-small"
                      onClick={async () => {
                        try {
                          const englishUrl = getStreamingUrl(selectedVideo.id, 'english');
                          console.log('Testing English audio URL:', englishUrl);
                          
                          const response = await axios.head(englishUrl, { timeout: 5000 });
                          console.log('English audio test result:', response.status);
                          
                          if (response.status === 200) {
                            alert('English audio file exists! Enabling English version.');
                            setHasEnglishAudio(true);
                          } else {
                            alert('English audio file not found.');
                          }
                        } catch (error) {
                          console.log('English audio test failed:', error.response?.status);
                          alert(`English audio test failed: ${error.response?.status || 'Network error'}`);
                        }
                      }}
                      style={{ marginRight: '10px', fontSize: '12px' }}
                    >
                      Test English Audio
                    </button>
                    
                    <button 
                      className="btn btn-small"
                      onClick={() => {
                        console.log('Force enabling English audio for testing');
                        setHasEnglishAudio(true);
                      }}
                      style={{ fontSize: '12px' }}
                    >
                      Force Enable English
                    </button>
                  </div>
                )}

                {/* Show analyzed video if available */}
                {(selectedVideo.analyzed_video_path || selectedVideo.processing_status === 'completed') && (
                  <div className="video-player-container">
                    <h4>Analysis Video</h4>
                    <div className="video-player-wrapper">
                      <video 
                        controls 
                        className="modal-video-player"
                        src={getStreamingUrl(selectedVideo.id, 'analyzed')}
                        onError={(e) => {
                          console.error('Error loading analyzed video:', e);
                          console.log('Analyzed Video URL:', getStreamingUrl(selectedVideo.id, 'analyzed'));
                        }}
                      >
                        Your browser does not support the video tag.
                      </video>
                    </div>
                  </div>
                )}
                
                <div className="video-info">
                  {selectedVideo.description && <p><strong>Description:</strong> {selectedVideo.description}</p>}
                  <p><strong>Brocade Type:</strong> {selectedVideo.brocade_type}</p>
                  <p><strong>Status:</strong> {selectedVideo.processing_status}</p>
                  <p><strong>Upload Date:</strong> {new Date(selectedVideo.upload_timestamp).toLocaleDateString()}</p>
                  {hasEnglishAudio && <p className="english-audio-badge">English Audio Available ✓</p>}
                  
                  {/* Debug button - only in development */}
                  {process.env.NODE_ENV === 'development' && (
                    <button 
                      className="btn btn-small debug-btn" 
                      onClick={() => debugVideoPaths(selectedVideo.id)}
                      style={{ marginTop: '10px', fontSize: '12px' }}
                    >
                      Debug Video Paths
                    </button>
                  )}
                </div>
              </div>
            </div>
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
            <p>Selected Master: {selectedMaster?.name} (ID: {selectedMaster?.id})</p>
            <p>Master Videos Count: {masterVideos.length}</p>
            <p>Videos Loading: {videosLoading ? 'Yes' : 'No'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Masters;

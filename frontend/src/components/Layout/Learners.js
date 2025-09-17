// src/components/Layout/Learners.js

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './PageStyles.css';
import './Learners.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

function Learners() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [learners, setLearners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLearner, setSelectedLearner] = useState(null);
  const [learnerVideos, setLearnerVideos] = useState([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState(null);

  // Redirect if not a master user
  useEffect(() => {
    if (user?.role !== 'master') {
      console.log("Access restricted: Only master users can view this page");
      navigate('/dashboard');
    }
  }, [user, navigate]);

  // Fetch learners who follow this master
  useEffect(() => {
    const fetchLearners = async () => {
      if (!token) return;
      
      setLoading(true);
      try {
        const response = await axios.get(`${BACKEND_URL}/api/relationships/learners`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        console.log('Fetched learners:', response.data);
        
        // Get additional learner details including video count and last activity
        const learnersWithDetails = await Promise.all(
          response.data.map(async (learner) => {
            try {
              const detailsResponse = await axios.get(
                `${BACKEND_URL}/api/relationships/learner-details/${learner.learner_id}`,
                {
                  headers: {
                    'Authorization': `Bearer ${token}`
                  }
                }
              );
              
              return {
                ...learner,
                ...detailsResponse.data
              };
            } catch (error) {
              console.error(`Error fetching details for learner ${learner.learner_id}:`, error);
              return learner;
            }
          })
        );
        
        console.log('Learners with details:', learnersWithDetails);
        setLearners(learnersWithDetails);
        setError(null);
      } catch (err) {
        console.error('Error fetching learners:', err);
        setError('Failed to load learners. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchLearners();
  }, [token]);

  // FIXED: Fetch videos for selected learner using multiple approaches
  const fetchLearnerVideos = async (learnerId) => {
    setVideosLoading(true);
    console.log(`Fetching videos for learner ${learnerId}`);
    
    try {
      let learnerVideosData = [];
      
      // Method 1: Try the original relationships endpoint
      try {
        const response = await axios.get(
          `${BACKEND_URL}/api/relationships/learner-videos/${learnerId}/analyzed`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        console.log('Method 1 - Relationships endpoint response:', response.data);
        learnerVideosData = response.data;
      } catch (relationshipError) {
        console.warn('Method 1 failed:', relationshipError);
        
        // Method 2: Try to get all videos for the learner and filter for analyzed ones
        try {
          const allVideosResponse = await axios.get(
            `${BACKEND_URL}/api/relationships/learner-videos/${learnerId}`,
            {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            }
          );
          
          console.log('Method 2 - All learner videos:', allVideosResponse.data);
          
          // Filter for completed/analyzed videos
          learnerVideosData = allVideosResponse.data.filter(video => 
            video.processing_status === 'completed' && 
            (video.analyzed_video_path || video.keypoints_path)
          );
          
          console.log('Method 2 - Filtered analyzed videos:', learnerVideosData);
        } catch (allVideosError) {
          console.warn('Method 2 failed:', allVideosError);
          
          // Method 3: If we have a direct API to get user's extracted videos, try that
          // This would require knowing the learner's user ID and calling with their context
          console.log('All methods failed, returning empty array');
          learnerVideosData = [];
        }
      }
      
      // Additional filtering to ensure we only show videos with analysis data
      const validAnalyzedVideos = learnerVideosData.filter(video => {
        const hasAnalysisFiles = video.analyzed_video_path && video.keypoints_path;
        const isCompleted = video.processing_status === 'completed';
        const isValid = hasAnalysisFiles && isCompleted;
        
        if (!isValid) {
          console.log(`Filtering out video ${video.id}: hasAnalysisFiles=${hasAnalysisFiles}, isCompleted=${isCompleted}`);
        }
        
        return isValid;
      });
      
      console.log(`Final filtered videos for learner ${learnerId}:`, validAnalyzedVideos);
      setLearnerVideos(validAnalyzedVideos);
      
    } catch (err) {
      console.error('Error fetching learner videos:', err);
      console.error('Error details:', err.response?.data);
      
      // More specific error messages
      if (err.response?.status === 404) {
        console.log('Learner not found or no videos available');
        setLearnerVideos([]);
      } else if (err.response?.status === 403) {
        console.log('Access denied to learner videos');
        setLearnerVideos([]);
      } else {
        console.log('Unknown error occurred');
        setLearnerVideos([]);
      }
    } finally {
      setVideosLoading(false);
    }
  };

  const handleSelectLearner = (learner) => {
    console.log('Selected learner:', learner);
    setSelectedLearner(learner);
    if (learner) {
      fetchLearnerVideos(learner.learner_id);
    }
  };

  const viewVideo = (video) => {
    setSelectedVideo(video);
    setShowVideoModal(true);
  };

  const closeVideoModal = () => {
    setShowVideoModal(false);
    setSelectedVideo(null);
  };

  // Updated to use the new stream-video endpoint
  const getStreamingUrl = (videoId, type = 'original') => {
    return `${BACKEND_URL}/api/videos/${videoId}/stream-video?type=${type}&token=${encodeURIComponent(token)}`;
  };

  const compareWithLearner = (learnerId, learnerVideoId) => {
    // Navigate to comparison selection with the learner video pre-selected
    navigate(`/comparison-selection?learnerVideo=${learnerVideoId}`);
  };

  const sendFeedback = (learnerId) => {
    // Navigate to feedback page or open feedback modal
    alert(`Send feedback to learner ${learnerId} - Feature coming soon!`);
  };

  return (
    <div className="page-container learners-page">
      <div className="page-content">
        <h2>Your Learners</h2>
        <p className="page-intro">
          View and manage learners who follow your teaching and techniques.
        </p>
        
        {loading ? (
          <div className="loading-spinner">Loading learners...</div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : learners.length === 0 ? (
          <div className="empty-state">
            <p>No learners are currently following you.</p>
            <p>Share your master profile to attract learners!</p>
          </div>
        ) : (
          <div className="learners-container">
            <div className="table-container">
              <table className="data-table learners-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Account Type</th>
                    <th>Email</th>
                    <th>Videos</th>
                    <th>Last Active</th>
                    <th>Following Since</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {learners.map(learner => (
                    <tr 
                      key={learner.learner_id} 
                      className={selectedLearner?.learner_id === learner.learner_id ? 'selected-row' : ''}
                      onClick={() => handleSelectLearner(learner)}
                    >
                      <td>{learner.name}</td>
                      <td>{learner.username}</td>
                      <td>{learner.email}</td>
                      <td>{learner.videos_count || 0}</td>
                      <td>{learner.last_active ? new Date(learner.last_active).toLocaleDateString() : 'N/A'}</td>
                      <td>{new Date(learner.created_at).toLocaleDateString()}</td>
                      <td>
                        <button 
                          className="btn btn-primary view-button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectLearner(learner);
                          }}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {selectedLearner && (
              <div className="learner-detail detail-panel">
                <h3>Videos by {selectedLearner.name}</h3>
                {/* Add learner ID for debugging */}
                {process.env.NODE_ENV === 'development' && (
                  <small style={{ color: '#666', display: 'block', marginBottom: '10px' }}>
                    Learner ID: {selectedLearner.learner_id}
                  </small>
                )}
                
                <div className="learner-videos">
                  <h4>Analyzed Videos Ready for Comparison</h4>
                  {videosLoading ? (
                    <div className="loading-spinner">Loading videos...</div>
                  ) : learnerVideos.length > 0 ? (
                    <div className="video-grid">
                      {learnerVideos.map(video => (
                        <div key={video.id} className="video-card">
                          <div className="video-info">
                            <h5>{video.title}</h5>
                            <p className="video-status">Status: {video.processing_status}</p>
                            <p className="video-type">Type: {video.brocade_type}</p>
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
                              <button 
                                className="btn btn-success"
                                onClick={() => compareWithLearner(selectedLearner.learner_id, video.id)}
                              >
                                Compare Performance
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-videos-message">
                      <p>This learner has no analyzed videos ready for comparison.</p>
                      <small>Videos must be fully processed with analysis data to appear here.</small>
                      {process.env.NODE_ENV === 'development' && (
                        <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
                          <p>Debug: Check browser console for API call details</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                <div className="learner-actions" style={{ marginTop: '20px' }}>
                  <button 
                    className="btn btn-secondary"
                    onClick={() => sendFeedback(selectedLearner.learner_id)}
                  >
                    Send Feedback (Coming Soon)
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Video Modal */}
        {showVideoModal && selectedVideo && (
          <div className="video-modal-overlay" onClick={closeVideoModal}>
            <div className="video-modal" onClick={(e) => e.stopPropagation()}>
              <div className="video-modal-header">
                <h3>{selectedVideo.title}</h3>
                <button className="close-btn" onClick={closeVideoModal}>×</button>
              </div>
              <div className="video-modal-content">
                <div className="video-player-container">
                  {/* Original Video */}
                  <div className="video-player-wrapper">
                    <h4>Original Video</h4>
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

                {/* Show analyzed video if available */}
                {(selectedVideo.analyzed_video_path || selectedVideo.processing_status === 'completed') && (
                  <div className="video-player-container">
                    <div className="video-player-wrapper">
                      <h4>Analysis Video</h4>
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
                  
                  {/* Debug button - only in development */}
                  {process.env.NODE_ENV === 'development' && (
                    <button 
                      className="btn btn-small debug-btn" 
                      onClick={async () => {
                        try {
                          const response = await axios.get(
                            `${BACKEND_URL}/api/videos/${selectedVideo.id}/debug-paths`,
                            {
                              headers: {
                                'Authorization': `Bearer ${token}`
                              }
                            }
                          );
                          console.log("Video paths:", response.data);
                          alert("Video paths logged to console. Check developer tools.");
                        } catch (err) {
                          console.error("Error checking video paths:", err);
                          alert("Error checking video paths");
                        }
                      }}
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
            <p>Total Learners: {learners.length}</p>
            <p>Selected Learner: {selectedLearner?.name} (ID: {selectedLearner?.learner_id})</p>
            <p>Learner Videos Count: {learnerVideos.length}</p>
            <p>Videos Loading: {videosLoading ? 'Yes' : 'No'}</p>
            <p>User Role: {user?.role}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Learners;
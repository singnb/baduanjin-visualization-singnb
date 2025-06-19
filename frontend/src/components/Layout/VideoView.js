// src/components/Layout/VideoView.js

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import axios from 'axios';
import './VideoView.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

function VideoView() {
  const { videoId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVideo = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${BACKEND_URL}/api/videos/${videoId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        setVideo(response.data);
      } catch (err) {
        console.error('Error fetching video:', err);
        if (err.response && err.response.status === 404) {
          setError('Video not found');
        } else {
          setError('Failed to load video. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchVideo();
  }, [videoId, token]);

  if (loading) {
    return (
      <div className="video-view-container">
        <div className="loading">Loading video...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-view-container">
        <div className="error-message">{error}</div>
        <button onClick={() => navigate(-1)} className="btn btn-secondary">
          Go Back
        </button>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="video-view-container">
        <div className="error-message">No video data available</div>
        <button onClick={() => navigate(-1)} className="btn btn-secondary">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="video-view-container">
      <div className="video-header">
        <h1>{video.title}</h1>
        <button onClick={() => navigate(-1)} className="btn btn-secondary">
          Back
        </button>
      </div>

      <div className="video-content">
        <div className="video-player-section">
          {video.web_video_path ? (
            <video 
              controls 
              className="video-player"
              src={`${BACKEND_URL}/api/videos/${videoId}/stream`}
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            <div className="no-video-placeholder">
              Video not available
            </div>
          )}
        </div>

        <div className="video-details">
          <div className="detail-section">
            <h3>Description</h3>
            <p>{video.description || 'No description available'}</p>
          </div>

          <div className="detail-section">
            <h3>Video Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Brocade Type:</span>
                <span className="info-value">{video.brocade_type || 'Not specified'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Duration:</span>
                <span className="info-value">{video.duration ? `${video.duration} seconds` : 'Unknown'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Processing Status:</span>
                <span className="info-value status">{video.processing_status}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Uploaded:</span>
                <span className="info-value">
                  {new Date(video.upload_timestamp).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {video.processing_status === 'completed' && (
            <div className="video-actions">
              <button 
                onClick={() => navigate(`/analysis/${videoId}`)} 
                className="btn btn-primary"
              >
                View Analysis
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default VideoView;

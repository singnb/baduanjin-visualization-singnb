// src/components/Layout/VideoAnalysis.js

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import './VideoAnalysis.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

const VideoAnalysis = () => {
  const { videoId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [autoRunAttempted, setAutoRunAttempted] = useState(false);
  const [imageErrors, setImageErrors] = useState({}); // Add image error tracking

  // Fetch analysis data
  const fetchAnalysisData = useCallback(async () => {
    console.log('Fetching analysis data for video:', videoId);
    setLoading(true);
    
    try {
      const response = await axios.get(`${BACKEND_URL}/api/analysis/${videoId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Analysis data received:', response.data);
      setAnalysisData(response.data);
      setError(null);
      
    } catch (err) {
      console.error('Error fetching analysis data:', err);
      setError('Failed to load analysis data: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [videoId, token]);

  // Run analysis
  const runAnalysis = useCallback(async () => {
    console.log('runAnalysis called, current state:', { isAnalyzing, autoRunAttempted });
    
    if (isAnalyzing) {
      console.log('Already analyzing, skipping...');
      return;
    }
    
    setIsAnalyzing(true);
    setError(null);
    console.log('Starting analysis for video:', videoId);
    
    try {
      const response = await axios.post(`${BACKEND_URL}/api/analysis/${videoId}/run`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Analysis started successfully:', response.data);
      
      // Start polling for completion
      const pollForResults = async (attempt = 1) => {
        console.log(`Polling attempt ${attempt} for video ${videoId}`);
        
        try {
          const analysisResponse = await axios.get(`${BACKEND_URL}/api/analysis/${videoId}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          console.log('Poll result:', analysisResponse.data.status);
          
          if (analysisResponse.data.status === 'analyzed') {
            console.log('Analysis completed successfully!');
            setAnalysisData(analysisResponse.data);
            setIsAnalyzing(false);
          } else if (analysisResponse.data.status === 'not_analyzed') {
            // Still processing, continue polling (max 40 attempts = 2 minutes)
            if (attempt < 40) {
              setTimeout(() => pollForResults(attempt + 1), 3000);
            } else {
              console.log('Polling timeout after 2 minutes');
              setIsAnalyzing(false);
              setError('Analysis is taking longer than expected. Please refresh the page to check status.');
            }
          } else {
            // Unknown status
            console.log('Unknown analysis status:', analysisResponse.data.status);
            setIsAnalyzing(false);
            setError('Analysis status unknown: ' + analysisResponse.data.status);
          }
        } catch (pollErr) {
          console.error('Error polling for results:', pollErr);
          if (attempt < 10) {
            // Retry polling with longer delay
            setTimeout(() => pollForResults(attempt + 1), 5000);
          } else {
            setIsAnalyzing(false);
            setError('Failed to check analysis status');
          }
        }
      };
      
      // Start polling after a short delay
      setTimeout(() => pollForResults(), 2000);
      
    } catch (err) {
      console.error('Failed to start analysis:', err);
      console.error('Error details:', err.response?.data);
      setError('Failed to start analysis: ' + (err.response?.data?.detail || err.message));
      setIsAnalyzing(false);
    }
  }, [videoId, token, isAnalyzing, autoRunAttempted]);

  // Initial data fetch
  useEffect(() => {
    console.log('Initial fetch triggered for video:', videoId);
    fetchAnalysisData();
  }, [videoId, fetchAnalysisData]);

  // Auto-run analysis logic with debugging
  useEffect(() => {
    console.log('Auto-run check triggered');
    console.log('Current analysis data:', analysisData);
    console.log('Current state:', { isAnalyzing, autoRunAttempted, loading });
      
    const shouldAutoRun = (
      analysisData && 
      analysisData.status === 'not_analyzed' && 
      analysisData.video_status === 'completed' && 
      !isAnalyzing && 
      !autoRunAttempted &&
      !loading
    );
    
    console.log('Should auto-run?', shouldAutoRun);
    
    if (shouldAutoRun) {
      console.log('Auto-starting analysis...');
      setAutoRunAttempted(true); // Prevent multiple attempts
      runAnalysis();
    }
  }, [analysisData, isAnalyzing, autoRunAttempted, loading, runAnalysis]);

  // UPDATED: Fixed getImageUrl function to handle new backend image proxy
  const getImageUrl = (imagePath) => {
    if (!imagePath) {
      console.warn('getImageUrl called with empty imagePath');
      return null;
    }
    
    try {
      // Check if it's a backend image proxy endpoint (new format)
      if (imagePath.startsWith('/api/analysis/')) {
        const backendUrl = `${BACKEND_URL}${imagePath}`;
        console.log('Using backend image proxy URL:', backendUrl);
        return backendUrl;
      }
      
      // Check if it's already a full URL (Azure blob URL or other)
      if (imagePath.startsWith('https://') || imagePath.startsWith('http://')) {
        console.log('Using direct URL:', imagePath);
        return imagePath;
      }
      
      // It's a relative path, use the backend static endpoint (legacy)
      const backendUrl = `${BACKEND_URL}/api/static/${imagePath}`;
      console.log('Using backend static URL:', backendUrl);
      return backendUrl;
      
    } catch (error) {
      console.error('Error processing image URL:', error, 'imagePath:', imagePath);
      return null;
    }
  };

  // Image error handling functions
  const handleImageError = (imageName, imageUrl) => {
    console.error(`Failed to load image: ${imageName}`, 'URL:', imageUrl);
    setImageErrors(prev => ({ ...prev, [imageName]: true }));
  };

  const handleImageLoad = (imageName) => {
    console.log(`Successfully loaded image: ${imageName}`);
    setImageErrors(prev => ({ ...prev, [imageName]: false }));
  };

  const retryImage = (imageName, imagePath) => {
    setImageErrors(prev => ({ ...prev, [imageName]: false }));
    // Force image reload by adding timestamp
    const imageUrl = getImageUrl(imagePath) + '?t=' + Date.now();
    const imgElements = document.querySelectorAll(`img[alt*="${imageName}"]`);
    imgElements.forEach(img => {
      img.src = imageUrl;
    });
  };

  // Helper function to render images with error handling
  const renderImageWithErrorHandling = (imagePath, altText, imageName) => {
    const imageUrl = getImageUrl(imagePath);
    
    if (!imageUrl) {
      return (
        <div className="image-error">
          <p>Image not available</p>
          <small>Path: {imagePath}</small>
        </div>
      );
    }

    if (imageErrors[imageName]) {
      return (
        <div className="image-error">
          <p>Failed to load image</p>
          <small>URL: {imageUrl}</small>
          <button 
            onClick={() => retryImage(imageName, imagePath)}
            className="retry-button"
          >
            Retry
          </button>
        </div>
      );
    }

    return (
      <img 
        src={imageUrl}
        alt={altText}
        className="analysis-image"
        onError={() => handleImageError(imageName, imageUrl)}
        onLoad={() => handleImageLoad(imageName)}
      />
    );
  };

  // Loading state
  if (loading) {
    console.log('Rendering loading state');
    return (
      <div className="analysis-container">
        <div className="loading-wrapper">
          <div className="loading-spinner"></div>
          <p>Loading analysis data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    console.log('Rendering error state:', error);
    return (
      <div className="analysis-container">
        <div className="error-wrapper">
          <p className="error-message">{error}</p>
          <button onClick={() => {
            setError(null);
            setAutoRunAttempted(false);
            fetchAnalysisData();
          }} className="btn btn-primary">
            Retry
          </button>
          <button onClick={() => navigate('/videos')} className="btn btn-secondary">
            Back to Videos
          </button>
        </div>
      </div>
    );
  }

  // Not analyzed yet - show status
  if (analysisData?.status === 'not_analyzed') {
    console.log('Rendering not-analyzed state, isAnalyzing:', isAnalyzing);
    
    return (
      <div className="analysis-container">
        <div className="not-analyzed-wrapper">
          <h2>{analysisData.video_title}</h2>
          
          {analysisData.video_status === 'completed' ? (
            <div>
              {isAnalyzing ? (
                <div>
                  <div className="loading-spinner"></div>
                  <p>Analyzing movement patterns...</p>
                  <p className="small-text">This usually takes 2-3 minutes</p>
                </div>
              ) : (
                <div>
                  <p>Preparing biomechanical analysis...</p>
                  {!autoRunAttempted && (
                    <button 
                      onClick={runAnalysis} 
                      className="btn btn-primary"
                    >
                      Start Analysis
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div>
              <p>Video processing must be completed before analysis can be run.</p>
              <p className="warning-message">
                Current status: {analysisData.video_status}
              </p>
            </div>
          )}
          
          <button onClick={() => navigate('/videos')} className="btn btn-secondary">
            Back to Videos
          </button>
        </div>
      </div>
    );
  }

  // Analysis running (this state might not be needed with the above logic)
  if (isAnalyzing) {
    console.log('Rendering analyzing state');
    return (
      <div className="analysis-container">
        <div className="analyzing-wrapper">
          <div className="loading-spinner"></div>
          <h2>Analyzing Video</h2>
          <p>Processing movement analysis. This may take a few minutes...</p>
        </div>
      </div>
    );
  }

  // Analysis complete - display results
  console.log('Rendering analysis results');
  return (
    <div className="analysis-container">
      <div className="analysis-header">
        <h1>Movement Analysis: {analysisData.video_title}</h1>
        <button onClick={() => navigate('/videos')} className="btn btn-secondary">
          Back to Videos
        </button>
      </div>

      <div className="analysis-content">
        {/* Key Poses Section */}
        <section className="analysis-section">
          <h2>Key Poses Identified</h2>
          {analysisData.images.key_poses && (
            <div className="image-container">
              {renderImageWithErrorHandling(
                analysisData.images.key_poses, 
                "Key Poses", 
                "key_poses"
              )}
            </div>
          )}
          <div className="key-poses-list">
            {analysisData.key_poses.map((pose, index) => (
              <div key={index} className="pose-item">
                <span className="pose-label">{pose.pose}</span>
                <span className="pose-frame">Frame {pose.frame}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Joint Angles Section */}
        <section className="analysis-section">
          <h2>Joint Angles Analysis</h2>
          {analysisData.images.joint_angles && (
            <div className="image-container">
              {renderImageWithErrorHandling(
                analysisData.images.joint_angles, 
                "Joint Angles", 
                "joint_angles"
              )}
            </div>
          )}
        </section>

        {/* Movement Smoothness Section */}
        <section className="analysis-section">
          <h2>Movement Smoothness</h2>
          {analysisData.images.movement_smoothness && (
            <div className="image-container">
              {renderImageWithErrorHandling(
                analysisData.images.movement_smoothness, 
                "Movement Smoothness", 
                "movement_smoothness"
              )}
            </div>
          )}
          <div className="metrics-grid">
            {Object.entries(analysisData.movement_smoothness).map(([joint, value]) => (
              <div key={joint} className="metric-item">
                <span className="metric-label">{joint}:</span>
                <span className="metric-value">{value.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Movement Symmetry Section */}
        <section className="analysis-section">
          <h2>Movement Symmetry</h2>
          {analysisData.images.movement_symmetry && (
            <div className="image-container">
              {renderImageWithErrorHandling(
                analysisData.images.movement_symmetry, 
                "Movement Symmetry", 
                "movement_symmetry"
              )}
            </div>
          )}
          <div className="metrics-grid">
            {Object.entries(analysisData.movement_symmetry).map(([pair, value]) => (
              <div key={pair} className="metric-item">
                <span className="metric-label">{pair}:</span>
                <span className="metric-value">{value.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Balance Metrics Section */}
        <section className="analysis-section">
          <h2>Balance Metrics</h2>
          <div className="metrics-row">
            {analysisData.images.com_trajectory && (
              <div className="image-container half-width">
                {renderImageWithErrorHandling(
                  analysisData.images.com_trajectory, 
                  "Center of Mass Trajectory", 
                  "com_trajectory"
                )}
              </div>
            )}
            {analysisData.images.balance_metrics && (
              <div className="image-container half-width">
                {renderImageWithErrorHandling(
                  analysisData.images.balance_metrics, 
                  "Balance Metrics", 
                  "balance_metrics"
                )}
              </div>
            )}
          </div>
          <div className="metrics-grid">
            {Object.entries(analysisData.balance_metrics).map(([metric, value]) => (
              <div key={metric} className="metric-item">
                <span className="metric-label">{metric}:</span>
                <span className="metric-value">{value.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default VideoAnalysis;
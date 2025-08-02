// src/components/Analysis/AnalysisView.js

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
// import Dashboard from '../Layout/Dashboard';
// import Sidebar from '../Layout/Sidebar';
import './Analysis.css'; 

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';
const API_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

const AnalysisView = () => {
  const { videoId } = useParams();
  const [videoData, setVideoData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { token } = useAuth();
  
  // For controlling the sidebar and analysis type
  // const [selectedAnalysis, setSelectedAnalysis] = useState('overview');
  // const [comparisonMode, setComparisonMode] = useState('sideBySide');
  
  useEffect(() => {
    const fetchVideoAndAnalysis = async () => {
      setLoading(true);
      try {
        // Fetch video details
        const videoResponse = await axios.get(`${BACKEND_URL}/api/videos/${videoId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        setVideoData(videoResponse.data);
        
        // Fetch analysis summary if processing is completed
        if (videoResponse.data.processing_status === 'completed') {
          const analysisResponse = await axios.get(`${API_URL}/api/analysis/${videoId}/analysis-summary`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          
          console.log('Analysis summary:', analysisResponse.data);
          setAnalysisData(analysisResponse.data);
        }
        
        setError(null);
      } catch (err) {
        console.error('Error fetching video data:', err);
        setError('Failed to load video data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    if (token && videoId) {
      fetchVideoAndAnalysis();
    }
  }, [videoId, token]);

  // const getAnalysisFileUrl = (filename, fileType) => {
  //   return `${BACKEND_URL}/api/analysis/${videoId}/files/${fileType}/${filename}?token=${encodeURIComponent(token)}`;
  // };

  // const getAnalyzedVideoUrl = () => {
  //   if (videoData && videoData.analyzed_video_path) {
  //     // If it's an Azure URL, use the streaming endpoint
  //     if (videoData.analyzed_video_path.startsWith('https://')) {
  //       return `${BACKEND_URL}/api/videos/${videoId}/stream-video?type=analyzed&token=${encodeURIComponent(token)}`;
  //     }
  //     // Fallback for local files
  //     return videoData.analyzed_video_path;
  //   }
  //   return null;
  // };
    
  if (loading) {
    return <div className="loading">Loading analysis data...</div>;
  }
  
  if (error) {
    return <div className="error-message">{error}</div>;
  }
  
  if (!videoData) {
    return <div className="error-message">Video not found</div>;
  }
  
  if (videoData.processing_status !== 'completed') {
    return (
      <div className="processing-message">
        <h2>Video Processing</h2>
        <p>Your video "{videoData.title}" is currently being processed.</p>
        <p>Current status: {videoData.processing_status}</p>
        <p>Please check back later to view the analysis results.</p>
      </div>
    );
  }
  
  return (
    <div className="analysis-view">
      <div className="video-info-header">
        <h2>{videoData.title} Analysis</h2>
        <p>Brocade Type: {videoData.brocade_type}</p>
      </div>
      
  {/* <div className="analysis-content">
        <Sidebar 
          selectedAnalysis={selectedAnalysis}
          setSelectedAnalysis={setSelectedAnalysis}
        />
        
        <Dashboard 
          selectedAnalysis={selectedAnalysis}
          comparisonMode={comparisonMode}
          analysisData={analysisData}
          getAnalysisFileUrl={getAnalysisFileUrl}
          getAnalyzedVideoUrl={getAnalyzedVideoUrl}
          videoData={videoData}
          videoId={videoId}
        />
      </div> */}
    </div>
  );
};

export default AnalysisView;

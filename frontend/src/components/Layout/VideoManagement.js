// src/components/Layout/VideoManagement.js 
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import VideoUpload from './VideoUpload';
import PiVideoTransfer from './PiVideoTransfer';
import './Layout.css';
import './VideoManagement.css';

const API_URL = process.env.REACT_APP_API_URL || 'https://baduanjin-backend-docker.azurewebsites.net';
// Add debug logging
console.log('VideoManagement - API_URL:', API_URL);
console.log('VideoManagement - Environment REACT_APP_API_URL:', process.env.REACT_APP_API_URL);

const VideoManagement = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [analysisInProgress, setAnalysisInProgress] = useState(false);
  const [processingVideoId, setProcessingVideoId] = useState(null);
  const [extractingData, setExtractingData] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionVideoId, setConversionVideoId] = useState(null);
  const [hasEnglishAudio, setHasEnglishAudio] = useState(false);
  const [piTransferComplete, setPiTransferComplete] = useState(false);
  const { token, user } = useAuth();
  const navigate = useNavigate();
  
  // Use useRef for polling interval to avoid dependency issues
  const pollingIntervalRef = useRef(null);

  // ADDED: Helper function to filter videos by current user
  const filterVideosByCurrentUser = (videoList) => {
    if (!user || !user.id) {
      console.warn('No user context available for filtering videos');
      return [];
    }
    
    // Filter videos to only show those belonging to the current user
    const userVideos = videoList.filter(video => {
      const belongsToUser = video.user_id === user.id;
      if (!belongsToUser) {
        console.log(`Filtering out video ${video.id} (belongs to user ${video.user_id}, current user is ${user.id})`);
      }
      return belongsToUser;
    });
    
    console.log(`Filtered ${videoList.length} videos down to ${userVideos.length} for user ${user.id} (${user.role})`);
    return userVideos;
  };

  // ENHANCED: Force completion check function
  const forceCompletionCheck = async (videoId) => {
    try {
      console.log('Performing force completion check for video:', videoId);
      
      // Call the new backend endpoint to check if analysis files exist
      const response = await axios.get(`${API_URL}/api/videos/${videoId}/check-completion`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('Completion check response:', response.data);
      
      if (response.data.completed) {
        console.log('Force completion detected analysis files, marking as complete');
        
        // Call the force-complete endpoint to update the database
        await axios.post(`${API_URL}/api/videos/${videoId}/force-complete`, {}, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        // Update local state
        setAnalysisInProgress(false);
        setProcessingVideoId(null);
        
        // Refresh videos to get updated status
        await fetchVideos();
        
        alert('Analysis appears to be complete! Status has been updated.');
        return true;
      } else {
        console.log('Force completion check - no analysis files found');
        setAnalysisInProgress(false);
        setProcessingVideoId(null);
        alert('Processing timeout reached. The analysis may still be running in the background. Please check back later.');
        return false;
      }
    } catch (err) {
      console.error('Error in force completion check:', err);
      setAnalysisInProgress(false);
      setProcessingVideoId(null);
      alert('Unable to verify completion status. Please refresh the page.');
      return false;
    }
  };

  // ENHANCED: Status polling for processing videos
  const startStatusPolling = useCallback((videoId) => {
    // Clear any existing polling interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    
    setProcessingVideoId(videoId);
    setAnalysisInProgress(true);
    
    const startTime = Date.now();
    const maxPollingTime = 20 * 60 * 1000; // 20 minutes max
    
    console.log(`Starting enhanced polling for video ${videoId}`);
    
    // Create new polling interval
    const intervalId = setInterval(async () => {
      try {
        const currentTime = Date.now();
        const pollingDuration = currentTime - startTime;
        
        // Check if we've been polling too long
        if (pollingDuration > maxPollingTime) {
          console.log('Polling timeout reached after 20 minutes, checking completion...');
          clearInterval(intervalId);
          pollingIntervalRef.current = null;
          
          // Try force completion check before giving up
          const completed = await forceCompletionCheck(videoId);
          if (!completed) {
            setAnalysisInProgress(false);
            setProcessingVideoId(null);
          }
          return;
        }
        
        // Get specific video status
        const response = await axios.get(`${API_URL}/api/videos/${videoId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        const videoData = response.data;
        console.log(`Polling update for video ${videoId}:`, videoData.processing_status);
        
        // ADDED: Verify video belongs to current user
        if (videoData.user_id !== user.id) {
          console.error(`Video ${videoId} does not belong to current user ${user.id}`);
          clearInterval(intervalId);
          pollingIntervalRef.current = null;
          setAnalysisInProgress(false);
          setProcessingVideoId(null);
          return;
        }
        
        // ENHANCED: Check for analysis completion even if status is still 'processing'
        const hasAnalysisFiles = videoData.analyzed_video_path && videoData.keypoints_path;
        const shouldStopPolling = videoData.processing_status !== 'processing' || hasAnalysisFiles;
        
        // Update videos list with new status
        setVideos(prevVideos => 
          prevVideos.map(v => 
            v.id === videoId ? { ...v, ...videoData } : v
          )
        );
        
        // Update selected video if it's the one being processed
        setSelectedVideo(prev => {
          if (prev && prev.id === videoId) {
            return { ...videoData };
          }
          return prev;
        });
        
        // Enhanced completion detection
        if (shouldStopPolling) {
          console.log('Stopping polling - completion detected');
          clearInterval(intervalId);
          pollingIntervalRef.current = null;
          setAnalysisInProgress(false);
          setProcessingVideoId(null);
          
          // If files exist but status is still 'processing', force update the status
          if (hasAnalysisFiles && videoData.processing_status === 'processing') {
            console.log('Analysis files found but status still processing - forcing completion');
            try {
              await axios.post(`${API_URL}/api/videos/${videoId}/force-complete`, {}, {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              });
            } catch (forceErr) {
              console.error('Error forcing completion:', forceErr);
            }
          }
          
          // Force a complete refresh of all videos
          try {
            const refreshResponse = await axios.get(`${API_URL}/api/videos`, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            
            // FIXED: Apply user filtering to refreshed videos
            const allVideos = refreshResponse.data.filter(v => v.processing_status !== 'deleted');
            const userVideos = filterVideosByCurrentUser(allVideos);
            setVideos(userVideos);
            
            // Update selected video if it's the one that just completed
            const completedVideo = userVideos.find(v => v.id === videoId);
            if (completedVideo && selectedVideo?.id === videoId) {
              setSelectedVideo(completedVideo);
            }
          } catch (refreshErr) {
            console.error('Error refreshing videos:', refreshErr);
          }

          // Show success/failure notification
          if (hasAnalysisFiles || videoData.processing_status === 'completed') {
            alert('Video analysis completed successfully!');
          } else if (videoData.processing_status === 'failed') {
            alert('Video analysis failed. Please try again.');
          }
        }
      } catch (err) {
        console.error('Error polling for status:', err);
        
        // If polling fails for too long, try completion check
        const currentTime = Date.now();
        const pollingDuration = currentTime - startTime;
        if (pollingDuration > maxPollingTime) {
          console.log('Polling failed and timeout reached, checking completion...');
          clearInterval(intervalId);
          pollingIntervalRef.current = null;
          await forceCompletionCheck(videoId);
        }
      }
    }, 5000); // Check every 5 seconds
    
    pollingIntervalRef.current = intervalId;
  }, [token, selectedVideo, user]);
  
  // FIXED: Fetch videos from server with proper user filtering
  const fetchVideos = useCallback(async () => {
    if (!token) {
      console.log('No token available for fetchVideos');
      return;
    }

    if (!user || !user.id) {
      console.log('No user context available for fetchVideos');
      setError('User authentication required');
      setLoading(false);
      return;
    }
    
    // Skip if we're already polling
    if (processingVideoId && pollingIntervalRef.current) {
      console.log('Skipping fetchVideos - already polling');
      return;
    }
    
    setLoading(true);

    const requestUrl = `${API_URL}/api/videos`;
    console.log('Making request to:', requestUrl);
    console.log('Current user:', user);
    console.log('With token:', token ? 'Present' : 'Missing');
  
    try {
      console.log('About to make axios request...');
      
      const response = await axios.get(requestUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        timeout: 15000, // 15 second timeout for cross-origin
        // Force fresh request, bypass cache
        params: {
          '_t': Date.now() // Cache buster
        }
      });

      console.log('Request completed successfully!');
      console.log('Videos API Response status:', response.status);
      console.log('Videos API Response data:', response.data);

      // CRITICAL: Check what we actually received
      if (response.data === null) {
        console.error('Response data is null');
        setError('Server returned null data');
        return;
      }
      
      if (response.data === undefined) {
        console.error('Response data is undefined');  
        setError('Server returned undefined data');
        return;
      }
      
      if (typeof response.data !== 'object') {
        console.error('Response data is not an object:', typeof response.data);
        setError('Server returned invalid data type');
        return;
      }
      
      // Check if response.data is an array before filtering
      if (!Array.isArray(response.data)) {
        console.error('ERROR: response.data is not an array:', response.data);
        console.error('Actual type:', typeof response.data);
        console.error('Constructor:', response.data?.constructor?.name);
        setError('Invalid response format from server - expected array');
        return;
      }
      
      // Filter out any videos with 'deleted' status
      const allActiveVideos = response.data.filter(v => v.processing_status !== 'deleted');
      console.log('All active videos from server:', allActiveVideos);
      
      // FIXED: Apply user filtering to ensure only current user's videos are shown
      const userVideos = filterVideosByCurrentUser(allActiveVideos);
      
      // Additional validation: Check for any videos that don't belong to current user
      const invalidVideos = allActiveVideos.filter(v => v.user_id !== user.id);
      if (invalidVideos.length > 0) {
        console.warn(`Found ${invalidVideos.length} videos that don't belong to current user:`, invalidVideos);
      }
      
      console.log(`Setting ${userVideos.length} videos for user ${user.id} (${user.role})`);
      setVideos(userVideos);
      
      // Check if any video is currently processing (only for current user)
      const processingVideo = userVideos.find(v => v.processing_status === 'processing');
      if (processingVideo && !processingVideoId && !pollingIntervalRef.current) {
        setProcessingVideoId(processingVideo.id);
        startStatusPolling(processingVideo.id);
      }
      
      // Update selected video if necessary
      if (selectedVideo) {
        const updatedVideo = userVideos.find(v => v.id === selectedVideo.id);
        if (updatedVideo && JSON.stringify(updatedVideo) !== JSON.stringify(selectedVideo)) {
          setSelectedVideo(updatedVideo);
        } else if (!updatedVideo) {
          // Selected video no longer belongs to user or was deleted
          console.log('Selected video no longer available for current user');
          setSelectedVideo(null);
        }
      }
      
      setError(null);
    } catch (err) {
      console.error('Request failed!');
      console.error('Error type:', err.constructor.name);
      console.error('Error code:', err.code);
      console.error('Detailed error in fetchVideos:', err);
      console.error('Error message:', err.message);
      console.error('Error response:', err.response);
      console.error('Error status:', err.response?.status);
      console.error('Error data:', err.response?.data);
      
      // Check if this is a CORS or network error
      if (!err.response) {
        setError('Network error: Unable to reach server. This might be a CORS issue.');
      } else if (err.response?.status === 401) {
        setError('Authentication failed. Please log in again.');
        // Could redirect to login here
      } else if (err.response?.status === 403) {
        setError('Access denied. You may not have permission to view these videos.');
      } else {
        setError(`Failed to load videos: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  }, [token, selectedVideo, processingVideoId, startStatusPolling, user]);

  // Initial load - FIXED: Added user dependency
  useEffect(() => {
    let isMounted = true;
    
    const loadInitialData = async () => {
      if (token && user && user.id && isMounted) {
        console.log(`Loading videos for user ${user.id} (${user.role})`);
        await fetchVideos();
      }
    };
    
    loadInitialData();
    
    return () => {
      isMounted = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [token, user, fetchVideos]);

  // to check for existing English audio version when a video is selected
  useEffect(() => {
    if (selectedVideo) {
      // ADDED: Verify selected video belongs to current user
      if (selectedVideo.user_id !== user?.id) {
        console.error(`Selected video ${selectedVideo.id} does not belong to current user ${user?.id}`);
        setSelectedVideo(null);
        return;
      }
      
      // Check if this video has an English audio version
      const checkEnglishVersion = async () => {
        try {
          const response = await axios.get(
            `${API_URL}/api/videos/${selectedVideo.id}/has-english-audio`,
            {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            }
          );
          
          setHasEnglishAudio(response.data.has_english_audio);
        } catch (err) {
          console.error('Error checking for English audio version:', err);
          setHasEnglishAudio(false);
        }
      };
      
      checkEnglishVersion();
    } else {
      setHasEnglishAudio(false);
    }
  }, [selectedVideo, token, user]);  
  
  const handleVideoSelect = async (videoId) => {
    const video = videos.find(v => v.id === videoId);
    if (video) {
      // ADDED: Additional verification that video belongs to current user
      if (video.user_id !== user?.id) {
        console.error(`Attempted to select video ${videoId} that doesn't belong to current user ${user?.id}`);
        alert('Error: This video does not belong to your account.');
        return;
      }
      setSelectedVideo(video);
    }
  };
  
  const handleDeleteVideo = async (videoId) => {
    // ADDED: Verify video belongs to current user before deletion
    const video = videos.find(v => v.id === videoId);
    if (!video || video.user_id !== user?.id) {
      console.error(`Attempted to delete video ${videoId} that doesn't belong to current user ${user?.id}`);
      alert('Error: This video does not belong to your account.');
      return;
    }
    
    if (!window.confirm('Are you sure you want to delete this video?')) {
      return;
    }
    
    try {
      setVideos(prevVideos => 
        prevVideos.map(v => 
          v.id === videoId ? { ...v, processing_status: 'deleting' } : v
        )
      );
      
      await axios.delete(`${API_URL}/api/videos/${videoId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      setVideos(prevVideos => prevVideos.filter(v => v.id !== videoId));
      
      if (selectedVideo && selectedVideo.id === videoId) {
        setSelectedVideo(null);
      }
      
      await fetchVideos();
      
    } catch (err) {
      console.error('Error deleting video:', err);
      alert('Failed to delete video. Please try again.');
      fetchVideos();
    }
  };
  
  const handleUploadComplete = () => {
    fetchVideos();
  };

  // getVideoUrl function to use streaming endpoints
  const getVideoUrl = (videoPath, videoId = null) => {
    if (!videoPath) return null;
    
    const normalizedPath = videoPath.replace(/\\/g, '/');
    
    // FIXED: Check for video files FIRST, regardless of URL type
    if (videoId && (normalizedPath.includes('.mp4') || normalizedPath.includes('.MP4'))) {
      return `${API_URL}/api/videos/${videoId}/stream-video?type=original&token=${encodeURIComponent(token)}`;
    }
    
    // For non-video files, if it's already a full URL, return as-is
    if (normalizedPath.startsWith('http://') || normalizedPath.startsWith('https://')) {
      return normalizedPath;
    }
    
    // For other static files, try the static endpoint
    return `${API_URL}/api/static/${normalizedPath}`;
  };

  const getStreamingUrl = (videoId, useEnglishAudio = false) => {
    const baseUrl = `${API_URL}/api/videos/${videoId}/stream-converted`;
    const params = new URLSearchParams();
    
    // Add token
    params.append('token', encodeURIComponent(token));
    
    // Add english_audio parameter if requested
    if (useEnglishAudio) {
      params.append('english_audio', 'true');
    }
    
    return `${baseUrl}?${params.toString()}`;
  };

  const goToAnalysis = (videoId) => {
    // ADDED: Verify video belongs to current user
    const video = videos.find(v => v.id === videoId);
    if (!video || video.user_id !== user?.id) {
      console.error(`Attempted to view analysis for video ${videoId} that doesn't belong to current user ${user?.id}`);
      alert('Error: This video does not belong to your account.');
      return;
    }
    navigate(`/analysis/${videoId}`);
  };

  const extractAnalysisData = async (videoId) => {
    // ADDED: Verify video belongs to current user
    const video = videos.find(v => v.id === videoId);
    if (!video || video.user_id !== user?.id) {
      console.error(`Attempted to extract data for video ${videoId} that doesn't belong to current user ${user?.id}`);
      alert('Error: This video does not belong to your account.');
      return;
    }
    
    setExtractingData(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/analysis-master/extract/${videoId}`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.status === 'success') {
        alert('Analysis data extracted successfully!');
      } else {
        alert('Failed to extract analysis data. Please try again.');
      }
    } catch (err) {
      console.error('Error extracting analysis data:', err);
      if (err.response && err.response.data && err.response.data.detail) {
        alert(`Error: ${err.response.data.detail}`);
      } else {
        alert('Error extracting analysis data. Please check the console.');
      }
    } finally {
      setExtractingData(false);
    }
  };

  const analyzeVideo = async (videoId) => {
    // ADDED: Verify video belongs to current user
    const video = videos.find(v => v.id === videoId);
    if (!video || video.user_id !== user?.id) {
      console.error(`Attempted to analyze video ${videoId} that doesn't belong to current user ${user?.id}`);
      alert('Error: This video does not belong to your account.');
      return;
    }
    
    if (analysisInProgress) {
      alert('Analysis is already in progress. Please wait.');
      return;
    }
    
    if (!window.confirm('Start video analysis? This may take a few minutes.')) {
      return;
    }
    
    try {
      setAnalysisInProgress(true);
      setProcessingVideoId(videoId);
      
      setVideos(prevVideos => 
        prevVideos.map(v => 
          v.id === videoId ? { ...v, processing_status: 'processing' } : v
        )
      );
      
      if (selectedVideo && selectedVideo.id === videoId) {
        setSelectedVideo(prev => ({ ...prev, processing_status: 'processing' }));
      }
      
      startStatusPolling(videoId);
      
      await axios.post(
        `${API_URL}/api/videos/${videoId}/analyze`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
    } catch (err) {
      console.error('Error starting video analysis:', err);
      
      if (!pollingIntervalRef.current) {
        startStatusPolling(videoId);
      }
      
      alert('There was an issue starting the analysis, but it may still be processing. Please wait for status updates.');
    }
  };

  const convertToEnglishAudio = async (videoId) => {
    // ADDED: Verify video belongs to current user and user is master
    const video = videos.find(v => v.id === videoId);
    if (!video || video.user_id !== user?.id) {
      console.error(`Attempted to convert audio for video ${videoId} that doesn't belong to current user ${user?.id}`);
      alert('Error: This video does not belong to your account.');
      return;
    }
    
    if (user?.role !== 'master') {
      alert('Only masters can convert audio to English.');
      return;
    }
    
    if (!window.confirm('Convert this video audio from Mandarin to English? This may take several minutes.')) {
      return;
    }
    
    setIsConverting(true);
    setConversionVideoId(videoId);
    
    try {
      // Start the conversion process
      const response = await axios.post(
        `${API_URL}/api/videos/${videoId}/convert-audio`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      // If response indicates conversion started, poll for status
      if (response.data.status === 'started') {
        // Poll for status updates
        const checkConversionStatus = async () => {
          try {
            const statusResponse = await axios.get(
              `${API_URL}/api/videos/${videoId}/conversion-status`,
              {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              }
            );
            
            // If conversion is complete, refresh video data
            if (statusResponse.data.status === 'completed') {
              await fetchVideos();
              setHasEnglishAudio(true);
              setIsConverting(false);
              setConversionVideoId(null);
              alert('Video audio successfully converted to English!');
            } 
            // If conversion failed
            else if (statusResponse.data.status === 'failed') {
              setIsConverting(false);
              setConversionVideoId(null);
              alert('Failed to convert video audio. Please try again.');
            }
            // Otherwise, continue polling
            else {
              setTimeout(checkConversionStatus, 5000); // Check every 5 seconds
            }
          } catch (err) {
            console.error('Error checking conversion status:', err);
            setIsConverting(false);
            setConversionVideoId(null);
            alert('Error checking conversion status. The process may still be running in the background.');
          }
        };
        
        // Start polling
        setTimeout(checkConversionStatus, 5000);
      } else {
        setIsConverting(false);
        setConversionVideoId(null);
        alert('Failed to start audio conversion. Please try again.');
      }
    } catch (err) {
      console.error('Error converting audio:', err);
      setIsConverting(false);
      setConversionVideoId(null);
      
      if (err.response && err.response.data && err.response.data.detail) {
        alert(`Error: ${err.response.data.detail}`);
      } else {
        alert('Error converting audio. Please try again.');
      }
    }
  };
    
  const resetProcessingStatus = async (videoId) => {
    // ADDED: Verify video belongs to current user
    const video = videos.find(v => v.id === videoId);
    if (!video || video.user_id !== user?.id) {
      console.error(`Attempted to reset status for video ${videoId} that doesn't belong to current user ${user?.id}`);
      alert('Error: This video does not belong to your account.');
      return;
    }
    
    if (!window.confirm('Reset processing status for this video? This will not stop any running processes but will reset the UI status.')) {
      return;
    }
    
    try {
      const response = await axios.post(
        `${API_URL}/api/videos/${videoId}/reset-status`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.data.status === 'uploaded') {
        // Update local state
        setAnalysisInProgress(false);
        setProcessingVideoId(null);
        
        // Update videos list
        setVideos(prevVideos => 
          prevVideos.map(v => 
            v.id === videoId ? { ...v, processing_status: 'uploaded' } : v
          )
        );
        
        // Update selected video if it's the one being reset
        if (selectedVideo && selectedVideo.id === videoId) {
          setSelectedVideo(prev => ({ ...prev, processing_status: 'uploaded' }));
        }
        
        alert('Processing status has been reset. You can now try analyzing again.');
      } else {
        alert(response.data.message);
      }
    } catch (err) {
      console.error('Error resetting processing status:', err);
      alert('Failed to reset processing status. Please try again.');
    }
  };

  // Debug function to help troubleshoot video paths
  const debugVideoPaths = async (videoId) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/videos/${videoId}/debug-paths`,
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

  // ADDED: Early return if no user context
  if (!user) {
    return (
      <div className="dashboard-container">
        <div className="loading-indicator">
          Loading user information...
        </div>
      </div>
    );
  }

  const handleTransferComplete = (data) => {
    console.log('Pi transfer completed:', data);
    setPiTransferComplete(true);
    
    // Refresh videos to show newly transferred videos
    fetchVideos();
    
    // Show success message briefly
    setTimeout(() => setPiTransferComplete(false), 3000);
  };

  // convert from 15 fps to 30 fps
  const convertForWeb = async (videoId, method = 'blend', targetFps = 30) => {
    // Safety checks
    if (!videoId || !selectedVideo) {
      alert('Please select a video first.');
      return;
    }

    const methods = {
      'duplicate': 'Frame Duplication (Fastest)',
      'blend': 'Frame Blending (Recommended)', 
      'mci': 'Motion Interpolation (Best Quality, Slowest)'
    };
    
    const methodName = methods[method] || methods['blend'];
    
    if (!window.confirm(`Convert video for web playback?\n\nMethod: ${methodName}\nFrame Rate: 15fps → ${targetFps}fps\n\nThis may take several minutes.`)) {
      return;
    }
    
    try {
      const response = await axios.post(
        `${API_URL}/api/videos/${videoId}/convert-for-web`,
        {}, 
        {
          headers: { 'Authorization': `Bearer ${token}` },
          params: {
            interpolation_method: method,
            target_fps: targetFps
          }
        }
      );
      
      alert(`Conversion started!\n${response.data.message}\n\nThe video will be optimized for web playback with ${targetFps}fps frame rate.`);
      
      // Start polling for completion
      startStatusPolling(videoId);
      
    } catch (err) {
      console.error('Conversion error:', err);
      alert(`Conversion failed: ${err.response?.data?.detail || err.message}`);
    }
  };


  const quickWebConvert = async (videoId) => {
    // Safety checks
    if (!videoId || !selectedVideo) {
      alert('Please select a video first.');
      return;
    }

    if (!window.confirm('Quick convert this Pi video for web playback?\n\n• 15fps → 30fps\n• Optimized for browsers\n• Frame blending for smooth playback\n\nThis may take 2-3 minutes.')) {
      return;
    }
    
    try {
      const response = await axios.post(`${API_URL}/api/videos/${videoId}/quick-web-convert`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      alert('Quick conversion started! Your Pi video will be optimized for web playback.');
      startStatusPolling(videoId);
      
    } catch (err) {
      console.error('Quick conversion error:', err);
      alert(`Quick conversion failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Add these buttons to video actions section:
  {selectedVideo.processing_status === 'uploaded' && (
    <div className="conversion-actions" style={{ marginTop: '15px' }}>
      <h4>Convert for Web Playback:</h4>
      
      <button 
        onClick={() => quickWebConvert(selectedVideo.id)}
        className="btn quick-convert-btn"
        style={{ backgroundColor: '#28a745', color: 'white', marginRight: '10px' }}
      >
        🚀 Quick Convert (15fps→30fps)
      </button>
      
      <div className="advanced-options" style={{ marginTop: '10px' }}>
        <h5>Advanced Options:</h5>
        <button 
          onClick={() => convertForWeb(selectedVideo.id, 'duplicate', 30)}
          className="btn"
          style={{ backgroundColor: '#17a2b8', color: 'white', marginRight: '5px', fontSize: '12px' }}
        >
          Fast (Duplicate)
        </button>
        
        <button 
          onClick={() => convertForWeb(selectedVideo.id, 'blend', 30)}
          className="btn"
          style={{ backgroundColor: '#007bff', color: 'white', marginRight: '5px', fontSize: '12px' }}
        >
          Balanced (Blend)
        </button>
        
        <button 
          onClick={() => convertForWeb(selectedVideo.id, 'mci', 30)}
          className="btn"
          style={{ backgroundColor: '#6f42c1', color: 'white', marginRight: '5px', fontSize: '12px' }}
        >
          Best Quality (MCI)
        </button>
      </div>
    </div>
  )}


  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>Welcome, {user?.name || 'User'}</h1>
        <h3>Role: {user?.role === 'master' ? 'Master' : 'Learner'} (ID: {user?.id})</h3>
      </div>
      
      <div className="content-container">
        <div className="main-content">
          <div className="section-header">
            <h2>Your Exercise Videos</h2>
            {analysisInProgress && (
              <div className="analysis-status-banner">
                <p>Analysis in progress... This may take several minutes. Please wait.</p>
              </div>
            )}
          </div>
          
          <div className="videos-grid-layout">
            {/* Left panel - Video list */}
            <div className="video-list-panel">
              {loading ? (
                <div className="loading-indicator">Loading videos...</div>
              ) : error ? (
                <div className="error-message">{error}</div>
              ) : videos.length === 0 ? (
                <div className="empty-state">
                  <p>No videos uploaded yet. Use the form below to upload your first video.</p>
                </div>
              ) : (
                <div className="video-cards">
                  {videos.map(video => (
                    <div 
                      key={video.id} 
                      className={`video-card ${selectedVideo && selectedVideo.id === video.id ? 'selected' : ''} ${video.processing_status === 'processing' ? 'processing-highlight' : ''}`}
                    >
                      <div className="video-card-content">
                        <h3 className="video-title">{video.title}</h3>
                        <div className="video-meta">
                          <span className="video-type">Type: {video.brocade_type} </span>
                          <span className={`video-status status-${video.processing_status}`}>
                            Status: {video.processing_status === 'processing' ? 'Processing...' : video.processing_status}
                          </span>
                          <span className="video-date"> Uploaded: {new Date(video.upload_timestamp).toLocaleString()}</span>
                          {/* ADDED: Debug info showing user_id for troubleshooting */}
                          {process.env.NODE_ENV === 'development' && (
                            <span className="video-debug">Owner: {video.user_id}</span>
                          )}
                        </div>
                      </div>
                      <div className="video-card-actions">
                        <button
                          className="btn preview-btn"
                          onClick={() => handleVideoSelect(video.id)}
                        >
                          Preview
                        </button>
                        <button 
                          className="btn delete-btn" 
                          onClick={() => handleDeleteVideo(video.id)}
                          disabled={video.processing_status === 'processing' || video.processing_status === 'deleting'}
                        >
                          {video.processing_status === 'deleting' ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Right panel - Video details and preview */}
            <div className="video-details-panel">
              {selectedVideo && selectedVideo.processing_status !== 'deleted' ? (
                <div className="video-details-content">
                  <div className="video-info-section">
                    <h2 className="section-header">{selectedVideo.title}</h2>
                    <div className="video-info-grid">
                      {selectedVideo.description && (
                        <div className="info-item">
                          <span className="info-label">Description: </span>
                          <span className="info-value">{selectedVideo.description}</span>
                        </div>
                      )}
                      <div className="info-item">
                        <span className="info-label">Brocade Type: </span>
                        <span className="info-value">{selectedVideo.brocade_type}</span>
                      </div>
                      <div className="info-item">
                        <span className="info-label">Status:</span>
                        <span className={`info-value status-badge status-${selectedVideo.processing_status}`}>
                          {selectedVideo.processing_status === 'processing' ? 'Processing...' : selectedVideo.processing_status}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* FIXED: Processing section with null checks */}
                  {selectedVideo.processing_status === 'processing' ? (
                    <div className="processing-message">
                      <h3>Video Processing</h3>
                      <p>Your video "{selectedVideo.title}" is currently being processed.</p>
                      <p>This may take several minutes. The page will update automatically when complete.</p>
                      <div className="loading-spinner"></div>
                      
                      <div className="processing-controls" style={{ marginTop: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <button 
                          className="btn refresh-btn"
                          onClick={async () => {
                            console.log('Manual refresh triggered');
                            if (pollingIntervalRef.current) {
                              clearInterval(pollingIntervalRef.current);
                              pollingIntervalRef.current = null;
                            }
                            setAnalysisInProgress(false);
                            setProcessingVideoId(null);
                            await fetchVideos();
                            alert('Status refreshed! Check your video status.');
                          }}
                          style={{ 
                            backgroundColor: '#007bff',
                            color: 'white',
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          🔄 Refresh Status
                        </button>
                        
                        <button 
                          className="btn force-check-btn"
                          onClick={() => forceCompletionCheck(selectedVideo.id)}
                          style={{
                            backgroundColor: '#28a745',
                            color: 'white',
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          ✅ Check if Complete
                        </button>
                        
                        <button 
                          className="btn cancel-processing-btn"
                          onClick={() => resetProcessingStatus(selectedVideo.id)}
                          style={{
                            backgroundColor: '#dc3545',
                            color: 'white',
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          🔄 Reset Status
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Video Preview Section - FIXED with null checks */
                    <div className="video-preview-section">
                      <h3 className="section-title">Video Preview</h3>
                      
                      {selectedVideo.analyzed_video_path && selectedVideo.processing_status === 'completed' ? (
                        <div className="video-players-container">
                          {/* Original Video */}
                          <div className="video-player-container">
                            <h4>Original Video</h4>
                            <div className="video-player-wrapper">
                              <video 
                                controls 
                                className="video-player"
                                key={`original-${selectedVideo.id}`}
                                src={getVideoUrl(selectedVideo.video_path, selectedVideo.id)}
                              >
                                Your browser does not support the video tag.
                              </video>
                            </div>
                          </div>
                          
                          {/* English Version Video - only show if it exists */}
                          {hasEnglishAudio && (
                            <div className="video-player-container">
                              <h4>English Version Video</h4>
                              <div className="video-player-wrapper">
                                <video 
                                  controls 
                                  className="video-player"
                                  key={`english-${selectedVideo.id}`}
                                  src={`${API_URL}/api/videos/${selectedVideo.id}/stream-video?type=english&token=${encodeURIComponent(token)}`}
                                >
                                  Your browser does not support the video tag.
                                </video>
                              </div>
                            </div>
                          )}

                          {/* Analyzed Video */}
                          <div className="video-player-container">
                            <h4>Analysis Video</h4>
                            <div className="video-player-wrapper">
                              <video 
                                controls 
                                className="video-player"
                                key={`analyzed-${selectedVideo.id}`}
                                src={`${API_URL}/api/videos/${selectedVideo.id}/stream-video?type=analyzed&token=${encodeURIComponent(token)}`}
                              >
                                Your browser does not support the video tag.
                              </video>
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* Just show the original video */
                        <div className="video-player-wrapper">
                          <video 
                            controls 
                            className="video-player"
                            key={`single-${selectedVideo.id}`}
                            src={getVideoUrl(selectedVideo.video_path, selectedVideo.id)}
                          >
                            Your browser does not support the video tag.
                          </video>
                          
                          {/* Show conversion in progress indicator */}
                          {isConverting && conversionVideoId === selectedVideo.id && (
                            <div className="conversion-status">
                              <div className="conversion-spinner"></div>
                              <p>Converting to English audio... This may take several minutes.</p>
                            </div>
                          )}

                          {/* Show English version available controls only for masters with completed videos */}
                          {user?.role === 'master' && selectedVideo.processing_status === 'completed' && hasEnglishAudio && (
                            <div className="english-version-available">
                              <p>English audio version available ✓</p>
                              <button 
                                className="btn english-play-btn"
                                onClick={() => {
                                  // Update video source to use English audio
                                  const videoElement = document.querySelector(`video[key="single-${selectedVideo.id}"]`);
                                  if (videoElement) {
                                    videoElement.src = `${API_URL}/api/videos/${selectedVideo.id}/stream-video?type=english&token=${encodeURIComponent(token)}`;
                                    videoElement.load();
                                    videoElement.play();
                                  }
                                }}
                              >
                                Play English Version
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* FIXED: Video action buttons with null checks */}
                      {selectedVideo.processing_status === 'uploaded' && (
                        <div className="video-actions-container">
                          {user?.role === 'master' && (
                            <p className="action-options-text">Choose an action for your video:</p>
                          )}
                          
                          <div className="video-actions-buttons">
                            {/* Show Convert button right after Analyze button for masters */}
                            {user?.role === 'master' && (
                              <button 
                                className="btn english-audio-btn"
                                onClick={() => convertToEnglishAudio(selectedVideo.id)}
                                disabled={isConverting}
                              >
                                {isConverting ? 'Converting...' : 'Convert to English Audio'}
                              </button>
                            )}

                            <button 
                              className="btn analysis-btn"
                              onClick={() => analyzeVideo(selectedVideo.id)}
                              disabled={analysisInProgress}
                            >
                              {analysisInProgress ? 'Processing...' : 'Analyze Video'}
                            </button>
                          </div>

                          {/* FIXED: Web conversion section with proper null checks */}
                          <div className="conversion-actions" style={{ marginTop: '15px' }}>
                            <h4>Convert for Web Playback:</h4>
                            
                            <button 
                              onClick={() => quickWebConvert(selectedVideo.id)}
                              className="btn quick-convert-btn"
                              style={{ backgroundColor: '#28a745', color: 'white', marginRight: '10px' }}
                            >
                              🚀 Quick Convert (15fps→30fps)
                            </button>
                            
                            <div className="advanced-options" style={{ marginTop: '10px' }}>
                              <h5>Advanced Options:</h5>
                              <button 
                                onClick={() => convertForWeb(selectedVideo.id, 'duplicate', 30)}
                                className="btn"
                                style={{ backgroundColor: '#17a2b8', color: 'white', marginRight: '5px', fontSize: '12px' }}
                              >
                                Fast (Duplicate)
                              </button>
                              
                              <button 
                                onClick={() => convertForWeb(selectedVideo.id, 'blend', 30)}
                                className="btn"
                                style={{ backgroundColor: '#007bff', color: 'white', marginRight: '5px', fontSize: '12px' }}
                              >
                                Balanced (Blend)
                              </button>
                              
                              <button 
                                onClick={() => convertForWeb(selectedVideo.id, 'mci', 30)}
                                className="btn"
                                style={{ backgroundColor: '#6f42c1', color: 'white', marginRight: '5px', fontSize: '12px' }}
                              >
                                Best Quality (MCI)
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* FIXED: Analysis Actions with null checks */}
                  <div className="video-actions-section">
                    {selectedVideo.processing_status === 'processing' ? (
                      <button className="btn processing-btn" disabled>
                        <span className="processing-spinner"></span>
                        Processing... Please wait
                      </button>
                    ) : selectedVideo.processing_status === 'completed' ? (
                      <>
                        <button 
                          className="btn view-results-btn"
                          onClick={() => goToAnalysis(selectedVideo.id)}
                        >
                          View Full Analysis Results
                        </button>
                        <button 
                          className="btn extract-btn"
                          onClick={() => extractAnalysisData(selectedVideo.id)}
                          disabled={extractingData}
                        >
                          {extractingData ? 'Extracting...' : 'Extract Analysis Data'}
                        </button>
                        {/* Only show Compare with Master button for learners */}
                        {user?.role === 'learner' && (
                          <button 
                            className="btn btn-primary"
                            onClick={() => navigate('/comparison-selection')}
                          >
                            Compare with Master
                          </button>
                        )}
                      </>
                    ) : selectedVideo.processing_status === 'failed' ? (
                      <>
                        <div className="error-message">Analysis failed. Please try again.</div>
                        <button 
                          className="btn analysis-btn"
                          onClick={() => analyzeVideo(selectedVideo.id)}
                          disabled={analysisInProgress}
                        >
                          Retry Analysis
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              ) : (
                <div className="select-prompt">
                  <p>Select a video to view details and preview</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Manual upload and Pi video transfer section */}
        <div className="upload-sections-container">
          {/* Success Banner - spans both columns */}
          {piTransferComplete && (
            <div className="transfer-success-banner-full">
              ✅ Pi videos transferred successfully! Check your video list above.
            </div>
          )}
          
          <div className="upload-columns">
            {/* Left Column - Manual Upload */}
            <div className="upload-column manual-upload-column">
              <div className="column-header">
                <h3>📤 Manual Upload</h3>
                <p>Upload videos directly from your device</p>
              </div>
              <div className="upload-section">
                <VideoUpload onUploadComplete={handleUploadComplete} />
              </div>
            </div>
            
            {/* Right Column - Pi Transfer */}
            <div className="upload-column pi-transfer-column">
              <div className="column-header">
                <h3>🤖 Pi Transfer</h3>
                <p>Transfer recorded videos from your Pi device</p>
              </div>
              <div className="pi-transfer-section">
                <PiVideoTransfer onTransferComplete={handleTransferComplete} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoManagement;
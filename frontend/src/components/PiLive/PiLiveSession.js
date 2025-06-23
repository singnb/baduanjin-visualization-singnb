// src/components/PiLive/PiLiveSession.js
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import PiStatusPanel from './PiStatusPanel';
import PiVideoStream from './PiVideoStream';
import PiControls from './PiControls';
import PiPoseData from './PiPoseData';
import './PiLive.css';

const PI_URL = 'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net';

const PiLiveSession = ({ onSessionComplete }) => {
  const [piStatus, setPiStatus] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [poseData, setPoseData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { token, user } = useAuth();

  // Check Pi connection status
  const checkPiStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Single call with authentication - no need for two calls
      const response = await axios.get(`${PI_URL}/api/pi-live/status`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        timeout: 15000  // Increased timeout for network issues
      });
      
      setPiStatus(response.data);
      setIsConnected(response.data.pi_connected);
      
    } catch (err) {
      console.error('Error checking Pi status:', err);
      setError('Failed to connect to Pi. Please check if the Pi is running.');
      setPiStatus({ pi_connected: false, error: err.message });
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Start a live session
  const startLiveSession = useCallback(async (sessionName = 'Live Practice Session') => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.post(
        `${PI_URL}/api/pi-live/start-session`,
        {
          session_name: sessionName
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        }
      );
      
      if (response.data.success) {
        setActiveSession({
          ...response.data,
          session_name: sessionName,
          start_time: new Date().toISOString()
        });
        
        // Start polling for pose data
        startPoseDataPolling();
        
        console.log('Live session started successfully:', response.data);
      } else {
        throw new Error(response.data.message || 'Failed to start session');
      }
      
    } catch (err) {
      console.error('Error starting live session:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to start live session');
      
      // Show user-friendly error message
      if (err.response?.status === 503) {
        setError('Pi camera is not available. Please check the Pi connection.');
      } else if (err.response?.status === 401) {
        setError('Authentication failed. Please try logging in again.');
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Stop the active live session
  const stopLiveSession = useCallback(async () => {
    if (!activeSession) return;
    
    try {
      setLoading(true);
      
      const response = await axios.post(
        `${PI_URL}/api/pi-live/stop-session/${activeSession.session_id}`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          timeout: 10000
        }
      );
      
      console.log('Session stopped:', response.data);
      
      // Clear session data
      setActiveSession(null);
      setPoseData(null);
      
      // Stop pose data polling
      stopPoseDataPolling();
      
      // Call completion callback if provided
      if (onSessionComplete) {
        onSessionComplete(response.data);
      }
      
    } catch (err) {
      console.error('Error stopping live session:', err);
      setError('Failed to stop session properly, but local session has been cleared.');
      
      // Clear local session even if API call failed
      setActiveSession(null);
      setPoseData(null);
      stopPoseDataPolling();
    } finally {
      setLoading(false);
    }
  }, [activeSession, token, onSessionComplete]);

  // Pose data polling
  const [posePollingInterval, setPosePollingInterval] = useState(null);
  
  const startPoseDataPolling = useCallback(() => {
    const intervalId = setInterval(async () => {
      try {
        const response = await axios.get(`${PI_URL}/api/pi-live/current-pose`, {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          timeout: 3000
        });
        
        if (response.data.success && response.data.pose_data) {
          setPoseData({
            pose_data: response.data.pose_data,
            stats: {
              current_fps: 15, // Placeholder - could be from Pi
              total_frames: 0,  // Placeholder
              persons_detected: response.data.pose_data.length
            },
            timestamp: response.data.timestamp
          });
        }
      } catch (err) {
        // Don't log every polling error to avoid spam
        if (err.response?.status !== 401) {
          console.warn('Pose data polling error:', err.message);
        }
      }
    }, 1000); // Poll every second
    
    setPosePollingInterval(intervalId);
  }, [token]);
  
  const stopPoseDataPolling = useCallback(() => {
    if (posePollingInterval) {
      clearInterval(posePollingInterval);
      setPosePollingInterval(null);
    }
  }, [posePollingInterval]);

  // Check Pi status on component mount
  useEffect(() => {
    checkPiStatus();
  }, [checkPiStatus]);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      stopPoseDataPolling();
    };
  }, [stopPoseDataPolling]);

  return (
    <div className="pi-live-container">
      <div className="pi-live-header">
        <h2>🥋 Real-time Baduanjin Analysis</h2>
        <PiStatusPanel 
          status={piStatus}
          isConnected={isConnected}
          loading={loading}
          onRefresh={checkPiStatus}
        />
      </div>
      
      {error && (
        <div className="error-banner">
          <p>⚠️ {error}</p>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}
      
      <div className="pi-live-content">
        <div className="pi-stream-section">
          <PiVideoStream 
            activeSession={activeSession}
            poseData={poseData}
            isConnected={isConnected}
          />
        </div>
        
        <div className="pi-controls-section">
          <PiControls
            piStatus={piStatus}
            activeSession={activeSession}
            loading={loading}
            onStartSession={startLiveSession}
            onStopSession={stopLiveSession}
            user={user}
          />
          
          <PiPoseData 
            poseData={poseData}
            activeSession={activeSession}
          />
        </div>
      </div>
      
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Processing...</p>
        </div>
      )}
    </div>
  );
};

export default PiLiveSession;
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
  // Pi Connection State
  const [piStatus, setPiStatus] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // Session State
  const [activeSession, setActiveSession] = useState(null);
  const [sessionStartTime, setSessionStartTime] = useState(null);
  
  // Recording State (separate from session)
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStartTime, setRecordingStartTime] = useState(null);
  const [availableRecordings, setAvailableRecordings] = useState([]);
  
  // Real-time Data
  const [poseData, setPoseData] = useState(null);
  
  // UI State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { token, user } = useAuth();

  // Polling intervals
  const [posePollingInterval, setPosePollingInterval] = useState(null);
  const [statusPollingInterval, setStatusPollingInterval] = useState(null);

  // === PI CONNECTION MANAGEMENT ===
  const checkPiStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`${PI_URL}/api/pi-live/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: 15000
      });
      
      setPiStatus(response.data);
      setIsConnected(response.data.pi_connected);
      
      // Update recording status from Pi
      if (response.data.is_recording !== undefined) {
        setIsRecording(response.data.is_recording);
      }
      
    } catch (err) {
      console.error('Error checking Pi status:', err);
      setError('Failed to connect to Pi. Please check if the Pi is running.');
      setPiStatus({ pi_connected: false, error: err.message });
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // === SESSION MANAGEMENT ===
  const startLiveSession = useCallback(async (sessionName = 'Live Practice Session') => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🚀 Starting live session:', sessionName);
      
      const response = await axios.post(
        `${PI_URL}/api/pi-live/start-session`,
        { session_name: sessionName },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        }
      );
      
      if (response.data.success) {
        const newSession = {
          ...response.data,
          session_name: sessionName,
          start_time: new Date().toISOString()
        };
        
        setActiveSession(newSession);
        setSessionStartTime(new Date());
        
        // Start polling for pose data and status
        startPoseDataPolling();
        startStatusPolling();
        
        console.log('✅ Live session started successfully:', newSession);
        
        // Clear any previous recordings list
        setAvailableRecordings([]);
        
      } else {
        throw new Error(response.data.message || 'Failed to start session');
      }
      
    } catch (err) {
      console.error('❌ Error starting live session:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to start live session';
      setError(errorMessage);
      
      // Provide specific error guidance
      if (err.response?.status === 503) {
        setError('Pi camera is not available. Please check the Pi connection.');
      } else if (err.response?.status === 401) {
        setError('Authentication failed. Please try logging in again.');
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  const stopLiveSession = useCallback(async () => {
    if (!activeSession) return null;
    
    try {
      setLoading(true);
      console.log('⏹️ Stopping live session:', activeSession.session_id);
      
      // If recording is active, stop it first
      if (isRecording) {
        console.log('⏹️ Stopping recording before session ends...');
        await stopRecording();
        
        // Wait for recording to be processed
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Refresh recordings list
        await fetchAvailableRecordings();
      }
      
      const response = await axios.post(
        `${PI_URL}/api/pi-live/stop-session/${activeSession.session_id}`,
        {},
        {
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: 10000
        }
      );
      
      console.log('✅ Session stopped:', response.data);
      
      // Stop polling
      stopPoseDataPolling();
      stopStatusPolling();
      
      // Calculate session duration
      const sessionDuration = sessionStartTime 
        ? Math.round((new Date() - sessionStartTime) / 1000) 
        : 0;
      
      // Return session data for save dialog
      const sessionData = {
        ...activeSession,
        end_time: new Date().toISOString(),
        duration_seconds: sessionDuration,
        recordings: availableRecordings
      };
      
      // Don't clear session data yet - let the save dialog handle it
      return sessionData;
      
    } catch (err) {
      console.error('❌ Error stopping live session:', err);
      setError('Failed to stop session properly, but local session has been cleared.');
      
      // Force cleanup even if API call failed
      cleanupSession();
      throw err;
    } finally {
      setLoading(false);
    }
  }, [activeSession, token, isRecording, sessionStartTime, availableRecordings]);

  const cleanupSession = useCallback(() => {
    console.log('🧹 Cleaning up session...');
    
    // Clear session data
    setActiveSession(null);
    setSessionStartTime(null);
    setPoseData(null);
    setIsRecording(false);
    setRecordingStartTime(null);
    setAvailableRecordings([]);
    
    // Stop all polling
    stopPoseDataPolling();
    stopStatusPolling();
  }, []);

  // === RECORDING MANAGEMENT ===
  const startRecording = useCallback(async () => {
    if (!activeSession) {
      setError('No active session. Please start a session first.');
      return false;
    }
    
    try {
      console.log('🔴 Starting recording for session:', activeSession.session_id);
      
      const response = await axios.post(
        `${PI_URL}/api/pi-live/recording/start/${activeSession.session_id}`,
        {},
        {
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: 10000
        }
      );
      
      if (response.data.success) {
        setIsRecording(true);
        setRecordingStartTime(new Date());
        console.log('✅ Recording started:', response.data.message);
        return true;
      } else {
        setError(response.data.message || 'Failed to start recording');
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      setError('Failed to start recording: ' + (error.response?.data?.detail || error.message));
      return false;
    }
  }, [activeSession, token]);

  const stopRecording = useCallback(async () => {
    if (!activeSession) return false;
    
    try {
      console.log('⏹️ Stopping recording for session:', activeSession.session_id);
      
      const response = await axios.post(
        `${PI_URL}/api/pi-live/recording/stop/${activeSession.session_id}`,
        {},
        {
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: 15000
        }
      );
      
      if (response.data.success) {
        setIsRecording(false);
        setRecordingStartTime(null);
        
        console.log('✅ Recording stopped:', response.data.recording_info);
        
        // Refresh recordings list
        await fetchAvailableRecordings();
        
        return response.data.recording_info;
      } else {
        setError(response.data.message || 'Failed to stop recording');
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to stop recording:', error);
      setError('Failed to stop recording: ' + (error.response?.data?.detail || error.message));
      return false;
    }
  }, [activeSession, token]);

  const fetchAvailableRecordings = useCallback(async () => {
    try {
      const response = await axios.get(`${PI_URL}/api/pi-live/recordings`, {
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: 10000
      });
      
      if (response.data.success) {
        const recordings = response.data.recordings || [];
        setAvailableRecordings(recordings);
        console.log('📹 Available recordings updated:', recordings.length);
        return recordings;
      }
    } catch (error) {
      console.warn('⚠️ Failed to fetch recordings:', error);
      return [];
    }
  }, [token]);

  // === DATA POLLING ===
  const startPoseDataPolling = useCallback(() => {
    if (posePollingInterval) return; // Already polling
    
    console.log('📊 Starting pose data polling...');
    const intervalId = setInterval(async () => {
      try {
        const response = await axios.get(`${PI_URL}/api/pi-live/current-pose`, {
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: 3000
        });
        
        if (response.data.success && response.data.pose_data) {
          setPoseData({
            pose_data: response.data.pose_data,
            stats: {
              current_fps: 15,
              total_frames: 0,
              persons_detected: response.data.pose_data.length
            },
            timestamp: response.data.timestamp
          });
        }
      } catch (err) {
        // Only log significant errors, not every polling failure
        if (err.response?.status !== 401) {
          console.warn('⚠️ Pose data polling error:', err.message);
        }
      }
    }, 1000);
    
    setPosePollingInterval(intervalId);
  }, [token, posePollingInterval]);

  const stopPoseDataPolling = useCallback(() => {
    if (posePollingInterval) {
      console.log('📊 Stopping pose data polling...');
      clearInterval(posePollingInterval);
      setPosePollingInterval(null);
    }
  }, [posePollingInterval]);

  const startStatusPolling = useCallback(() => {
    if (statusPollingInterval) return; // Already polling
    
    console.log('🔄 Starting status polling...');
    const intervalId = setInterval(async () => {
      try {
        const response = await axios.get(`${PI_URL}/api/pi-live/status`, {
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: 5000
        });
        
        // Update recording status
        if (response.data.is_recording !== undefined) {
          setIsRecording(response.data.is_recording);
        }
        
        // Update connection status
        setIsConnected(response.data.pi_connected);
        
      } catch (error) {
        console.warn('⚠️ Status polling error:', error.message);
      }
    }, 3000);
    
    setStatusPollingInterval(intervalId);
  }, [token, statusPollingInterval]);

  const stopStatusPolling = useCallback(() => {
    if (statusPollingInterval) {
      console.log('🔄 Stopping status polling...');
      clearInterval(statusPollingInterval);
      setStatusPollingInterval(null);
    }
  }, [statusPollingInterval]);

  // === COMPONENT LIFECYCLE ===
  useEffect(() => {
    checkPiStatus();
  }, [checkPiStatus]);

  useEffect(() => {
    return () => {
      stopPoseDataPolling();
      stopStatusPolling();
    };
  }, [stopPoseDataPolling, stopStatusPolling]);

  // === SESSION COMPLETION HANDLER ===
  const handleSessionComplete = useCallback((result) => {
    console.log('✅ Session completed:', result);
    
    // Cleanup local state
    cleanupSession();
    
    // Notify parent component
    if (onSessionComplete) {
      onSessionComplete(result);
    }
  }, [cleanupSession, onSessionComplete]);

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
            token={token} 
          />
        </div>
        
        <div className="pi-controls-section">
          <PiControls
            // Pi Status
            piStatus={piStatus}
            isConnected={isConnected}
            
            // Session State
            activeSession={activeSession}
            sessionStartTime={sessionStartTime}
            
            // Recording State  
            isRecording={isRecording}
            recordingStartTime={recordingStartTime}
            availableRecordings={availableRecordings}
            
            // Actions
            onStartSession={startLiveSession}
            onStopSession={stopLiveSession}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            onFetchRecordings={fetchAvailableRecordings}
            onSessionComplete={handleSessionComplete}
            
            // UI State
            loading={loading}
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
// src/components/PiLive/PiLiveSession.js
// CLEANED VERSION - Consolidated state management and polling

import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import { PI_CONFIG, getPiUrl, isDirectPiAvailable } from '../../config/piConfig';
import PiStatusPanel from './PiStatusPanel';
import PiVideoStream from './PiVideoStream';
import PiControls from './PiControls';
import PiPoseData from './PiPoseData';
import './PiLive.css';

const PiLiveSession = ({ onSessionComplete }) => {
  // === CONSOLIDATED STATE MANAGEMENT ===
  const [piState, setPiState] = useState({
    // Connection status
    isConnected: false,
    connectionError: null,
    loading: false,
    
    // Pi status data
    status: null,
    
    // Session data (auto-managed, hidden from user)
    activeSession: null,
    sessionStartTime: null,
    
    // Recording data (main user interface)
    isRecording: false,
    recordingStartTime: null,
    availableRecordings: [],
    
    // Real-time data
    poseData: null,
    currentFrame: null,
    streamStats: { fps: 0, persons: 0, latency: 0 }
  });

  const { token, user } = useAuth();
  const pollingIntervalRef = useRef(null);
  
  // === UNIFIED POLLING SYSTEM ===
  const unifiedPolling = useCallback(async () => {
    if (!piState.activeSession) return;
    
    try {
      // Single API call to get all Pi data
      const statusResponse = await axios.get(`${getPiUrl('api')}/api/pi-live/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: PI_CONFIG.TIMEOUTS.STATUS_CHECK
      });
      
      const statusData = statusResponse.data;
      
      // Get pose data if session is active
      let poseResponse = null;
      if (statusData.is_running) {
        try {
          poseResponse = await axios.get(`${getPiUrl('api')}/api/pi-live/current-pose`, {
            headers: { 'Authorization': `Bearer ${token}` },
            timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
          });
        } catch (poseError) {
          console.warn('⚠️ Pose data fetch failed:', poseError.message);
        }
      }
      
      // Update consolidated state
      setPiState(prev => ({
        ...prev,
        isConnected: statusData.pi_connected || false,
        status: statusData,
        isRecording: statusData.is_recording || false,
        poseData: poseResponse?.data?.success ? {
          pose_data: poseResponse.data.pose_data || [],
          stats: {
            current_fps: statusData.current_fps || 0,
            persons_detected: poseResponse.data.pose_data?.length || 0,
            total_frames: 0
          },
          timestamp: poseResponse.data.timestamp
        } : null,
        connectionError: null,
        loading: false
      }));
      
    } catch (error) {
      console.error('❌ Unified polling error:', error);
      setPiState(prev => ({
        ...prev,
        isConnected: false,
        connectionError: error.response?.data?.detail || error.message || 'Pi connection failed',
        loading: false
      }));
    }
  }, [token]); // Removed piState.activeSession dependency to break circular reference

  // === PI STATUS CHECK ===
  const checkPiStatus = useCallback(async () => {
    setPiState(prev => ({ ...prev, loading: true, connectionError: null }));
    
    try {
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: PI_CONFIG.TIMEOUTS.STATUS_CHECK
      });
      
      setPiState(prev => ({
        ...prev,
        isConnected: response.data.pi_connected || false,
        status: response.data,
        isRecording: response.data.is_recording || false,
        loading: false,
        connectionError: null
      }));
      
    } catch (error) {
      console.error('❌ Pi status check failed:', error);
      setPiState(prev => ({
        ...prev,
        isConnected: false,
        status: { pi_connected: false, error: error.message },
        loading: false,
        connectionError: 'Failed to connect to Pi service'
      }));
    }
  }, [token, startUnifiedPolling]);

  // === EXISTING SESSION MANAGEMENT (KEPT FOR INTERNAL USE) ===
  const startLiveSession = useCallback(async (sessionName = 'Live Practice Session') => {
    try {
      console.log('🚀 Starting live session:', sessionName);
      
      const response = await axios.post(
        `${getPiUrl('api')}/api/pi-live/start-session`,
        { session_name: sessionName },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
        }
      );
      
      if (response.data.success) {
        const newSession = {
          ...response.data,
          session_name: sessionName,
          start_time: new Date().toISOString()
        };
        
        setPiState(prev => ({
          ...prev,
          activeSession: newSession,
          sessionStartTime: new Date(),
          loading: false,
          availableRecordings: []
        }));
        
        // Start unified polling
        startUnifiedPolling();
        
        console.log('✅ Live session started successfully:', newSession);
        return newSession;
      } else {
        throw new Error(response.data.message || 'Failed to start session');
      }
      
    } catch (error) {
      console.error('❌ Error starting live session:', error);
      setPiState(prev => ({
        ...prev,
        loading: false,
        connectionError: error.response?.data?.detail || error.message || 'Failed to start live session'
      }));
      throw error;
    }
  }, [token]);

  const stopLiveSession = useCallback(async () => {
    if (!piState.activeSession) return null;
    
    try {
      console.log('⏹️ Stopping live session:', piState.activeSession.session_id);
      
      const response = await axios.post(
        `${getPiUrl('api')}/api/pi-live/stop-session/${piState.activeSession.session_id}`,
        {},
        { 
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
        }
      );
      
      console.log('✅ Session stopped:', response.data);
      
      // Stop polling
      stopUnifiedPolling();
      
      // Calculate session duration
      const sessionDuration = piState.sessionStartTime 
        ? Math.round((new Date() - piState.sessionStartTime) / 1000) 
        : 0;
      
      const sessionData = {
        ...piState.activeSession,
        end_time: new Date().toISOString(),
        duration_seconds: sessionDuration,
        recordings: piState.availableRecordings
      };
      
      return sessionData;
      
    } catch (error) {
      console.error('❌ Error stopping live session:', error);
      cleanupSession();
      throw error;
    }
  }, [piState.activeSession, piState.sessionStartTime, piState.availableRecordings, token, stopUnifiedPolling, cleanupSession]);

  const startRecording = useCallback(async () => {
    if (!piState.activeSession) {
      setPiState(prev => ({ ...prev, connectionError: 'No active session. Please start a session first.' }));
      return false;
    }
    
    try {
      console.log('🔴 Starting recording for session:', piState.activeSession.session_id);
      
      const response = await axios.post(
        `${getPiUrl('api')}/api/pi-live/recording/start/${piState.activeSession.session_id}`,
        {},
        { 
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
        }
      );
      
      if (response.data.success) {
        setPiState(prev => ({
          ...prev,
          isRecording: true,
          recordingStartTime: new Date()
        }));
        console.log('✅ Recording started:', response.data.message);
        return true;
      } else {
        setPiState(prev => ({ ...prev, connectionError: response.data.message || 'Failed to start recording' }));
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      setPiState(prev => ({ ...prev, connectionError: 'Failed to start recording: ' + error.message }));
      return false;
    }
  }, [piState.activeSession, token, fetchAvailableRecordings]);

  const stopRecording = useCallback(async () => {
    if (!piState.activeSession) return false;
    
    try {
      console.log('⏹️ Stopping recording for session:', piState.activeSession.session_id);
      
      const response = await axios.post(
        `${getPiUrl('api')}/api/pi-live/recording/stop/${piState.activeSession.session_id}`,
        {},
        { 
          headers: { 'Authorization': `Bearer ${token}` },
          timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
        }
      );
      
      if (response.data.success) {
        setPiState(prev => ({
          ...prev,
          isRecording: false,
          recordingStartTime: null
        }));
        
        console.log('✅ Recording stopped:', response.data.recording_info);
        await fetchAvailableRecordings();
        return response.data.recording_info;
      } else {
        setPiState(prev => ({ ...prev, connectionError: response.data.message || 'Failed to stop recording' }));
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to stop recording:', error);
      setPiState(prev => ({ ...prev, connectionError: 'Failed to stop recording: ' + error.message }));
      return false;
    }
  }, [piState.activeSession, token]);

  // === POLLING MANAGEMENT (DEFINED EARLY) ===
  const startUnifiedPolling = useCallback(() => {
    if (pollingIntervalRef.current) return;
    
    console.log('🔄 Starting unified polling...');
    const intervalId = setInterval(unifiedPolling, PI_CONFIG.POLLING.UNIFIED_INTERVAL);
    pollingIntervalRef.current = intervalId;
  }, [unifiedPolling]);

  const stopUnifiedPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      console.log('🔄 Stopping unified polling...');
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // === RECORDING MANAGEMENT ===
  const fetchAvailableRecordings = useCallback(async () => {
    try {
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/recordings`, {
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
      });
      
      if (response.data.success) {
        const recordings = response.data.recordings || [];
        setPiState(prev => ({ ...prev, availableRecordings: recordings }));
        console.log('📹 Available recordings updated:', recordings.length);
        return recordings;
      }
    } catch (error) {
      console.warn('⚠️ Failed to fetch recordings:', error);
      return [];
    }
  }, [token]);

  const cleanupSession = useCallback(() => {
    console.log('🧹 Cleaning up session...');
    stopUnifiedPolling();
    
    setPiState(prev => ({
      ...prev,
      activeSession: null,
      sessionStartTime: null,
      poseData: null,
      isRecording: false,
      recordingStartTime: null,
      availableRecordings: [],
      currentFrame: null
    }));
  }, [stopUnifiedPolling]);

  // === NEW SIMPLIFIED FUNCTIONS ===
  const startRecordingSession = useCallback(async (sessionName, selectedExercise = null) => {
    setPiState(prev => ({ ...prev, loading: true, connectionError: null }));
    
    try {
      // Step 1: Check Pi connection
      const piStatus = await checkPiStatus();
      if (!piState.isConnected) {
        throw new Error('Pi not connected. Please check the connection.');
      }
      
      // Step 2: Start session automatically
      const session = await startLiveSession(sessionName);
      if (!session) {
        throw new Error('Failed to start session');
      }
      
      // Step 3: Immediately start recording
      const recordingStarted = await startRecording();
      if (!recordingStarted) {
        // If recording fails, cleanup session
        await stopLiveSession();
        throw new Error('Failed to start recording');
      }
      
      console.log('✅ Recording session started successfully');
      setPiState(prev => ({ ...prev, loading: false }));
      
    } catch (error) {
      console.error('❌ Error starting recording session:', error);
      setPiState(prev => ({
        ...prev,
        loading: false,
        connectionError: error.message
      }));
      cleanupSession();
      throw error;
    }
  }, [checkPiStatus, startLiveSession, startRecording, stopLiveSession, piState.isConnected, cleanupSession]);

  const stopAndSave = useCallback(async () => {
    setPiState(prev => ({ ...prev, loading: true }));
    
    try {
      // Step 1: Stop recording first
      const recordingInfo = await stopRecording();
      if (recordingInfo) {
        // Small delay to ensure recording is finalized
        await new Promise(resolve => setTimeout(resolve, 2000));
        await fetchAvailableRecordings();
      }
      
      // Step 2: Stop session
      const sessionData = await stopLiveSession();
      
      // Step 3: Return data for save dialog
      setPiState(prev => ({ ...prev, loading: false }));
      
      return sessionData;
      
    } catch (error) {
      console.error('❌ Error stopping recording session:', error);
      setPiState(prev => ({ ...prev, loading: false }));
      cleanupSession();
      throw error;
    }
  }, [stopRecording, stopLiveSession, fetchAvailableRecordings, cleanupSession]);

  // === COMPONENT LIFECYCLE ===
  useEffect(() => {
    checkPiStatus();
    return () => stopUnifiedPolling();
  }, [checkPiStatus, stopUnifiedPolling]);

  // === SESSION COMPLETION HANDLER ===
  const handleSessionComplete = useCallback((result) => {
    console.log('✅ Session completed:', result);
    cleanupSession();
    if (onSessionComplete) {
      onSessionComplete(result);
    }
  }, [cleanupSession, onSessionComplete]);

  return (
    <div className="pi-live-container simplified">
      <div className="pi-live-header">
        <h2>🎥 Record Your Baduanjin Practice</h2>
        <PiStatusPanel 
          status={piState.status}
          isConnected={piState.isConnected}
          loading={piState.loading}
          onRefresh={checkPiStatus}
        />
      </div>
      
      {piState.connectionError && (
        <div className="error-banner">
          <p>⚠️ {piState.connectionError}</p>
          <button onClick={() => setPiState(prev => ({ ...prev, connectionError: null }))}>
            Dismiss
          </button>
        </div>
      )}
      
      <div className="pi-live-content">
        <div className="pi-stream-section">
          <PiVideoStream 
            // Pass consolidated state
            piState={piState}
            activeSession={piState.activeSession}
            poseData={piState.poseData}
            isConnected={piState.isConnected}
            connectionError={piState.connectionError}
            token={token} 
          />
        </div>
        
        <div className="pi-controls-section">
          <PiControls
            // Pass consolidated state
            piState={piState}
            
            // NEW SIMPLIFIED ACTIONS
            onStartRecordingSession={startRecordingSession}
            onStopAndSave={stopAndSave}
            onSessionComplete={handleSessionComplete}
            
            // UI State
            user={user}
          />
          
          <PiPoseData 
            poseData={piState.poseData}
            activeSession={piState.activeSession}
          />
        </div>
      </div>
      
      {piState.loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Processing...</p>
        </div>
      )}
    </div>
  );
};

export default PiLiveSession;
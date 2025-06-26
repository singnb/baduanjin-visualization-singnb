// src/components/PiLive/PiControls.js
// CLEANED VERSION - Uses centralized state, simplified logic

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import { PI_CONFIG, getPiUrl } from '../../config/piConfig';

const PiControls = ({ 
  piState,
  onStartSession, 
  onStopSession,
  onStartRecording,
  onStopRecording,
  onFetchRecordings,
  onSessionComplete,
  user
}) => {
  // === LOCAL STATE ===
  const [sessionName, setSessionName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [sessionToSave, setSessionToSave] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  
  // Save form fields
  const [saveForm, setSaveForm] = useState({
    title: '',
    description: '',
    brocadeType: 'FIRST',
    transferVideo: true,
    selectedRecording: null
  });
  
  // Duration timers
  const [sessionDuration, setSessionDuration] = useState(0);
  const [recordingDuration, setRecordingDuration] = useState(0);
  
  const { token } = useAuth();

  // === DURATION TRACKING ===
  useEffect(() => {
    let interval;
    if (piState.sessionStartTime) {
      interval = setInterval(() => {
        const duration = Math.floor((new Date() - piState.sessionStartTime) / 1000);
        setSessionDuration(duration);
      }, 1000);
    } else {
      setSessionDuration(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [piState.sessionStartTime]);

  useEffect(() => {
    let interval;
    if (piState.recordingStartTime) {
      interval = setInterval(() => {
        const duration = Math.floor((new Date() - piState.recordingStartTime) / 1000);
        setRecordingDuration(duration);
      }, 1000);
    } else {
      setRecordingDuration(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [piState.recordingStartTime]);

  // Auto-select latest recording
  useEffect(() => {
    if (piState.availableRecordings.length > 0 && !saveForm.selectedRecording) {
      const latest = piState.availableRecordings[0];
      setSaveForm(prev => ({ 
        ...prev, 
        selectedRecording: latest.filename,
        transferVideo: true
      }));
    }
  }, [piState.availableRecordings, saveForm.selectedRecording]);

  // === HELPER FUNCTIONS ===
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes) => {
    return (bytes / 1024 / 1024).toFixed(2) + ' MB';
  };

  // === SESSION CONTROLS ===
  const handleStartSession = async () => {
    const name = sessionName.trim() || 'Live Practice Session';
    await onStartSession(name);
    setSessionName('');
  };

  const handleStopSession = async () => {
    try {
      const sessionData = await onStopSession();
      if (sessionData) {
        await onFetchRecordings();
        setSessionToSave(sessionData);
        setShowSaveDialog(true);
        setSaveForm(prev => ({
          ...prev,
          title: sessionData.session_name || 'Live Session',
          description: '',
          brocadeType: 'FIRST',
          transferVideo: piState.availableRecordings.length > 0
        }));
        setSaveError(null);
      }
    } catch (error) {
      console.error('❌ Error stopping session:', error);
      alert('Error stopping session. Please try again.');
    }
  };

  // === SAVE LOGIC ===
  const handleSaveSession = async () => {
    if (!saveForm.title.trim()) {
      setSaveError('Please enter a title for the session');
      return;
    }

    setSaving(true);
    setSaveError(null);

    try {
      let videoFilename = null;
      let transferSuccess = false;

      // Transfer video if requested
      if (saveForm.transferVideo && saveForm.selectedRecording) {
        try {
          const transferResponse = await axios.post(
            `${getPiUrl('api')}/api/pi-live/transfer-video/${saveForm.selectedRecording}`,
            {},
            {
              headers: { 'Authorization': `Bearer ${token}` },
              timeout: 120000
            }
          );
          
          if (transferResponse.data.success) {
            videoFilename = transferResponse.data.filename;
            transferSuccess = true;
          }
        } catch (transferError) {
          console.error('❌ Video transfer failed:', transferError);
          setSaveError(`Video transfer failed: ${transferError.message}. Session will be saved without video.`);
        }
      }

      // Save session metadata
      const saveData = {
        title: saveForm.title.trim(),
        description: saveForm.description.trim() || '',
        brocade_type: saveForm.brocadeType,
        session_id: sessionToSave.session_id,
        video_filename: videoFilename,
        has_video_file: transferSuccess,
        duration_seconds: sessionToSave.duration_seconds || 0
      };

      const response = await axios.post(
        `${getPiUrl('api')}/api/pi-live/save-session`,
        saveData,
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        }
      );

      // Cleanup Pi recording if transferred
      if (transferSuccess && saveForm.selectedRecording) {
        try {
          await axios.delete(`${getPiUrl('api')}/api/pi-live/recordings/${saveForm.selectedRecording}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
        } catch (cleanupError) {
          console.warn('⚠️ Failed to clean up Pi recording:', cleanupError);
        }
      }
      
      setShowSaveDialog(false);
      setSessionToSave(null);
      
      if (onSessionComplete) {
        onSessionComplete(response.data);
      }

      const message = transferSuccess 
        ? 'Live session and video saved successfully!'
        : 'Live session saved successfully (without video file)';
      alert(message);

    } catch (error) {
      console.error('❌ Save error:', error);
      setSaveError(error.response?.data?.detail || 'Error saving session');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardSession = async () => {
    if (window.confirm('Are you sure you want to discard this session? This cannot be undone.')) {
      try {
        if (saveForm.selectedRecording) {
          await axios.delete(`${getPiUrl('api')}/api/pi-live/recordings/${saveForm.selectedRecording}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
        }
        
        setShowSaveDialog(false);
        setSessionToSave(null);
        
        if (onSessionComplete) {
          onSessionComplete(null);
        }

      } catch (error) {
        console.error('❌ Error discarding session:', error);
        alert('Error discarding session. Please try again.');
      }
    }
  };

  return (
    <div className="pi-controls">
      <h3>🎮 Session Controls</h3>
      
      {/* WORKFLOW STATUS */}
      <div className="workflow-status">
        <div className="workflow-steps">
          <div className={`workflow-step ${!piState.activeSession ? 'current' : 'completed'}`}>
            <span className="step-number">1</span>
            <span className="step-text">Start Session</span>
          </div>
          <div className={`workflow-step ${piState.activeSession && !piState.isRecording ? 'current' : piState.isRecording ? 'completed' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-text">Record (Optional)</span>
          </div>
          <div className={`workflow-step ${showSaveDialog ? 'current' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-text">Save</span>
          </div>
        </div>
      </div>
      
      {!piState.activeSession ? (
        // Start session form
        <div className="start-session-form">
          <div className="form-group">
            <label htmlFor="sessionName">Session Name:</label>
            <input
              id="sessionName"
              type="text"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="Enter session name (optional)..."
              disabled={piState.loading}
            />
          </div>
          
          <button
            className="btn start-session-btn"
            onClick={handleStartSession}
            disabled={!piState.isConnected || piState.loading}
          >
            {piState.loading ? 'Starting...' : '🚀 Start Live Session'}
          </button>
          
          {!piState.isConnected && !piState.loading && (
            <div className="connection-warning">
              <p>⚠️ Pi camera not connected. Please check the connection and refresh.</p>
            </div>
          )}
        </div>
      ) : (
        // Active session controls
        <div className="active-session-controls">
          <div className="session-info">
            <h4>📡 Active Session</h4>
            <div className="session-details">
              <p><strong>Name:</strong> {piState.activeSession.session_name || 'Live Session'}</p>
              <p><strong>Duration:</strong> {formatDuration(sessionDuration)}</p>
              <p><strong>Status:</strong> <span className="status-live">🔴 LIVE</span></p>
            </div>
          </div>
          
          {/* RECORDING SECTION */}
          <div className="recording-section">
            <h4>🎥 Recording (Optional)</h4>
            
            <div className="recording-status">
              {piState.isRecording ? (
                <div className="recording-active">
                  <span className="recording-indicator">🔴 RECORDING</span>
                  <span className="recording-duration">{formatDuration(recordingDuration)}</span>
                </div>
              ) : (
                <div className="recording-inactive">
                  <span className="recording-indicator">⚪ Not Recording</span>
                </div>
              )}
            </div>
            
            <div className="recording-controls">
              {!piState.isRecording ? (
                <button
                  className="btn start-recording-btn"
                  onClick={onStartRecording}
                  disabled={piState.loading}
                >
                  🔴 Start Recording
                </button>
              ) : (
                <button
                  className="btn stop-recording-btn"
                  onClick={onStopRecording}
                  disabled={piState.loading}
                >
                  ⏹️ Stop Recording
                </button>
              )}
            </div>
            
            {piState.availableRecordings.length > 0 && (
              <div className="recordings-available">
                <p>📹 {piState.availableRecordings.length} recording(s) available</p>
              </div>
            )}
          </div>
          
          <div className="session-actions">
            <button
              className="btn stop-session-btn"
              onClick={handleStopSession}
              disabled={piState.loading || showSaveDialog}
            >
              {piState.loading ? 'Stopping...' : '⏹️ Stop Session'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PiControls;
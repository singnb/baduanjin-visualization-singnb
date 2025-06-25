// src/components/PiLive/PiControls.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext'; 

const PiControls = ({ 
  // Pi Status
  piStatus, 
  isConnected,
  
  // Session State
  activeSession, 
  sessionStartTime,
  
  // Recording State
  isRecording,
  recordingStartTime,
  availableRecordings,
  
  // Actions
  onStartSession, 
  onStopSession,
  onStartRecording,
  onStopRecording,
  onFetchRecordings,
  onSessionComplete,
  
  // UI State
  loading, 
  user
}) => {
  // === LOCAL STATE ===
  const [sessionName, setSessionName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [sessionToSave, setSessionToSave] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  
  // Save form fields
  const [saveTitle, setSaveTitle] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [saveBrocadeType, setSaveBrocadeType] = useState('FIRST');
  const [transferVideo, setTransferVideo] = useState(true);
  const [selectedRecording, setSelectedRecording] = useState(null);
  
  // UI State
  const [sessionDuration, setSessionDuration] = useState(0);
  const [recordingDuration, setRecordingDuration] = useState(0);
  
  const { token } = useAuth();
  const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

  // === DURATION TIMERS ===
  useEffect(() => {
    let interval;
    if (sessionStartTime) {
      interval = setInterval(() => {
        const duration = Math.floor((new Date() - sessionStartTime) / 1000);
        setSessionDuration(duration);
      }, 1000);
    } else {
      setSessionDuration(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [sessionStartTime]);

  useEffect(() => {
    let interval;
    if (recordingStartTime) {
      interval = setInterval(() => {
        const duration = Math.floor((new Date() - recordingStartTime) / 1000);
        setRecordingDuration(duration);
      }, 1000);
    } else {
      setRecordingDuration(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [recordingStartTime]);

  // === AUTO-SELECT LATEST RECORDING ===
  useEffect(() => {
    if (availableRecordings.length > 0 && !selectedRecording) {
      // Auto-select the most recent recording
      const latest = availableRecordings[0];
      setSelectedRecording(latest.filename);
      console.log('🎯 Auto-selected latest recording:', latest.filename);
    }
  }, [availableRecordings, selectedRecording]);

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
      console.log('🛑 Initiating session stop...');
      
      // Stop the session and get session data
      const sessionData = await onStopSession();
      
      if (sessionData) {
        // Refresh recordings one more time
        await onFetchRecordings();
        
        // Show save dialog
        setSessionToSave(sessionData);
        setShowSaveDialog(true);
        setSaveTitle(sessionData.session_name || 'Live Session');
        setSaveDescription('');
        setSaveBrocadeType('FIRST');
        setTransferVideo(availableRecordings.length > 0);
        setSaveError(null);
      }
    } catch (error) {
      console.error('❌ Error stopping session:', error);
      alert('Error stopping session. Please try again.');
    }
  };

  // === RECORDING CONTROLS ===
  const handleStartRecording = async () => {
    const success = await onStartRecording();
    if (success) {
      console.log('✅ Recording started successfully');
    }
  };

  const handleStopRecording = async () => {
    const result = await onStopRecording();
    if (result) {
      console.log('✅ Recording stopped:', result);
      // Refresh recordings list
      await onFetchRecordings();
    }
  };

  // === SAVE/DISCARD LOGIC ===
  const handleSaveSession = async () => {
    if (!saveTitle.trim()) {
      setSaveError('Please enter a title for the session');
      return;
    }

    setSaving(true);
    setSaveError(null);

    try {
      let videoFilename = null;
      let transferSuccess = false;

      console.log('💾 Saving session...', {
        transferVideo,
        selectedRecording,
        availableRecordings: availableRecordings.length
      });

      // Step 1: Transfer video if requested and available
      if (transferVideo && selectedRecording) {
        try {
          console.log('📤 Transferring video:', selectedRecording);
          
          const transferResponse = await axios.post(
            `${BACKEND_URL}/api/pi-live/transfer-video/${selectedRecording}`,
            {},
            {
              headers: { 'Authorization': `Bearer ${token}` },
              timeout: 120000 // 2 minute timeout
            }
          );
          
          if (transferResponse.data.success) {
            videoFilename = transferResponse.data.filename;
            transferSuccess = true;
            console.log('✅ Video transferred successfully:', videoFilename);
          } else {
            throw new Error(transferResponse.data.message || 'Transfer failed');
          }
        } catch (transferError) {
          console.error('❌ Video transfer failed:', transferError);
          setSaveError(`Video transfer failed: ${transferError.message}. Session will be saved without video.`);
          // Continue to save session metadata even if transfer fails
        }
      }

      // Step 2: Save session metadata
      const saveData = {
        title: saveTitle.trim(),
        description: saveDescription.trim() || '',
        brocade_type: saveBrocadeType,
        session_id: sessionToSave.session_id,
        video_filename: videoFilename,
        has_video_file: transferSuccess,
        duration_seconds: sessionToSave.duration_seconds || 0
      };

      console.log('💾 Saving session metadata:', saveData);

      const response = await axios.post(
        `${BACKEND_URL}/api/pi-live/save-session`,
        saveData,
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        }
      );

      console.log('✅ Session saved:', response.data);

      // Step 3: Clean up Pi recording if transferred
      if (transferSuccess && selectedRecording) {
        try {
          await axios.delete(`${BACKEND_URL}/api/pi-live/recordings/${selectedRecording}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          console.log('🧹 Cleaned up Pi recording:', selectedRecording);
        } catch (cleanupError) {
          console.warn('⚠️ Failed to clean up Pi recording:', cleanupError);
        }
      }
      
      // Close dialog and notify completion
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
        console.log('🗑️ Discarding session...');
        
        // Delete any recordings from this session
        if (selectedRecording) {
          try {
            await axios.delete(`${BACKEND_URL}/api/pi-live/recordings/${selectedRecording}`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            console.log('🗑️ Deleted recording:', selectedRecording);
          } catch (error) {
            console.warn('⚠️ Failed to delete recording:', error);
          }
        }
        
        // Close dialog and notify completion
        setShowSaveDialog(false);
        setSessionToSave(null);
        
        if (onSessionComplete) {
          onSessionComplete(null);
        }

        console.log('✅ Session discarded');

      } catch (error) {
        console.error('❌ Error discarding session:', error);
        alert('Error discarding session. Please try again.');
      }
    }
  };

  const handleCancelSaveDialog = () => {
    setShowSaveDialog(false);
    setSessionToSave(null);
    setSaveError(null);
  };

  return (
    <div className="pi-controls">
      <h3>🎮 Session Controls</h3>
      
      {/* WORKFLOW GUIDE */}
      <div className="workflow-status">
        <div className="workflow-steps">
          <div className={`workflow-step ${!activeSession ? 'current' : 'completed'}`}>
            <span className="step-number">1</span>
            <span className="step-text">Start Session</span>
          </div>
          <div className={`workflow-step ${activeSession && !isRecording ? 'current' : isRecording ? 'completed' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-text">Record (Optional)</span>
          </div>
          <div className={`workflow-step ${activeSession && isRecording ? 'current' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-text">Practice</span>
          </div>
          <div className={`workflow-step ${showSaveDialog ? 'current' : ''}`}>
            <span className="step-number">4</span>
            <span className="step-text">Save</span>
          </div>
        </div>
      </div>
      
      {!activeSession ? (
        // === START SESSION FORM ===
        <div className="start-session-form">
          <div className="form-group">
            <label htmlFor="sessionName">Session Name:</label>
            <input
              id="sessionName"
              type="text"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="Enter session name (optional)..."
              className="session-name-input"
              disabled={loading}
            />
          </div>
          
          <button
            className="btn start-session-btn"
            onClick={handleStartSession}
            disabled={!isConnected || loading}
          >
            {loading ? 'Starting...' : '🚀 Start Live Session'}
          </button>
          
          {!isConnected && !loading && (
            <div className="connection-warning">
              <p>⚠️ Pi camera not connected. Please check the connection and refresh.</p>
            </div>
          )}
          
          <div className="workflow-reminder">
            <h4>💡 Remember:</h4>
            <ul>
              <li>Start session first for live streaming</li>
              <li>Click "Start Recording" if you want to save video</li>
              <li>Recording is optional - you can practice with just streaming</li>
            </ul>
          </div>
        </div>
      ) : (
        // === ACTIVE SESSION CONTROLS ===
        <div className="active-session-controls">
          <div className="session-info">
            <h4>📡 Active Session</h4>
            <div className="session-details">
              <p><strong>Name:</strong> {activeSession.session_name || 'Live Session'}</p>
              <p><strong>Duration:</strong> {formatDuration(sessionDuration)}</p>
              <p><strong>User:</strong> {user?.name} ({user?.role})</p>
              <p><strong>Status:</strong> 
                <span className="status-live">🔴 LIVE STREAMING</span>
              </p>
            </div>
          </div>
          
          {/* RECORDING SECTION */}
          <div className="recording-section">
            <h4>🎥 Video Recording (Optional)</h4>
            
            <div className="recording-status">
              {isRecording ? (
                <div className="recording-active">
                  <span className="recording-indicator">🔴 RECORDING</span>
                  <span className="recording-duration">{formatDuration(recordingDuration)}</span>
                </div>
              ) : (
                <div className="recording-inactive">
                  <span className="recording-indicator">⚪ Not Recording</span>
                  <span className="recording-note">Click below to record video</span>
                </div>
              )}
            </div>
            
            <div className="recording-controls">
              {!isRecording ? (
                <button
                  className="btn start-recording-btn"
                  onClick={handleStartRecording}
                  disabled={loading}
                >
                  🔴 Start Recording
                </button>
              ) : (
                <button
                  className="btn stop-recording-btn"
                  onClick={handleStopRecording}
                  disabled={loading}
                >
                  ⏹️ Stop Recording
                </button>
              )}
              
              <button
                className="btn refresh-recordings-btn"
                onClick={onFetchRecordings}
                disabled={loading}
              >
                🔄 Refresh
              </button>
            </div>
            
            {availableRecordings.length > 0 && (
              <div className="recordings-available">
                <p>📹 {availableRecordings.length} recording(s) available for this session</p>
              </div>
            )}
            
            <div className="recording-info">
              <p>💡 <strong>Recording is optional!</strong></p>
              <ul>
                <li>✅ Stream-only: Real-time feedback without storage</li>
                <li>🎥 With recording: Save video for detailed analysis</li>
              </ul>
            </div>
          </div>
          
          {/* SESSION ACTIONS */}
          <div className="session-actions">
            <button
              className="btn stop-session-btn"
              onClick={handleStopSession}
              disabled={loading || showSaveDialog}
            >
              {loading ? 'Stopping...' : '⏹️ Stop Session'}
            </button>
          </div>
        </div>
      )}

      {/* === SAVE/DISCARD DIALOG === */}
      {showSaveDialog && sessionToSave && (
        <div className="save-dialog-overlay">
          <div className="save-dialog">
            <h3>💾 Save Session</h3>
            
            <div className="session-summary">
              <h4>Session Summary:</h4>
              <p><strong>Duration:</strong> {formatDuration(sessionToSave.duration_seconds || 0)}</p>
              <p><strong>Recordings Available:</strong> {availableRecordings.length}</p>
              <p><strong>Session Type:</strong> {availableRecordings.length > 0 ? '🎥 With Video' : '📡 Streaming Only'}</p>
            </div>
            
            {saveError && <div className="error-message">{saveError}</div>}
            
            <div className="save-form">
              <div className="form-group">
                <label htmlFor="saveTitle">Title:</label>
                <input
                  id="saveTitle"
                  type="text"
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  placeholder="Enter session title..."
                  disabled={saving}
                  required
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="saveDescription">Description (Optional):</label>
                <textarea
                  id="saveDescription"
                  value={saveDescription}
                  onChange={(e) => setSaveDescription(e.target.value)}
                  placeholder="Enter description..."
                  disabled={saving}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="saveBrocadeType">Brocade Type:</label>
                <select
                  id="saveBrocadeType"
                  value={saveBrocadeType}
                  onChange={(e) => setSaveBrocadeType(e.target.value)}
                  disabled={saving}
                >
                  <option value="FIRST">First Brocade</option>
                  <option value="SECOND">Second Brocade</option>
                  <option value="THIRD">Third Brocade</option>
                  <option value="FOURTH">Fourth Brocade</option>
                  <option value="FIFTH">Fifth Brocade</option>
                  <option value="SIXTH">Sixth Brocade</option>
                  <option value="SEVENTH">Seventh Brocade</option>
                  <option value="EIGHTH">Eighth Brocade</option>
                </select>
              </div>

              {/* VIDEO TRANSFER OPTIONS */}
              {availableRecordings.length > 0 ? (
                <div className="video-transfer-section">
                  <h4>🎥 Video Recording</h4>
                  
                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={transferVideo}
                        onChange={(e) => setTransferVideo(e.target.checked)}
                        disabled={saving}
                      />
                      Transfer video file to permanent storage
                    </label>
                  </div>

                  {transferVideo && (
                    <div className="form-group">
                      <label htmlFor="selectedRecording">Select Recording:</label>
                      <select
                        id="selectedRecording"
                        value={selectedRecording || ''}
                        onChange={(e) => setSelectedRecording(e.target.value)}
                        disabled={saving}
                      >
                        <option value="">Select a recording...</option>
                        {availableRecordings.map((recording) => (
                          <option key={recording.filename} value={recording.filename}>
                            {recording.filename} - {formatFileSize(recording.size)}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              ) : (
                <div className="no-recordings-info">
                  <h4>📡 Streaming-Only Session</h4>
                  <p>This session used live streaming without video recording.</p>
                  <p>💡 Next time, click "Start Recording" to save video files.</p>
                </div>
              )}
            </div>
            
            <div className="dialog-actions">
              <button
                className="btn save-btn"
                onClick={handleSaveSession}
                disabled={saving || (transferVideo && !selectedRecording)}
              >
                {saving ? 'Saving...' : '💾 Save Session'}
              </button>
              
              <button
                className="btn discard-btn"
                onClick={handleDiscardSession}
                disabled={saving}
              >
                🗑️ Discard
              </button>
              
              <button
                className="btn cancel-btn"
                onClick={handleCancelSaveDialog}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PiControls;
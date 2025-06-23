// src/components/PiLive/PiControls.js - Enhanced with debugging
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';

const PiControls = ({ 
  piStatus, 
  activeSession, 
  loading, 
  onStartSession, 
  onStopSession, 
  user, 
  onSessionComplete 
}) => {
  const [sessionName, setSessionName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  
  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [availableRecordings, setAvailableRecordings] = useState([]);
  const [transferProgress, setTransferProgress] = useState({});
  const [debugInfo, setDebugInfo] = useState({});
  
  // Save form fields
  const [saveTitle, setSaveTitle] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [saveBrocadeType, setSaveBrocadeType] = useState('FIRST');
  const [transferVideo, setTransferVideo] = useState(true);
  const [selectedRecording, setSelectedRecording] = useState(null);
  
  const { token } = useAuth();
  const PI_SERVICE_URL = 'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net';
  const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

  // Enhanced debug logging
  const logDebug = (action, data) => {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] PiControls - ${action}:`, data);
    
    setDebugInfo(prev => ({
      ...prev,
      [action]: { timestamp, data }
    }));
  };

  // Poll for recording status and available recordings
  useEffect(() => {
    let interval;
    if (activeSession) {
      interval = setInterval(async () => {
        try {
          // Check recording status
          logDebug('Checking Pi status', { url: `${PI_URL}/api/pi-live/status` });
          const statusResponse = await axios.get(`${PI_SERVICE_URL}/api/pi-live/status`, { 
            headers: { 'Authorization': `Bearer ${token}` },
            timeout: 5000 
          });
          
          logDebug('Pi status response', statusResponse.data);
          setIsRecording(statusResponse.data.is_recording || false);
          
          // Get available recordings
          logDebug('Fetching recordings', { url: `${PI_URL}/api/recordings` });
          const recordingsResponse = await axios.get(`${PI_SERVICE_URL}/api/pi-live/recordings`, { 
            headers: { 'Authorization': `Bearer ${token}` },
            timeout: 10000 
          });
          
          logDebug('Recordings response', recordingsResponse.data);
          
          if (recordingsResponse.data.success) {
            const recordings = recordingsResponse.data.recordings || [];
            setAvailableRecordings(recordings);
            logDebug('Available recordings updated', { count: recordings.length, recordings });
          } else {
            logDebug('Recordings fetch failed', recordingsResponse.data);
          }
        } catch (error) {
          logDebug('Polling error', { 
            message: error.message, 
            response: error.response?.data,
            status: error.response?.status 
          });
          console.error('Error polling Pi status:', error);
        }
      }, 3000); // Poll every 3 seconds for better debugging
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeSession]);

  const handleStartSession = async () => {
    const name = sessionName.trim() || 'Live Practice Session';
    logDebug('Starting session', { name });
    await onStartSession(name);
    setSessionName('');
    
    // Clear debug info for new session
    setDebugInfo({});
  };

  const handleStopSession = async () => {
    logDebug('Stopping session initiated', { 
      isRecording, 
      availableRecordings: availableRecordings.length 
    });
    
    // If recording, stop it first
    if (isRecording) {
      logDebug('Stopping recording before session stop', {});
      await handleStopRecording();
      
      // Wait a moment for the recording to be processed
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Refresh recordings list
      await fetchAvailableRecordings();
    }
    
    // Show save/discard dialog
    setShowSaveDialog(true);
    setSaveTitle(activeSession?.session_name || 'Live Session');
    setSaveDescription('');
    setSaveBrocadeType('FIRST');
    setTransferVideo(true);
    setSaveError(null);
    
    // Get latest recordings list
    await fetchAvailableRecordings();
  };

  const handleStartRecording = async () => {
    try {
      logDebug('Starting recording', { url: `${PI_URL}/api/recording/start` });
      const response = await axios.post(`${PI_SERVICE_URL}/api/pi-live/recording/start/${activeSession.session_id}`, {}, { 
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: 10000 
      });
      
      logDebug('Start recording response', response.data);
      
      if (response.data.success) {
        setIsRecording(true);
        console.log('✅ Recording started:', response.data.message);
        
        // Show success message
        alert('Recording started successfully!');
      } else {
        logDebug('Recording start failed', response.data);
        alert(response.data.message || 'Failed to start recording');
      }
    } catch (error) {
      logDebug('Recording start error', { 
        message: error.message, 
        response: error.response?.data,
        status: error.response?.status 
      });
      console.error('Failed to start recording:', error);
      alert('Failed to start recording: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleStopRecording = async () => {
    try {
      logDebug('Stopping recording', { url: `${PI_URL}/api/recording/stop` });
      const response = await axios.post(`${PI_SERVICE_URL}/api/pi-live/recording/stop/${activeSession.session_id}`, {}, { 
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: 15000 
      });
      
      logDebug('Stop recording response', response.data);
      
      if (response.data.success) {
        setIsRecording(false);
        console.log('✅ Recording stopped:', response.data.recording_info);
        
        // Refresh recordings list
        await fetchAvailableRecordings();
        
        // Auto-select the latest recording
        if (response.data.recording_info?.filename) {
          const filename = response.data.recording_info.filename;
          setSelectedRecording(filename);
          logDebug('Auto-selected recording', { filename });
        }
        
        // Show success message
        alert(`Recording stopped successfully! File: ${response.data.recording_info?.filename || 'Unknown'}`);
      } else {
        logDebug('Recording stop failed', response.data);
        alert(response.data.message || 'Failed to stop recording');
      }
    } catch (error) {
      logDebug('Recording stop error', { 
        message: error.message, 
        response: error.response?.data,
        status: error.response?.status 
      });
      console.error('Failed to stop recording:', error);
      alert('Failed to stop recording: ' + (error.response?.data?.detail || error.message));
    }
  };

  const fetchAvailableRecordings = async () => {
    try {
      logDebug('Fetching recordings manually', { url: `${PI_URL}/api/recordings` });
      const recordingsResponse = await axios.get(`${PI_SERVICE_URL}/api/pi-live/recordings`, { 
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: 10000 
      });
      
      logDebug('Manual recordings fetch response', response.data);
      
      if (response.data.success) {
        const recordings = response.data.recordings || [];
        setAvailableRecordings(recordings);
        
        logDebug('Recordings updated', { 
          count: recordings.length, 
          filenames: recordings.map(r => r.filename)
        });
        
        // Auto-select the most recent recording if none selected
        if (recordings.length > 0 && !selectedRecording) {
          const latest = recordings[0].filename;
          setSelectedRecording(latest);
          logDebug('Auto-selected latest recording', { filename: latest });
        }
        
        return recordings;
      } else {
        logDebug('Recordings fetch failed', { error: response.data });
        throw new Error(response.data.error || 'Failed to fetch recordings');
      }
    } catch (error) {
      logDebug('Recordings fetch error', { 
        message: error.message, 
        response: error.response?.data,
        status: error.response?.status 
      });
      console.error('Failed to fetch recordings:', error);
      return [];
    }
  };

  // Test Pi connection
  const testPiConnection = async () => {
    try {
      logDebug('Testing Pi connection', { url: `${PI_URL}/api/pi-live/status` });
      const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/status`, { 
        headers: { 'Authorization': `Bearer ${token}` },
        timeout: 5000 
      });
      
      logDebug('Pi connection test result', response.data);
      alert(`Pi Connection: ${response.data.is_running ? 'Connected and Running' : 'Connected but Not Running'}`);
    } catch (error) {
      logDebug('Pi connection test failed', error);
      alert(`Pi Connection Failed: ${error.message}`);
    }
  };

  const handleSaveVideo = async () => {
    if (!saveTitle.trim()) {
      setSaveError('Please enter a title for the video');
      return;
    }

    setSaving(true);
    setSaveError(null);

    try {
      let videoFilename = null;
      let transferSuccess = false;

      logDebug('Save video initiated', {
        transferVideo,
        selectedRecording,
        availableRecordings: availableRecordings.length
      });

      // Step 1: Transfer video file if requested and selected
      if (transferVideo && selectedRecording) {
        setTransferProgress({ status: 'transferring', filename: selectedRecording });
        
        try {
          logDebug('Starting video transfer', { 
            filename: selectedRecording,
            url: `${BACKEND_URL}/api/pi-live/transfer-video/${selectedRecording}`
          });
          
          const transferResponse = await axios.post(
            `${BACKEND_URL}/api/pi-live/transfer-video/${selectedRecording}`,
            {},
            {
              headers: { 'Authorization': `Bearer ${token}` },
              timeout: 120000 // 2 minute timeout for large files
            }
          );
          
          logDebug('Transfer response', transferResponse.data);
          
          if (transferResponse.data.success) {
            videoFilename = transferResponse.data.filename;
            transferSuccess = true;
            setTransferProgress({ status: 'completed', filename: selectedRecording });
            logDebug('Transfer completed', { videoFilename });
          } else {
            throw new Error(transferResponse.data.message || 'Transfer failed');
          }
        } catch (transferError) {
          logDebug('Video transfer failed', transferError);
          console.error('Video transfer failed:', transferError);
          setTransferProgress({ status: 'failed', error: transferError.message });
          setSaveError(`Video transfer failed: ${transferError.message}. Session will be saved without video.`);
          // Continue to save session metadata even if transfer fails
        }
      }

      // Step 2: Save session metadata
      const saveData = {
        title: saveTitle.trim(),
        description: saveDescription.trim() || '',
        brocade_type: saveBrocadeType,
        session_id: activeSession.session_id,
        video_filename: videoFilename,
        has_video_file: transferSuccess
      };

      logDebug('Saving session metadata', saveData);

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

      logDebug('Save session response', response.data);

      // Step 3: Stop the session
      await onStopSession();
      
      // Step 4: Clean up Pi recording if transferred successfully
      if (transferSuccess && selectedRecording) {
        try {
          logDebug('Cleaning up Pi recording', { filename: selectedRecording });
          await axios.delete(`${BACKEND_URL}/api/pi-live/recordings/${selectedRecording}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          console.log(`Cleaned up Pi recording: ${selectedRecording}`);
        } catch (cleanupError) {
          logDebug('Cleanup failed', cleanupError);
          console.warn('Failed to clean up Pi recording:', cleanupError);
        }
      }
      
      // Close dialog and notify parent
      setShowSaveDialog(false);
      setTransferProgress({});
      
      if (onSessionComplete) {
        onSessionComplete(response.data);
      }

      const message = transferSuccess 
        ? 'Live session and video saved successfully!'
        : 'Live session saved successfully (without video file)';
      alert(message);

    } catch (error) {
      logDebug('Save video error', error);
      setSaveError(error.response?.data?.detail || 'Error saving video');
      console.error('Save error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardVideo = async () => {
    if (window.confirm('Are you sure you want to discard this live session? This cannot be undone.')) {
      try {
        logDebug('Discarding session', {});
        
        // Stop recording if active
        if (isRecording) {
          await handleStopRecording();
        }
        
        // Delete any recordings made during this session
        if (selectedRecording) {
          try {
            logDebug('Deleting Pi recording', { filename: selectedRecording });
            await axios.delete(`${BACKEND_URL}/api/pi-live/recordings/${selectedRecording}`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
          } catch (error) {
            logDebug('Delete recording failed', error);
            console.warn('Failed to delete Pi recording:', error);
          }
        }
        
        // Stop the session
        await onStopSession();
        
        // Close dialog and notify parent
        setShowSaveDialog(false);
        setTransferProgress({});
        
        if (onSessionComplete) {
          onSessionComplete(null);
        }

      } catch (error) {
        logDebug('Discard session error', error);
        console.error('Error discarding session:', error);
        alert('Error discarding session. Please try again.');
      }
    }
  };

  const handleCancelSaveDialog = () => {
    setShowSaveDialog(false);
    setSaveError(null);
    setTransferProgress({});
  };

  const formatFileSize = (bytes) => {
    return (bytes / 1024 / 1024).toFixed(2) + ' MB';
  };

  const formatDuration = (created) => {
    const createdTime = new Date(created);
    const now = new Date();
    const diffMs = now - createdTime;
    const diffSeconds = Math.floor(diffMs / 1000);
    
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    return `${Math.floor(diffSeconds / 3600)}h ago`;
  };

  return (
    <div className="pi-controls">
      <h3>Session Controls</h3>
      
      {/* Debug Panel - Remove in production */}
      <div className="debug-panel" style={{ 
        background: '#f0f0f0', 
        padding: '10px', 
        marginBottom: '15px', 
        borderRadius: '5px',
        fontSize: '12px' 
      }}>
        <details>
          <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
            🔍 Debug Info (Click to expand)
          </summary>
          <div style={{ marginTop: '10px' }}>
            <p><strong>Recording Status:</strong> {isRecording ? '🔴 Recording' : '⚪ Not Recording'}</p>
            <p><strong>Available Recordings:</strong> {availableRecordings.length}</p>
            <p><strong>Selected Recording:</strong> {selectedRecording || 'None'}</p>
            <p><strong>Pi URL:</strong> {PI_URL}</p>
            <button onClick={testPiConnection} style={{ marginRight: '10px' }}>Test Pi Connection</button>
            <button onClick={fetchAvailableRecordings}>Refresh Recordings</button>
            
            {availableRecordings.length > 0 && (
              <div style={{ marginTop: '10px' }}>
                <strong>Recordings:</strong>
                <ul style={{ fontSize: '11px', marginLeft: '20px' }}>
                  {availableRecordings.map((rec, idx) => (
                    <li key={idx}>
                      {rec.filename} - {formatFileSize(rec.size)} - {formatDuration(rec.created)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </details>
      </div>
      
      {!activeSession ? (
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
            disabled={!piStatus?.pi_connected || loading}
          >
            {loading ? 'Starting...' : '🚀 Start Live Session'}
          </button>
          
          {!piStatus?.pi_connected && !loading && (
            <p className="connection-warning">
              ⚠️ Pi camera not connected. Please check the connection and refresh.
              <br />
              <button onClick={testPiConnection} style={{ marginTop: '5px' }}>
                Test Connection
              </button>
            </p>
          )}
        </div>
      ) : (
        <div className="active-session-controls">
          <div className="session-info">
            <h4>Active Session</h4>
            <p><strong>Name:</strong> {activeSession.session_name || 'Live Session'}</p>
            <p><strong>Started:</strong> {new Date(activeSession.start_time).toLocaleTimeString()}</p>
            <p><strong>User:</strong> {user?.name} ({user?.role})</p>
            <p><strong>Session ID:</strong> {activeSession.session_id}</p>
            {isRecording && (
              <p className="recording-status">
                <span className="recording-indicator">🔴</span>
                <strong>Recording in progress...</strong>
              </p>
            )}
          </div>
          
          <div className="session-actions">
            <div className="recording-controls">
              <button
                className={`btn recording-btn ${isRecording ? 'stop-recording' : 'start-recording'}`}
                onClick={isRecording ? handleStopRecording : handleStartRecording}
                disabled={loading}
              >
                {isRecording ? '⏹️ Stop Recording' : '🔴 Start Recording'}
              </button>
              
              {availableRecordings.length > 0 && (
                <span className="recordings-count">
                  📹 {availableRecordings.length} recording(s) available
                </span>
              )}
              
              <button onClick={fetchAvailableRecordings} disabled={loading}>
                🔄 Refresh
              </button>
            </div>
            
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

      {/* Enhanced Save/Discard Dialog - Same as before but with better debugging */}
      {showSaveDialog && (
        <div className="save-dialog-overlay">
          <div className="save-dialog enhanced">
            <h3>Save Live Session</h3>
            
            {saveError && <div className="error-message">{saveError}</div>}
            
            {transferProgress.status && (
              <div className={`transfer-status ${transferProgress.status}`}>
                {transferProgress.status === 'transferring' && (
                  <p>🔄 Transferring video: {transferProgress.filename}...</p>
                )}
                {transferProgress.status === 'completed' && (
                  <p>✅ Video transferred successfully: {transferProgress.filename}</p>
                )}
                {transferProgress.status === 'failed' && (
                  <p>❌ Transfer failed: {transferProgress.error}</p>
                )}
              </div>
            )}
            
            <div className="save-form">
              <div className="form-group">
                <label htmlFor="saveTitle">Title:</label>
                <input
                  id="saveTitle"
                  type="text"
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  placeholder="Enter video title..."
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
                  required
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

              {/* Video Transfer Options */}
              {availableRecordings.length > 0 ? (
                <div className="video-transfer-section">
                  <h4>Video Recording ({availableRecordings.length} available)</h4>
                  
                  <div className="form-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={transferVideo}
                        onChange={(e) => setTransferVideo(e.target.checked)}
                        disabled={saving}
                      />
                      Transfer video file to backend storage
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
                            {recording.filename} - {formatFileSize(recording.size)} - {formatDuration(recording.created)}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {!transferVideo && (
                    <p className="note">
                      💡 Session will be saved as metadata only. Video files will remain on the Pi.
                    </p>
                  )}
                </div>
              ) : (
                <div className="no-recordings">
                  <p>ℹ️ No video recordings available. Session will be saved as streaming-only metadata.</p>
                  <p style={{ fontSize: '12px', color: '#666' }}>
                    💡 Tip: Use the "Start Recording" button during your session to create video files.
                  </p>
                </div>
              )}
            </div>
            
            <div className="dialog-actions">
              <button
                className="btn save-video-btn"
                onClick={handleSaveVideo}
                disabled={saving || (transferVideo && !selectedRecording)}
              >
                {saving ? 'Saving...' : '💾 Save Session'}
              </button>
              
              <button
                className="btn discard-video-btn"
                onClick={handleDiscardVideo}
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
      
      {loading && (
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
          <p>Processing request...</p>
        </div>
      )}
    </div>
  );
};

export default PiControls;
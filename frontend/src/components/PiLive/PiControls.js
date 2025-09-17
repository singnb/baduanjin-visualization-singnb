// src/components/PiLive/PiControls.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import { PI_CONFIG, getPiUrl } from '../../config/piConfig';

const PiControls = ({ 
  piState,
  onStartRecordingSession, 
  onStopAndSave,
  onSessionComplete,
  user
}) => {
  // === SIMPLIFIED STATE ===
  const [selectedExercise, setSelectedExercise] = useState('');
  const [currentExercise, setCurrentExercise] = useState('');
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

  // Exercise tracking state
  const [exerciseState, setExerciseState] = useState({
    isTracking: false,
    currentExercise: null,
    exercises: [],
    feedback: null,
    loading: false
  });
  
  // Duration timer
  const [recordingDuration, setRecordingDuration] = useState(0);
  
  const { token } = useAuth();

  // === DURATION TRACKING ===
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

  // Load exercises when component mounts
  useEffect(() => {
    loadExercises();
  }, []);

  // Auto-select latest recording for save
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

  // Poll for feedback when tracking
  useEffect(() => {
    let feedbackInterval;
    if (exerciseState.isTracking && piState.isRecording) {
      feedbackInterval = setInterval(fetchExerciseFeedback, 2000);
    }
    return () => {
      if (feedbackInterval) clearInterval(feedbackInterval);
    };
  }, [exerciseState.isTracking, piState.isRecording]);

  // === HELPER FUNCTIONS ===
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // === SIMPLIFIED MAIN ACTIONS ===
  const handleStartRecordingSession = async () => {
    try {
      // Auto-generate session name
      const sessionName = `Recording ${new Date().toLocaleString()}`;
      
      // Call the parent function that handles session + recording
      await onStartRecordingSession(sessionName, selectedExercise);
      
      // If exercise was selected, start tracking it
      if (selectedExercise) {
        await startExerciseTracking(parseInt(selectedExercise));
      }
      
    } catch (error) {
      console.error('Error starting recording session:', error);
      alert('Failed to start recording. Please try again.');
    }
  };

  const handleStopAndSave = async () => {
    try {
      // Stop exercise tracking first if active
      if (exerciseState.isTracking) {
        await stopExerciseTracking();
      }
      
      // Call parent function that handles stop recording + session
      const sessionData = await onStopAndSave();
      
      if (sessionData) {
        // Directly show save dialog
        setSessionToSave(sessionData);
        setShowSaveDialog(true);
        setSaveForm(prev => ({
          ...prev,
          title: `Recording ${new Date().toLocaleDateString()}`,
          description: exerciseState.currentExercise ? 
            `Baduanjin practice - ${exerciseState.currentExercise.exercise_name}` : 
            'Baduanjin practice session',
          brocadeType: 'FIRST',
          transferVideo: piState.availableRecordings.length > 0
        }));
        setSaveError(null);
      }
    } catch (error) {
      console.error('Error stopping session:', error);
      alert('Error stopping recording. Please try again.');
    }
  };

  // === EXERCISE MANAGEMENT ===
  const loadExercises = async () => {
    try {
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/baduanjin/exercises`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.data.success) {
        setExerciseState(prev => ({ ...prev, exercises: response.data.exercises }));
      }
    } catch (error) {
      console.error('Error loading exercises:', error);
    }
  };

  const startExerciseTracking = async (exerciseId) => {
    if (!exerciseId) return;
    
    setExerciseState(prev => ({ ...prev, loading: true }));
    
    try {
      const response = await axios.post(`${getPiUrl('api')}/api/pi-live/baduanjin/start/${exerciseId}`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.data.success) {
        setExerciseState(prev => ({
          ...prev,
          isTracking: true,
          currentExercise: response.data.exercise_info,
          loading: false
        }));
        setCurrentExercise(exerciseId.toString());
        console.log('Exercise tracking started:', response.data.exercise_info.exercise_name);
      }
    } catch (error) {
      console.error('Error starting exercise:', error);
      setExerciseState(prev => ({ ...prev, loading: false }));
    }
  };

  const stopExerciseTracking = async () => {
    if (!exerciseState.isTracking) return;
    
    try {
      const response = await axios.post(`${getPiUrl('api')}/api/pi-live/baduanjin/stop`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.data.success) {
        setExerciseState(prev => ({
          ...prev,
          isTracking: false,
          currentExercise: null,
          feedback: null,
          loading: false
        }));
        setCurrentExercise('');
        console.log('Exercise tracking stopped');
      }
    } catch (error) {
      console.error('Error stopping exercise:', error);
    }
  };

  const changeExerciseDuringRecording = async (exerciseId) => {
    // Stop current tracking
    if (exerciseState.isTracking) {
      await stopExerciseTracking();
    }
    
    // Start new exercise if selected
    if (exerciseId) {
      await startExerciseTracking(parseInt(exerciseId));
    }
    
    setCurrentExercise(exerciseId);
  };

  const fetchExerciseFeedback = async () => {
    if (!exerciseState.isTracking) return;
    
    try {
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/baduanjin/feedback`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.data.feedback) {
        setExerciseState(prev => ({ ...prev, feedback: response.data.feedback }));
      }
    } catch (error) {
      console.error('Error fetching feedback:', error);
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
          console.error('Video transfer failed:', transferError);
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
          console.warn('Failed to clean up Pi recording:', cleanupError);
        }
      }
      
      setShowSaveDialog(false);
      setSessionToSave(null);
      
      if (onSessionComplete) {
        onSessionComplete(response.data);
      }

      const message = transferSuccess 
        ? 'Recording saved successfully!'
        : 'Recording saved successfully (without video file)';
      alert(message);

    } catch (error) {
      console.error('Save error:', error);
      setSaveError(error.response?.data?.detail || 'Error saving recording');
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardSession = async () => {
    if (window.confirm('Are you sure you want to discard this recording? This cannot be undone.')) {
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
        console.error('Error discarding session:', error);
        alert('Error discarding recording. Please try again.');
      }
    }
  };

  return (
    <div className="pi-controls simplified">
      <h3>🎥 Record Your Practice</h3>
      
      {!piState.isRecording ? (
        // === START RECORDING SECTION ===
        <div className="start-recording-section">
          <div className="connection-status">
            {piState.isConnected ? (
              <div className="status-good">
                ✅ Camera Ready
              </div>
            ) : (
              <div className="status-bad">
                ❌ Camera Not Connected
              </div>
            )}
          </div>

          {/* Exercise Selection (Optional) */}
          <div className="exercise-selector">
            <label htmlFor="exerciseSelect">📚 Exercise Tracking (Optional):</label>
            <select 
              id="exerciseSelect"
              value={selectedExercise} 
              onChange={(e) => setSelectedExercise(e.target.value)}
              disabled={piState.loading}
            >
              <option value="">No specific exercise tracking</option>
              {exerciseState.exercises.map(exercise => (
                <option key={exercise.id} value={exercise.id}>
                  {exercise.id}. {exercise.name.split('(')[0].trim()}
                </option>
              ))}
            </select>
            {selectedExercise && (
              <p className="exercise-description">
                {exerciseState.exercises.find(e => e.id === parseInt(selectedExercise))?.description}
              </p>
            )}
          </div>
          
          {/* Main Start Button */}
          <button
            className="btn-primary large start-recording-btn"
            onClick={handleStartRecordingSession}
            disabled={!piState.isConnected || piState.loading}
          >
            {piState.loading ? (
              <>⏳ Starting...</>
            ) : (
              <>🔴 Start Recording</>
            )}
          </button>
          
          <p className="help-text">
            This will automatically start the camera and begin recording
          </p>
        </div>
      ) : (
        // === RECORDING ACTIVE SECTION ===
        <div className="recording-active-section">
          <div className="recording-status">
            <div className="recording-indicator">
              <span className="recording-dot">🔴</span>
              <span className="recording-text">RECORDING</span>
              <span className="recording-duration">{formatDuration(recordingDuration)}</span>
            </div>
          </div>

          {/* Exercise Control During Recording */}
          <div className="live-exercise-controls">
            <label htmlFor="currentExerciseSelect">📚 Current Exercise:</label>
            <select 
              id="currentExerciseSelect"
              value={currentExercise} 
              onChange={(e) => changeExerciseDuringRecording(e.target.value)}
              disabled={exerciseState.loading}
            >
              <option value="">No tracking</option>
              {exerciseState.exercises.map(exercise => (
                <option key={exercise.id} value={exercise.id}>
                  {exercise.id}. {exercise.name.split('(')[0].trim()}
                </option>
              ))}
            </select>
          </div>

          {/* Live Exercise Feedback */}
          {exerciseState.isTracking && exerciseState.feedback && (
            <div className="live-feedback-compact">
              <div className="feedback-header">
                <h5>🎯 {exerciseState.currentExercise?.exercise_name}</h5>
              </div>
              
              <div className="feedback-scores-grid">
                <div className="score-item">
                  <span className="score-label">Form Score:</span>
                  <span className={`score-value ${exerciseState.feedback.form_score > 80 ? 'excellent' : exerciseState.feedback.form_score > 60 ? 'good' : 'needs-work'}`}>
                    {exerciseState.feedback.form_score?.toFixed(1) || 0}/100
                  </span>
                </div>
                <div className="score-item">
                  <span className="score-label">Progress:</span>
                  <span className="score-value">
                    {exerciseState.feedback.completion_percentage?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="score-item">
                  <span className="score-label">Phase:</span>
                  <span className="score-value">
                    {exerciseState.feedback.current_phase || 'Unknown'}
                  </span>
                </div>
              </div>
              
              {exerciseState.feedback.feedback_messages && exerciseState.feedback.feedback_messages.length > 0 && (
                <div className="feedback-tip">
                  💡 {exerciseState.feedback.feedback_messages[0]}
                </div>
              )}
            </div>
          )}
          
          {/* Main Stop Button */}
          <button
            className="btn-danger large stop-recording-btn"
            onClick={handleStopAndSave}
            disabled={piState.loading}
          >
            {piState.loading ? (
              <>⏳ Stopping...</>
            ) : (
              <>⏹️ Stop & Save Recording</>
            )}
          </button>
          
          <p className="help-text">
            Recording will be automatically saved after stopping
          </p>
        </div>
      )}

      {/* === SAVE DIALOG === */}
      {showSaveDialog && (
        <div className="save-dialog-overlay">
          <div className="save-dialog">
            <h3>💾 Save Your Recording</h3>
            
            {saveError && (
              <div className="save-error">
                ❌ {saveError}
              </div>
            )}
            
            <div className="save-form">
              <div className="form-group">
                <label htmlFor="saveTitle">Title *</label>
                <input
                  id="saveTitle"
                  type="text"
                  value={saveForm.title}
                  onChange={(e) => setSaveForm(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Enter recording title..."
                  disabled={saving}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="saveDescription">Description</label>
                <textarea
                  id="saveDescription"
                  value={saveForm.description}
                  onChange={(e) => setSaveForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Optional description..."
                  disabled={saving}
                  rows="3"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="saveBrocade">Brocade Type</label>
                <select
                  id="saveBrocade"
                  value={saveForm.brocadeType}
                  onChange={(e) => setSaveForm(prev => ({ ...prev, brocadeType: e.target.value }))}
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
              
              {piState.availableRecordings.length > 0 && (
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={saveForm.transferVideo}
                      onChange={(e) => setSaveForm(prev => ({ ...prev, transferVideo: e.target.checked }))}
                      disabled={saving}
                    />
                    Save video file ({piState.availableRecordings[0]?.size ? 
                      `${(piState.availableRecordings[0].size / 1024 / 1024).toFixed(1)} MB` : 
                      'Unknown size'})
                  </label>
                </div>
              )}
            </div>
            
            <div className="save-actions">
              <button
                className="btn-secondary"
                onClick={handleDiscardSession}
                disabled={saving}
              >
                🗑️ Discard
              </button>
              <button
                className="btn-primary"
                onClick={handleSaveSession}
                disabled={saving || !saveForm.title.trim()}
              >
                {saving ? '⏳ Saving...' : '💾 Save Recording'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PiControls;
// src/components/PiLive/PiVideoStream.js 
// CLEANED VERSION - Uses centralized state, removed redundant polling

// src/components/PiLive/SimplifiedPiLiveSession.js
// FIXED VERSION - Uses correct Pi-Service backend

import { useState, useCallback, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';

// ✅ FIXED: Use Pi-Service backend for all Pi-Live endpoints
const PI_SERVICE_URL = 'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net';

const usePiSession = () => {
  const [state, setState] = useState({
    // Session state
    activeSession: null,
    sessionStartTime: null,
    
    // Connection state  
    isConnected: false,
    connectionError: null,
    loading: false,
    
    // Recording state
    isRecording: false,
    recordingStartTime: null,
    availableRecordings: [],
    
    // Exercise state (NEW - uses your Pi endpoints)
    currentExercise: null,
    exerciseFeedback: null,
    availableExercises: [],
    
    // Video state
    currentFrame: null,
    poseData: null
  });

  const { token } = useAuth();
  const pollingInterval = useRef(null);

  // SINGLE UNIFIED POLLING (replaces multiple intervals)
  const pollPiData = useCallback(async () => {
    if (!state.activeSession) return;

    try {
      // ✅ FIXED: Use Pi-Service URL
      const statusResponse = await axios.get(`${PI_SERVICE_URL}/api/pi-live/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const status = statusResponse.data;

      // ✅ FIXED: Use Pi-Service URL
      const frameResponse = await axios.get(`${PI_SERVICE_URL}/api/pi-live/current-frame`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const frameData = frameResponse.data;

      // Get exercise feedback if tracking active
      let exerciseFeedback = null;
      if (status.exercise_tracking?.enabled || status.exercise_tracking?.current_exercise) {
        try {
          // ✅ FIXED: Use Pi-Service URL
          const feedbackResponse = await axios.get(`${PI_SERVICE_URL}/api/pi-live/baduanjin/feedback`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (feedbackResponse.data.feedback) {
            exerciseFeedback = feedbackResponse.data.feedback;
          }
        } catch (feedbackError) {
          console.warn('Exercise feedback fetch failed:', feedbackError);
        }
      }

      // Update all state at once
      setState(prev => ({
        ...prev,
        isConnected: status.pi_connected,
        isRecording: status.is_recording,
        currentExercise: status.exercise_tracking?.current_exercise,
        exerciseFeedback: exerciseFeedback,
        currentFrame: frameData.success ? frameData.image : null,
        poseData: frameData.pose_data || null,
        connectionError: null
      }));

    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnected: false,
        connectionError: error.message,
        currentFrame: null,
        exerciseFeedback: null
      }));
    }
  }, [state.activeSession, token]);

  // Start/stop polling
  useEffect(() => {
    if (state.activeSession) {
      pollingInterval.current = setInterval(pollPiData, 200); // 5 FPS polling
      return () => {
        if (pollingInterval.current) {
          clearInterval(pollingInterval.current);
          pollingInterval.current = null;
        }
      };
    }
  }, [state.activeSession, pollPiData]);

  // Load exercises once
  useEffect(() => {
    const loadExercises = async () => {
      console.log('🔑 Loading exercises with token:', token ? 'EXISTS' : 'MISSING');
      
      if (!token) {
        console.error('❌ No token available - user may not be authenticated');
        return;
      }
      
      try {
        console.log('📡 Making request to:', `${PI_SERVICE_URL}/api/pi-live/baduanjin/exercises`);
        
        // ✅ FIXED: Use Pi-Service URL
        const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/baduanjin/exercises`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        console.log('✅ Exercise response:', response.data);
        
        if (response.data.success) {
          setState(prev => ({
            ...prev,
            availableExercises: response.data.exercises
          }));
        }
      } catch (error) {
        console.error('❌ Failed to load exercises:', error);
        console.error('❌ Error details:', error.response?.data);
        console.error('❌ Status code:', error.response?.status);
      }
    };

    loadExercises();
  }, [token]);

  return { state, setState, pollPiData };
};

// SIMPLIFIED VIDEO STREAM COMPONENT (unchanged)
const SimplifiedPiVideoStream = ({ piState, token }) => {
  const [streamError, setStreamError] = useState(null);

  const renderStreamContent = () => {
    // No session
    if (!piState.activeSession) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">📹</div>
          <p>Start a live session to view camera feed</p>
        </div>
      );
    }

    // Not connected
    if (!piState.isConnected) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">🔌</div>
          <p>Pi Camera Not Connected</p>
          <p style={{ fontSize: '14px', color: '#dc3545' }}>
            Waiting for Pi device to connect...
          </p>
        </div>
      );
    }

    // Connection error
    if (piState.connectionError) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">⚠️</div>
          <p>Pi Connection Error</p>
          <p style={{ fontSize: '14px', color: '#dc3545' }}>
            {piState.connectionError}
          </p>
        </div>
      );
    }

    // Video stream active
    if (piState.currentFrame) {
      return (
        <div className="stream-content">
          <img 
            src={`data:image/jpeg;base64,${piState.currentFrame}`}
            alt="Live Baduanjin analysis"
            className="live-stream"
            style={{ 
              width: '100%',
              height: 'auto',
              maxHeight: '500px',
              objectFit: 'contain',
              border: piState.isRecording ? '3px solid #dc3545' : '1px solid #dee2e6',
              borderRadius: '8px'
            }}
          />
          
          {/* Recording indicator */}
          {piState.isRecording && (
            <div className="recording-overlay" style={{
              position: 'absolute',
              top: '10px',
              left: '10px',
              background: 'rgba(220, 53, 69, 0.9)',
              color: 'white',
              padding: '5px 10px',
              borderRadius: '4px',
              fontWeight: 'bold'
            }}>
              🔴 RECORDING
            </div>
          )}

          {/* Note: Exercise feedback overlay is already baked into Pi video frame */}
        </div>
      );
    }

    // Loading
    return (
      <div className="stream-loading">
        <div className="loading-spinner"></div>
        <p>Starting camera feed...</p>
      </div>
    );
  };

  return (
    <div className="pi-video-stream">
      <div className="stream-header">
        <h3>📹 Live Camera Feed</h3>
        {piState.activeSession && (
          <div className="session-info">
            <span className="session-id">
              Session: {piState.activeSession.session_id?.substring(0, 8) || 'Unknown'}
            </span>
            {piState.isConnected && piState.currentFrame ? (
              <span className="live-indicator" style={{ color: '#28a745' }}>🔴 LIVE</span>
            ) : (
              <span className="offline-indicator" style={{ color: '#dc3545' }}>❌ OFFLINE</span>
            )}
          </div>
        )}
      </div>
      
      <div className="stream-container" style={{ position: 'relative' }}>
        {renderStreamContent()}
      </div>

      {/* Stream stats - Enhanced for exercise tracking */}
      {piState.activeSession && piState.isConnected && piState.currentFrame && (
        <div className="stream-status">
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Source:</span>
              <span className="status-value success">🔗 Pi Service</span>
            </div>
            <div className="status-item">
              <span className="status-label">Persons:</span>
              <span className="status-value">{piState.poseData?.length || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Recording:</span>
              <span className={`status-value ${piState.isRecording ? 'recording' : ''}`}>
                {piState.isRecording ? '🔴 Active' : '⚪ Stopped'}
              </span>
            </div>
            {piState.currentExercise && (
              <div className="status-item">
                <span className="status-label">Exercise:</span>
                <span className="status-value success">
                  🎯 {piState.currentExercise.name?.split('(')[0]?.trim() || 'Active'}
                </span>
              </div>
            )}
          </div>
          
          {/* Exercise feedback summary (Pi already overlays detailed feedback on video) */}
          {piState.exerciseFeedback && (
            <div className="exercise-summary">
              <div className="feedback-row">
                <span>Form: {piState.exerciseFeedback.form_score?.toFixed(1) || 0}/100</span>
                <span>Progress: {piState.exerciseFeedback.completion_percentage?.toFixed(1) || 0}%</span>
                <span>Phase: {piState.exerciseFeedback.current_phase || 'Unknown'}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// SIMPLIFIED EXERCISE CONTROLS
const SimplifiedExerciseControls = ({ piState, token }) => {
  const [loading, setLoading] = useState(false);

  const startExercise = async (exerciseId) => {
    setLoading(true);
    try {
      // ✅ FIXED: Use Pi-Service URL
      const response = await axios.post(`${PI_SERVICE_URL}/api/pi-live/baduanjin/start/${exerciseId}`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.data.success) {
        alert(`Started tracking: ${response.data.exercise_info.exercise_name}`);
      } else {
        alert(`Failed to start exercise: ${response.data.error}`);
      }
    } catch (error) {
      alert(`Error starting exercise: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const stopExercise = async () => {
    setLoading(true);
    try {
      // ✅ FIXED: Use Pi-Service URL
      const response = await axios.post(`${PI_SERVICE_URL}/api/pi-live/baduanjin/stop`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.data.success) {
        const summary = response.data.summary;
        alert(`Exercise completed!\nFinal Score: ${summary?.final_form_score || 'N/A'}`);
      }
    } catch (error) {
      alert(`Error stopping exercise: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!piState.activeSession) {
    return (
      <div className="exercise-controls">
        <h3>🥋 Baduanjin Exercise Tracking</h3>
        <p>Start a session first to enable exercise tracking</p>
      </div>
    );
  }

  return (
    <div className="exercise-controls">
      <h3>🥋 Baduanjin Exercise Tracking</h3>
      
      {!piState.currentExercise ? (
        <div className="exercise-selection">
          <p>Select an exercise to track your form:</p>
          <div className="exercise-buttons">
            {piState.availableExercises.slice(0, 4).map(exercise => (
              <button
                key={exercise.id}
                className="btn exercise-btn"
                onClick={() => startExercise(exercise.id)}
                disabled={loading}
                title={exercise.description}
              >
                {exercise.id}. {exercise.name.split('(')[0].trim()}
              </button>
            ))}
          </div>
          
          {piState.availableExercises.length > 4 && (
            <details>
              <summary>More exercises ({piState.availableExercises.length - 4} more)</summary>
              <div className="exercise-buttons">
                {piState.availableExercises.slice(4).map(exercise => (
                  <button
                    key={exercise.id}
                    className="btn exercise-btn"
                    onClick={() => startExercise(exercise.id)}
                    disabled={loading}
                    title={exercise.description}
                  >
                    {exercise.id}. {exercise.name.split('(')[0].trim()}
                  </button>
                ))}
              </div>
            </details>
          )}
        </div>
      ) : (
        <div className="exercise-active">
          <div className="current-exercise">
            <h5>🎯 Tracking: {piState.currentExercise.name}</h5>
            <p>{piState.currentExercise.description}</p>
          </div>
          
          {/* Real-time feedback display */}
          {piState.exerciseFeedback && (
            <div className="live-feedback">
              <div className="feedback-scores">
                <div className="score-item">
                  <span className="score-label">Form Score:</span>
                  <span className={`score-value ${
                    piState.exerciseFeedback.form_score > 80 ? 'excellent' : 
                    piState.exerciseFeedback.form_score > 60 ? 'good' : 'needs-work'
                  }`}>
                    {piState.exerciseFeedback.form_score?.toFixed(1) || 0}/100
                  </span>
                </div>
                
                <div className="score-item">
                  <span className="status-label">Progress:</span>
                  <span className="score-value">
                    {piState.exerciseFeedback.completion_percentage?.toFixed(1) || 0}%
                  </span>
                </div>
                
                <div className="score-item">
                  <span className="score-label">Phase:</span>
                  <span className="score-value">
                    {piState.exerciseFeedback.current_phase || 'Unknown'}
                  </span>
                </div>
              </div>
              
              {/* Feedback messages */}
              {piState.exerciseFeedback.feedback_messages && 
               piState.exerciseFeedback.feedback_messages.length > 0 && (
                <div className="feedback-messages">
                  <h6>💡 Tips:</h6>
                  {piState.exerciseFeedback.feedback_messages.slice(0, 2).map((msg, idx) => (
                    <p key={idx} className="feedback-message">• {msg}</p>
                  ))}
                </div>
              )}
              
              {/* Corrections */}
              {piState.exerciseFeedback.corrections && 
               piState.exerciseFeedback.corrections.length > 0 && (
                <div className="feedback-corrections">
                  <h6>⚠️ Corrections:</h6>
                  {piState.exerciseFeedback.corrections.slice(0, 2).map((correction, idx) => (
                    <p key={idx} className="feedback-correction">• {correction}</p>
                  ))}
                </div>
              )}
            </div>
          )}
          
          <button
            className="btn stop-exercise-btn"
            onClick={stopExercise}
            disabled={loading}
          >
            {loading ? 'Stopping...' : '⏹️ Stop Exercise Tracking'}
          </button>
        </div>
      )}
    </div>
  );
};

// SIMPLIFIED MAIN COMPONENT
const SimplifiedPiLiveSession = ({ onSessionComplete }) => {
  const { state: piState, setState: setPiState } = usePiSession();
  const { token, user } = useAuth();
  const [sessionName, setSessionName] = useState('');

  // Session management (simplified)
  const startLiveSession = async (name = 'Live Practice Session') => {
    setPiState(prev => ({ ...prev, loading: true }));
    
    try {
      // ✅ FIXED: Use Pi-Service URL
      const response = await axios.post(`${PI_SERVICE_URL}/api/pi-live/start-session`, 
        { session_name: name },
        { headers: { 'Authorization': `Bearer ${token}` }}
      );
      
      if (response.data.success) {
        setPiState(prev => ({
          ...prev,
          activeSession: response.data,
          sessionStartTime: new Date(),
          loading: false
        }));
      }
    } catch (error) {
      setPiState(prev => ({
        ...prev,
        loading: false,
        connectionError: error.message
      }));
    }
  };

  const stopLiveSession = async () => {
    if (!piState.activeSession) return;
    
    setPiState(prev => ({ ...prev, loading: true }));
    
    try {
      // ✅ FIXED: Use Pi-Service URL
      await axios.post(`${PI_SERVICE_URL}/api/pi-live/stop-session/${piState.activeSession.session_id}`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      // Reset state
      setPiState(prev => ({
        ...prev,
        activeSession: null,
        sessionStartTime: null,
        currentExercise: null,
        exerciseFeedback: null,
        loading: false
      }));
      
      if (onSessionComplete) onSessionComplete();
      
    } catch (error) {
      setPiState(prev => ({
        ...prev,
        loading: false,
        connectionError: error.message
      }));
    }
  };

  // Recording management (simplified)
  const toggleRecording = async () => {
    if (!piState.activeSession) return;
    
    const endpoint = piState.isRecording ? 'stop' : 'start';
    
    try {
      // ✅ FIXED: Use Pi-Service URL
      await axios.post(`${PI_SERVICE_URL}/api/pi-live/recording/${endpoint}/${piState.activeSession.session_id}`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setPiState(prev => ({
        ...prev,
        isRecording: !prev.isRecording,
        recordingStartTime: !prev.isRecording ? new Date() : null
      }));
      
    } catch (error) {
      alert(`Failed to ${endpoint} recording: ${error.message}`);
    }
  };

  return (
    <div className="pi-live-container">
      <div className="pi-live-header">
        <h2>🥋 Real-time Baduanjin Analysis</h2>
        
        {/* Connection status */}
        <div className="status-panel">
          <span className={`status-dot ${piState.isConnected ? 'green' : 'red'}`}></span>
          <span>Pi Camera: {piState.isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
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
        {/* Video stream */}
        <div className="pi-stream-section">
          <SimplifiedPiVideoStream piState={piState} token={token} />
        </div>
        
        {/* Controls */}
        <div className="pi-controls-section">
          {!piState.activeSession ? (
            <div className="start-session-form">
              <h3>🎮 Session Controls</h3>
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="Enter session name (optional)..."
                disabled={piState.loading}
              />
              <button
                className="btn start-session-btn"
                onClick={() => startLiveSession(sessionName || 'Live Practice Session')}
                disabled={piState.loading}  // ← Only disable when loading, not when disconnected
              >
                {piState.loading ? 'Starting...' : '🚀 Start Live Session'}
              </button>
            </div>
          ) : (
            <div className="active-session-controls">
              <h3>📡 Active Session</h3>
              <p><strong>Name:</strong> {piState.activeSession.session_name}</p>
              
              {/* Recording controls */}
              <div className="recording-section">
                <h4>🎥 Recording</h4>
                <button
                  className={`btn ${piState.isRecording ? 'stop-recording-btn' : 'start-recording-btn'}`}
                  onClick={toggleRecording}
                  disabled={piState.loading}
                >
                  {piState.isRecording ? '⏹️ Stop Recording' : '🔴 Start Recording'}
                </button>
              </div>
              
              <button
                className="btn stop-session-btn"
                onClick={stopLiveSession}
                disabled={piState.loading}
              >
                {piState.loading ? 'Stopping...' : '⏹️ Stop Session'}
              </button>
            </div>
          )}
          
          {/* Exercise controls */}
          <SimplifiedExerciseControls piState={piState} token={token} />
        </div>
      </div>
    </div>
  );
};

export default SimplifiedPiLiveSession;
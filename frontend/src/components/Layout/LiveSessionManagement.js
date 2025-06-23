// src/components/Layout/LiveSessionManagement.js
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import PiLiveSession from '../PiLive/PiLiveSession';
import './Layout.css';
import './LiveSessionManagement.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

const LiveSessionManagement = () => {
  const [liveSessions, setLiveSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [showWorkflowGuide, setShowWorkflowGuide] = useState(false);
  const { token, user } = useAuth();

  // Helper function to detect live sessions
  const isLiveSession = (video) => {
    return video?.processing_status === 'live_completed' || 
           video?.processing_status === 'live_active' ||
           video?.video_path?.includes('LIVE_SESSION_NO_VIDEO') ||
           video?.video_path?.includes('LIVE_SESSION_STREAM_ONLY') ||
           video?.title?.startsWith('[LIVE]');
  };

  // Helper function to check if session has video file
  const hasVideoFile = (session) => {
    return session.video_path && 
           !session.video_path.includes('LIVE_SESSION_NO_VIDEO') &&
           !session.video_path.includes('LIVE_SESSION_STREAM_ONLY') &&
           !session.video_path.includes('TRANSFER_FAILED');
  };

  // Helper function to get session status display
  const getSessionStatusDisplay = (session) => {
    if (session.processing_status === 'live_active') {
      return 'Live Session Active';
    } else if (session.processing_status === 'live_completed') {
      return hasVideoFile(session) ? 'Session with Video' : 'Streaming Only';
    } else if (session.processing_status === 'completed') {
      return 'Video Analysis Complete';
    } else {
      return 'Unknown Status';
    }
  };

  // Helper function to get session type icon
  const getSessionTypeIcon = (session) => {
    if (hasVideoFile(session)) {
      return '🎥'; // Video recorded
    } else {
      return '📡'; // Streaming only
    }
  };

  // Helper function to get session duration
  const getSessionDuration = (session) => {
    if (session.video_path) {
      // Extract duration from various path formats
      let match = session.video_path.match(/_(\d+)s$/);
      if (match) {
        const seconds = parseInt(match[1]);
        if (seconds >= 60) {
          const minutes = Math.floor(seconds / 60);
          const remainingSeconds = seconds % 60;
          return `${minutes}m ${remainingSeconds}s`;
        }
        return `${seconds}s`;
      }
      
      // Try alternative format
      match = session.video_path.match(/(\d+\.\d+)s/);
      if (match) {
        const seconds = parseFloat(match[1]);
        if (seconds >= 60) {
          const minutes = Math.floor(seconds / 60);
          const remainingSeconds = Math.round(seconds % 60);
          return `${minutes}m ${remainingSeconds}s`;
        }
        return `${Math.round(seconds)}s`;
      }
    }
    return 'Unknown duration';
  };

  // Fetch live sessions from server
  const fetchLiveSessions = useCallback(async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`${BACKEND_URL}/api/videos`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Filter to only show live sessions
      const sessions = response.data.filter(v => 
        v.processing_status !== 'deleted' && 
        isLiveSession(v)
      );
      
      // Sort by date (newest first)
      sessions.sort((a, b) => new Date(b.upload_timestamp) - new Date(a.upload_timestamp));
      
      setLiveSessions(sessions);
      setError(null);
    } catch (err) {
      setError('Failed to load live sessions. Please try again.');
      console.error('Error fetching live sessions:', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Initial load and check if user is new
  useEffect(() => {
    fetchLiveSessions();
    
    // Show workflow guide for new users
    const hasSeenGuide = localStorage.getItem('baduanjin_workflow_guide_seen');
    if (!hasSeenGuide) {
      setShowWorkflowGuide(true);
    }
  }, [fetchLiveSessions]);

  const handleSessionSelect = (sessionId) => {
    const session = liveSessions.find(s => s.id === sessionId);
    if (session) {
      setSelectedSession(session);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to delete this live session record?')) {
      return;
    }
    
    try {
      setLiveSessions(prevSessions => 
        prevSessions.map(s => 
          s.id === sessionId ? { ...s, processing_status: 'deleting' } : s
        )
      );
      
      await axios.delete(`${BACKEND_URL}/api/videos/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      setLiveSessions(prevSessions => prevSessions.filter(s => s.id !== sessionId));
      
      if (selectedSession && selectedSession.id === sessionId) {
        setSelectedSession(null);
      }
      
      await fetchLiveSessions();
      
    } catch (err) {
      console.error('Error deleting session:', err);
      alert('Failed to delete session. Please try again.');
      fetchLiveSessions();
    }
  };

  const handleSessionComplete = () => {
    // Refresh sessions when a new live session is completed
    fetchLiveSessions();
  };

  const closeWorkflowGuide = () => {
    setShowWorkflowGuide(false);
    localStorage.setItem('baduanjin_workflow_guide_seen', 'true');
  };

  const showGuideAgain = () => {
    setShowWorkflowGuide(true);
  };

  return (
    <div className="live-session-management-container">
      {/* Workflow Guide Modal */}
      {showWorkflowGuide && (
        <div className="workflow-guide-overlay">
          <div className="workflow-guide-modal">
            <div className="workflow-guide-header">
              <h2>🎥 How to Record Videos During Live Sessions</h2>
              <button className="close-guide-btn" onClick={closeWorkflowGuide}>×</button>
            </div>
            
            <div className="workflow-guide-content">
              <div className="workflow-step">
                <div className="step-number">1</div>
                <div className="step-content">
                  <h3>🚀 Start Live Session</h3>
                  <p>Click "Start Live Session" to begin streaming with pose detection</p>
                </div>
              </div>
              
              <div className="workflow-step">
                <div className="step-number">2</div>
                <div className="step-content">
                  <h3>🔴 Start Recording (Important!)</h3>
                  <p><strong>Manually click "Start Recording"</strong> to create a video file</p>
                  <div className="step-note">
                    ⚠️ This is separate from starting the session! Recording is optional.
                  </div>
                </div>
              </div>
              
              <div className="workflow-step">
                <div className="step-number">3</div>
                <div className="step-content">
                  <h3>🥋 Practice Baduanjin</h3>
                  <p>Perform your exercises with real-time pose feedback</p>
                </div>
              </div>
              
              <div className="workflow-step">
                <div className="step-number">4</div>
                <div className="step-content">
                  <h3>⏹️ Stop Recording</h3>
                  <p>Click "Stop Recording" when finished (if you started recording)</p>
                </div>
              </div>
              
              <div className="workflow-step">
                <div className="step-number">5</div>
                <div className="step-content">
                  <h3>💾 Save Session</h3>
                  <p>Click "Stop Session" and choose to save with or without video</p>
                </div>
              </div>
            </div>
            
            <div className="workflow-guide-footer">
              <div className="guide-options">
                <h4>Two Types of Sessions:</h4>
                <div className="session-types">
                  <div className="session-type">
                    <span className="type-icon">📡</span>
                    <div>
                      <strong>Streaming Only</strong>
                      <p>Real-time feedback, no file storage</p>
                    </div>
                  </div>
                  <div className="session-type">
                    <span className="type-icon">🎥</span>
                    <div>
                      <strong>Recorded Session</strong>
                      <p>Video file saved for detailed analysis</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <button className="btn understand-btn" onClick={closeWorkflowGuide}>
                ✅ I Understand
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Live Session Interface */}
      <div className="live-session-interface">
        <div className="interface-header">
          <h2>🔴 Live Practice Session</h2>
          <div className="interface-actions">
            <button className="btn help-btn" onClick={showGuideAgain}>
              ❓ How to Record Videos
            </button>
          </div>
        </div>
        <PiLiveSession onSessionComplete={handleSessionComplete} />
      </div>

      {/* Session History */}
      <div className="session-history-section">
        <div className="section-header">
          <h2>📚 Live Session History</h2>
          <p>Your previous live streaming practice sessions</p>
          <div className="session-stats">
            <span className="stat">
              📡 {liveSessions.filter(s => !hasVideoFile(s)).length} Streaming Only
            </span>
            <span className="stat">
              🎥 {liveSessions.filter(s => hasVideoFile(s)).length} With Video
            </span>
            <span className="stat">
              📊 {liveSessions.length} Total Sessions
            </span>
          </div>
        </div>
        
        <div className="sessions-grid-layout">
          {/* Left panel - Session list */}
          <div className="session-list-panel">
            {loading ? (
              <div className="loading-indicator">Loading sessions...</div>
            ) : error ? (
              <div className="error-message">{error}</div>
            ) : liveSessions.length === 0 ? (
              <div className="empty-state">
                <h3>No live sessions yet</h3>
                <p>Start your first live session above to practice with real-time feedback!</p>
                <div className="empty-state-content">
                  <div className="empty-state-icon">🔴</div>
                  <button className="btn start-first-session-btn" onClick={showGuideAgain}>
                    📖 Learn How to Record Videos
                  </button>
                </div>
              </div>
            ) : (
              <div className="session-cards">
                {liveSessions.map(session => (
                  <div 
                    key={session.id} 
                    className={`session-card ${selectedSession && selectedSession.id === session.id ? 'selected' : ''} ${hasVideoFile(session) ? 'has-video' : 'streaming-only'}`}
                  >
                    <div className="session-card-content">
                      <h3 className="session-title">
                        {getSessionTypeIcon(session)} {session.title.replace('[LIVE]', '').trim()}
                      </h3>
                      <div className="session-meta">
                        <span className="session-type">
                          Type: {hasVideoFile(session) ? 'Recorded Session' : 'Streaming Only'}
                        </span>
                        <span className={`session-status status-${session.processing_status}`}>
                          Status: {getSessionStatusDisplay(session)}
                        </span>
                        <span className="session-date">
                          Date: {new Date(session.upload_timestamp).toLocaleString()}
                        </span>
                        <span className="session-duration">
                          Duration: {getSessionDuration(session)}
                        </span>
                        {hasVideoFile(session) && (
                          <span className="video-indicator">
                            🎥 Video file available
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="session-card-actions">
                      <button
                        className="btn view-btn"
                        onClick={() => handleSessionSelect(session.id)}
                      >
                        View Details
                      </button>
                      <button 
                        className="btn delete-btn" 
                        onClick={() => handleDeleteSession(session.id)}
                        disabled={session.processing_status === 'deleting'}
                      >
                        {session.processing_status === 'deleting' ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Right panel - Session details */}
          <div className="session-details-panel">
            {selectedSession ? (
              <div className="session-details-content">
                <div className="session-info-section">
                  <h2 className="section-header">
                    {getSessionTypeIcon(selectedSession)} {selectedSession.title.replace('[LIVE]', '').trim()}
                  </h2>
                  <div className="session-info-grid">
                    <div className="info-item">
                      <span className="info-label">Session Type:</span>
                      <span className="info-value">
                        {hasVideoFile(selectedSession) ? 'Live Session with Video Recording' : 'Live Streaming Practice'}
                      </span>
                    </div>
                    {selectedSession.description && (
                      <div className="info-item">
                        <span className="info-label">Description:</span>
                        <span className="info-value">{selectedSession.description}</span>
                      </div>
                    )}
                    <div className="info-item">
                      <span className="info-label">Exercise Type:</span>
                      <span className="info-value">{selectedSession.brocade_type}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Status:</span>
                      <span className={`info-value status-badge status-${selectedSession.processing_status}`}>
                        {getSessionStatusDisplay(selectedSession)}
                      </span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Session Date:</span>
                      <span className="info-value">
                        {new Date(selectedSession.upload_timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Duration:</span>
                      <span className="info-value">{getSessionDuration(selectedSession)}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Video File:</span>
                      <span className="info-value">
                        {hasVideoFile(selectedSession) ? '✅ Available' : '❌ Not recorded'}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="live-session-display">
                  {hasVideoFile(selectedSession) ? (
                    <div className="recorded-session-info">
                      <h3>🎥 Recorded Live Session</h3>
                      <p>This session included video recording for detailed analysis.</p>
                      
                      <div className="session-benefits">
                        <h4>Session included:</h4>
                        <ul>
                          <li>✅ Real-time pose detection and feedback</li>
                          <li>✅ Live form correction guidance</li>
                          <li>✅ Video file saved for review</li>
                          <li>✅ Detailed movement analysis</li>
                          <li>✅ Progress tracking capability</li>
                        </ul>
                      </div>
                      
                      <div className="video-actions">
                        <button className="btn view-analysis-btn">
                          📊 View Detailed Analysis
                        </button>
                        <button className="btn download-video-btn">
                          ⬇️ Download Video
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="streaming-session-info">
                      <h3>📡 Streaming-Only Session</h3>
                      <p>This was a live streaming session without video recording.</p>
                      
                      <div className="session-benefits">
                        <h4>What you practiced:</h4>
                        <ul>
                          <li>✅ Real-time pose detection and feedback</li>
                          <li>✅ Live form correction guidance</li>
                          <li>✅ Interactive practice session</li>
                          <li>✅ Immediate visual feedback</li>
                          <li>✅ No storage overhead</li>
                        </ul>
                      </div>
                      
                      <div className="next-steps">
                        <h4>Want video analysis?</h4>
                        <p>Next time, click "Start Recording" during your live session to save a video file for detailed analysis.</p>
                        <button className="btn learn-recording-btn" onClick={showGuideAgain}>
                          📖 Learn How to Record
                        </button>
                      </div>
                    </div>
                  )}
                  
                  <div className="live-session-actions">
                    <button 
                      className="btn start-new-session-btn"
                      onClick={() => {
                        // Scroll to the top where PiLiveSession is
                        const liveInterface = document.querySelector('.live-session-interface');
                        if (liveInterface) {
                          liveInterface.scrollIntoView({ behavior: 'smooth' });
                        }
                      }}
                    >
                      🔴 Start New Live Session
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="select-prompt">
                <h3>Select a session to view details</h3>
                <p>Choose a live session from the list to view information about your practice</p>
                <div className="select-prompt-icon">👆</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveSessionManagement;
// src/components/PiLive/PiVideoStream.js 
// CLEANED VERSION - Uses centralized state, removed redundant polling
// eslint-disable-next-line react-hooks/exhaustive-deps

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { PI_CONFIG, getPiUrl, isDirectPiAvailable } from '../../config/piConfig';

const PiVideoStream = ({ piState, token }) => {
  const [streamImage, setStreamImage] = useState(null);
  const [frameStats, setFrameStats] = useState({ fps: 0, latency: 0, persons: 0 });
  const [streamError, setStreamError] = useState(null);
  const framePollingRef = useRef(null);
  const frameBuffer = useRef([]);
  const lastFrameTime = useRef(0);

  // === ENHANCED FRAME FETCHING WITH BETTER ERROR HANDLING ===
  const fetchVideoFrame = useCallback(async () => {
    // Only fetch frames if session is active
    if (!piState.activeSession) {
      return;
    }

    try {
      setStreamError(null);
      
      // Try direct Pi connection first
      if (isDirectPiAvailable()) {
        const directPiUrl = getPiUrl('video_stream');
        console.log('🎥 Fetching frame from direct Pi:', directPiUrl);
        
        const response = await fetch(`${directPiUrl}/api/current_frame`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true',
            'Origin': window.location.origin
          },
          mode: 'cors',
          signal: AbortSignal.timeout(PI_CONFIG.TIMEOUTS.VIDEO_STREAM)
        });

        if (!response.ok) {
          throw new Error(`Direct Pi HTTP ${response.status}: ${response.statusText}`);
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          const textContent = await response.text();
          if (textContent.includes('ngrok')) {
            throw new Error('Ngrok authentication required');
          }
          throw new Error('Invalid response format from Pi');
        }

        const data = await response.json();

        if (data.success && data.image) {
          console.log('✅ Frame received from direct Pi');
          handleFrameUpdate({
            image: data.image,
            timestamp: data.timestamp || Date.now(),
            stats: data.stats || {},
            poseData: data.pose_data || [],
            isRecording: data.is_recording || false
          });
          return;
        } else if (data.error) {
          throw new Error(`Pi server error: ${data.error}`);
        }
      }
      
      // Fallback: Try getting frame through Azure Pi Service
      console.log('🎥 Trying frame fetch through Azure Pi Service...');
      const azureResponse = await fetch(`${getPiUrl('api')}/api/pi-live/current-frame`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        },
        timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
      });

      if (azureResponse.ok) {
        const azureData = await azureResponse.json();
        if (azureData.success && azureData.image) {
          console.log('✅ Frame received through Azure Pi Service');
          handleFrameUpdate({
            image: azureData.image,
            timestamp: azureData.timestamp || Date.now(),
            stats: azureData.stats || {},
            poseData: azureData.pose_data || [],
            isRecording: azureData.is_recording || false
          });
          return;
        }
      }

      // If both methods fail, show appropriate error
      throw new Error('No video stream available from Pi');

    } catch (error) {
      // Only log significant errors to avoid spam
      if (!error.message.includes('timeout') && !error.message.includes('AbortError')) {
        console.warn('⚠️ Frame fetch failed:', error.message);
        setStreamError(error.message);
      }
      
      // Clear stream image if persistent errors
      if (streamImage && error.message.includes('authentication')) {
        setStreamImage(null);
      }
    }
  }, [piState.activeSession, token, streamImage]);

  // === FRAME PROCESSING (SAME AS BEFORE) ===
  const handleFrameUpdate = useCallback((frameData) => {
    const now = Date.now();
    const latency = now - frameData.timestamp;

    // Drop old frames to prevent buffering
    if (latency > 2000) {
      console.warn('🗑️ Dropping old frame, latency:', latency + 'ms');
      return;
    }

    // Limit buffer size
    if (frameBuffer.current.length > 2) {
      frameBuffer.current = frameBuffer.current.slice(-1);
    }

    frameBuffer.current.push({ ...frameData, latency });
    processNextFrame();
  }, []);

  const processNextFrame = useCallback(() => {
    if (frameBuffer.current.length === 0) return;

    const frame = frameBuffer.current.shift();
    const now = Date.now();

    // Update image immediately
    setStreamImage(frame.image);
    setStreamError(null); // Clear error when frame received

    // Update stats less frequently
    if (now - lastFrameTime.current > 1000) {
      setFrameStats({
        fps: frame.stats.current_fps || 0,
        latency: frame.latency,
        persons: frame.stats.persons_detected || 0
      });
      lastFrameTime.current = now;
    }
  }, []);

  // === ENHANCED FRAME POLLING LIFECYCLE ===
  useEffect(() => {
    console.log('🎥 Video stream effect triggered:', {
      activeSession: !!piState.activeSession,
      isConnected: piState.isConnected,
      sessionId: piState.activeSession?.session_id
    });

    if (piState.activeSession && piState.isConnected) {
      console.log('🎥 Starting video frame polling...');
      
      // Start immediate fetch
      fetchVideoFrame();
      
      // Start interval polling
      framePollingRef.current = setInterval(fetchVideoFrame, PI_CONFIG.POLLING.FRAME_INTERVAL);
      
      return () => {
        if (framePollingRef.current) {
          console.log('🎥 Stopping video frame polling...');
          clearInterval(framePollingRef.current);
          framePollingRef.current = null;
        }
        frameBuffer.current = [];
      };
    } else {
      // Clear when no session or disconnected
      console.log('🎥 Clearing video stream - no active session or not connected');
      setStreamImage(null);
      setStreamError(null);
      frameBuffer.current = [];
    }
  }, [piState.activeSession, piState.isConnected, fetchVideoFrame]);

  // === NGROK AUTHENTICATION HELPER ===
  const authenticateNgrok = useCallback(() => {
    const directPiUrl = getPiUrl('video_stream');
    if (directPiUrl) {
      console.log('🌐 Opening ngrok URL for authentication:', directPiUrl);
      window.open(directPiUrl, '_blank');
      
      alert(`
Opening ngrok URL for authentication.

Steps:
1. Click "Visit Site" if prompted
2. Wait for the page to load completely
3. Close the tab and click "Retry" below

URL: ${directPiUrl}
      `);
    }
  }, []);

  const retryConnection = useCallback(() => {
    console.log('🔄 Retrying video connection...');
    setStreamError(null);
    setStreamImage(null);
    frameBuffer.current = [];
    
    // Force immediate frame fetch
    if (piState.activeSession && piState.isConnected) {
      fetchVideoFrame();
    }
  }, [piState.activeSession, piState.isConnected, fetchVideoFrame]);

  // === ENHANCED RENDER LOGIC ===
  const renderStreamContent = () => {
    // No session
    if (!piState.activeSession) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">📹</div>
          <p>Start a live session to view camera feed</p>
          <p style={{ fontSize: '14px', color: '#6c757d' }}>
            Camera will start automatically when session begins
          </p>
        </div>
      );
    }

    // Pi not connected
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
          <p style={{ fontSize: '14px', color: '#dc3545', marginBottom: '15px' }}>
            {piState.connectionError}
          </p>
          <button 
            className="retry-btn"
            onClick={retryConnection}
          >
            🔄 Retry Connection
          </button>
        </div>
      );
    }

    // Stream error (different from connection error)
    if (streamError && !streamImage) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">📡</div>
          <p>Video Stream Error</p>
          <p style={{ fontSize: '14px', color: '#dc3545', marginBottom: '15px' }}>
            {streamError}
          </p>
          <div className="error-actions">
            <button 
              className="retry-btn"
              onClick={retryConnection}
            >
              🔄 Retry Video Stream
            </button>
            
            {streamError.includes('ngrok') && (
              <button 
                className="auth-btn"
                onClick={authenticateNgrok}
                style={{ 
                  backgroundColor: '#007bff', 
                  color: 'white', 
                  border: 'none', 
                  padding: '8px 12px', 
                  borderRadius: '4px',
                  marginLeft: '10px'
                }}
              >
                🌐 Authenticate Ngrok
              </button>
            )}
          </div>
          
          <div className="debug-info" style={{ marginTop: '15px', fontSize: '12px', color: '#6c757d' }}>
            <details>
              <summary>Debug Info</summary>
              <p>Direct Pi URL: {isDirectPiAvailable() ? getPiUrl('video_stream') : 'Not configured'}</p>
              <p>Azure Pi Service: {getPiUrl('api')}</p>
              <p>Session ID: {piState.activeSession?.session_id}</p>
            </details>
          </div>
        </div>
      );
    }

    // Successfully showing video
    if (streamImage) {
      return (
        <div className="stream-content">
          <img 
            src={`data:image/jpeg;base64,${streamImage}`}
            alt="Live pose detection"
            className="live-stream"
            style={{ 
              display: 'block',
              width: '100%',
              height: 'auto',
              maxHeight: '500px',
              objectFit: 'contain',
              border: piState.isRecording ? '3px solid #dc3545' : '1px solid #dee2e6',
              borderRadius: '8px',
              boxShadow: piState.isRecording ? '0 0 20px rgba(220, 53, 69, 0.3)' : 'none'
            }}
            onError={() => {
              console.error('❌ Image load error');
              setStreamImage(null);
              setStreamError('Failed to load video frame');
            }}
          />
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
        </div>
      );
    }

    // Loading state
    return (
      <div className="stream-loading">
        <div className="loading-spinner"></div>
        <p>Starting camera feed...</p>
        <p style={{ fontSize: '14px', color: '#6c757d' }}>
          {isDirectPiAvailable() ? 
            `Connecting to: ${getPiUrl('video_stream')}` :
            'Using Azure Pi Service for video'
          }
        </p>
        <button 
          onClick={retryConnection}
          style={{
            marginTop: '10px',
            padding: '5px 10px',
            background: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          🔄 Force Retry
        </button>
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
            {piState.isConnected && streamImage && !streamError ? (
              <span className="live-indicator" style={{ color: '#28a745' }}>🔴 LIVE</span>
            ) : piState.isConnected && piState.activeSession ? (
              <span className="connecting-indicator" style={{ color: '#ffc107' }}>🔄 CONNECTING</span>
            ) : (
              <span className="offline-indicator" style={{ color: '#dc3545' }}>❌ OFFLINE</span>
            )}
          </div>
        )}
      </div>
      
      <div className="stream-container" style={{ position: 'relative' }}>
        {renderStreamContent()}
      </div>

      {/* Enhanced stream status */}
      {piState.activeSession && piState.isConnected && streamImage && !streamError && (
        <div className="stream-status">
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Source:</span>
              <span className="status-value success">
                {isDirectPiAvailable() ? '📡 Direct Pi' : '🔗 Azure API'}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">FPS:</span>
              <span className="status-value">{frameStats.fps || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Latency:</span>
              <span className={`status-value ${frameStats.latency > 500 ? 'warning' : 'success'}`}>
                {frameStats.latency || 0}ms
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Persons:</span>
              <span className="status-value">{frameStats.persons || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Recording:</span>
              <span className={`status-value ${piState.isRecording ? 'recording' : ''}`}>
                {piState.isRecording ? '🔴 Active' : '⚪ Stopped'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PiVideoStream;
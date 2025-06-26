// src/components/PiLive/PiVideoStream.js 
// CLEANED VERSION - Uses centralized state, removed redundant polling

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { PI_CONFIG, getPiUrl, isDirectPiAvailable } from '../../config/piConfig';

const PiVideoStream = ({ piState, token }) => {
  const [streamImage, setStreamImage] = useState(null);
  const [frameStats, setFrameStats] = useState({ fps: 0, latency: 0, persons: 0 });
  const framePollingRef = useRef(null);
  const frameBuffer = useRef([]);
  const lastFrameTime = useRef(0);

  // === FRAME FETCHING ===
  const fetchVideoFrame = useCallback(async () => {
    // Only fetch frames if we have direct Pi access and session is active
    if (!piState.activeSession || !isDirectPiAvailable()) {
      return;
    }

    try {
      const directPiUrl = getPiUrl('video_stream');
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
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Invalid response format');
      }

      const data = await response.json();

      if (data.success && data.image) {
        const frameData = {
          image: data.image,
          timestamp: data.timestamp || Date.now(),
          stats: data.stats || {},
          poseData: data.pose_data || [],
          isRecording: data.is_recording || false
        };

        handleFrameUpdate(frameData);
      } else if (data.error) {
        console.warn('⚠️ Pi frame error:', data.error);
      }

    } catch (error) {
      // Only log significant errors to avoid spam
      if (!error.message.includes('timeout') && !error.message.includes('AbortError')) {
        console.warn('⚠️ Frame fetch failed:', error.message);
      }
    }
  }, [piState.activeSession]);

  // === FRAME PROCESSING ===
  const handleFrameUpdate = useCallback((frameData) => {
    const now = Date.now();
    const latency = now - frameData.timestamp;

    // Drop old frames to prevent buffering
    if (latency > 1000) {
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

  // === FRAME POLLING LIFECYCLE ===
  useEffect(() => {
    if (piState.activeSession && piState.isConnected && isDirectPiAvailable()) {
      console.log('🎥 Starting video frame polling...');
      
      // Start frame polling
      framePollingRef.current = setInterval(fetchVideoFrame, PI_CONFIG.POLLING.FRAME_INTERVAL);
      
      return () => {
        if (framePollingRef.current) {
          console.log('🎥 Stopping video frame polling...');
          clearInterval(framePollingRef.current);
          framePollingRef.current = null;
        }
        frameBuffer.current = [];
        setStreamImage(null);
      };
    } else {
      // Clear frame when no session
      setStreamImage(null);
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
            2. Wait for the page to load
            3. Close the tab and retry connection

            URL: ${directPiUrl}
                  `);
                }
              }, []);

  // === RENDER LOGIC ===
  const renderStreamContent = () => {
    if (!piState.activeSession) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">📹</div>
          <p>Start a live session to view camera feed</p>
        </div>
      );
    }

    if (piState.connectionError) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">⚠️</div>
          <p>Connection Error</p>
          <p style={{ fontSize: '14px', color: '#dc3545', marginBottom: '15px' }}>
            {piState.connectionError}
          </p>
          <div className="error-actions">
            <button 
              className="retry-btn"
              onClick={() => window.location.reload()}
            >
              🔄 Retry Connection
            </button>
            
            {isDirectPiAvailable() && (
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
          
          {!isDirectPiAvailable() && (
            <div className="setup-notice">
              <p><strong>Direct video streaming not configured</strong></p>
              <p>Add REACT_APP_DIRECT_PI_URL to your .env file</p>
            </div>
          )}
        </div>
      );
    }

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
          />
          {piState.isRecording && (
            <div className="recording-overlay">
              <span className="recording-indicator">🔴 RECORDING</span>
            </div>
          )}
        </div>
      );
    }

    if (piState.activeSession && !piState.isConnected) {
      return (
        <div className="stream-loading">
          <div className="loading-spinner"></div>
          <p>Connecting to Pi camera...</p>
          <p style={{ fontSize: '14px', color: '#6c757d' }}>
            {isDirectPiAvailable() ? 
              `Connecting to: ${getPiUrl('video_stream')}` :
              'Direct video streaming not configured'
            }
          </p>
        </div>
      );
    }

    return (
      <div className="stream-loading">
        <div className="loading-spinner"></div>
        <p>Waiting for video stream...</p>
        <p style={{ fontSize: '14px', color: '#6c757d' }}>
          Session active, connecting to camera feed...
        </p>
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
              Session: {piState.activeSession.session_id?.substring(5, 13) || 'Unknown'}
            </span>
            {piState.isConnected && streamImage ? (
              <span className="live-indicator">🔴 LIVE</span>
            ) : (
              <span className="connecting-indicator">🔄 CONNECTING</span>
            )}
          </div>
        )}
      </div>
      
      <div className="stream-container">
        {renderStreamContent()}
      </div>

      {/* Stream status - only show when active and connected */}
      {piState.activeSession && piState.isConnected && streamImage && (
        <div className="stream-status">
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Source:</span>
              <span className="status-value success">
                {isDirectPiAvailable() ? '📡 Direct' : '🔗 Via API'}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">FPS:</span>
              <span className="status-value">{frameStats.fps || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Latency:</span>
              <span className={`status-value ${frameStats.latency > 300 ? 'warning' : 'success'}`}>
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
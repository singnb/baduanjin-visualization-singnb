// src/components/PiLive/PiVideoStream.js 
import React, { useEffect, useRef, useState, useCallback } from 'react';
import io from 'socket.io-client';

const PiVideoStream = ({ activeSession, poseData, isConnected, token }) => {
  const [socket, setSocket] = useState(null);
  const [streamImage, setStreamImage] = useState(null);
  const [connectionError, setConnectionError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [streamStats, setStreamStats] = useState({ fps: 0, latency: 0, persons: 0 });
  const [isRecording, setIsRecording] = useState(false);
  const videoRef = useRef(null);
  const lastFrameTime = useRef(0);
  const frameBuffer = useRef([]);

  // Optimized frame handler with frame dropping
  const handleFrameUpdate = useCallback((data) => {
    const now = Date.now();
    const frameTimestamp = data.timestamp || now;
    
    // Calculate latency
    const latency = now - frameTimestamp;
    
    // Drop old frames to reduce buffering delay (be more lenient)
    if (latency > 1000) { // Drop frames older than 1 second
      console.warn(`⚠️ Dropping old frame, latency: ${latency}ms`);
      return;
    }
    
    // Clear frame buffer if it's getting too long
    if (frameBuffer.current.length > 3) {
      frameBuffer.current = frameBuffer.current.slice(-1); // Keep only latest frame
    }
    
    // Add frame to buffer
    frameBuffer.current.push({
      image: data.image,
      stats: data.stats || {},
      poseData: data.pose_data || [],
      isRecording: data.is_recording || false,
      timestamp: frameTimestamp,
      latency: latency
    });
    
    // Process next frame
    processNextFrame();
  }, []);

  const processNextFrame = useCallback(() => {
    if (frameBuffer.current.length === 0) return;
    
    const frame = frameBuffer.current.shift();
    const now = Date.now();
    
    // Update stream image immediately
    setStreamImage(frame.image);
    setIsRecording(frame.isRecording);
    
    // Update stats less frequently to avoid excessive re-renders
    if (now - lastFrameTime.current > 500) { // Update every 500ms
      setStreamStats({
        fps: frame.stats.current_fps || 0,
        latency: frame.latency,
        persons: frame.stats.persons_detected || 0
      });
      lastFrameTime.current = now;
    }
  }, []);

  useEffect(() => {
    if (activeSession && isConnected) {
      let newSocket = null;
      let httpPolling = null;
      
      try {
        const NGROK_URL = 'https://fbad-122-11-245-27.ngrok-free.app';
        console.log(`🔗 Attempting WebSocket connection to ${NGROK_URL}...`);
        
        // Try WebSocket first
        newSocket = io(NGROK_URL, {
          transports: ['polling', 'websocket'],
          timeout: 10000,
          forceNew: true,
          autoConnect: true,
          secure: true
        });
        
        // WebSocket success
        newSocket.on('connect', () => {
          console.log('✅ WebSocket connected successfully');
          setWsConnected(true);
          setConnectionError(null);
          frameBuffer.current = [];
        });

        // WebSocket frame updates
        newSocket.on('frame_update', handleFrameUpdate);
        
        // WebSocket error - switch to HTTP polling
        newSocket.on('connect_error', (error) => {
          console.error('🔴 WebSocket failed, switching to HTTP polling:', error);
          
          // Disconnect WebSocket
          if (newSocket) {
            newSocket.disconnect();
            newSocket = null;
          }
          
          // Start HTTP polling fallback
          startHttpPolling(NGROK_URL);
        });
        
        setSocket(newSocket);
        
      } catch (error) {
        console.error('🔴 WebSocket setup failed, using HTTP polling:', error);
        startHttpPolling('https://25de-122-11-245-27.ngrok-free.app');
      }
      
      // HTTP Polling Fallback Function
      function startHttpPolling(baseUrl) {
        console.log('🔄 Starting HTTP polling for frames...');
        setConnectionError('Using HTTP polling (WebSocket unavailable)');
        
        httpPolling = setInterval(async () => {
          try {
            const response = await fetch(`${baseUrl}/api/current_frame`);
            const data = await response.json();
            
            if (data.success && data.image) {
              // Simulate WebSocket frame data structure
              const frameData = {
                image: data.image,
                pose_data: data.pose_data || [],
                stats: data.stats || {},
                timestamp: data.timestamp || Date.now()
              };
              
              handleFrameUpdate(frameData);
              setWsConnected(true);
              setConnectionError(null);
              
            } else if (data.error) {
              console.warn('HTTP polling error:', data.error);
              setConnectionError(`HTTP polling: ${data.error}`);
              setWsConnected(false);
            }
            
          } catch (error) {
            console.warn('HTTP polling failed:', error);
            setConnectionError('HTTP polling connection failed');
            setWsConnected(false);
          }
        }, 200); // Poll every 200ms (5 FPS)
      }
      
      // Cleanup function
      return () => {
        if (newSocket) {
          console.log('🔌 Disconnecting WebSocket');
          newSocket.disconnect();
        }
        if (httpPolling) {
          console.log('🔌 Stopping HTTP polling');
          clearInterval(httpPolling);
        }
        frameBuffer.current = [];
      };
      
    } else {
      // Clean up when session ends
      if (socket) {
        socket.disconnect();
        setSocket(null);
      }
      setStreamImage(null);
      setWsConnected(false);
      setConnectionError(null);
      setIsRecording(false);
      frameBuffer.current = [];
    }
  }, [activeSession, isConnected, handleFrameUpdate]);

  const testDirectConnection = useCallback(async () => {
    try {
      console.log('🧪 Testing Pi connection via Azure service...');
      
      // FIXED: Test through Azure pi-service instead of direct Pi connection
      const response = await fetch('https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net/api/pi-live/status', {
        headers: {
          'Authorization': `Bearer ${token}` // You'll need to pass token as prop
        }
      });
      
      const data = await response.json();
      console.log('✅ Pi status via Azure:', data);
      
      if (data.pi_connected && data.is_running) {
        console.log('✅ Pi is connected and running, WebSocket should work');
        // Try to reconnect
        if (socket) {
          socket.connect();
        }
      } else if (data.pi_connected && !data.is_running) {
        console.log('⚠️ Pi is connected but not running streaming');
        setConnectionError('Pi is connected but streaming is not active');
      } else {
        console.log('❌ Pi is not connected');
        setConnectionError('Pi is not connected to Azure service');
      }
    } catch (error) {
      console.error('❌ Pi connection test failed:', error);
      setConnectionError('Cannot reach Pi through Azure service');
    }
  }, [socket]);

  const renderStreamContent = () => {
    if (!activeSession) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">📹</div>
          <p>Start a live session to view camera feed</p>
        </div>
      );
    }

    if (connectionError) {
      return (
        <div className="stream-placeholder">
          <div className="placeholder-icon">⚠️</div>
          <p>Video Stream Connection Error</p>
          <p style={{ fontSize: '14px', color: '#dc3545', marginBottom: '15px' }}>
            {connectionError}
          </p>
          <div className="error-actions">
            <button 
              className="retry-btn"
              onClick={() => {
                setConnectionError(null);
                frameBuffer.current = [];
                if (socket) {
                  socket.connect();
                }
              }}
            >
              🔄 Retry Connection
            </button>
            <button 
              className="test-btn"
              onClick={testDirectConnection}
            >
              🧪 Test Pi Connection
            </button>
          </div>
          <div className="troubleshooting">
            <details>
              <summary>Troubleshooting Tips</summary>
              <ul>
                <li>Check if Pi server is running at 172.20.10.5:5001</li>
                <li>Verify network connection to Pi</li>
                <li>Try refreshing the page</li>
                <li>Check browser console for more details</li>
              </ul>
            </details>
          </div>
        </div>
      );
    }

    if (streamImage) {
      return (
        <div className="stream-content">
          <img 
            ref={videoRef}
            src={`data:image/jpeg;base64,${streamImage}`}
            alt="Live pose detection"
            className="live-stream"
            style={{ 
              display: 'block',
              width: '100%',
              height: 'auto',
              maxHeight: '500px',
              objectFit: 'contain',
              border: isRecording ? '3px solid #dc3545' : '1px solid #dee2e6',
              borderRadius: '8px',
              boxShadow: isRecording ? '0 0 20px rgba(220, 53, 69, 0.3)' : 'none'
            }}
          />
          {isRecording && (
            <div className="recording-overlay">
              <span className="recording-indicator">🔴 RECORDING</span>
            </div>
          )}
        </div>
      );
    }

    if (activeSession && !wsConnected) {
      return (
        <div className="stream-loading">
          <div className="loading-spinner"></div>
          <p>Connecting to Pi camera...</p>
          <p style={{ fontSize: '14px', color: '#6c757d' }}>
            Attempting Socket.IO connection with fallback...
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
        {activeSession && (
          <div className="session-info">
            <span className="session-id">
              Session: {activeSession.session_id?.substring(5, 13) || 'Unknown'}
            </span>
            {wsConnected ? (
              <span className="live-indicator">
                🔴 LIVE
                {socket && (
                  <span className="transport-info">
                    ({socket.io.engine.transport.name})
                  </span>
                )}
              </span>
            ) : (
              <span className="connecting-indicator">🔄 CONNECTING</span>
            )}
          </div>
        )}
      </div>
      
      <div className="stream-container">
        {renderStreamContent()}
      </div>

      {/* Enhanced stream status with performance metrics */}
      {activeSession && wsConnected && (
        <div className="stream-status">
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Connection:</span>
              <span className="status-value success">
                ✅ {socket?.io.engine.transport.name || 'Connected'}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">FPS:</span>
              <span className="status-value">{streamStats.fps || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Latency:</span>
              <span className={`status-value ${streamStats.latency > 300 ? 'warning' : 'success'}`}>
                {streamStats.latency || 0}ms
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Persons:</span>
              <span className="status-value">{streamStats.persons || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Buffer:</span>
              <span className="status-value">{frameBuffer.current.length}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Recording:</span>
              <span className={`status-value ${isRecording ? 'recording' : ''}`}>
                {isRecording ? '🔴 Active' : '⚪ Stopped'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PiVideoStream;
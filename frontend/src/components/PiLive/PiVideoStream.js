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

  // Update your ngrok URL here when it changes
  const NGROK_URL = 'https://mongoose-hardy-caiman.ngrok-free.app';

  // Optimized frame handler with frame dropping
  const handleFrameUpdate = useCallback((data) => {
    const now = Date.now();
    const frameTimestamp = data.timestamp || now;
    
    // Calculate latency
    const latency = now - frameTimestamp;
    
    // Drop old frames to reduce buffering delay
    if (latency > 1000) {
      console.warn(`⚠️ Dropping old frame, latency: ${latency}ms`);
      return;
    }
    
    // Clear frame buffer if it's getting too long
    if (frameBuffer.current.length > 3) {
      frameBuffer.current = frameBuffer.current.slice(-1);
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
    if (now - lastFrameTime.current > 500) {
      setStreamStats({
        fps: frame.stats.current_fps || 0,
        latency: frame.latency,
        persons: frame.stats.persons_detected || 0
      });
      lastFrameTime.current = now;
    }
  }, []);

  // Test ngrok authentication
  const testNgrokAuthentication = useCallback(async () => {
    try {
      console.log('🧪 Testing ngrok authentication...');
      
      const response = await fetch(NGROK_URL, {
        method: 'GET',
        headers: {
          'ngrok-skip-browser-warning': 'true', // This header skips ngrok warning
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        },
        mode: 'cors'
      });
      
      const text = await response.text();
      console.log('🧪 Ngrok response:', text.substring(0, 200));
      
      if (text.includes('ngrok') && text.includes('Visit Site')) {
        return false; // Needs authentication
      }
      return true; // Already authenticated
    } catch (error) {
      console.error('🧪 Ngrok test failed:', error);
      return false;
    }
  }, []);

  // Enhanced HTTP polling with ngrok handling
  const startHttpPolling = useCallback((baseUrl) => {
    console.log('🔄 Starting HTTP polling for frames...');
    
    const httpPolling = setInterval(async () => {
      try {
        console.log(`📡 Polling: ${baseUrl}/api/current_frame`);
        
        const response = await fetch(`${baseUrl}/api/current_frame`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true', // Skip ngrok warning page
            'Origin': window.location.origin
          },
          mode: 'cors'
        });
        
        console.log(`📊 Response status: ${response.status}`);
        
        const contentType = response.headers.get('content-type');
        console.log(`📊 Content-Type: ${contentType}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`❌ HTTP ${response.status}:`, errorText.substring(0, 200));
          
          // Check for specific ngrok errors
          if (errorText.includes('ngrok') && errorText.includes('Visit Site')) {
            setConnectionError('Ngrok authentication required. Click "Authenticate Ngrok" below.');
          } else if (response.status === 404) {
            setConnectionError('Pi server endpoint not found. Check if web_server.py is running.');
          } else {
            setConnectionError(`HTTP ${response.status}: ${errorText.substring(0, 100)}`);
          }
          setWsConnected(false);
          return;
        }
        
        if (!contentType || !contentType.includes('application/json')) {
          const htmlContent = await response.text();
          console.error('❌ Received HTML instead of JSON:', htmlContent.substring(0, 500));
          
          // Enhanced ngrok detection
          if (htmlContent.includes('ngrok')) {
            if (htmlContent.includes('Visit Site') || htmlContent.includes('only for legitimate traffic')) {
              setConnectionError('Ngrok requires browser authentication. Click "Authenticate Ngrok" below.');
            } else if (htmlContent.includes('Tunnel not found')) {
              setConnectionError('Ngrok tunnel not found. Please check your ngrok URL.');
            } else {
              setConnectionError('Ngrok issue detected. Try authenticating in browser first.');
            }
          } else if (htmlContent.includes('CORS')) {
            setConnectionError('CORS error - Pi server not accepting requests from this domain');
          } else {
            setConnectionError(`Received HTML instead of JSON. Check if Pi server is running correctly.`);
          }
          setWsConnected(false);
          return;
        }
        
        const data = await response.json();
        console.log('📦 Parsed JSON data keys:', Object.keys(data));
        
        if (data.success && data.image) {
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
          setConnectionError(`Pi server error: ${data.error}`);
          setWsConnected(false);
        } else {
          console.warn('Unexpected response format:', data);
          setConnectionError('Unexpected response format from Pi server');
          setWsConnected(false);
        }
        
      } catch (error) {
        console.error('HTTP polling failed:', error);
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
          setConnectionError('Network error: Cannot reach Pi server. Check ngrok tunnel.');
        } else {
          setConnectionError(`HTTP polling failed: ${error.message}`);
        }
        setWsConnected(false);
      }
    }, 2000); // Poll every 2 seconds
    
    return httpPolling;
  }, [handleFrameUpdate]);

  useEffect(() => {
    console.log('🔍 PiVideoStream useEffect triggered:', {
      activeSession: !!activeSession,
      isConnected,
      sessionId: activeSession?.session_id
    });

    if (activeSession && isConnected) {
      console.log('🚀 Starting video stream for session:', activeSession.session_id);
      
      const NGROK_URL = 'https://mongoose-hardy-caiman.ngrok-free.app';
      console.log('🔗 Using ngrok URL:', NGROK_URL);
      
      // SKIP WEBSOCKET ENTIRELY - Go straight to HTTP polling for ngrok compatibility
      console.log('🔄 Starting HTTP polling immediately (WebSocket disabled for ngrok)');
      
      let httpPolling = null;
      
      const startPolling = () => {
        httpPolling = setInterval(async () => {
          try {
            const url = `${NGROK_URL}/api/current_frame`;
            
            const response = await fetch(url, {
              method: 'GET',
              headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true',
                'Origin': window.location.origin
              },
              mode: 'cors'
            });
            
            if (!response.ok) {
              const errorText = await response.text();
              console.error(`❌ HTTP ${response.status}:`, errorText.substring(0, 200));
              setConnectionError(`HTTP ${response.status}: ${errorText.substring(0, 100)}`);
              setWsConnected(false);
              return;
            }
            
            const contentType = response.headers.get('content-type');
            
            if (!contentType || !contentType.includes('application/json')) {
              const htmlContent = await response.text();
              console.error('❌ Received HTML instead of JSON:', htmlContent.substring(0, 200));
              setConnectionError('Received HTML instead of JSON');
              setWsConnected(false);
              return;
            }
            
            const data = await response.json();
            
            if (data.success && data.image) {
              console.log('✅ Frame received:', {
                imageSize: data.image.length,
                poseCount: data.pose_data?.length || 0,
                isRecording: data.is_recording
              });
              
              const frameData = {
                image: data.image,
                pose_data: data.pose_data || [],
                stats: data.stats || {},
                is_recording: data.is_recording || false,
                timestamp: data.timestamp || Date.now()
              };
              
              handleFrameUpdate(frameData);
              setWsConnected(true);  // Use this to indicate "connected"
              setConnectionError(null);
              
            } else if (data.error) {
              console.warn('⚠️ Pi server error:', data.error);
              if (data.error.includes('No active stream')) {
                setConnectionError('Waiting for camera to start...');
              } else {
                setConnectionError(`Pi server: ${data.error}`);
              }
              setWsConnected(false);
            } else {
              console.warn('⚠️ Unexpected response:', data);
              setConnectionError('Unexpected response from Pi');
              setWsConnected(false);
            }
            
          } catch (error) {
            console.error('❌ HTTP polling failed:', error);
            setConnectionError(`Network error: ${error.message}`);
            setWsConnected(false);
          }
        }, 2000); // Poll every 2 seconds
      };
      
      // Start polling immediately
      startPolling();
      
      // Set initial state
      setWsConnected(false); // Will be set to true when first frame arrives
      setConnectionError('Connecting to camera...');
      
      // Cleanup function
      return () => {
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

  // Open ngrok URL in new tab for authentication
  const authenticateNgrok = useCallback(() => {
    const authUrl = NGROK_URL;
    console.log('🌐 Opening ngrok URL for authentication:', authUrl);
    window.open(authUrl, '_blank');
    
    // Provide instructions
    alert(`
Opening ngrok URL in new tab for authentication.

After the page loads:
1. Click "Visit Site" if prompted
2. You may see a warning page - this is normal for ngrok free tier
3. Wait for the page to load completely
4. Close the tab and click "Retry Connection" below

The ngrok URL is: ${authUrl}
    `);
  }, []);

  const testDirectConnection = useCallback(async () => {
    try {
      console.log('🧪 Testing Pi connection via Azure service...');
      
      const response = await fetch('https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net/api/pi-live/status', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      console.log('✅ Pi status via Azure:', data);
      
      if (data.pi_connected && data.is_running) {
        console.log('✅ Pi is connected and running, testing ngrok authentication...');
        const ngrokAuthenticated = await testNgrokAuthentication();
        
        if (ngrokAuthenticated) {
          console.log('✅ Ngrok is authenticated, trying to reconnect...');
          if (socket) {
            socket.connect();
          } else {
            // Force a reconnection attempt
            window.location.reload();
          }
        } else {
          setConnectionError('Ngrok authentication required. Click "Authenticate Ngrok" below.');
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
  }, [socket, testNgrokAuthentication, token]);

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
                } else {
                  // Force component re-mount to retry connection
                  window.location.reload();
                }
              }}
            >
              🔄 Retry Connection
            </button>
            
            {connectionError.includes('ngrok') && (
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
            
            <button 
              className="test-btn"
              onClick={testDirectConnection}
            >
              🧪 Test Pi Connection
            </button>
          </div>
          
          <div className="troubleshooting">
            <details>
              <summary>Troubleshooting Steps</summary>
              <ol style={{ textAlign: 'left', fontSize: '13px' }}>
                <li><strong>Ngrok Authentication:</strong> Click "Authenticate Ngrok" button above</li>
                <li><strong>Check Pi Server:</strong> Ensure web_server.py is running on Pi</li>
                <li><strong>Update Ngrok URL:</strong> Ngrok URLs change frequently on free tier</li>
                <li><strong>Network Check:</strong> Verify Pi can reach internet</li>
                <li><strong>Firewall:</strong> Check if ports 5001 are open</li>
              </ol>
              
              <div style={{ marginTop: '10px', padding: '8px', backgroundColor: '#f8f9fa' }}>
                <strong>Current Ngrok URL:</strong><br />
                <code style={{ fontSize: '12px' }}>{NGROK_URL}</code><br />
                <small>Update this URL in the code if it has changed</small>
              </div>
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
            Attempting connection to: {NGROK_URL}
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
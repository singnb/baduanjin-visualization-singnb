// src/components/Layout/PiVideoTransfer.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import { PI_CONFIG, getPiUrl } from '../../config/piConfig';
import './Layout.css';

// FIXED: Use main backend for video storage (same as VideoUpload.js)
const MAIN_BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';
const PI_SERVICE_URL = 'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net';

const PiVideoTransfer = ({ onTransferComplete }) => {
  const [piRecordings, setPiRecordings] = useState([]);
  const [piStatus, setPiStatus] = useState('unknown');
  const [loading, setLoading] = useState(false);
  const [transferStatus, setTransferStatus] = useState({});
  const [error, setError] = useState(null);
  const { token } = useAuth();

  // Transfer form state
  const [transferForm, setTransferForm] = useState({
    title: '',
    description: '',
    brocadeType: 'FIRST' // Changed from LIVE_SESSION to match main backend
  });

  useEffect(() => {
    loadPiRecordings();
    checkPiStatus();
  }, []);

  // === Get recordings list from Pi Service (this stays the same) ===
  const loadPiRecordings = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Use pi-service for getting recordings list
      const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/recordings`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
      });
      
      const data = response.data;
      
      if (data.success) {
        setPiRecordings(data.recordings || []);
        setPiStatus('connected');
      } else {
        setError(data.message || 'Failed to load recordings');
        setPiStatus('error');
      }
      
    } catch (err) {
      console.error('Error loading Pi recordings:', err);
      setError('Failed to connect to Pi service: ' + err.message);
      setPiStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const checkPiStatus = async () => {
    try {
      // Use pi-service for status check
      const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/status`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        timeout: PI_CONFIG.TIMEOUTS.STATUS_CHECK
      });
      
      const data = response.data;
      setPiStatus(data.pi_connected ? 'connected' : 'disconnected');
      
    } catch (err) {
      setPiStatus('error');
    }
  };

  // === FIXED: Transfer to main backend instead of pi-service ===
  const handleTransfer = async (recording) => {
    // Determine the filename for transfer
    let filename;
    if (recording.files && recording.files.original) {
      filename = recording.files.original.filename;
    } else if (recording.filename) {
      filename = recording.filename;
    } else if (recording.timestamp) {
      filename = `baduanjin_original_${recording.timestamp}.mp4`;
    } else {
      setError('Cannot determine filename for transfer');
      return;
    }
    
    const recordingId = recording.timestamp || recording.filename || recording.id;
    const title = transferForm.title || `Pi Session ${recordingId}`;
    const description = transferForm.description || `Baduanjin practice session from Pi`;
    
    setTransferStatus(prev => ({ ...prev, [recordingId]: 'transferring' }));
    setError(null);

    try {
      console.log('📤 Starting transfer to MAIN BACKEND for:', filename);
      
      // FIXED: Send transfer request to main backend
      const transferData = {
        pi_filename: filename,
        title: title,
        description: description,
        brocade_type: transferForm.brocadeType,
        source: 'pi_transfer',
        pi_recording_data: recording // Include full recording metadata
      };

      console.log('📤 Transfer data:', transferData);
      
      const response = await axios.post(
        `${MAIN_BACKEND_URL}/api/videos/pi-transfer-requests`, // Note: different endpoint
        transferData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 600000
        }
      );

      console.log('📤 Main backend transfer response:', response.data);

      // Check if transfer started successfully
      if (response.data.success || response.data.status === 'success') {
        // For main backend, we can assume it's completed immediately
        // since it handles the Pi download internally
        setTransferStatus(prev => ({ ...prev, [recordingId]: 'completed' }));
        
        // Remove from Pi recordings list
        setPiRecordings(prev => prev.filter(r => 
          r.timestamp !== recordingId && 
          r.filename !== recordingId && 
          r.id !== recordingId
        ));
        
        if (onTransferComplete) {
          onTransferComplete(response.data);
        }

        alert(`Transfer completed successfully!\nFile: ${filename}\nSaved to main backend storage`);
        
      } else {
        throw new Error(response.data.message || response.data.detail || 'Transfer failed to start');
      }
      
    } catch (err) {
      console.error('Transfer error:', err);
      setTransferStatus(prev => ({ ...prev, [recordingId]: 'failed' }));
      
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message || 
                          err.message || 
                          'Transfer failed';
      
      setError(`Transfer failed for ${filename}: ${errorMessage}`);
      
      // Show more specific error information
      if (err.response?.status === 404) {
        setError(`Transfer endpoint not found on main backend. Please check if /api/videos/pi-transfer exists.`);
      } else if (err.response?.status === 500) {
        setError(`Main backend error during transfer. Check backend logs for details.`);
      }
    }
  };

  // === ALTERNATIVE: Direct file transfer method ===
  const handleDirectTransfer = async (recording) => {
    // Alternative approach: Download from Pi and upload to main backend
    let filename;
    if (recording.files && recording.files.original) {
      filename = recording.files.original.filename;
    } else if (recording.filename) {
      filename = recording.filename;
    } else if (recording.timestamp) {
      filename = `baduanjin_original_${recording.timestamp}.mp4`;
    } else {
      setError('Cannot determine filename for transfer');
      return;
    }
    
    const recordingId = recording.timestamp || recording.filename || recording.id;
    const title = transferForm.title || `Pi Session ${recordingId}`;
    const description = transferForm.description || `Baduanjin practice session from Pi`;
    
    setTransferStatus(prev => ({ ...prev, [recordingId]: 'transferring' }));
    setError(null);

    try {
      console.log('📤 Starting direct transfer for:', filename);
      
      // Step 1: Download file from Pi via pi-service
      console.log('📥 Step 1: Downloading from Pi...');
      const downloadResponse = await axios.get(
        `${PI_SERVICE_URL}/api/pi-live/download-video/${encodeURIComponent(filename)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          responseType: 'blob', // Important for video files
          timeout: 300000 // 5 minutes
        }
      );

      console.log('📥 Downloaded video blob, size:', downloadResponse.data.size);

      // Step 2: Upload to main backend like regular file upload
      console.log('📤 Step 2: Uploading to main backend...');
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);
      formData.append('brocade_type', transferForm.brocadeType);
      formData.append('file', downloadResponse.data, filename);
      formData.append('source', 'pi_transfer');

      const uploadResponse = await axios.post(
        `${MAIN_BACKEND_URL}/api/videos/upload`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`
            // Don't set Content-Type, let browser set it for FormData
          },
          timeout: 600000 // 10 minutes
        }
      );

      console.log('📤 Upload complete:', uploadResponse.data);

      // Success
      setTransferStatus(prev => ({ ...prev, [recordingId]: 'completed' }));
      
      // Remove from Pi recordings list
      setPiRecordings(prev => prev.filter(r => 
        r.timestamp !== recordingId && 
        r.filename !== recordingId && 
        r.id !== recordingId
      ));
      
      if (onTransferComplete) {
        onTransferComplete(uploadResponse.data);
      }

      alert(`Direct transfer completed!\nFile: ${filename}\nUploaded to main backend storage`);
      
    } catch (err) {
      console.error('Direct transfer error:', err);
      setTransferStatus(prev => ({ ...prev, [recordingId]: 'failed' }));
      
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message || 
                          err.message || 
                          'Direct transfer failed';
      
      setError(`Direct transfer failed for ${filename}: ${errorMessage}`);
    }
  };

  // === Test Pi connection ===
  const testPiConnection = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/test-pi-connection`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        timeout: PI_CONFIG.TIMEOUTS.STATUS_CHECK
      });
      
      const data = response.data;
      setPiStatus(data.pi_connected ? 'connected' : 'disconnected');
      
      if (data.pi_connected) {
        alert('Pi connection test successful!');
        loadPiRecordings();
      } else {
        alert(`Pi connection failed: ${data.message || 'Unknown error'}`);
      }
    } catch (err) {
      setPiStatus('error');
      alert(`Pi connection test failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // === Test main backend connection ===
  const testMainBackendConnection = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${MAIN_BACKEND_URL}/api/videos/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        timeout: 10000
      });
      
      alert('Main backend connection successful!');
      console.log('Main backend response:', response.data);
    } catch (err) {
      alert(`Main backend connection failed: ${err.message}`);
      console.error('Main backend error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  };

  const formatTimestamp = (timestamp) => {
    if (timestamp && timestamp.length === 15) { // YYYYMMDD_HHMMSS
      const date = timestamp.substring(0, 8);
      const time = timestamp.substring(9);
      return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)} ${time.substring(0, 2)}:${time.substring(2, 4)}:${time.substring(4, 6)}`;
    }
    return timestamp || 'Unknown';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return '#28a745';
      case 'disconnected': return '#dc3545';
      case 'error': return '#dc3545';
      default: return '#6c757d';
    }
  };

  return (
    <div className="pi-video-transfer-container">
      <div className="section-header">
        <h2>Pi Video Transfer</h2>
        <div className="backend-info">
          <div className="pi-status" style={{ color: getStatusColor(piStatus) }}>
            Pi Status: {piStatus === 'connected' ? '✅ Connected' : 
                       piStatus === 'disconnected' ? '❌ Disconnected' : 
                       piStatus === 'error' ? '❌ Error' : '⏳ Checking...'}
          </div>
          <div className="backend-url" style={{ fontSize: '12px', color: '#6c757d' }}>
            Transfers to: {MAIN_BACKEND_URL}
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="transfer-controls">
        <button 
          onClick={loadPiRecordings} 
          disabled={loading}
          className="refresh-btn"
        >
          {loading ? 'Loading...' : 'Refresh Pi Recordings'}
        </button>
        
        <button 
          onClick={testPiConnection} 
          disabled={loading}
          className="test-connection-btn"
          style={{
            background: '#17a2b8',
            color: 'white',
            border: 'none',
            padding: '8px 15px',
            borderRadius: '4px',
            cursor: 'pointer',
            marginLeft: '10px'
          }}
        >
          {loading ? 'Testing...' : 'Test Pi Connection'}
        </button>

        <button 
          onClick={testMainBackendConnection} 
          disabled={loading}
          className="test-backend-btn"
          style={{
            background: '#28a745',
            color: 'white',
            border: 'none',
            padding: '8px 15px',
            borderRadius: '4px',
            cursor: 'pointer',
            marginLeft: '10px'
          }}
        >
          {loading ? 'Testing...' : 'Test Main Backend'}
        </button>
      </div>

      {/* Transfer Settings */}
      <div className="transfer-settings">
        <h3>Transfer Settings</h3>
        <div className="form-row">
          <div className="form-group">
            <label>Default Title Prefix</label>
            <input
              type="text"
              value={transferForm.title}
              onChange={(e) => setTransferForm(prev => ({ ...prev, title: e.target.value }))}
              placeholder="e.g., Morning Practice"
            />
          </div>
          <div className="form-group">
            <label>Brocade Type</label>
            <select
              value={transferForm.brocadeType}
              onChange={(e) => setTransferForm(prev => ({ ...prev, brocadeType: e.target.value }))}
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
        </div>
        <div className="form-group">
          <label>Description Template</label>
          <textarea
            value={transferForm.description}
            onChange={(e) => setTransferForm(prev => ({ ...prev, description: e.target.value }))}
            placeholder="Optional description template for all transfers"
          />
        </div>
      </div>

      {/* Pi Recordings List */}
      <div className="recordings-section">
        <h3>Available on Pi ({piRecordings.length})</h3>
        
        {loading ? (
          <div className="loading-message">Loading Pi recordings...</div>
        ) : piRecordings.length === 0 ? (
          <div className="no-recordings">
            {piStatus === 'connected' ? 
              'No recordings available on Pi' : 
              'Cannot connect to Pi to check recordings'
            }
          </div>
        ) : (
          <div className="recordings-grid">
            {piRecordings.map((recording) => {
              const recordingId = recording.timestamp || recording.filename || recording.id || Math.random();
              const displayName = recording.title || 
                                 recording.timestamp || 
                                 recording.filename || 
                                 `Recording ${recordingId}`;
              
              return (
                <div key={recordingId} className="recording-card">
                  <div className="recording-header">
                    <h4>{displayName}</h4>
                    {recording.timestamp && (
                      <div className="recording-time">
                        {formatTimestamp(recording.timestamp)}
                      </div>
                    )}
                    {recording.created && (
                      <div className="recording-time">
                        Created: {new Date(recording.created).toLocaleString()}
                      </div>
                    )}
                  </div>

                  <div className="recording-info">
                    <div className="info-row">
                      <span>Files:</span>
                      <span>{recording.file_count || Object.keys(recording.files || {}).length || 1}</span>
                    </div>
                    <div className="info-row">
                      <span>Total Size:</span>
                      <span>{formatFileSize(recording.total_size || recording.size || 0)}</span>
                    </div>
                    {recording.processing_status && (
                      <div className="info-row">
                        <span>Status:</span>
                        <span>{recording.processing_status}</span>
                      </div>
                    )}
                  </div>

                  {/* File Details */}
                  <div className="file-details">
                    {recording.files ? (
                      Object.entries(recording.files).map(([type, file]) => (
                        <div key={type} className="file-item">
                          <span className="file-type">{type}:</span>
                          <span className="file-size">{formatFileSize(file.size)}</span>
                          <span className="file-desc">{file.description}</span>
                        </div>
                      ))
                    ) : (
                      <div className="file-item">
                        <span className="file-type">File:</span>
                        <span className="file-size">{formatFileSize(recording.size || 0)}</span>
                        <span className="file-desc">{recording.filename || 'Video file'}</span>
                      </div>
                    )}
                  </div>

                  {/* Transfer Controls */}
                  <div className="transfer-controls">
                    {transferStatus[recordingId] === 'transferring' ? (
                      <div className="transfer-progress">
                        <div className="spinner"></div>
                        <span>Transferring to main backend...</span>
                      </div>
                    ) : transferStatus[recordingId] === 'completed' ? (
                      <div className="transfer-success">
                        ✅ Transfer Completed
                      </div>
                    ) : transferStatus[recordingId] === 'failed' ? (
                      <div className="transfer-failed">
                        ❌ Transfer Failed
                        <button 
                          onClick={() => handleTransfer(recording)}
                          className="retry-btn"
                        >
                          Retry
                        </button>
                        <button 
                          onClick={() => handleDirectTransfer(recording)}
                          className="retry-btn"
                          style={{ marginLeft: '5px' }}
                        >
                          Try Direct Transfer
                        </button>
                      </div>
                    ) : (
                      <div className="transfer-buttons">
                        <button
                          onClick={() => handleTransfer(recording)}
                          className="transfer-btn"
                          disabled={piStatus !== 'connected'}
                        >
                          Transfer to Main Backend
                        </button>
                        <button
                          onClick={() => handleDirectTransfer(recording)}
                          className="transfer-btn"
                          disabled={piStatus !== 'connected'}
                          style={{ 
                            marginLeft: '5px', 
                            background: '#17a2b8',
                            fontSize: '12px',
                            padding: '6px 10px'
                          }}
                        >
                          Direct Transfer
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default PiVideoTransfer;
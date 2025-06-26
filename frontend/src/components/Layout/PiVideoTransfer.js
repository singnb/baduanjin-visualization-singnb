// src/components/Layout/PiVideoTransfer.js
// FIXED VERSION - Uses correct API endpoints from documentation

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import { PI_CONFIG, getPiUrl } from '../../config/piConfig';
import './Layout.css';

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
    brocadeType: 'LIVE_SESSION'
  });

  useEffect(() => {
    loadPiRecordings();
    checkPiStatus();
  }, []);

  // === Use correct API endpoint ===
  const loadPiRecordings = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Use actual API endpoint from docs
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/recordings`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
      });
      
      const data = response.data;
      
      // Handle response format from actual API
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
      // Use actual status endpoint
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/status`, {
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

  // === Use correct transfer endpoint with filename ===
  const handleTransfer = async (recording) => {
    // Determine the filename for transfer
    let filename;
    if (recording.files && recording.files.original) {
      filename = recording.files.original.filename;
    } else if (recording.filename) {
      filename = recording.filename;
    } else if (recording.timestamp) {
      // Default to original file naming convention
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
      console.log('📤 Starting transfer for:', filename);
      
      // Use actual transfer endpoint from docs
      const response = await axios.post(
        `${getPiUrl('api')}/api/pi-live/transfer-video/${encodeURIComponent(filename)}`,
        {
          title: title,
          description: description,
          brocade_type: transferForm.brocadeType
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 600000 // 10 minutes for large video transfers
        }
      );

      console.log('📤 Transfer response:', response.data);

      // Check if transfer started successfully
      if (response.data.success || response.data.status === 'started') {
        // Poll for transfer completion using status endpoint
        await pollTransferStatus(filename, recordingId);
      } else {
        throw new Error(response.data.message || 'Transfer failed to start');
      }
      
    } catch (err) {
      console.error('Transfer error:', err);
      setTransferStatus(prev => ({ ...prev, [recordingId]: 'failed' }));
      
      const errorMessage = err.response?.data?.detail || 
                          err.response?.data?.message || 
                          err.message || 
                          'Transfer failed';
      setError(`Transfer failed for ${filename}: ${errorMessage}`);
    }
  };

  // === Poll transfer status using correct endpoint ===
  const pollTransferStatus = async (filename, recordingId) => {
    const maxAttempts = 60; // 10 minutes with 10-second intervals
    let attempts = 0;

    const checkStatus = async () => {
      try {
        attempts++;
        console.log(`📊 Checking transfer status (${attempts}/${maxAttempts})...`);
        
        // Use actual status endpoint from docs
        const statusResponse = await axios.get(
          `${getPiUrl('api')}/api/pi-live/transfer-status/${encodeURIComponent(filename)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            },
            timeout: PI_CONFIG.TIMEOUTS.API_REQUEST
          }
        );
        
        const statusData = statusResponse.data;
        console.log('📊 Transfer status:', statusData);
        
        if (statusData.status === 'completed' || statusData.success) {
          // Transfer completed successfully
          setTransferStatus(prev => ({ ...prev, [recordingId]: 'completed' }));
          
          // Remove from Pi recordings list
          setPiRecordings(prev => prev.filter(r => 
            r.timestamp !== recordingId && 
            r.filename !== recordingId && 
            r.id !== recordingId
          ));
          
          if (onTransferComplete) {
            onTransferComplete(statusData);
          }

          const transferInfo = statusData.transfer_info || {};
          const sizeMB = transferInfo.total_size ? 
            (transferInfo.total_size / 1024 / 1024).toFixed(1) : 'Unknown';
          
          alert(`Transfer completed!\nFile: ${filename}\nSize: ${sizeMB} MB`);
          
        } else if (statusData.status === 'failed' || statusData.error) {
          // Transfer failed
          setTransferStatus(prev => ({ ...prev, [recordingId]: 'failed' }));
          setError(`Transfer failed: ${statusData.error || statusData.message || 'Unknown error'}`);
          
        } else if (statusData.status === 'in_progress' || statusData.status === 'transferring') {
          // Still transferring, check again
          if (attempts < maxAttempts) {
            setTimeout(checkStatus, 10000); // Check every 10 seconds
          } else {
            // Timeout reached
            setTransferStatus(prev => ({ ...prev, [recordingId]: 'failed' }));
            setError(`Transfer timeout after ${maxAttempts * 10} seconds`);
          }
        } else {
          // Unknown status, assume completed
          console.warn('⚠️ Unknown transfer status:', statusData);
          setTransferStatus(prev => ({ ...prev, [recordingId]: 'completed' }));
          if (onTransferComplete) {
            onTransferComplete(statusData);
          }
        }
        
      } catch (statusError) {
        console.error('❌ Status check failed:', statusError);
        
        if (attempts < maxAttempts) {
          // Retry status check
          setTimeout(checkStatus, 10000);
        } else {
          // Give up after max attempts
          setTransferStatus(prev => ({ ...prev, [recordingId]: 'failed' }));
          setError(`Status check failed: ${statusError.message}`);
        }
      }
    };

    // Start status checking
    setTimeout(checkStatus, 2000); // Initial delay
  };

  // === Test Pi connection ===
  const testPiConnection = async () => {
    setLoading(true);
    try {
      // Use actual test endpoint from docs
      const response = await axios.get(`${getPiUrl('api')}/api/pi-live/test-pi-connection`, {
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
        <div className="pi-status" style={{ color: getStatusColor(piStatus) }}>
          Pi Status: {piStatus === 'connected' ? '✅ Connected' : 
                     piStatus === 'disconnected' ? '❌ Disconnected' : 
                     piStatus === 'error' ? '❌ Error' : '⏳ Checking...'}
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
              <option value="LIVE_SESSION">Live Session</option>
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
                        <span>Transferring... This may take several minutes</span>
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
                      </div>
                    ) : (
                      <button
                        onClick={() => handleTransfer(recording)}
                        className="transfer-btn"
                        disabled={piStatus !== 'connected'}
                      >
                        Transfer to Storage
                      </button>
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
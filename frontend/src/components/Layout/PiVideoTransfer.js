// src/components/Layout/PiVideoTransfer.js

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import './Layout.css';

// pi-service backend
const PI_SERVICE_URL = 'https://https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net';

const PiVideoTransfer = ({ onTransferComplete }) => {
  const [piRecordings, setPiRecordings] = useState([]);
  const [piStatus, setPiStatus] = useState('unknown');
  const [loading, setLoading] = useState(false);
  const [transferStatus, setTransferStatus] = useState({});
  const [error, setError] = useState(null);
  const { token } = useAuth();

  // Form state for transfer
  const [transferForm, setTransferForm] = useState({
    timestamp: '',
    title: '',
    description: '',
    brocadeType: 'LIVE_SESSION'
  });

  useEffect(() => {
    // Test connection first, then load recordings
    const initializePiConnection = async () => {
        await checkPiStatus();
        if (piStatus !== 'error') {
        await loadPiRecordings();
        }
    };
    
    initializePiConnection();
  }, []); 

  const loadPiRecordings = async () => {
    setLoading(true);
    setError(null);
    
    try {
        // Use correct endpoint
        const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/recordings`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
        });
        
        const data = response.data;
        setPiRecordings(data.recordings || []); 
        setPiStatus(data.success ? 'connected' : 'disconnected'); 
        
        if (!data.success) {
        setError(data.message || 'Failed to load recordings');
        }
    } catch (err) {
        console.error('Error loading Pi recordings:', err);
        setError('Failed to connect to Pi service');
        setPiStatus('error');
    } finally {
        setLoading(false);
    }
  };

  const checkPiStatus = async () => {
    try {
        // Use correct endpoint
        const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/status`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
        });
        
        const data = response.data;
        // Check for pi_connected or is_running to determine status
        setPiStatus(data.pi_connected || data.is_running ? 'connected' : 'disconnected');
    } catch (err) {
        setPiStatus('error');
    }
  };

  const handleTransfer = async (recording) => {
    // Handle both legacy timestamp format and new recording format
    const identifier = recording.timestamp || recording.filename || recording.id;
    
    if (!identifier) {
        setError('Cannot identify recording for transfer');
        return;
    }
    
    // Extract filename for the API call
    let filename;
    if (recording.files && recording.files.original) {
        filename = recording.files.original.filename;
    } else if (recording.filename) {
        filename = recording.filename;
    } else if (recording.timestamp) {
        // original file format for timestamp
        filename = `baduanjin_original_${recording.timestamp}.mp4`;
    } else {
        setError('Cannot determine filename for transfer');
        return;
    }
    
    const title = transferForm.title || `Pi Session ${identifier}`;
    const description = transferForm.description || `Baduanjin practice session recorded on ${identifier}`;
    
    setTransferStatus(prev => ({ ...prev, [identifier]: 'transferring' }));
    setError(null);

    try {
        // Use the new transfer endpoint with filename
        const response = await axios.post(
        `${PI_SERVICE_URL}/api/pi-live/transfer-video/${encodeURIComponent(filename)}`,
        {
            // Send as JSON body instead of FormData
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

        // Check transfer status using the new endpoint
        const checkTransferComplete = async () => {
        try {
            const statusResponse = await axios.get(
            `${PI_SERVICE_URL}/api/pi-live/transfer-status/${encodeURIComponent(filename)}`,
            {
                headers: {
                'Authorization': `Bearer ${token}`
                }
            }
            );
            
            const statusData = statusResponse.data;
            
            if (statusData.status === 'completed' || statusData.success) {
            setTransferStatus(prev => ({ ...prev, [identifier]: 'completed' }));
            
            // Remove transferred recording from list
            setPiRecordings(prev => prev.filter(r => 
                r.timestamp !== identifier && 
                r.filename !== identifier && 
                r.id !== identifier
            ));
            
            if (onTransferComplete) {
                onTransferComplete(statusData);
            }

            // Improved success message
            const transferInfo = statusData.transfer_info || {};
            const totalSizeMB = transferInfo.total_size ? 
                (transferInfo.total_size / 1024 / 1024).toFixed(1) : 'Unknown';
            
            alert(`Transfer completed!\nFilename: ${filename}\nTotal Size: ${totalSizeMB} MB`);
            
            } else if (statusData.status === 'failed' || statusData.error) {
            setTransferStatus(prev => ({ ...prev, [identifier]: 'failed' }));
            setError(`Transfer failed: ${statusData.error || 'Unknown error'}`);
            } else if (statusData.status === 'in_progress' || statusData.status === 'transferring') {
            // Still transferring, check again in 3 seconds
            setTimeout(checkTransferComplete, 3000);
            } else {
            // Unknown status, assume completed after initial response
            setTransferStatus(prev => ({ ...prev, [identifier]: 'completed' }));
            if (onTransferComplete) {
                onTransferComplete(response.data);
            }
            alert(`Transfer initiated for ${filename}`);
            }
        } catch (statusErr) {
            console.error('Error checking transfer status:', statusErr);
            // Assume success if we can't check status
            setTransferStatus(prev => ({ ...prev, [identifier]: 'completed' }));
            if (onTransferComplete) {
            onTransferComplete(response.data);
            }
        }
        };

        // Start checking transfer status
        if (response.data.status === 'started' || response.data.success) {
        setTimeout(checkTransferComplete, 2000); // Check after 2 seconds
        } else {
        // Immediate completion
        setTransferStatus(prev => ({ ...prev, [identifier]: 'completed' }));
        if (onTransferComplete) {
            onTransferComplete(response.data);
        }
        alert(`Transfer completed for ${filename}`);
        }
        
    } catch (err) {
        console.error('Transfer error:', err);
        setTransferStatus(prev => ({ ...prev, [identifier]: 'failed' }));
        
        const errorMessage = err.response?.data?.detail || 
                            err.response?.data?.error || 
                            err.response?.data?.message || 
                            err.message || 
                            'Transfer failed';
        setError(`Transfer failed for ${filename}: ${errorMessage}`);
    }
  };

  const formatFileSize = (bytes) => {
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  };

  const formatTimestamp = (timestamp) => {
    if (timestamp.length === 15) { // YYYYMMDD_HHMMSS
      const date = timestamp.substring(0, 8);
      const time = timestamp.substring(9);
      return `${date.substring(0, 4)}-${date.substring(4, 6)}-${date.substring(6, 8)} ${time.substring(0, 2)}:${time.substring(2, 4)}:${time.substring(4, 6)}`;
    }
    return timestamp;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return '#28a745';
      case 'disconnected': return '#dc3545';
      case 'error': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const testPiConnection = async () => {
    setLoading(true);
    try {
        const response = await axios.get(`${PI_SERVICE_URL}/api/pi-live/test-pi-connection`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
        });
        
        const data = response.data;
        setPiStatus(data.pi_connected ? 'connected' : 'disconnected');
        
        if (data.pi_connected) {
        alert('Pi connection test successful!');
        // Refresh recordings after successful connection
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
            // Handle different recording formats
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

                {/* File Details - handle both old and new formats */}
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
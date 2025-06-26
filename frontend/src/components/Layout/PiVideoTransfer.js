// src/components/Layout/PiVideoTransfer.js
// New component to handle Pi video transfers alongside existing VideoUpload

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import './Layout.css';

// Use your pi-service URL (adjust as needed)
const PI_SERVICE_URL = 'https://baduanjin-pi-service.azurewebsites.net';

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
    loadPiRecordings();
    checkPiStatus();
  }, []);

  const loadPiRecordings = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`${PI_SERVICE_URL}/api/video-transfer/list-pi-recordings`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = response.data;
      setPiRecordings(data.pi_recordings || []);
      setPiStatus(data.pi_status);
      
      if (!data.success) {
        setError(data.message);
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
      const response = await axios.get(`${PI_SERVICE_URL}/api/video-transfer/pi-status`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = response.data;
      setPiStatus(data.pi_connected ? 'connected' : 'disconnected');
    } catch (err) {
      setPiStatus('error');
    }
  };

  const handleTransfer = async (recording) => {
    const { timestamp } = recording;
    
    // Set form data from recording
    const title = transferForm.title || `Pi Session ${timestamp}`;
    const description = transferForm.description || `Baduanjin practice session recorded on ${timestamp}`;
    
    setTransferStatus(prev => ({ ...prev, [timestamp]: 'transferring' }));
    setError(null);

    try {
      const formData = new FormData();
      formData.append('timestamp', timestamp);
      formData.append('title', title);
      formData.append('description', description);
      formData.append('brocade_type', transferForm.brocadeType);

      const response = await axios.post(
        `${PI_SERVICE_URL}/api/video-transfer/transfer-from-pi`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          timeout: 600000 // 10 minutes for large video transfers
        }
      );

      setTransferStatus(prev => ({ ...prev, [timestamp]: 'completed' }));
      
      // Remove transferred recording from list
      setPiRecordings(prev => prev.filter(r => r.timestamp !== timestamp));
      
      if (onTransferComplete) {
        onTransferComplete(response.data);
      }

      // Show success message
      const transferInfo = response.data.transfer_info;
      const totalSizeMB = (transferInfo.total_size / 1024 / 1024).toFixed(1);
      alert(`Transfer completed!\nOriginal Video ID: ${response.data.uploaded_videos.original.id}\nAnnotated Video ID: ${response.data.uploaded_videos.annotated.id}\nTotal Size: ${totalSizeMB} MB`);
      
    } catch (err) {
      console.error('Transfer error:', err);
      setTransferStatus(prev => ({ ...prev, [timestamp]: 'failed' }));
      
      const errorMessage = err.response?.data?.detail || err.message || 'Transfer failed';
      setError(`Transfer failed for ${timestamp}: ${errorMessage}`);
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
            {piRecordings.map((recording) => (
              <div key={recording.timestamp} className="recording-card">
                <div className="recording-header">
                  <h4>Session {recording.timestamp}</h4>
                  <div className="recording-time">
                    {formatTimestamp(recording.timestamp)}
                  </div>
                </div>

                <div className="recording-info">
                  <div className="info-row">
                    <span>Files:</span>
                    <span>{recording.file_count || Object.keys(recording.files || {}).length}</span>
                  </div>
                  <div className="info-row">
                    <span>Total Size:</span>
                    <span>{formatFileSize(recording.total_size || 0)}</span>
                  </div>
                </div>

                {/* File Details */}
                <div className="file-details">
                  {Object.entries(recording.files || {}).map(([type, file]) => (
                    <div key={type} className="file-item">
                      <span className="file-type">{type}:</span>
                      <span className="file-size">{formatFileSize(file.size)}</span>
                      <span className="file-desc">{file.description}</span>
                    </div>
                  ))}
                </div>

                {/* Transfer Controls */}
                <div className="transfer-controls">
                  {transferStatus[recording.timestamp] === 'transferring' ? (
                    <div className="transfer-progress">
                      <div className="spinner"></div>
                      <span>Transferring... This may take several minutes</span>
                    </div>
                  ) : transferStatus[recording.timestamp] === 'completed' ? (
                    <div className="transfer-success">
                      ✅ Transfer Completed
                    </div>
                  ) : transferStatus[recording.timestamp] === 'failed' ? (
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
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Updated main upload page component to include both manual upload and Pi transfer
const VideoManagementPage = () => {
  const [activeTab, setActiveTab] = useState('manual');
  const [uploadComplete, setUploadComplete] = useState(false);

  const handleUploadComplete = (data) => {
    console.log('Upload completed:', data);
    setUploadComplete(true);
    setTimeout(() => setUploadComplete(false), 3000);
  };

  const handleTransferComplete = (data) => {
    console.log('Transfer completed:', data);
    setUploadComplete(true);
    setTimeout(() => setUploadComplete(false), 3000);
  };

  return (
    <div className="video-management-page">
      <div className="page-header">
        <h1>Video Management</h1>
        <div className="tab-navigation">
          <button 
            className={`tab-btn ${activeTab === 'manual' ? 'active' : ''}`}
            onClick={() => setActiveTab('manual')}
          >
            Manual Upload
          </button>
          <button 
            className={`tab-btn ${activeTab === 'pi-transfer' ? 'active' : ''}`}
            onClick={() => setActiveTab('pi-transfer')}
          >
            Pi Transfer
          </button>
        </div>
      </div>

      {uploadComplete && (
        <div className="success-banner">
          ✅ Video operation completed successfully!
        </div>
      )}

      <div className="tab-content">
        {activeTab === 'manual' && (
          <VideoUpload onUploadComplete={handleUploadComplete} />
        )}
        
        {activeTab === 'pi-transfer' && (
          <PiVideoTransfer onTransferComplete={handleTransferComplete} />
        )}
      </div>
    </div>
  );
};

export { PiVideoTransfer, VideoManagementPage};
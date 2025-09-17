// src/components/PiLive/PiStatusPanel.js

const PiStatusPanel = ({ status, isConnected, loading, onRefresh }) => {
  return (
    <div className={`pi-status-panel ${isConnected ? 'connected' : 'disconnected'}`}>
      <div className="status-indicator">
        <span className={`status-dot ${isConnected ? 'green' : 'red'}`}></span>
        <span className="status-text">
          Pi Camera: {loading ? 'Checking...' : (isConnected ? 'Connected' : 'Disconnected')}
        </span>
      </div>
      
      {status && !loading && (
        <div className="status-details">
          <span>Camera: {status.camera_available ? '✅' : '❌'}</span>
          <span>YOLO: {status.yolo_available ? '✅' : '❌'}</span>
          <span>Running: {status.is_running ? '✅' : '❌'}</span>
          {status.persons_detected !== undefined && (
            <span>Persons: {status.persons_detected}</span>
          )}
        </div>
      )}
      
      {status && status.error && (
        <div className="status-error">
          <span>❌ {status.error}</span>
        </div>
      )}
      
      <button 
        className="refresh-btn" 
        onClick={onRefresh}
        disabled={loading}
      >
        {loading ? '⏳' : '🔄'} Refresh
      </button>
    </div>
  );
};

export default PiStatusPanel;

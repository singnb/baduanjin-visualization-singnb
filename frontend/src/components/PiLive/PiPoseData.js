// src/components/PiLive/PiPoseData.js

const PiPoseData = ({ poseData, activeSession }) => {
  if (!activeSession) {
    return (
      <div className="pi-pose-data empty">
        <h3>Pose Analysis</h3>
        <p>Start a session to see pose data</p>
      </div>
    );
  }

  if (!poseData || !poseData.pose_data) {
    return (
      <div className="pi-pose-data empty">
        <h3>Pose Analysis</h3>
        <p>Waiting for pose data...</p>
      </div>
    );
  }

  const { pose_data, stats } = poseData;

  return (
    <div className="pi-pose-data">
      <h3>Real-time Analysis</h3>
      
      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-label">FPS:</span>
          <span className="stat-value">{stats?.current_fps || 0}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Persons:</span>
          <span className="stat-value">{pose_data?.length || 0}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Last Update:</span>
          <span className="stat-value">
            {poseData.timestamp ? new Date(poseData.timestamp).toLocaleTimeString() : 'N/A'}
          </span>
        </div>
      </div>
      
      {pose_data && pose_data.length > 0 && (
        <div className="pose-details">
          <h4>Person 1 Analysis:</h4>
          <div className="keypoints-summary">
            <p>Keypoints: {pose_data[0].keypoints?.length || 0}</p>
            {pose_data[0].confidences && (
              <p>
                Avg Confidence: {(pose_data[0].confidences.reduce((a, b) => a + b, 0) / pose_data[0].confidences.length * 100).toFixed(1)}%
              </p>
            )}
          </div>
          
          <div className="live-feedback">
            <div className="feedback-item good">
              ✅ Pose detected
            </div>
            {pose_data[0].confidences && pose_data[0].confidences.some(c => c < 0.5) && (
              <div className="feedback-item warning">
                ⚠️ Some keypoints have low confidence
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PiPoseData;
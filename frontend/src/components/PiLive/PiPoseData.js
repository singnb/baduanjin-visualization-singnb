// src/components/PiLive/PiPoseData.js
import React from 'react';

const PiPoseData = ({ poseData, activeSession }) => {
  if (!activeSession || !poseData) {
    return (
      <div className="pi-pose-data empty">
        <h3>Pose Analysis</h3>
        <p>No pose data available</p>
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
          <span className="stat-label">Frames:</span>
          <span className="stat-value">{stats?.total_frames || 0}</span>
        </div>
      </div>
      
      {pose_data && pose_data.length > 0 && (
        <div className="pose-details">
          <h4>Person 1 Analysis:</h4>
          <div className="keypoints-summary">
            <p>Keypoints detected: {pose_data[0].keypoints?.length || 0}</p>
            <p>Confidence: {(pose_data[0].confidences?.reduce((a, b) => a + b, 0) / pose_data[0].confidences?.length * 100).toFixed(1)}%</p>
          </div>
          
          {/* Real-time feedback could go here */}
          <div className="live-feedback">
            <div className="feedback-item good">
              ✅ Good posture detected
            </div>
            <div className="feedback-item warning">
              ⚠️ Adjust left arm position
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PiPoseData;
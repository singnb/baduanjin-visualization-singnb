// src/components/Charts/BalanceChart.js

import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { loadMasterData, loadLearnerData } from '../../services/dataLoader';
import './ChartCommon.css';

function BalanceChart({ comparisonMode = 'both', compact = false }) {
  const [masterData, setMasterData] = useState(null);
  const [learnerData, setLearnerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [displayMode, setDisplayMode] = useState('both');
  const [showBodyPosition, setShowBodyPosition] = useState(true);
  const [selectedPose, setSelectedPose] = useState(null);
  const [dataStructureInfo, setDataStructureInfo] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const masterResult = await loadMasterData('balance');
        setMasterData(masterResult);
        
        const learnerResult = await loadLearnerData('balance');
        setLearnerData(learnerResult);
        
        // Debug: Log data structure info in development
        if (process.env.NODE_ENV === 'development') {
          const info = analyzeDataStructure(masterResult, learnerResult);
          setDataStructureInfo(info);
          console.log('📊 Balance Data Structure Analysis:', info);
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Error loading balance data:', err);
        setError('Failed to load balance data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // IMPROVED: Analyze data structure to understand what's available
  const analyzeDataStructure = (masterData, learnerData) => {
    const analysis = {
      master: {},
      learner: {},
      recommendations: []
    };

    // Analyze master data
    if (masterData) {
      analysis.master = {
        hasBalanceMetrics: !!masterData.balanceMetrics,
        balanceMetricsKeys: masterData.balanceMetrics ? Object.keys(masterData.balanceMetrics) : [],
        hasOverallStability: typeof masterData.overallStability === 'number',
        hasComTrajectory: !!(masterData.comTrajectory && masterData.comTrajectory.x && masterData.comTrajectory.y),
        rootKeys: Object.keys(masterData)
      };
    }

    // Analyze learner data
    if (learnerData) {
      analysis.learner = {
        hasBalanceMetrics: !!learnerData.balanceMetrics,
        balanceMetricsKeys: learnerData.balanceMetrics ? Object.keys(learnerData.balanceMetrics) : [],
        hasOverallStability: typeof learnerData.overallStability === 'number',
        hasComTrajectory: !!(learnerData.comTrajectory && learnerData.comTrajectory.x && learnerData.comTrajectory.y),
        hasKeyPoseBalance: !!(learnerData.keyPoseBalance && Array.isArray(learnerData.keyPoseBalance)),
        rootKeys: Object.keys(learnerData)
      };
    }

    // Generate recommendations
    if (!analysis.master.hasBalanceMetrics && !analysis.learner.hasBalanceMetrics) {
      analysis.recommendations.push('Consider adding balanceMetrics object with com_stability_x and com_stability_y properties');
    }
    if (!analysis.master.hasOverallStability && !analysis.learner.hasOverallStability) {
      analysis.recommendations.push('Consider adding overallStability numeric property');
    }

    return analysis;
  };

  // Helper function to safely get numeric values with fallbacks
  const getNumericValue = (value, fallback = 0) => {
    if (typeof value === 'number' && !isNaN(value)) {
      return value;
    }
    return fallback;
  };

  // IMPROVED: Helper function to safely get balance metrics with better fallback logic
  const getBalanceMetrics = (data, metricName, fallback = 0) => {
    try {
      // First check: standard balanceMetrics object
      if (data && data.balanceMetrics && typeof data.balanceMetrics[metricName] === 'number') {
        return data.balanceMetrics[metricName];
      }

      // Second check: maybe the metric is directly on the data object
      if (data && typeof data[metricName] === 'number') {
        return data[metricName];
      }

      // Third check: try alternative naming conventions
      const alternativeNames = {
        'com_stability_x': ['comStabilityX', 'stability_x', 'stabilityX', 'com_x_stability'],
        'com_stability_y': ['comStabilityY', 'stability_y', 'stabilityY', 'com_y_stability']
      };

      if (alternativeNames[metricName]) {
        for (const altName of alternativeNames[metricName]) {
          if (data && data.balanceMetrics && typeof data.balanceMetrics[altName] === 'number') {
            return data.balanceMetrics[altName];
          }
          if (data && typeof data[altName] === 'number') {
            return data[altName];
          }
        }
      }

      // Fourth check: calculate from trajectory data if available
      if (metricName.includes('stability') && data && data.comTrajectory) {
        const calculatedStability = calculateStabilityFromTrajectory(data.comTrajectory, metricName);
        if (calculatedStability !== null) {
          return calculatedStability;
        }
      }

      // Only warn in development mode to reduce console noise
      if (process.env.NODE_ENV === 'development') {
        console.warn(`⚠️ Balance metric '${metricName}' not found, using fallback: ${fallback}`);
      }
      
      return fallback;
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`❌ Error accessing balance metric '${metricName}':`, error);
      }
      return fallback;
    }
  };

  // NEW: Calculate stability from trajectory data as fallback
  const calculateStabilityFromTrajectory = (trajectory, metricName) => {
    try {
      if (!trajectory || !Array.isArray(trajectory.x) || !Array.isArray(trajectory.y)) {
        return null;
      }

      if (metricName.includes('x')) {
        // Calculate X-axis stability (lower variance = more stable)
        const xValues = trajectory.x.filter(val => typeof val === 'number' && !isNaN(val));
        if (xValues.length === 0) return null;
        
        const mean = xValues.reduce((sum, val) => sum + val, 0) / xValues.length;
        const variance = xValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / xValues.length;
        return Math.max(0, 1 - Math.sqrt(variance)); // Convert to stability score (0-1)
      }

      if (metricName.includes('y')) {
        // Calculate Y-axis stability
        const yValues = trajectory.y.filter(val => typeof val === 'number' && !isNaN(val));
        if (yValues.length === 0) return null;
        
        const mean = yValues.reduce((sum, val) => sum + val, 0) / yValues.length;
        const variance = yValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / yValues.length;
        return Math.max(0, 1 - Math.sqrt(variance)); // Convert to stability score (0-1)
      }

      return null;
    } catch (error) {
      console.warn('Error calculating stability from trajectory:', error);
      return null;
    }
  };

  // IMPROVED: Helper function to safely get stability score with better fallback
  const getStabilityScore = (data, fallback = 0) => {
    try {
      // First check: standard overallStability property
      if (data && typeof data.overallStability === 'number') {
        return Math.round(data.overallStability * 100);
      }

      // Second check: alternative naming conventions
      const alternativeNames = ['overall_stability', 'stabilityScore', 'stability_score', 'totalStability'];
      for (const altName of alternativeNames) {
        if (data && typeof data[altName] === 'number') {
          const score = data[altName];
          // If it's already a percentage (0-100), use as is, otherwise convert
          return Math.round(score > 1 ? score : score * 100);
        }
      }

      // Third check: calculate from balance metrics if available
      if (data && data.balanceMetrics) {
        const stabilityX = getBalanceMetrics(data, 'com_stability_x', null);
        const stabilityY = getBalanceMetrics(data, 'com_stability_y', null);
        
        if (stabilityX !== null && stabilityY !== null) {
          // Average the X and Y stability scores
          const avgStability = (stabilityX + stabilityY) / 2;
          return Math.round(avgStability * 100);
        }
      }

      // Fourth check: calculate from trajectory data
      if (data && data.comTrajectory) {
        const xStability = calculateStabilityFromTrajectory(data.comTrajectory, 'stability_x');
        const yStability = calculateStabilityFromTrajectory(data.comTrajectory, 'stability_y');
        
        if (xStability !== null && yStability !== null) {
          const avgStability = (xStability + yStability) / 2;
          return Math.round(avgStability * 100);
        }
      }

      if (process.env.NODE_ENV === 'development') {
        console.warn('⚠️ Overall stability not found, using fallback:', fallback);
      }
      return fallback;
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.warn('❌ Error calculating stability score:', error);
      }
      return fallback;
    }
  };
  
  if (loading) {
    return (
      <div className="chart-container">
        <div className="loading-container">Loading balance data...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="chart-container">
        <div className="error-container">{error}</div>
      </div>
    );
  }
  
  if (!masterData || !learnerData) {
    return (
      <div className="chart-container">
        <div className="error-container">No balance data available</div>
      </div>
    );
  }

  // Calculate stability scores with improved error handling
  const masterStabilityScore = getStabilityScore(masterData, 50); // Default to 50% if no data
  const learnerStabilityScore = getStabilityScore(learnerData, 50);

  // Get balance metrics with improved error handling
  const masterStabilityX = getBalanceMetrics(masterData, 'com_stability_x', 0.5);
  const masterStabilityY = getBalanceMetrics(masterData, 'com_stability_y', 0.5);
  const learnerStabilityX = getBalanceMetrics(learnerData, 'com_stability_x', 0.5);
  const learnerStabilityY = getBalanceMetrics(learnerData, 'com_stability_y', 0.5);

  // Render the trajectory plot
  const renderTrajectoryPlot = () => {
    const data = [];
    
    // Add master data if selected and available
    if ((displayMode === 'both' || displayMode === 'masterOnly') && 
        masterData && masterData.comTrajectory && 
        Array.isArray(masterData.comTrajectory.x) && 
        Array.isArray(masterData.comTrajectory.y)) {
      
      // Master line
      data.push({
        x: masterData.comTrajectory.x,
        y: masterData.comTrajectory.y,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Master',
        line: { color: '#3498db', width: 3 },
        marker: { size: 8, color: '#3498db' }
      });
      
      // Add time progression markers
      const timeMarkers = [];
      for (let i = 0; i < masterData.comTrajectory.x.length; i++) {
        const opacity = 0.3 + (0.7 * i / masterData.comTrajectory.x.length);
        timeMarkers.push({
          x: [masterData.comTrajectory.x[i]],
          y: [masterData.comTrajectory.y[i]],
          type: 'scatter',
          mode: 'markers',
          marker: { 
            size: 5, 
            color: 'purple',
            opacity: opacity
          },
          showlegend: i === 0,
          name: i === 0 ? 'Time Progression' : '',
          hoverinfo: 'none'
        });
      }
      data.push(...timeMarkers);
    }
    
    // Add learner data if selected and available
    if ((displayMode === 'both' || displayMode === 'learnerOnly') && 
        learnerData && learnerData.comTrajectory && 
        Array.isArray(learnerData.comTrajectory.x) && 
        Array.isArray(learnerData.comTrajectory.y)) {
      
      data.push({
        x: learnerData.comTrajectory.x,
        y: learnerData.comTrajectory.y,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Learner',
        line: { color: '#e74c3c', width: 3, dash: 'dash' },
        marker: { size: 8, color: '#e74c3c' }
      });
    }
    
    // Add key pose markers if showing body positions and data is available
    if (showBodyPosition && 
        (displayMode === 'both' || displayMode === 'learnerOnly') &&
        learnerData && learnerData.keyPoseBalance && 
        Array.isArray(learnerData.keyPoseBalance)) {
      
      // Regular key poses
      const keyPoseData = {
        x: [],
        y: [],
        type: 'scatter',
        mode: 'markers',
        name: 'Key Poses',
        marker: { 
          size: 12,
          color: '#2ecc71',
          symbol: 'circle',
          line: { width: 2, color: '#27ae60' }
        },
        text: [],
        hoverinfo: 'text'
      };
      
      // Selected pose (if any)
      const selectedPoseData = {
        x: [],
        y: [],
        type: 'scatter',
        mode: 'markers+text',
        name: 'Selected Pose',
        marker: { 
          size: 18,
          color: '#f39c12',
          symbol: 'circle',
          line: { width: 3, color: '#e67e22' }
        },
        text: [],
        textposition: 'top center',
        hoverinfo: 'text',
        showlegend: false
      };
      
      learnerData.keyPoseBalance.forEach((pose, index) => {
        // Safely access pose data
        if (pose && pose.comPosition && 
            typeof pose.comPosition.x === 'number' && 
            typeof pose.comPosition.y === 'number') {
          
          const poseName = pose.poseName || `Pose ${index + 1}`;
          
          if (selectedPose === index) {
            selectedPoseData.x.push(pose.comPosition.x);
            selectedPoseData.y.push(pose.comPosition.y);
            selectedPoseData.text.push(`${index + 1}: ${poseName}`);
          } else {
            keyPoseData.x.push(pose.comPosition.x);
            keyPoseData.y.push(pose.comPosition.y);
            keyPoseData.text.push(`${index + 1}: ${poseName}`);
          }
        }
      });
      
      if (keyPoseData.x.length > 0) {
        data.push(keyPoseData);
      }
      
      if (selectedPoseData.x.length > 0) {
        data.push(selectedPoseData);
      }
    }
    
    const layout = {
      autosize: true,
      margin: { l: 40, r: 20, t: 20, b: 40 },
      xaxis: {
        title: '',
        zeroline: false,
        range: [359, 365],
        fixedrange: true
      },
      yaxis: {
        title: '',
        zeroline: false,
        range: [401, 406],
        fixedrange: true,
        scaleanchor: 'x',
        scaleratio: 1
      },
      height: 320,
      width: 400,
      showlegend: false,
      hovermode: 'closest',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(245,245,245,0.8)',
      shapes: [
        // Add a light circle for the "ideal" zone
        {
          type: 'circle',
          xref: 'x',
          yref: 'y',
          x0: 361.5,
          y0: 402,
          x1: 363.5,
          y1: 404,
          opacity: 0.2,
          fillcolor: 'lightblue',
          line: { width: 0 }
        }
      ]
    };
    
    return <Plot data={data} layout={layout} config={{ displayModeBar: false }} />;
  };
  
  // Render the circular gauge for stability score with proper error handling
  const renderStabilityGauge = (score, title, xValue, yValue, color) => {
    // Ensure we have valid numeric values
    const safeScore = getNumericValue(score, 50);
    const safeXValue = getNumericValue(xValue, 0.5);
    const safeYValue = getNumericValue(yValue, 0.5);
    
    return (
      <div className="stability-gauge">
        <h4>{title}</h4>
        <div className="gauge-container">
          <div className="gauge" style={{ background: `conic-gradient(${color} 0% ${safeScore}%, #e0e0e0 ${safeScore}% 100%)` }}>
            <div className="gauge-center">
              <span className="gauge-value">{safeScore}</span>
            </div>
          </div>
        </div>
        <div className="stability-metrics">
          <p>X: {safeXValue.toFixed(2)} Y: {safeYValue.toFixed(2)}</p>
        </div>
      </div>
    );
  };

  // Render key pose indicators with error handling
  const renderKeyPoses = () => {
    if (!learnerData || !learnerData.keyPoseBalance || !Array.isArray(learnerData.keyPoseBalance)) {
      return (
        <div className="key-poses">
          <h4>Key Poses (for learner)</h4>
          <p>No key pose data available</p>
        </div>
      );
    }

    return (
      <div className="key-poses">
        <h4>Key Poses (for learner)</h4>
        <div className="pose-indicators">
          {learnerData.keyPoseBalance.map((pose, index) => (
            <div 
              key={index} 
              className="pose-indicator"
              onClick={() => handlePoseClick(index)}
            >
              <div 
                className={`pose-circle ${selectedPose === index ? 'selected' : ''}`}
                style={{ backgroundColor: selectedPose === index ? '#f39c12' : '#2ecc71' }}
              >
                {index + 1}
              </div>
              <div className="pose-name">{getShortPoseName(pose ? pose.poseName : `Pose ${index + 1}`)}</div>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  // Handle clicking on a pose button
  const handlePoseClick = (index) => {
    // Toggle selection - if already selected, deselect it
    if (selectedPose === index) {
      setSelectedPose(null);
    } else {
      setSelectedPose(index);
    }
  };

  // Helper function to get shorter pose names for the circles
  const getShortPoseName = (poseName) => {
    if (!poseName || typeof poseName !== 'string') {
      return 'Unknown';
    }
    
    switch(poseName) {
      case "Initial Position": return "Starting";
      case "Transition Phase": return "Transition";
      case "Peak Position": return "Peak";
      case "Holding Phase": return "Holding";
      case "Return Phase": return "Return";
      case "Final Position": return "Final";
      case "Stabilization Phase": return "Stabilization";
      case "Ready Position": return "Ending";
      default: return poseName.length > 8 ? poseName.substring(0, 8) + '...' : poseName;
    }
  };
  
  return (
    <div className="balance-chart-container">
      <div className="chart-header">
        <h3>Balance and Stability Analysis</h3>
        <p className="chart-description">This visualization shows your center of mass movement throughout the exercise compared to the master.</p>
      </div>
      
      <div className="display-controls">
        <div className="button-group">
          <button 
            className={`control-button ${displayMode === 'both' ? 'active' : ''}`}
            onClick={() => setDisplayMode('both')}
          >
            Both Trajectories
          </button>
          <button 
            className={`control-button ${displayMode === 'masterOnly' ? 'active' : ''}`}
            onClick={() => setDisplayMode('masterOnly')}
          >
            Master Only
          </button>
          <button 
            className={`control-button ${displayMode === 'learnerOnly' ? 'active' : ''}`}
            onClick={() => setDisplayMode('learnerOnly')}
          >
            Learner Only
          </button>
        </div>
        
        <div className="body-position-toggle">
          <input 
            type="checkbox" 
            id="showBodyPosition" 
            checked={showBodyPosition} 
            onChange={() => setShowBodyPosition(!showBodyPosition)} 
          />
          <label htmlFor="showBodyPosition">Show Body Position Context</label>
        </div>
      </div>
      
      <div className="legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#3498db' }}></span>
          <span>Master</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#e74c3c' }}></span>
          <span>Learner</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#2ecc71' }}></span>
          <span>Key Poses</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: 'purple' }}></span>
          <span>Time Progression</span>
        </div>
      </div>
      
      <div className="chart-content">
        <div className="gauge-section">
          {renderStabilityGauge(
            masterStabilityScore, 
            "Master Stability Score", 
            masterStabilityX,
            masterStabilityY,
            '#3498db'
          )}
        </div>
        
        <div className="trajectory-section">
          {renderTrajectoryPlot()}
        </div>
        
        <div className="gauge-section">
          {renderStabilityGauge(
            learnerStabilityScore, 
            "Your Stability Score", 
            learnerStabilityX,
            learnerStabilityY,
            '#e74c3c'
          )}
        </div>
      </div>
      
      {renderKeyPoses()}

      {/* Data Structure Debug Info (Development Only) */}
      {process.env.NODE_ENV === 'development' && dataStructureInfo && (
        <div className="debug-section" style={{ 
          marginTop: '20px', 
          padding: '15px', 
          background: '#f8f9fa', 
          borderRadius: '4px',
          fontSize: '12px',
          border: '1px solid #dee2e6'
        }}>
          <h4>🔍 Data Structure Analysis (Development Mode)</h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginTop: '10px' }}>
            <div>
              <h5>Master Data:</h5>
              <ul style={{ fontSize: '11px', listStyle: 'none', padding: 0 }}>
                <li>✓ Balance Metrics: {dataStructureInfo.master.hasBalanceMetrics ? 'Yes' : 'No'}</li>
                <li>✓ Overall Stability: {dataStructureInfo.master.hasOverallStability ? 'Yes' : 'No'}</li>
                <li>✓ COM Trajectory: {dataStructureInfo.master.hasComTrajectory ? 'Yes' : 'No'}</li>
                {dataStructureInfo.master.balanceMetricsKeys.length > 0 && (
                  <li>Keys: {dataStructureInfo.master.balanceMetricsKeys.join(', ')}</li>
                )}
              </ul>
            </div>
            
            <div>
              <h5>Learner Data:</h5>
              <ul style={{ fontSize: '11px', listStyle: 'none', padding: 0 }}>
                <li>✓ Balance Metrics: {dataStructureInfo.learner.hasBalanceMetrics ? 'Yes' : 'No'}</li>
                <li>✓ Overall Stability: {dataStructureInfo.learner.hasOverallStability ? 'Yes' : 'No'}</li>
                <li>✓ COM Trajectory: {dataStructureInfo.learner.hasComTrajectory ? 'Yes' : 'No'}</li>
                <li>✓ Key Pose Balance: {dataStructureInfo.learner.hasKeyPoseBalance ? 'Yes' : 'No'}</li>
                {dataStructureInfo.learner.balanceMetricsKeys.length > 0 && (
                  <li>Keys: {dataStructureInfo.learner.balanceMetricsKeys.join(', ')}</li>
                )}
              </ul>
            </div>
          </div>
          
          {dataStructureInfo.recommendations.length > 0 && (
            <div style={{ marginTop: '10px' }}>
              <h5>💡 Recommendations:</h5>
              <ul style={{ fontSize: '11px' }}>
                {dataStructureInfo.recommendations.map((rec, index) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default BalanceChart;
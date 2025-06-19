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

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const masterResult = await loadMasterData('balance');
        setMasterData(masterResult);
        
        const learnerResult = await loadLearnerData('balance');
        setLearnerData(learnerResult);
        
        setLoading(false);
      } catch (err) {
        console.error('Error loading balance data:', err);
        setError('Failed to load balance data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
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

  // Calculate master stability score as a percentage (0-100)
  const masterStabilityScore = Math.round(masterData.overallStability * 100);
  
  // Calculate learner stability score as a percentage (0-100)
  const learnerStabilityScore = Math.round(learnerData.overallStability * 100);

  // Render the trajectory plot
  const renderTrajectoryPlot = () => {
    const data = [];
    
    // Add master data if selected
    if (displayMode === 'both' || displayMode === 'masterOnly') {
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
    
    // Add learner data if selected
    if (displayMode === 'both' || displayMode === 'learnerOnly') {
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
    
    // Add key pose markers if showing body positions
    if (showBodyPosition && (displayMode === 'both' || displayMode === 'learnerOnly')) {
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
        if (selectedPose === index) {
          selectedPoseData.x.push(pose.comPosition.x);
          selectedPoseData.y.push(pose.comPosition.y);
          selectedPoseData.text.push(`${index + 1}: ${pose.poseName}`);
        } else {
          keyPoseData.x.push(pose.comPosition.x);
          keyPoseData.y.push(pose.comPosition.y);
          keyPoseData.text.push(`${index + 1}: ${pose.poseName}`);
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
  
  // Render the circular gauge for stability score
  const renderStabilityGauge = (score, title, xValue, yValue, color) => {
    return (
      <div className="stability-gauge">
        <h4>{title}</h4>
        <div className="gauge-container">
          <div className="gauge" style={{ background: `conic-gradient(${color} 0% ${score}%, #e0e0e0 ${score}% 100%)` }}>
            <div className="gauge-center">
              <span className="gauge-value">{score}</span>
            </div>
          </div>
        </div>
        <div className="stability-metrics">
          <p>X: {xValue.toFixed(2)} Y: {yValue.toFixed(2)}</p>
        </div>
      </div>
    );
  };

  // Render key pose indicators
  const renderKeyPoses = () => {
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
              <div className="pose-name">{getShortPoseName(pose.poseName)}</div>
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
    switch(poseName) {
      case "Initial Position": return "Starting";
      case "Transition Phase": return "Transition";
      case "Peak Position": return "Peak";
      case "Holding Phase": return "Holding";
      case "Return Phase": return "Return";
      case "Final Position": return "Final";
      case "Stabilization Phase": return "Stabilization";
      case "Ready Position": return "Ending";
      default: return poseName;
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
            masterData.balanceMetrics.com_stability_x, 
            masterData.balanceMetrics.com_stability_y,
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
            learnerData.balanceMetrics.com_stability_x, 
            learnerData.balanceMetrics.com_stability_y,
            '#e74c3c'
          )}
        </div>
      </div>
      
      {renderKeyPoses()}
    </div>
  );
}

export default BalanceChart;
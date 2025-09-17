// src/components/Charts/SmoothnessChart.js

import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { loadMasterData, loadLearnerData } from '../../services/dataLoader';
import './SmoothnessChart.css';

function SmoothnessChart({ comparisonMode, compact = false }) {
  const [masterData, setMasterData] = useState(null);
  const [learnerData, setLearnerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [displayMode, setDisplayMode] = useState('both');
  const [showPhasesOnly, setShowPhasesOnly] = useState(false);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const masterResult = await loadMasterData('smoothness');
        setMasterData(masterResult);
        
        const learnerResult = await loadLearnerData('smoothness');
        setLearnerData(learnerResult);
        
        setLoading(false);
      } catch (err) {
        console.error('Error loading smoothness data:', err);
        setError('Failed to load smoothness data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  if (loading) {
    return (
      <div className="smoothness-chart-container">
        <div className="loading-container">Loading smoothness data...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="smoothness-chart-container">
        <div className="error-container">{error}</div>
      </div>
    );
  }
  
  if (!masterData) {
    return (
      <div className="smoothness-chart-container">
        <div className="error-container">No smoothness data available</div>
      </div>
    );
  }

  // Calculate master smoothness score as a percentage (0-100)
  const masterSmoothnessScore = Math.round(masterData.overallSmoothness * 100);
  
  // Calculate learner smoothness score as a percentage (0-100)
  const learnerSmoothnessScore = learnerData ? Math.round(learnerData.overallSmoothness * 100) : 0;

  // Prepare phase plot data
  const renderPhasePlot = () => {
    if (!masterData.movementPhases) return null;
    
    const data = [];
    
    // Master data if selected
    if (displayMode === 'both' || displayMode === 'masterOnly') {
      data.push({
        x: masterData.movementPhases.map(phase => phase.name),
        y: masterData.movementPhases.map(phase => phase.averageJerk),
        type: 'bar',
        name: 'Master Performer',
        marker: { color: '#3498db' },
        showlegend: false
      });
    }
    
    // Learner data if selected
    if ((displayMode === 'both' || displayMode === 'learnerOnly') && learnerData && learnerData.movementPhases) {
      data.push({
        x: learnerData.movementPhases.map(phase => phase.name),
        y: learnerData.movementPhases.map(phase => phase.averageJerk),
        type: 'bar',
        name: 'Learner',
        marker: { color: '#e74c3c' },
        showlegend: false
      });
    }
    
    // Add optimal range as a horizontal line
    if (masterData.optimalJerkRange) {
      data.push({
        x: masterData.movementPhases.map(phase => phase.name),
        y: Array(masterData.movementPhases.length).fill(masterData.optimalJerkRange[0]),
        type: 'scatter',
        mode: 'lines',
        name: 'Min Optimal',
        line: { color: '#2ecc71', width: 2, dash: 'dash' },
        showlegend: false
      });
      
      data.push({
        x: masterData.movementPhases.map(phase => phase.name),
        y: Array(masterData.movementPhases.length).fill(masterData.optimalJerkRange[1]),
        type: 'scatter',
        mode: 'lines',
        name: 'Max Optimal',
        line: { color: '#2ecc71', width: 2, dash: 'dash' },
        showlegend: false
      });
    }
    
    const layout = {
      title: '',
      xaxis: {
        title: '',
        tickangle: -45
      },
      yaxis: {
        title: 'Average Jerk (Lower is Smoother)',
        range: [0, 1.2]
      },
      margin: { l: 50, r: 20, t: 20, b: 100 },
      height: 400,
      width: '100%',
      showlegend: false,
      barmode: 'group',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(245,245,245,0.8)',
    };
    
    return <Plot data={data} layout={layout} config={{ displayModeBar: false }} />;
  };
  
  // Render smoothness gauge
  const renderSmoothnessGauge = (score, title, color) => {
    return (
      <div className="smoothness-gauge">
        <h4>{title}</h4>
        <div className="gauge-container">
          <div className="gauge" style={{ background: `conic-gradient(${color} 0% ${score}%, #e0e0e0 ${score}% 100%)` }}>
            <div className="gauge-center">
              <span className="gauge-value">{score}</span>
            </div>
          </div>
        </div>
        {/* <div className="optimal-range-label">
          <span>Optimal Range: {masterData.optimalJerkRange[0]} - {masterData.optimalJerkRange[1]}</span>
        </div> */}
      </div>
    );
  };
  
  // Render metrics table
  const renderMetricsTable = () => {
    if (!masterData.jerkMetrics || !masterData.keypointNames) return null;
    
    return (
      <div className="metrics-section">
        <h3>Joint Smoothness Metrics</h3>
        <table className="metrics-table">
          <thead>
            <tr>
              <th>Joint</th>
              {(displayMode === 'both' || displayMode === 'masterOnly') && <th>Master Jerk Value</th>}
              {(displayMode === 'both' || displayMode === 'learnerOnly') && <th>Learner Jerk Value</th>}
              {displayMode === 'both' && <th>Comparison</th>}
            </tr>
          </thead>
          <tbody>
            {Object.keys(masterData.jerkMetrics).map(keypoint => (
              <tr key={keypoint}>
                <td>{masterData.keypointNames[keypoint]}</td>
                
                {(displayMode === 'both' || displayMode === 'masterOnly') && 
                  <td>{masterData.jerkMetrics[keypoint].toFixed(2)}</td>
                }
                
                {(displayMode === 'both' || displayMode === 'learnerOnly') && 
                  <td>{(learnerData && learnerData.jerkMetrics && learnerData.jerkMetrics[keypoint]) ? 
                    learnerData.jerkMetrics[keypoint].toFixed(2) : 'N/A'}</td>
                }
                
                {displayMode === 'both' && 
                  <td>
                    {learnerData && learnerData.jerkMetrics && learnerData.jerkMetrics[keypoint] ? 
                      compareValues(masterData.jerkMetrics[keypoint], learnerData.jerkMetrics[keypoint]) : 
                      'N/A'}
                  </td>
                }
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
  
  return (
    <div className="smoothness-chart-container">
      <div className="chart-header">
        <h3>Movement Smoothness Analysis</h3>
        <p className="chart-description">Analysis of movement jerk to evaluate control and fluidity throughout the sequence</p>
      </div>
      
      <div className="display-controls">
        <div className="button-group">
          <button 
            className={`control-button ${displayMode === 'both' ? 'active' : ''}`}
            onClick={() => setDisplayMode('both')}
          >
            Both Performers
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
        
        <div className="view-toggle">
          <input 
            type="checkbox" 
            id="showPhasesOnly" 
            checked={showPhasesOnly} 
            onChange={() => setShowPhasesOnly(!showPhasesOnly)} 
          />
          <label htmlFor="showPhasesOnly">Show Phases Only</label>
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
          <span>Optimal Range</span>
        </div>
      </div>
      
      <div className="chart-content">
        {!showPhasesOnly && (
          <div className="gauge-section">
            {(displayMode === 'both' || displayMode === 'masterOnly') && 
              renderSmoothnessGauge(masterSmoothnessScore, "Master Smoothness Score", '#3498db')
            }
          </div>
        )}
        
        <div className="plot-section">
          {renderPhasePlot()}
        </div>
        
        {!showPhasesOnly && (
          <div className="gauge-section">
            {(displayMode === 'both' || displayMode === 'learnerOnly') && 
              renderSmoothnessGauge(learnerSmoothnessScore, "Your Smoothness Score", '#e74c3c')
            }
          </div>
        )}
      </div>
      
      {!showPhasesOnly && renderMetricsTable()}
    </div>
  );
}

// Helper function to compare master and learner values
function compareValues(masterValue, learnerValue) {
  const difference = ((learnerValue - masterValue) / masterValue) * 100;
  
  if (Math.abs(difference) < 5) {
    return <span style={{ color: '#2ecc71' }}>Excellent match</span>;
  } else if (Math.abs(difference) < 15) {
    return <span style={{ color: '#f39c12' }}>Good match</span>;
  } else {
    return <span style={{ color: '#e74c3c' }}>Needs improvement</span>;
  }
}

export default SmoothnessChart;
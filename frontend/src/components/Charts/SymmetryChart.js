// src/components/Charts/SymmetryChart.js
import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { loadMasterData, loadLearnerData } from '../../services/dataLoader';
import './ChartCommon.css';

function SymmetryChart({ comparisonMode, compact = false }) {
  const [masterData, setMasterData] = useState(null);
  const [learnerData, setLearnerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [displayMode, setDisplayMode] = useState('both');
  const [activePanelView, setActivePanelView] = useState('pose'); // 'pose' or 'joint'
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const masterResult = await loadMasterData('symmetry');
        setMasterData(masterResult);
        
        const learnerResult = await loadLearnerData('symmetry');
        setLearnerData(learnerResult);
        
        setLoading(false);
      } catch (err) {
        console.error('Error loading symmetry data:', err);
        setError('Failed to load symmetry data');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  if (loading) {
    return (
      <div className="symmetry-chart-container">
        <div className="loading-container">Loading symmetry data...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="symmetry-chart-container">
        <div className="error-container">{error}</div>
      </div>
    );
  }
  
  if (!masterData) {
    return (
      <div className="symmetry-chart-container">
        <div className="error-container">No symmetry data available</div>
      </div>
    );
  }

  // Calculate master symmetry score as a percentage (0-100)
  const masterSymmetryScore = Math.round(masterData.overallSymmetry * 100);
  
  // Calculate learner symmetry score as a percentage (0-100)
  const learnerSymmetryScore = learnerData ? Math.round(learnerData.overallSymmetry * 100) : 0;

  // Render pose symmetry chart
  const renderPoseSymmetryChart = () => {
    if (!masterData.keyPoseSymmetry) return null;
    
    const data = [];
    
    // Master data if selected
    if (displayMode === 'both' || displayMode === 'masterOnly') {
      data.push({
        x: masterData.keyPoseSymmetry.map(pose => pose.poseName),
        y: masterData.keyPoseSymmetry.map(pose => pose.symmetryScore),
        type: 'bar',
        name: 'Master Performer',
        marker: { color: '#3498db' },
        showlegend: false
      });
    }
    
    // Learner data if selected
    if ((displayMode === 'both' || displayMode === 'learnerOnly') && learnerData && learnerData.keyPoseSymmetry) {
      data.push({
        x: learnerData.keyPoseSymmetry.map(pose => pose.poseName),
        y: learnerData.keyPoseSymmetry.map(pose => pose.symmetryScore),
        type: 'bar',
        name: 'Learner',
        marker: { color: '#e74c3c' },
        showlegend: false
      });
    }
    
    // Add optimal range as a horizontal line
    if (masterData.optimalSymmetryRange) {
      data.push({
        x: masterData.keyPoseSymmetry.map(pose => pose.poseName),
        y: Array(masterData.keyPoseSymmetry.length).fill(masterData.optimalSymmetryRange[0]),
        type: 'scatter',
        mode: 'lines',
        name: 'Min Optimal',
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
        title: 'Symmetry Score (Higher is Better)',
        range: [0, 1.1]
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
  
  // Render joint pair symmetry chart
  const renderJointPairChart = () => {
    if (!masterData.symmetryScores || !masterData.keypointPairNames) return null;
    
    const data = [];
    const jointPairs = Object.keys(masterData.symmetryScores);
    
    // Master data if selected
    if (displayMode === 'both' || displayMode === 'masterOnly') {
      data.push({
        x: jointPairs.map(pair => masterData.keypointPairNames[pair]),
        y: jointPairs.map(pair => masterData.symmetryScores[pair]),
        type: 'bar',
        name: 'Master Performer',
        marker: { color: '#3498db' },
        showlegend: false
      });
    }
    
    // Learner data if selected
    if ((displayMode === 'both' || displayMode === 'learnerOnly') && learnerData && learnerData.symmetryScores) {
      data.push({
        x: jointPairs.map(pair => masterData.keypointPairNames[pair]), // Use master joint pair names for consistency
        y: jointPairs.map(pair => 
          learnerData.symmetryScores[pair] ? learnerData.symmetryScores[pair] : 0
        ),
        type: 'bar',
        name: 'Learner',
        marker: { color: '#e74c3c' },
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
        title: 'Asymmetry Value (Lower is Better)',
      },
      margin: { l: 50, r: 20, t: 20, b: 120 },
      height: 400,
      width: '100%',
      showlegend: false,
      barmode: 'group',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(245,245,245,0.8)',
    };
    
    return <Plot data={data} layout={layout} config={{ displayModeBar: false }} />;
  };
  
  // Render symmetry gauge
  const renderSymmetryGauge = (score, title, color) => {
    return (
      <div className="symmetry-gauge">
        <h4>{title}</h4>
        <div className="gauge-container">
          <div className="gauge" style={{ background: `conic-gradient(${color} 0% ${score}%, #e0e0e0 ${score}% 100%)` }}>
            <div className="gauge-center">
              <span className="gauge-value">{score}</span>
            </div>
          </div>
        </div>
        <div className="optimal-range-label">
          <span>Optimal Range: {masterData.optimalSymmetryRange[0]} - {masterData.optimalSymmetryRange[1]}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="symmetry-chart-container">
      <div className="chart-header">
        <h3>Movement Symmetry Analysis</h3>
        <p className="chart-description">Analysis of left and right side movement symmetry throughout the sequence</p>
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
          <button 
            className={`view-button ${activePanelView === 'pose' ? 'active' : ''}`}
            onClick={() => setActivePanelView('pose')}
          >
            Pose Symmetry
          </button>
          <button 
            className={`view-button ${activePanelView === 'joint' ? 'active' : ''}`}
            onClick={() => setActivePanelView('joint')}
          >
            Joint Pair Symmetry
          </button>
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
        <div className="gauge-section">
          {(displayMode === 'both' || displayMode === 'masterOnly') && 
            renderSymmetryGauge(masterSymmetryScore, "Master Symmetry Score", '#3498db')
          }
        </div>
        
        <div className="plot-section">
          {activePanelView === 'pose' ? renderPoseSymmetryChart() : renderJointPairChart()}
        </div>
        
        <div className="gauge-section">
          {(displayMode === 'both' || displayMode === 'learnerOnly') && 
            renderSymmetryGauge(learnerSymmetryScore, "Your Symmetry Score", '#e74c3c')
          }
        </div>
      </div>
    </div>
  );
}

export default SymmetryChart;
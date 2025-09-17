// src/components/Analysis/ComparisonView.js

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import { loadComparisonData } from '../../services/dataLoader'; 
import JointAngleChart from '../Charts/JointAngleChart';
import SmoothnessChart from '../Charts/SmoothnessChart';
import SymmetryChart from '../Charts/SymmetryChart';
import BalanceChart from '../Charts/BalanceChart';
import './ComparisonView.css';

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

const ComparisonView = () => {
  const { userVideoId, masterVideoId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('jointAngles');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [chartData, setChartData] = useState({
    jointAngles: null,
    smoothness: null,
    symmetry: null,
    balance: null
  });

  useEffect(() => {
    const fetchComparisonData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        console.log(`Fetching comparison data for user video ${userVideoId} and master video ${masterVideoId}`);
        
        // Method 1: Try the backend comparison endpoint first
        try {
          const response = await axios.get(
            `${BACKEND_URL}/api/analysis-master/compare/${userVideoId}/${masterVideoId}`,
            {
              headers: { 'Authorization': `Bearer ${token}` }
            }
          );
          console.log('Backend comparison response:', response.data);
          setComparisonData(response.data);
        } catch (backendError) {
          console.warn('Backend comparison endpoint failed:', backendError);
          // Continue to try individual data loading
        }
        
        // Method 2: Load individual chart data using dataLoader
        const loadChartData = async () => {
          const dataTypes = ['jointAngles', 'smoothness', 'symmetry', 'balance'];
          const chartDataPromises = dataTypes.map(async (dataType) => {
            try {
              const data = await loadComparisonData(userVideoId, masterVideoId, dataType);
              console.log(`Loaded ${dataType} comparison data:`, data);
              return { [dataType]: data };
            } catch (error) {
              console.error(`Failed to load ${dataType} data:`, error);
              return { [dataType]: null };
            }
          });
          
          const results = await Promise.all(chartDataPromises);
          const combinedChartData = results.reduce((acc, curr) => ({ ...acc, ...curr }), {});
          
          console.log('Combined chart data:', combinedChartData);
          setChartData(combinedChartData);
        };
        
        await loadChartData();
        
      } catch (err) {
        console.error('Error fetching comparison data:', err);
        console.error('Error response:', err.response?.data);
        setError(`Failed to load comparison data: ${err.response?.data?.detail || err.message}`);
      } finally {
        setLoading(false);
      }
    };
    
    fetchComparisonData();
  }, [userVideoId, masterVideoId, token]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading comparison data for videos {userVideoId} and {masterVideoId}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <h3>Error Loading Comparison Data</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
        <button onClick={() => navigate('/comparison-selection')}>Back to Selection</button>
      </div>
    );
  }

  // FIXED: Render the appropriate chart based on the active tab WITH DATA
  const renderChart = () => {
    const currentData = chartData[activeTab];
    
    if (!currentData) {
      return (
        <div className="no-data-message">
          <h3>No data available for {activeTab}</h3>
          <p>Please ensure both videos have extracted analysis data.</p>
        </div>
      );
    }
    
    switch (activeTab) {
      case 'jointAngles':
        return (
          <JointAngleChart 
            learnerData={currentData.learnerData}
            masterData={currentData.masterData}
            comparisonMode={true}
          />
        );
      case 'smoothness':
        return (
          <SmoothnessChart 
            learnerData={currentData.learnerData}
            masterData={currentData.masterData}
            comparisonMode={true}
          />
        );
      case 'symmetry':
        return (
          <SymmetryChart 
            learnerData={currentData.learnerData}
            masterData={currentData.masterData}
            comparisonMode={true}
          />
        );
      case 'balance':
        return (
          <BalanceChart 
            learnerData={currentData.learnerData}
            masterData={currentData.masterData}
            comparisonMode={true}
          />
        );
      default:
        return <div>Unknown chart type</div>;
    }
  };

  return (
    <div className="comparison-view-container">
      <div className="comparison-header">
        <h1>Movement Analysis Comparison</h1>
        <div className="header-info">
          <span>Comparing User Video {userVideoId} vs Master Video {masterVideoId}</span>
        </div>
        <div className="header-controls">
          <button 
            className="btn btn-secondary"
            onClick={() => navigate('/comparison-selection')}
          >
            Back to Selection
          </button>
        </div>
      </div>

      {/* Debug Information */}
      {process.env.NODE_ENV === 'development' && (
        <div className="debug-info" style={{ 
          background: '#f0f0f0', 
          padding: '10px', 
          margin: '10px 0', 
          fontSize: '12px',
          borderRadius: '4px'
        }}>
          <h4>Debug Info:</h4>
          <p>User Video ID: {userVideoId}</p>
          <p>Master Video ID: {masterVideoId}</p>
          <p>Has Comparison Data: {comparisonData ? 'Yes' : 'No'}</p>
          <p>Chart Data Status:</p>
          <ul>
            {Object.entries(chartData).map(([key, value]) => (
              <li key={key}>{key}: {value ? 'Loaded' : 'Missing'}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button 
          className={`tab-button ${activeTab === 'jointAngles' ? 'active' : ''}`}
          onClick={() => setActiveTab('jointAngles')}
        >
          Joint Angles
        </button>
        <button 
          className={`tab-button ${activeTab === 'smoothness' ? 'active' : ''}`}
          onClick={() => setActiveTab('smoothness')}
        >
          Movement Smoothness
        </button>
        <button 
          className={`tab-button ${activeTab === 'symmetry' ? 'active' : ''}`}
          onClick={() => setActiveTab('symmetry')}
        >
          Symmetry Analysis
        </button>
        <button 
          className={`tab-button ${activeTab === 'balance' ? 'active' : ''}`}
          onClick={() => setActiveTab('balance')}
        >
          Balance Metrics
        </button>
      </div>

      {/* Chart Content */}
      <div className="chart-content">
        {renderChart()}
      </div>

      {/* Recommendations Section */}
      {comparisonData?.recommendations && (
        <div className="recommendations-section">
          <h2>Personalized Recommendations</h2>
          <div className="recommendations-list">
            {comparisonData.recommendations.map((rec, index) => (
              <div key={index} className="recommendation-item">
                <span className="recommendation-number">{index + 1}</span>
                <p>{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Status Summary */}
      <div className="data-status-summary">
        <h3>Data Availability</h3>
        <div className="status-grid">
          {Object.entries(chartData).map(([dataType, data]) => (
            <div key={dataType} className={`status-item ${data ? 'available' : 'missing'}`}>
              <span className="status-icon">{data ? '✅' : '❌'}</span>
              <span className="status-label">{dataType}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ComparisonView;

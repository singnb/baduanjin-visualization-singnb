// ============================================================
// FIXED: src/services/dataLoader.js
// ============================================================
import axios from 'axios';

const API_URL = 'https://baduanjin-backend-docker.azurewebsites.net';
const API_BASE = `${API_URL}/api`; 

// Get the auth token for requests
const getAuthHeader = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// ===================================================================
// NEW COMPARISON DATA FUNCTIONS
// ===================================================================

// Load master data based on type from comparison endpoint
export const loadMasterData = async (analysisType) => {
  try {
    // Get context from URL - check if we're in comparison view
    const pathParts = window.location.pathname.split('/');
    const isComparison = pathParts[1] === 'comparison';
    
    if (isComparison && pathParts.length >= 4) {
      // We're in comparison view: /comparison/userVideoId/masterVideoId
      const masterVideoId = pathParts[3];
      
      // Map analysisType to file names
      const fileTypeMap = {
        'jointAngles': 'joint_angles',
        'smoothness': 'smoothness',
        'symmetry': 'symmetry',
        'balance': 'balance'
      };
      
      const fileName = `master_${fileTypeMap[analysisType]}.json`;
      
      console.log(`Loading master data: ${API_BASE}/analysis-master/data/${masterVideoId}/${fileName}`);
      
      // Get master data from new endpoint
      const response = await axios.get(
        `${API_BASE}/analysis-master/data/${masterVideoId}/${fileName}`,
        { headers: getAuthHeader() }
      );
      
      console.log(`Master ${analysisType} data loaded:`, response.data);
      return response.data;
    } else {
      // Legacy single video analysis - return mock data
      console.log(`Not in comparison view, returning mock data for ${analysisType}`);
      return getMockData(analysisType);
    }
  } catch (error) {
    console.error(`Error loading master ${analysisType} data:`, error);
    console.error('Response:', error.response?.data);
    return getMockData(analysisType);
  }
};

// Load learner data based on type from comparison endpoint
export const loadLearnerData = async (analysisType) => {
  try {
    // Get context from URL - check if we're in comparison view
    const pathParts = window.location.pathname.split('/');
    const isComparison = pathParts[1] === 'comparison';
    
    if (isComparison && pathParts.length >= 4) {
      // We're in comparison view: /comparison/userVideoId/masterVideoId
      const userVideoId = pathParts[2];
      
      // Map analysisType to file names
      const fileTypeMap = {
        'jointAngles': 'joint_angles',
        'smoothness': 'smoothness',
        'symmetry': 'symmetry',
        'balance': 'balance'
      };
      
      const fileName = `learner_${fileTypeMap[analysisType]}.json`;
      
      console.log(`Loading learner data: ${API_BASE}/analysis-master/data/${userVideoId}/${fileName}`);
      
      // Get learner data from new endpoint
      const response = await axios.get(
        `${API_BASE}/analysis-master/data/${userVideoId}/${fileName}`,
        { headers: getAuthHeader() }
      );
      
      console.log(`Learner ${analysisType} data loaded:`, response.data);
      return response.data;
    } else {
      // Legacy single video analysis - return mock data
      console.log(`Not in comparison view, returning mock data for ${analysisType}`);
      return getMockData(analysisType);
    }
  } catch (error) {
    console.error(`Error loading learner ${analysisType} data:`, error);
    console.error('Response:', error.response?.data);
    return getMockData(analysisType);
  }
};

// ===================================================================
// EXISTING LEGACY FUNCTIONS (kept for backward compatibility)
// ===================================================================

// New function to load analysis data from the backend API
export const loadAnalysisData = async (videoId, analysisType) => {
  try {
    const response = await axios.get(`${API_BASE}/videos/${videoId}/analysis`, {
      headers: getAuthHeader()
    });
    
    // Extract the requested analysis type from the response
    if (response.data && response.data[`${analysisType}_data`]) {
      return response.data[`${analysisType}_data`];
    }
    
    return getMockData(analysisType);
  } catch (error) {
    console.error(`Error loading ${analysisType} data:`, error);
    return getMockData(analysisType);
  }
};

// Load user's videos
export const loadUserVideos = async () => {
  try {
    const response = await axios.get(`${API_BASE}/videos`, {
      headers: getAuthHeader()
    });
    return response.data;
  } catch (error) {
    console.error('Error loading videos:', error);
    return [];
  }
};

// Load recommendations for a specific video
export const loadRecommendations = async (videoId) => {
  try {
    const response = await axios.get(`${API_BASE}/videos/${videoId}/analysis`, {
      headers: getAuthHeader()
    });
    
    if (response.data && response.data.recommendations) {
      return response.data.recommendations;
    }
    
    return {
      overall: "No recommendations available yet."
    };
  } catch (error) {
    console.error('Error loading recommendations:', error);
    return {
      overall: "No recommendations available yet."
    };
  }
};

// ===================================================================
// HELPER FUNCTIONS
// ===================================================================

// Mock data function for new users or when API fails
const getMockData = (analysisType) => {
  // Return empty data structures for new users
  switch (analysisType) {
    case 'jointAngles':
      return {
        title: "Joint Angles Analysis",
        description: "No data available",
        frames: [],
        angles: {},
        keyPoseFrames: [],
        keyPoseNames: [],
        rangeOfMotion: {}
      };
    case 'smoothness':
      return {
        title: "Movement Smoothness",
        description: "No data available",
        jerkMetrics: {},
        keypointNames: {},
        movementPhases: [],
        overallSmoothness: 0,
        optimalJerkRange: [0.85, 0.95]
      };
    case 'symmetry':
      return {
        title: "Movement Symmetry",
        description: "No data available",
        symmetryScores: {},
        keypointPairNames: {},
        keyPoseSymmetry: [],
        overallSymmetry: 0,
        optimalSymmetryRange: [0.90, 1.0]
      };
    case 'balance':
      return {
        title: "Balance Analysis",
        description: "No data available",
        balanceMetrics: {},
        comTrajectory: { x: [], y: [], sampleFrames: [] },
        keyPoseBalance: [],
        overallStability: 0,
        optimalStabilityRange: [0.85, 1.0]
      };
    default:
      return { error: 'Unknown analysis type' };
  }
};

// Alternative method to load comparison data directly with video IDs
export const loadComparisonData = async (userVideoId, masterVideoId, dataType) => {
  try {
    const fileTypeMap = {
      'jointAngles': 'joint_angles',
      'smoothness': 'smoothness',
      'symmetry': 'symmetry',
      'balance': 'balance'
    };
    
    console.log(`Loading comparison data for user video ${userVideoId} and master video ${masterVideoId}, type: ${dataType}`);
    
    const results = await Promise.all([
      axios.get(
        `${API_BASE}/analysis-master/data/${userVideoId}/learner_${fileTypeMap[dataType]}.json`,
        { headers: getAuthHeader() }
      ),
      axios.get(
        `${API_BASE}/analysis-master/data/${masterVideoId}/master_${fileTypeMap[dataType]}.json`,
        { headers: getAuthHeader() }
      )
    ]);
    
    return {
      learnerData: results[0].data,
      masterData: results[1].data
    };
  } catch (error) {
    console.error('Error loading comparison data:', error);
    console.error('Error details:', error.response?.data);
    throw error;
  }
};

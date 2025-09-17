// src/config/piConfig.js

export const PI_CONFIG = {
  // Azure Pi Service (primary API)
  AZURE_PI_SERVICE: process.env.REACT_APP_PI_SERVICE_URL || 'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net',
  
  // Direct Pi connection (ngrok tunnel for video streaming)
  DIRECT_PI_URL: process.env.REACT_APP_DIRECT_PI_URL || 'https://mongoose-hardy-caiman.ngrok-free.app',
  
  // Main backend for video storage
  MAIN_BACKEND: process.env.REACT_APP_API_URL || 'https://baduanjin-backend-docker.azurewebsites.net',
  
  // Polling intervals (in milliseconds)
  POLLING: {
    STATUS_INTERVAL: 5000,     // Check Pi status every 5 seconds
    POSE_INTERVAL: 1000,       // Get pose data every 1 second  
    FRAME_INTERVAL: 2000,      // Get video frames every 2 seconds
    UNIFIED_INTERVAL: 2000     // Unified polling interval
  },
  
  // Timeout settings
  TIMEOUTS: {
    STATUS_CHECK: 10000,       // 10 seconds
    API_REQUEST: 15000,        // 15 seconds
    VIDEO_STREAM: 5000         // 5 seconds for video requests
  }
};

// Helper function to check if direct Pi URL is available
export const isDirectPiAvailable = () => {
  return PI_CONFIG.DIRECT_PI_URL && !PI_CONFIG.DIRECT_PI_URL.includes('mongoose-hardy-caiman');
};

// Helper function to get appropriate Pi URL for different operations
export const getPiUrl = (operation = 'api') => {
  switch (operation) {
    case 'video_stream':
      return isDirectPiAvailable() ? PI_CONFIG.DIRECT_PI_URL : null;
    case 'api':
    default:
      return PI_CONFIG.AZURE_PI_SERVICE;
  }
};
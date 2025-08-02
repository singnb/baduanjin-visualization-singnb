// Pi Live Integration Tests - Browser Console
// Copy and paste these functions into your browser console on the Pi Live session page

console.log('=== PI INTEGRATION TESTS ===');

// Global test state
window.piTestState = {
  testResults: [],
  testStartTime: null
};

// Configuration
const PI_CONFIG = {
  BACKEND_URL: 'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net',
  AUTH_TOKEN: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzaW5nbmJAeWFob28uY29tIiwidXNlcl9pZCI6MiwiZXhwIjoxNzUxMjQ4MzY4fQ.Aj3RtCwKbJKnnwO8hIX_lwWW7wowHhzP3NWrt9QIZ-E'
};

// Setup token
localStorage.setItem('authToken', PI_CONFIG.AUTH_TOKEN);
console.log('Auth token configured successfully');

// Helper function to get auth token
function getAuthToken() {
  return localStorage.getItem('authToken') || PI_CONFIG.AUTH_TOKEN;
}

// Helper function to log test results
function logTestResult(testName, passed, message = '') {
  const result = {
    test: testName,
    passed,
    message,
    timestamp: new Date().toISOString()
  };
  
  window.piTestState.testResults.push(result);
  
  const status = passed ? 'PASS' : 'FAIL';
  const icon = passed ? 'checkmark' : 'x';
  console.log(`[${status}] ${testName}: ${icon} ${message}`);
  
  return result;
}

// Test 1: Pi Connection Status
async function testPiConnectionStatus() {
  console.log('--- Testing Pi Connection Status ---');
  
  try {
    const token = getAuthToken();
    if (!token) {
      return logTestResult('Pi Connection', false, 'No auth token');
    }
    
    const response = await fetch(`${PI_CONFIG.BACKEND_URL}/api/pi-live/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!response.ok) {
      return logTestResult('Pi Connection', false, `HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Pi Status Response:', data);
    
    // Test Pi Connection
    const isConnected = data.pi_connected === true;
    logTestResult('Pi Connection', isConnected, `Connected: ${isConnected}`);
    
    // Test Camera Availability  
    const hasCamera = data.camera_available === true;
    logTestResult('Camera Available', hasCamera, `Camera: ${hasCamera}`);
    
    // Test YOLO Availability
    const hasYolo = data.yolo_available === true;
    logTestResult('YOLO Available', hasYolo, `YOLO: ${hasYolo}`);
    
    // Additional status info
    if (data.pi_ip) {
      console.log(`Pi IP Address: ${data.pi_ip}`);
    }
    
    if (data.is_running !== undefined) {
      console.log(`Pi Service Running: ${data.is_running}`);
    }
    
    if (data.persons_detected !== undefined) {
      console.log(`Persons Detected: ${data.persons_detected}`);
    }
    
    return data;
    
  } catch (error) {
    logTestResult('Pi Connection', false, `Error: ${error.message}`);
    console.error('Test error:', error);
    return null;
  }
}

// Test 2: Basic API Health Check
async function testApiHealthCheck() {
  console.log('--- Testing API Health Check ---');
  
  try {
    const token = getAuthToken();
    const response = await fetch(`${PI_CONFIG.BACKEND_URL}/api/pi-live/status`, {
      method: 'GET',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    const responseTime = Date.now();
    const isHealthy = response.ok;
    const statusCode = response.status;
    
    logTestResult('API Health Check', isHealthy, `Status: ${statusCode}`);
    
    if (isHealthy) {
      const data = await response.json();
      console.log('API Response Time:', `${Date.now() - responseTime}ms`);
      console.log('API Response Data Keys:', Object.keys(data));
    }
    
    return { healthy: isHealthy, status: statusCode };
    
  } catch (error) {
    logTestResult('API Health Check', false, `Error: ${error.message}`);
    return { healthy: false, error: error.message };
  }
}

// Test 3: Authentication Validation
async function testAuthenticationValidation() {
  console.log('--- Testing Authentication Validation ---');
  
  try {
    const token = getAuthToken();
    
    // Test with valid token
    const validResponse = await fetch(`${PI_CONFIG.BACKEND_URL}/api/pi-live/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    const validAuth = validResponse.ok;
    logTestResult('Valid Token Authentication', validAuth, `Status: ${validResponse.status}`);
    
    // Test with invalid token
    const invalidResponse = await fetch(`${PI_CONFIG.BACKEND_URL}/api/pi-live/status`, {
      headers: { 'Authorization': 'Bearer invalid-token' }
    });
    
    const invalidAuth = invalidResponse.status === 401;
    logTestResult('Invalid Token Rejection', invalidAuth, `Status: ${invalidResponse.status}`);
    
    // Test with no token
    const noTokenResponse = await fetch(`${PI_CONFIG.BACKEND_URL}/api/pi-live/status`);
    const noTokenAuth = noTokenResponse.status === 401;
    logTestResult('No Token Rejection', noTokenAuth, `Status: ${noTokenResponse.status}`);
    
    return {
      validToken: validAuth,
      invalidTokenRejected: invalidAuth,
      noTokenRejected: noTokenAuth
    };
    
  } catch (error) {
    logTestResult('Authentication Validation', false, `Error: ${error.message}`);
    return null;
  }
}

// Main test runner
async function runSimplifiedPiTests() {
  console.log('=== STARTING SIMPLIFIED PI INTEGRATION TESTS ===');
  console.log(`Backend URL: ${PI_CONFIG.BACKEND_URL}`);
  console.log(`Token configured: ${!!getAuthToken()}`);
  console.log('');
  
  window.piTestState.testStartTime = new Date();
  window.piTestState.testResults = [];
  
  // Run tests in sequence
  await testPiConnectionStatus();
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  await testApiHealthCheck();
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  await testAuthenticationValidation();
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Show results
  showTestResults();
}

// Show test results summary
function showTestResults() {
  console.log('\n=== TEST RESULTS SUMMARY ===');
  
  const results = window.piTestState.testResults;
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => r.passed === false).length;
  const total = results.length;
  
  console.log(`Total Tests: ${total}`);
  console.log(`Passed: ${passed}`);
  console.log(`Failed: ${failed}`);
  console.log(`Success Rate: ${((passed / total) * 100).toFixed(1)}%`);
  
  if (failed > 0) {
    console.log('\nFailed Tests:');
    results.filter(r => r.passed === false).forEach(r => {
      console.log(`- ${r.test}: ${r.message}`);
    });
  }
  
  console.log('\nDetailed Results:');
  results.forEach(r => {
    const status = r.passed ? 'PASS' : 'FAIL';
    console.log(`[${status}] ${r.test}: ${r.message}`);
  });
  
  const testDuration = new Date() - window.piTestState.testStartTime;
  console.log(`\nTest Duration: ${(testDuration / 1000).toFixed(1)} seconds`);
  
  // Overall status
  const overallSuccess = failed === 0;
  console.log(`\nOverall Status: ${overallSuccess ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED'}`);
}

// Quick individual test functions
function quickPiStatus() {
  testPiConnectionStatus();
}

function quickApiHealth() {
  testApiHealthCheck();
}

function quickAuth() {
  testAuthenticationValidation();
}

function quickTokenCheck() {
  const token = getAuthToken();
  console.log('Token Status:', token ? 'Available' : 'Missing');
  console.log('Token Preview:', token ? token.substring(0, 20) + '...' : 'No token');
  console.log('Backend URL:', PI_CONFIG.BACKEND_URL);
}

// Configuration functions
function updateToken(newToken) {
  PI_CONFIG.AUTH_TOKEN = newToken;
  localStorage.setItem('authToken', newToken);
  console.log('Token updated successfully');
}

function updateBackendUrl(newUrl) {
  PI_CONFIG.BACKEND_URL = newUrl;
  console.log('Backend URL updated to:', newUrl);
}

// Test connectivity
async function testConnectivity() {
  console.log('Testing basic connectivity...');
  
  try {
    const response = await fetch(`${PI_CONFIG.BACKEND_URL}/api/pi-live/status`, {
      headers: { 'Authorization': `Bearer ${getAuthToken()}` }
    });
    
    console.log('Connection Status:', response.ok ? 'SUCCESS' : 'FAILED');
    console.log('HTTP Status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Response Data:', data);
    }
    
  } catch (error) {
    console.log('Connection Error:', error.message);
  }
}

// Instructions
console.log(`
=== SIMPLIFIED PI INTEGRATION TESTS ===

Available commands:
- runSimplifiedPiTests()  : Run all 3 basic tests
- quickPiStatus()         : Test Pi connection only
- quickApiHealth()        : Test API health only  
- quickAuth()             : Test authentication only
- quickTokenCheck()       : Check token status
- testConnectivity()      : Quick connectivity test
- showTestResults()       : Show latest results

Configuration:
- updateToken('new-token')    : Update auth token
- updateBackendUrl('new-url') : Update backend URL

Quick start: runSimplifiedPiTests()
`);

console.log('Ready to test! Token and backend URL configured.');
console.log('Run: runSimplifiedPiTests()');
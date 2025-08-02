// Simple Integration Test Script
// Copy and paste this entire code block into browser console

const runIntegrationTest = async () => {
  console.log('BADUANJIN INTEGRATION TEST STARTING...');
  console.log('================================================');
  
  let testResults = {
    backend: 'NOT TESTED',
    registration: 'NOT TESTED',
    login: 'NOT TESTED',
    overall: 'FAILED'
  };
  
  // Test 1: Backend Connectivity
  console.log('\nTEST 1: Backend Connectivity');
  try {
    const response = await fetch('https://baduanjin-backend-docker.azurewebsites.net/docs');
    if (response.ok) {
      console.log('PASS: Backend is responding (Status: ' + response.status + ')');
      testResults.backend = 'PASS';
    } else {
      console.log('FAIL: Backend error (Status: ' + response.status + ')');
      testResults.backend = 'FAIL';
    }
  } catch (error) {
    console.log('FAIL: Cannot reach backend - ' + error.message);
    testResults.backend = 'FAIL';
    return testResults; // Stop if backend not reachable
  }
  
  // Test 2: User Registration
  console.log('\n TEST 2: User Registration');
  const timestamp = Date.now();
  const testUser = {
    username: `testuser${timestamp}`,
    email: `test${timestamp}@example.com`,
    password: 'password123',
    name: 'Integration Test User',
    role: 'learner'
  };
  
  try {
    const regResponse = await fetch('https://baduanjin-backend-docker.azurewebsites.net/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testUser)
    });
    
    const regResult = await regResponse.json();
    
    if (regResponse.ok) {
      console.log('PASS: User registration successful');
      console.log('   Email: ' + testUser.email);
      console.log('   User ID: ' + regResult.user_id);
      testResults.registration = 'PASS';
    } else {
      console.log('FAIL: Registration failed - ' + regResult.detail);
      testResults.registration = 'FAIL';
      return testResults;
    }
  } catch (error) {
    console.log('FAIL: Registration error - ' + error.message);
    testResults.registration = 'FAIL';
    return testResults;
  }
  
  // Test 3: User Login
  console.log('\n TEST 3: User Login');
  try {
    const loginResponse = await fetch('https://baduanjin-backend-docker.azurewebsites.net/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: testUser.email,
        password: testUser.password
      })
    });
    
    const loginResult = await loginResponse.json();
    
    if (loginResponse.ok) {
      console.log('PASS: User login successful');
      console.log('   Token received: ' + (loginResult.access_token ? 'YES' : 'NO'));
      console.log('   User role: ' + loginResult.user.role);
      testResults.login = 'PASS';
      testResults.overall = 'PASS';
    } else {
      console.log('FAIL: Login failed - ' + loginResult.detail);
      testResults.login = 'FAIL';
    }
  } catch (error) {
    console.log('FAIL: Login error - ' + error.message);
    testResults.login = 'FAIL';
  }
  
  // Test Summary
  console.log('\n TEST RESULTS SUMMARY');
  console.log('================================================');
  console.log('Backend Connectivity: ' + testResults.backend);
  console.log('User Registration:    ' + testResults.registration);
  console.log('User Login:          ' + testResults.login);
  console.log('================================================');
  console.log('OVERALL RESULT:      ' + testResults.overall);
  console.log('================================================');
  
  if (testResults.overall === 'PASS') {
    console.log('INTEGRATION TEST: ALL SYSTEMS WORKING!');
    console.log('Frontend can communicate with backend');
    console.log('Users can register successfully');
    console.log('Users can login successfully');
    console.log('Authentication system is functional');
  } else {
    console.log('INTEGRATION TEST: ISSUES FOUND');
    console.log('Check failed tests above for details');
  }
  
  return testResults;
};

// Test invalid login (should fail)
const testInvalidLogin = async () => {
  console.log('\n EXTRA TEST: Invalid Login (Should Fail)');
  try {
    const response = await fetch('https://baduanjin-backend-docker.azurewebsites.net/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'nonexistent@test.com',
        password: 'wrongpassword'
      })
    });
    
    if (response.status === 401) {
      console.log('PASS: Invalid login correctly rejected (401 Unauthorized)');
      return true;
    } else {
      console.log('FAIL: Invalid login should return 401, got: ' + response.status);
      return false;
    }
  } catch (error) {
    console.log('FAIL: Error testing invalid login - ' + error.message);
    return false;
  }
};

// console.log('Integration test functions loaded!');
// console.log('');
// console.log('To run the test:');
// console.log('1. Copy the above codes and paste in console');
// console.log('2. Type: runIntegrationTest()');
// console.log('3. Press Enter and wait for results');
// console.log('4. Extra: Type testInvalidLogin() to test error handling');

// run the test script
runIntegrationTest();

// run the extra test script for fail
testInvalidLogin();
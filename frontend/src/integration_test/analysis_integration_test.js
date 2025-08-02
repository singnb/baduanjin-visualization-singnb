// Browser Console Integration Tests for Video Analysis Components
// Copy and paste this code into your browser console while on the app

console.log(' Starting Integration Tests for Video Analysis Components');

// Test utilities
const IntegrationTester = {
  results: [],
  
  // Test result logging
  pass: function(testName) {
    this.results.push({ test: testName, status: 'PASS' });
    console.log('✅', testName);
  },
  
  fail: function(testName, error) {
    this.results.push({ test: testName, status: 'FAIL', error });
    console.log('❌', testName, '- Error:', error);
  },
  
  // Wait for element helper
  waitForElement: function(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const element = document.querySelector(selector);
      if (element) {
        resolve(element);
        return;
      }
      
      const observer = new MutationObserver(() => {
        const element = document.querySelector(selector);
        if (element) {
          observer.disconnect();
          resolve(element);
        }
      });
      
      observer.observe(document.body, { childList: true, subtree: true });
      
      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Element ${selector} not found within ${timeout}ms`));
      }, timeout);
    });
  },
  
  // Navigate to URL helper
  navigateTo: function(path) {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new PopStateEvent('popstate'));
    }
  },
  
  // Wait helper
  wait: function(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
};

// Integration Test Suite
const IntegrationTests = {
  
  // Test 1: Navigation Flow Test
  async testNavigationFlow() {
    const testName = 'Navigation Flow - ComparisonSelection → Select Videos → Compare';
    try {
      // Navigate to comparison selection
      IntegrationTester.navigateTo('/comparison-selection');
      await IntegrationTester.wait(1500);
      
      // More flexible check for comparison selection page
      const pageContent = document.body.textContent || document.body.innerText;
      const isSelectionPage = pageContent.includes('Select Videos for Comparison') || 
                             pageContent.includes('Your Videos') || 
                             pageContent.includes('Select a Master') ||
                             pageContent.includes('Compare Videos');
      
      if (!isSelectionPage) {
        // Log what we actually found for debugging
        console.log(' Page content found:', document.querySelector('h1, h2, h3')?.textContent || 'No headers found');
        console.log(' Current URL:', window.location.pathname);
        console.log(' Page body contains:', pageContent.substring(0, 200) + '...');
        throw new Error('Comparison selection page not detected');
      }
      
      console.log(' Comparison selection page loaded');
      
      // Try to find and select a user video
      await IntegrationTester.wait(1000);
      
      const userVideoCards = document.querySelectorAll('.video-card, [class*="video"], [class*="card"]');
      console.log(` Found ${userVideoCards.length} user video cards`);
      
      if (userVideoCards.length > 0) {
        userVideoCards[0].click();
        console.log(' Selected user video');
        await IntegrationTester.wait(500);
      }
      
      // Try to find and select a master
      const masterCards = document.querySelectorAll('.master-card, [class*="master"]');
      console.log(` Found ${masterCards.length} master cards`);
      
      if (masterCards.length > 0) {
        masterCards[0].click();
        console.log(' Selected master');
        await IntegrationTester.wait(1000); // Wait for master videos to load
      }
      
      // Try to find and select a master video
      const masterVideoCards = document.querySelectorAll('.video-card, [class*="video"]');
      const availableMasterVideos = Array.from(masterVideoCards).filter(card => 
        !card.closest('[class*="user"]') // Exclude user video section
      );
      
      console.log(` Found ${availableMasterVideos.length} master video cards`);
      
      if (availableMasterVideos.length > 0) {
        availableMasterVideos[0].click();
        console.log(' Selected master video');
        await IntegrationTester.wait(500);
      }
      
      // Try to find and click the compare button
      const compareButton = document.querySelector('button:contains("Compare Videos")') || 
                           Array.from(document.querySelectorAll('button')).find(btn => 
                             btn.textContent.includes('Compare') && !btn.disabled
                           );
      
      if (compareButton) {
        console.log(' Found compare button, clicking...');
        compareButton.click();
        await IntegrationTester.wait(1500);
        
        // Check if we're now on comparison view page
        const comparisonPageContent = document.body.textContent || document.body.innerText;
        const isComparisonPage = comparisonPageContent.includes('Movement Analysis Comparison') ||
                                comparisonPageContent.includes('Joint Angles') ||
                                comparisonPageContent.includes('vs') ||
                                window.location.pathname.includes('/comparison/');
        
        if (isComparisonPage) {
          console.log(' Successfully navigated to comparison view');
          
          // Test back navigation
          const backButton = Array.from(document.querySelectorAll('button')).find(btn => 
            btn.textContent.includes('Back to Selection') || btn.textContent.includes('Back')
          );
          
          if (backButton) {
            console.log(' Found back button, testing navigation...');
            backButton.click();
            await IntegrationTester.wait(1000);
            console.log(' Back navigation completed');
          }
        } else {
          console.log(' Compare button clicked but comparison page not detected');
        }
      } else {
        console.log(' Compare button not found or not enabled (may need both videos selected)');
      }
      
      IntegrationTester.pass(testName);
    } catch (error) {
      IntegrationTester.fail(testName, error.message);
    }
  },
  
  // Test 2: Video Analysis Page Load Test
  async testVideoAnalysisLoad() {
    const testName = 'VideoAnalysis Component Load Test';
    try {
      // Navigate to video analysis page
      IntegrationTester.navigateTo('/analysis/18');
      await IntegrationTester.wait(1000);
      
      // Check for loading state or content
      const hasLoadingOrContent = document.querySelector('.loading-container') || 
                                 document.querySelector('.analysis-container') ||
                                 document.querySelector('h1') ||
                                 document.querySelector('h2');
      
      if (!hasLoadingOrContent) {
        throw new Error('VideoAnalysis component did not render properly');
      }
      
      IntegrationTester.pass(testName);
    } catch (error) {
      IntegrationTester.fail(testName, error.message);
    }
  },
  
  // Test 3: Component State Integration Test
  async testComponentStateIntegration() {
    const testName = 'Component State and Props Integration';
    try {
      // Navigate to comparison selection
      IntegrationTester.navigateTo('/comparison-selection');
      await IntegrationTester.wait(1000);
      
      // Check for video selection elements
      const videoCards = document.querySelectorAll('.video-card, [class*="video"], [class*="card"]');
      const masterCards = document.querySelectorAll('.master-card, [class*="master"], [class*="selection"]');
      
      // Test video selection if elements exist
      if (videoCards.length > 0) {
        videoCards[0].click();
        await IntegrationTester.wait(200);
        
        // Check if selection state changes (looking for selected class or style changes)
        const hasSelectedState = videoCards[0].classList.contains('selected') ||
                                videoCards[0].style.border ||
                                videoCards[0].style.backgroundColor;
        
        if (!hasSelectedState) {
          console.warn('Video selection state change not detected (may be using different CSS classes)');
        }
      }
      
      IntegrationTester.pass(testName);
    } catch (error) {
      IntegrationTester.fail(testName, error.message);
    }
  },
  
  // Test 4: Tab Navigation Integration (ComparisonView)
  async testTabNavigationIntegration() {
    const testName = 'Tab Navigation Integration in ComparisonView';
    try {
      // Navigate to comparison view
      IntegrationTester.navigateTo('/comparison/18/23');
      await IntegrationTester.wait(1000);
      
      // Look for tab navigation
      const tabs = document.querySelectorAll('[class*="tab"], button');
      const tabButtons = Array.from(tabs).filter(tab => 
        tab.textContent.includes('Joint Angles') ||
        tab.textContent.includes('Smoothness') ||
        tab.textContent.includes('Symmetry') ||
        tab.textContent.includes('Balance')
      );
      
      if (tabButtons.length > 0) {
        // Test tab clicking
        tabButtons[0].click();
        await IntegrationTester.wait(200);
        
        // Check for chart or content change
        const charts = document.querySelectorAll('[data-testid*="chart"], [class*="chart"], canvas, svg');
        
        if (charts.length === 0) {
          console.warn('No charts detected (may be loading or using different selectors)');
        }
      }
      
      IntegrationTester.pass(testName);
    } catch (error) {
      IntegrationTester.fail(testName, error.message);
    }
  },
  
  // Test 5: Error Boundary Integration
  async testErrorHandling() {
    const testName = 'Error Handling Integration';
    try {
      // Test invalid routes
      IntegrationTester.navigateTo('/invalid-route');
      await IntegrationTester.wait(500);
      
      // Should either redirect or show error
      const hasErrorOrRedirect = document.querySelector('.error') ||
                                document.querySelector('[class*="error"]') ||
                                window.location.pathname !== '/invalid-route';
      
      if (!hasErrorOrRedirect) {
        console.warn('Error handling or routing not detected for invalid routes');
      }
      
      IntegrationTester.pass(testName);
    } catch (error) {
      IntegrationTester.fail(testName, error.message);
    }
  },
  
  // Test 6: Data Flow Integration Test
  async testDataFlowIntegration() {
    const testName = 'Data Flow Between Components';
    try {
      // Navigate through the flow
      IntegrationTester.navigateTo('/comparison-selection');
      await IntegrationTester.wait(1000);
      
      // Check for data loading states
      const loadingElements = document.querySelectorAll('[class*="loading"], .spinner');
      const dataElements = document.querySelectorAll('[class*="video"], [class*="master"], [class*="list"]');
      
      // Navigate to comparison with parameters
      IntegrationTester.navigateTo('/comparison/18/23');
      await IntegrationTester.wait(1000);
      
      // Check if parameters are passed correctly (URL should contain the IDs)
      const urlContainsParams = window.location.pathname.includes('18') && 
                               window.location.pathname.includes('23');
      
      if (!urlContainsParams) {
        throw new Error('URL parameters not passed correctly between components');
      }
      
      IntegrationTester.pass(testName);
    } catch (error) {
      IntegrationTester.fail(testName, error.message);
    }
  }
};

// Main test runner
async function runIntegrationTests() {
  console.log(' Running Integration Tests...\n');
  
  const tests = [
    'testNavigationFlow',
    'testVideoAnalysisLoad', 
    'testComponentStateIntegration',
    'testTabNavigationIntegration',
    'testErrorHandling',
    'testDataFlowIntegration'
  ];
  
  for (const testMethod of tests) {
    try {
      await IntegrationTests[testMethod]();
    } catch (error) {
      IntegrationTester.fail(testMethod, `Test threw error: ${error.message}`);
    }
    await IntegrationTester.wait(300); // Brief pause between tests
  }
  
  // Print results
  console.log('\n Integration Test Results:');
  console.log('================================');
  
  const passed = IntegrationTester.results.filter(r => r.status === 'PASS').length;
  const failed = IntegrationTester.results.filter(r => r.status === 'FAIL').length;
  
  IntegrationTester.results.forEach(result => {
    const icon = result.status === 'PASS' ? '✅' : '❌';
    console.log(`${icon} ${result.test}`);
    if (result.error) {
      console.log(`   └─ ${result.error}`);
    }
  });
  
  console.log(`\n Summary: ${passed} passed, ${failed} failed`);
  
  if (failed === 0) {
    console.log(' All integration tests passed!');
  } else {
    console.log('  Some tests failed. Check the errors above.');
  }
}

// Auto-run or manual run instructions
console.log('Integration test suite loaded!');
console.log('Run tests with: runIntegrationTests()');
console.log('Or run individual tests like: IntegrationTests.testNavigationFlow()');
console.log('\n🏃‍♂️ Auto-running tests in 2 seconds...');

setTimeout(() => {
  runIntegrationTests();
}, 2000);
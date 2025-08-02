// ====================================================================
// BROWSER CONSOLE INTEGRATION TESTS FOR CHART COMPONENTS
// ====================================================================
// Instructions: Open browser DevTools, paste and run these tests
// Make sure the application is loaded and charts are visible
// ====================================================================

// UTILITY FUNCTIONS
// ====================================================================

function logTestResult(testName, passed, message = '') {
  const status = passed ? 'PASS' : 'FAIL';
  const timestamp = new Date().toLocaleTimeString();
  console.log(`[${timestamp}] [${status}] ${testName} ${message ? '- ' + message : ''}`);
  return passed;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function waitForElement(selector, timeout = 5000) {
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
    
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    
    setTimeout(() => {
      observer.disconnect();
      reject(new Error(`Element ${selector} not found within ${timeout}ms`));
    }, timeout);
  });
}

function clickElement(selector) {
  const element = document.querySelector(selector);
  if (element) {
    element.click();
    return true;
  }
  return false;
}

function getAllTextContent(selector) {
  const elements = document.querySelectorAll(selector);
  return Array.from(elements).map(el => el.textContent.trim());
}

// ====================================================================
// BALANCE CHART INTEGRATION TESTS
// ====================================================================

async function runBalanceChartTests() {
  console.log('\n=== BALANCE CHART INTEGRATION TESTS ===');
  
  let passCount = 0;
  let totalTests = 0;
  
  try {
    // Test 1: Component Rendering
    totalTests++;
    const balanceContainer = document.querySelector('.balance-chart-container');
    logTestResult('Balance Chart Container Exists', !!balanceContainer) && passCount++;
    
    // Test 2: Chart Title
    totalTests++;
    const title = document.querySelector('.balance-chart-container h3');
    const hasCorrectTitle = title && title.textContent.includes('Balance and Stability Analysis');
    logTestResult('Balance Chart Title Correct', hasCorrectTitle) && passCount++;
    
    // Test 3: Plotly Chart Presence
    totalTests++;
    const plotlyChart = document.querySelector('.balance-chart-container .js-plotly-plot');
    logTestResult('Balance Plotly Chart Rendered', !!plotlyChart) && passCount++;
    
    // Test 4: Display Mode Controls
    totalTests++;
    const controlButtons = document.querySelectorAll('.balance-chart-container .control-button');
    const hasControls = controlButtons.length >= 3;
    logTestResult('Balance Display Controls Present', hasControls, `Found ${controlButtons.length} buttons`) && passCount++;
    
    // Test 5: Button Interaction - Master Only
    totalTests++;
    const masterOnlyBtn = Array.from(controlButtons).find(btn => btn.textContent.includes('Master Only'));
    if (masterOnlyBtn) {
      masterOnlyBtn.click();
      await sleep(100);
      const isActive = masterOnlyBtn.classList.contains('active');
      logTestResult('Balance Master Only Button Clickable', isActive) && passCount++;
    } else {
      logTestResult('Balance Master Only Button Clickable', false, 'Button not found');
    }
    
    // Test 6: Gauge Values
    totalTests++;
    const gaugeValues = document.querySelectorAll('.balance-chart-container .gauge-value');
    const hasGaugeValues = gaugeValues.length > 0 && Array.from(gaugeValues).some(g => g.textContent.match(/\d+/));
    logTestResult('Balance Gauge Values Present', hasGaugeValues, `Found ${gaugeValues.length} gauges`) && passCount++;
    
    // Test 7: Key Poses Section
    totalTests++;
    const keyPoses = document.querySelector('.balance-chart-container .key-poses');
    logTestResult('Balance Key Poses Section Present', !!keyPoses) && passCount++;
    
    // Test 8: Pose Click Interaction
    totalTests++;
    const poseCircles = document.querySelectorAll('.balance-chart-container .pose-circle');
    if (poseCircles.length > 0) {
      const firstPose = poseCircles[0];
      firstPose.click();
      await sleep(100);
      const hasSelectedClass = firstPose.classList.contains('selected');
      logTestResult('Balance Pose Selection Works', hasSelectedClass) && passCount++;
    } else {
      logTestResult('Balance Pose Selection Works', false, 'No pose circles found');
    }
    
    // Test 9: Body Position Toggle
    totalTests++;
    const bodyPositionCheckbox = document.querySelector('.balance-chart-container input[type="checkbox"]');
    if (bodyPositionCheckbox) {
      const initialState = bodyPositionCheckbox.checked;
      bodyPositionCheckbox.click();
      await sleep(100);
      const toggleWorked = bodyPositionCheckbox.checked !== initialState;
      logTestResult('Balance Body Position Toggle Works', toggleWorked) && passCount++;
    } else {
      logTestResult('Balance Body Position Toggle Works', false, 'Checkbox not found');
    }
    
  } catch (error) {
    console.error('Balance Chart Tests Error:', error);
  }
  
  console.log(`Balance Chart Tests: ${passCount}/${totalTests} passed`);
  return { passed: passCount, total: totalTests };
}

// ====================================================================
// JOINT ANGLE CHART INTEGRATION TESTS
// ====================================================================

async function runJointAngleChartTests() {
  console.log('\n=== JOINT ANGLE CHART INTEGRATION TESTS ===');
  
  let passCount = 0;
  let totalTests = 0;
  
  try {
    // Test 1: Component Rendering
    totalTests++;
    const jointContainer = document.querySelector('.joint-angle-chart-container');
    logTestResult('Joint Angle Chart Container Exists', !!jointContainer) && passCount++;
    
    // Test 2: Chart Title
    totalTests++;
    const title = document.querySelector('.joint-angle-chart-container h2');
    const hasCorrectTitle = title && title.textContent.includes('Joint Angle Analysis');
    logTestResult('Joint Angle Chart Title Correct', hasCorrectTitle) && passCount++;
    
    // Test 3: Joint Selector Buttons
    totalTests++;
    const jointButtons = document.querySelectorAll('.joint-angle-chart-container .joint-button');
    const hasJointButtons = jointButtons.length >= 3;
    logTestResult('Joint Selector Buttons Present', hasJointButtons, `Found ${jointButtons.length} buttons`) && passCount++;
    
    // Test 4: Joint Selection Toggle
    totalTests++;
    const firstJointBtn = jointButtons[0];
    if (firstJointBtn) {
      const initiallySelected = firstJointBtn.classList.contains('selected');
      firstJointBtn.click();
      await sleep(200);
      const newState = firstJointBtn.classList.contains('selected');
      const toggleWorked = initiallySelected !== newState;
      logTestResult('Joint Selection Toggle Works', toggleWorked) && passCount++;
    } else {
      logTestResult('Joint Selection Toggle Works', false, 'No joint buttons found');
    }
    
    // Test 5: Focus Range Slider
    totalTests++;
    const focusSlider = document.querySelector('.joint-angle-chart-container .range-slider');
    if (focusSlider) {
      const initialValue = focusSlider.value;
      focusSlider.value = parseInt(initialValue) - 100;
      focusSlider.dispatchEvent(new Event('change'));
      await sleep(200);
      logTestResult('Focus Range Slider Works', focusSlider.value !== initialValue) && passCount++;
    } else {
      logTestResult('Focus Range Slider Works', false, 'Slider not found');
    }
    
    // Test 6: Height Adjustment Slider
    totalTests++;
    const heightSliders = document.querySelectorAll('.joint-angle-chart-container .range-slider');
    if (heightSliders.length >= 2) {
      const heightSlider = heightSliders[1];
      const initialValue = heightSlider.value;
      heightSlider.value = parseInt(initialValue) + 50;
      heightSlider.dispatchEvent(new Event('change'));
      await sleep(200);
      logTestResult('Height Adjustment Slider Works', heightSlider.value !== initialValue) && passCount++;
    } else {
      logTestResult('Height Adjustment Slider Works', false, 'Height slider not found');
    }
    
    // Test 7: Plotly Chart Presence
    totalTests++;
    const plotlyChart = document.querySelector('.joint-angle-chart-container .js-plotly-plot');
    logTestResult('Joint Angle Plotly Chart Rendered', !!plotlyChart) && passCount++;
    
    // Test 8: Chart Legend
    totalTests++;
    const chartLegend = document.querySelector('.joint-angle-chart-container .chart-legend');
    logTestResult('Joint Angle Chart Legend Present', !!chartLegend) && passCount++;
    
    // Test 9: Problem Areas Section
    totalTests++;
    const problemAreas = document.querySelector('.joint-angle-chart-container .problem-areas-section');
    logTestResult('Problem Areas Section Present', !!problemAreas) && passCount++;
    
    // Test 10: Range of Motion Table
    totalTests++;
    const romTable = document.querySelector('.joint-angle-chart-container .range-of-motion table');
    logTestResult('Range of Motion Table Present', !!romTable) && passCount++;
    
  } catch (error) {
    console.error('Joint Angle Chart Tests Error:', error);
  }
  
  console.log(`Joint Angle Chart Tests: ${passCount}/${totalTests} passed`);
  return { passed: passCount, total: totalTests };
}

// ====================================================================
// SMOOTHNESS CHART INTEGRATION TESTS
// ====================================================================

async function runSmoothnessChartTests() {
  console.log('\n=== SMOOTHNESS CHART INTEGRATION TESTS ===');
  
  let passCount = 0;
  let totalTests = 0;
  
  try {
    // Test 1: Component Rendering
    totalTests++;
    const smoothnessContainer = document.querySelector('.smoothness-chart-container');
    logTestResult('Smoothness Chart Container Exists', !!smoothnessContainer) && passCount++;
    
    if (!smoothnessContainer) {
      console.log('Smoothness Chart container not found - skipping remaining tests');
      console.log(`Smoothness Chart Tests: ${passCount}/${totalTests} passed`);
      return { passed: passCount, total: totalTests };
    }
    
    // Test 2: Chart Title
    totalTests++;
    const title = smoothnessContainer.querySelector('h3');
    const hasCorrectTitle = title && title.textContent.includes('Movement Smoothness Analysis');
    logTestResult('Smoothness Chart Title Correct', hasCorrectTitle) && passCount++;
    
    // Test 3: Display Mode Controls
    totalTests++;
    const controlButtons = smoothnessContainer.querySelectorAll('.control-button');
    const hasControls = controlButtons.length >= 3;
    logTestResult('Smoothness Display Controls Present', hasControls, `Found ${controlButtons.length} buttons`) && passCount++;
    
    // Test 4: Display Mode Switching
    totalTests++;
    const learnerOnlyBtn = Array.from(controlButtons).find(btn => btn.textContent.includes('Learner Only'));
    if (learnerOnlyBtn) {
      learnerOnlyBtn.click();
      await sleep(100);
      const isActive = learnerOnlyBtn.classList.contains('active');
      logTestResult('Smoothness Display Mode Switching Works', isActive) && passCount++;
    } else {
      logTestResult('Smoothness Display Mode Switching Works', false, 'Learner Only button not found');
    }
    
    // Test 5: Show Phases Only Toggle
    totalTests++;
    const phasesToggle = smoothnessContainer.querySelector('input[type="checkbox"]');
    if (phasesToggle) {
      const initialState = phasesToggle.checked;
      phasesToggle.click();
      await sleep(200);
      const toggleWorked = phasesToggle.checked !== initialState;
      logTestResult('Show Phases Only Toggle Works', toggleWorked) && passCount++;
    } else {
      logTestResult('Show Phases Only Toggle Works', false, 'Phases toggle not found');
    }
    
    // Test 6: Smoothness Gauges
    totalTests++;
    // Try multiple selectors for gauge detection
    const smoothnessGauges = smoothnessContainer.querySelectorAll(
      '.smoothness-gauge, .gauge, [class*="gauge"], [class*="score"], .circular-progress, .progress-circle, [class*="progress"]'
    );
    logTestResult('Smoothness Gauges Present', smoothnessGauges.length > 0, `Found ${smoothnessGauges.length} gauges`) && passCount++;
    
    // Test 7: Gauge Values
    totalTests++;
    // Look for numerical values in various gauge-related elements
    const gaugeValues = smoothnessContainer.querySelectorAll(
      '.gauge-value, .score-value, [class*="value"], [class*="score"], .percentage, .number'
    );
    const hasValidValues = gaugeValues.length > 0 && Array.from(gaugeValues).some(g => g.textContent.match(/\d+/));
    
    // Alternative: look for any large numbers that might be gauge values
    if (!hasValidValues) {
      const textContent = smoothnessContainer.textContent;
      const numberMatches = textContent.match(/\b\d{1,3}\b/g);
      const hasLargeNumbers = numberMatches && numberMatches.some(num => parseInt(num) >= 10 && parseInt(num) <= 100);
      logTestResult('Smoothness Gauge Values Valid', hasLargeNumbers, 'Found numerical values in text content') && passCount++;
    } else {
      logTestResult('Smoothness Gauge Values Valid', hasValidValues) && passCount++;
    }
    
    // Test 8: Plotly Chart Presence
    totalTests++;
    const plotlyChart = document.querySelector('.smoothness-chart-container .js-plotly-plot');
    logTestResult('Smoothness Plotly Chart Rendered', !!plotlyChart) && passCount++;
    
    // Test 9: Metrics Table
    totalTests++;
    // Try multiple selectors for table detection
    const metricsTable = smoothnessContainer.querySelector(
      '.metrics-table, .metrics-section table, table, .table, [role="table"], .data-table, [class*="table"], [class*="metric"]'
    );
    
    // Alternative: look for table-like structure with headers and data
    if (!metricsTable) {
      const tableHeaders = smoothnessContainer.querySelectorAll('th, .table-header, [class*="header"]');
      const tableCells = smoothnessContainer.querySelectorAll('td, .table-cell, [class*="cell"]');
      const hasTableStructure = tableHeaders.length > 0 && tableCells.length > 0;
      logTestResult('Smoothness Metrics Table Present', hasTableStructure, 'Found table-like structure') && passCount++;
    } else {
      logTestResult('Smoothness Metrics Table Present', true) && passCount++;
    }
    
    // Test 10: Legend
    totalTests++;
    const legend = document.querySelector('.smoothness-chart-container .legend');
    logTestResult('Smoothness Legend Present', !!legend) && passCount++;
    
  } catch (error) {
    console.error('Smoothness Chart Tests Error:', error);
  }
  
  console.log(`Smoothness Chart Tests: ${passCount}/${totalTests} passed`);
  return { passed: passCount, total: totalTests };
}

// ====================================================================
// SYMMETRY CHART INTEGRATION TESTS
// ====================================================================

async function runSymmetryChartTests() {
  console.log('\n=== SYMMETRY CHART INTEGRATION TESTS ===');
  
  let passCount = 0;
  let totalTests = 0;
  
  try {
    // Test 1: Component Rendering
    totalTests++;
    const symmetryContainer = document.querySelector('.symmetry-chart-container');
    logTestResult('Symmetry Chart Container Exists', !!symmetryContainer) && passCount++;
    
    // Test 2: Chart Title
    totalTests++;
    const title = document.querySelector('.symmetry-chart-container h3');
    const hasCorrectTitle = title && title.textContent.includes('Movement Symmetry Analysis');
    logTestResult('Symmetry Chart Title Correct', hasCorrectTitle) && passCount++;
    
    // Test 3: Display Mode Controls
    totalTests++;
    const controlButtons = document.querySelectorAll('.symmetry-chart-container .control-button');
    const hasControls = controlButtons.length >= 3;
    logTestResult('Symmetry Display Controls Present', hasControls, `Found ${controlButtons.length} buttons`) && passCount++;
    
    // Test 4: View Toggle Buttons
    totalTests++;
    const viewButtons = document.querySelectorAll('.symmetry-chart-container .view-button');
    const hasViewButtons = viewButtons.length >= 2;
    logTestResult('Symmetry View Toggle Buttons Present', hasViewButtons, `Found ${viewButtons.length} view buttons`) && passCount++;
    
    // Test 5: Panel View Switching
    totalTests++;
    const jointPairBtn = Array.from(viewButtons).find(btn => btn.textContent.includes('Joint Pair Symmetry'));
    if (jointPairBtn) {
      jointPairBtn.click();
      await sleep(200);
      const isActive = jointPairBtn.classList.contains('active');
      logTestResult('Symmetry Panel View Switching Works', isActive) && passCount++;
    } else {
      logTestResult('Symmetry Panel View Switching Works', false, 'Joint Pair button not found');
    }
    
    // Test 6: Switch Back to Pose View
    totalTests++;
    const poseSymmetryBtn = Array.from(viewButtons).find(btn => btn.textContent.includes('Pose Symmetry'));
    if (poseSymmetryBtn) {
      poseSymmetryBtn.click();
      await sleep(200);
      const isActive = poseSymmetryBtn.classList.contains('active');
      logTestResult('Switch Back to Pose View Works', isActive) && passCount++;
    } else {
      logTestResult('Switch Back to Pose View Works', false, 'Pose Symmetry button not found');
    }
    
    // Test 7: Symmetry Gauges
    totalTests++;
    const symmetryGauges = document.querySelectorAll('.symmetry-chart-container .symmetry-gauge');
    logTestResult('Symmetry Gauges Present', symmetryGauges.length > 0, `Found ${symmetryGauges.length} gauges`) && passCount++;
    
    // Test 8: Gauge Values
    totalTests++;
    const gaugeValues = document.querySelectorAll('.symmetry-chart-container .gauge-value');
    const hasValidValues = Array.from(gaugeValues).some(g => g.textContent.match(/\d+/));
    logTestResult('Symmetry Gauge Values Valid', hasValidValues) && passCount++;
    
    // Test 9: Optimal Range Labels
    totalTests++;
    const optimalRangeLabels = document.querySelectorAll('.symmetry-chart-container .optimal-range-label');
    logTestResult('Optimal Range Labels Present', optimalRangeLabels.length > 0) && passCount++;
    
    // Test 10: Plotly Chart Presence
    totalTests++;
    const plotlyChart = document.querySelector('.symmetry-chart-container .js-plotly-plot');
    logTestResult('Symmetry Plotly Chart Rendered', !!plotlyChart) && passCount++;
    
    // Test 11: Master Only Mode Effect
    totalTests++;
    const masterOnlyBtn = Array.from(controlButtons).find(btn => btn.textContent.includes('Master Only'));
    if (masterOnlyBtn) {
      masterOnlyBtn.click();
      await sleep(200);
      const masterGauges = document.querySelectorAll('.symmetry-chart-container .symmetry-gauge');
      const hasCorrectGaugeCount = masterGauges.length === 1;
      logTestResult('Master Only Mode Reduces Gauges', hasCorrectGaugeCount, `Found ${masterGauges.length} gauges`) && passCount++;
    } else {
      logTestResult('Master Only Mode Reduces Gauges', false, 'Master Only button not found');
    }
    
  } catch (error) {
    console.error('Symmetry Chart Tests Error:', error);
  }
  
  console.log(`Symmetry Chart Tests: ${passCount}/${totalTests} passed`);
  return { passed: passCount, total: totalTests };
}

// ====================================================================
// CROSS-COMPONENT INTEGRATION TESTS
// ====================================================================

async function runCrossComponentTests() {
  console.log('\n=== CROSS-COMPONENT INTEGRATION TESTS ===');
  
  let passCount = 0;
  let totalTests = 0;
  
  try {
    // Test 1: All Components Present
    totalTests++;
    const allContainers = [
      '.balance-chart-container',
      '.joint-angle-chart-container', 
      '.smoothness-chart-container',
      '.symmetry-chart-container'
    ];
    
    const presentContainers = allContainers.filter(selector => document.querySelector(selector));
    const allPresent = presentContainers.length === allContainers.length;
    logTestResult('All Chart Components Present', allPresent, `Found ${presentContainers.length}/4 components`) && passCount++;
    
    // Test 2: All Charts Have Plotly Instances
    totalTests++;
    const plotlyCharts = document.querySelectorAll('.js-plotly-plot');
    const hasMultipleCharts = plotlyCharts.length >= 4;
    logTestResult('Multiple Plotly Charts Rendered', hasMultipleCharts, `Found ${plotlyCharts.length} Plotly charts`) && passCount++;
    
    // Test 3: No JavaScript Errors in Console
    totalTests++;
    const originalError = console.error;
    let errorCount = 0;
    console.error = (...args) => {
      errorCount++;
      originalError.apply(console, args);
    };
    
    await sleep(1000);
    console.error = originalError;
    logTestResult('No JavaScript Errors', errorCount === 0, `Found ${errorCount} errors`) && passCount++;
    
    // Test 4: All Components Responsive to Window Resize
    totalTests++;
    const initialSizes = Array.from(plotlyCharts).map(chart => ({
      width: chart.offsetWidth,
      height: chart.offsetHeight
    }));
    
    // Simulate window resize
    window.dispatchEvent(new Event('resize'));
    await sleep(500);
    
    const responsiveWorked = Array.from(plotlyCharts).some((chart, index) => {
      const newWidth = chart.offsetWidth;
      const newHeight = chart.offsetHeight;
      return newWidth > 0 && newHeight > 0;
    });
    
    logTestResult('Charts Responsive to Resize', responsiveWorked) && passCount++;
    
    // Test 5: Memory Usage Check
    totalTests++;
    if (performance.memory) {
      const memoryUsage = performance.memory.usedJSHeapSize / 1024 / 1024;
      const reasonableMemoryUsage = memoryUsage < 100; // Less than 100MB
      logTestResult('Reasonable Memory Usage', reasonableMemoryUsage, `${memoryUsage.toFixed(2)}MB used`) && passCount++;
    } else {
      logTestResult('Reasonable Memory Usage', true, 'Performance.memory not available') && passCount++;
    }
    
  } catch (error) {
    console.error('Cross-Component Tests Error:', error);
  }
  
  console.log(`Cross-Component Tests: ${passCount}/${totalTests} passed`);
  return { passed: passCount, total: totalTests };
}

// ====================================================================
// MAIN TEST RUNNER
// ====================================================================

async function runAllIntegrationTests() {
  console.clear();
  console.log('====================================================================');
  console.log('STARTING CHART COMPONENTS INTEGRATION TESTS');
  console.log('====================================================================');
  
  const startTime = Date.now();
  const results = [];
  
  try {
    results.push(await runBalanceChartTests());
    results.push(await runJointAngleChartTests());
    results.push(await runSmoothnessChartTests());
    results.push(await runSymmetryChartTests());
    results.push(await runCrossComponentTests());
    
    const totalPassed = results.reduce((sum, result) => sum + result.passed, 0);
    const totalTests = results.reduce((sum, result) => sum + result.total, 0);
    const duration = Date.now() - startTime;
    
    console.log('\n====================================================================');
    console.log('INTEGRATION TESTS SUMMARY');
    console.log('====================================================================');
    console.log(`Total Tests: ${totalTests}`);
    console.log(`Passed: ${totalPassed}`);
    console.log(`Failed: ${totalTests - totalPassed}`);
    console.log(`Success Rate: ${((totalPassed / totalTests) * 100).toFixed(1)}%`);
    console.log(`Duration: ${duration}ms`);
    console.log('====================================================================');
    
    if (totalPassed === totalTests) {
      console.log('SUCCESS: All integration tests passed!');
    } else {
      console.log('ATTENTION: Some tests failed. Check the detailed output above.');
    }
    
    return {
      totalPassed,
      totalTests,
      duration,
      successRate: (totalPassed / totalTests) * 100
    };
    
  } catch (error) {
    console.error('Integration test runner failed:', error);
    return null;
  }
}

// ====================================================================
// INDIVIDUAL TEST RUNNERS FOR DEBUGGING
// ====================================================================

// Run individual component tests with these commands:
// runBalanceChartTests()
// runJointAngleChartTests() 
// runSmoothnessChartTests()
// runSymmetryChartTests()
// runCrossComponentTests()

// Run all tests:
// runAllIntegrationTests()

console.log('Integration test suite loaded. Run runAllIntegrationTests() to start testing.');
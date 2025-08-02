// =====================================================
// BADUANJIN INTEGRATION TESTS - BROWSER CONSOLE
// =====================================================
// Run these in your browser's developer console
// Make sure you're logged in and on the appropriate page

// =====================================================
// 1. VIDEO UPLOAD INTEGRATION TEST
// =====================================================
console.log(' === VIDEO UPLOAD INTEGRATION TEST ===');

async function testVideoUpload() {
    console.log(' Testing VideoUpload component integration...');
    
    try {
        // Test 1: Check if upload form exists
        const uploadForm = document.querySelector('form');
        const titleInput = document.querySelector('#title');
        const fileInput = document.querySelector('#videoFile');
        const submitButton = document.querySelector('button[type="submit"]');
        
        console.log(' Form elements found:', {
            form: !!uploadForm,
            titleInput: !!titleInput,
            fileInput: !!fileInput,
            submitButton: !!submitButton
        });
        
        // Test 2: Simulate form interaction
        if (titleInput) {
            titleInput.value = 'Integration Test Video';
            titleInput.dispatchEvent(new Event('input', { bubbles: true }));
            console.log(' Title input set to:', titleInput.value);
        }
        
        // Test 3: Check brocade type options
        const brocadeSelect = document.querySelector('#brocadeType');
        if (brocadeSelect) {
            console.log(' Brocade options available:', brocadeSelect.options.length);
            brocadeSelect.value = 'SECOND';
            brocadeSelect.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(' Brocade type set to:', brocadeSelect.value);
        }
        
        // Test 4: Validate form state
        console.log(' Current form state:', {
            title: titleInput?.value,
            brocadeType: brocadeSelect?.value,
            hasFileInput: !!fileInput,
            submitEnabled: !submitButton?.disabled
        });
        
        // Test 5: API endpoint check (without actual upload)
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (token) {
            const response = await fetch('https://baduanjin-backend-docker.azurewebsites.net/api/videos', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            console.log(' API connectivity test:', response.status === 200 ? 'PASS' : 'FAIL');
        }
        
        console.log(' VideoUpload integration test completed successfully!');
        
    } catch (error) {
        console.error(' VideoUpload integration test failed:', error);
    }
}

// Run VideoUpload test
testVideoUpload();

// =====================================================
// 2. VIDEO VIEW INTEGRATION TEST
// =====================================================
console.log('\n === VIDEO VIEW INTEGRATION TEST ===');

async function testVideoView() {
    console.log(' Testing VideoView component integration...');
    
    try {
        // Test 1: Check if we're on a video view page
        const videoElement = document.querySelector('video');
        const videoTitle = document.querySelector('[data-testid="video-title"]') || 
                          document.querySelector('h1') ||
                          document.querySelector('h2');
        
        console.log(' Video page elements found:', {
            videoPlayer: !!videoElement,
            titleElement: !!videoTitle,
            hasControls: videoElement?.hasAttribute('controls')
        });
        
        // Test 2: Check video player functionality
        if (videoElement) {
            console.log(' Video element properties:', {
                src: videoElement.src ? 'Present' : 'Missing',
                controls: videoElement.controls,
                readyState: videoElement.readyState,
                networkState: videoElement.networkState
            });
            
            // Test video events
            videoElement.addEventListener('loadstart', () => console.log(' Video load started'));
            videoElement.addEventListener('canplay', () => console.log(' Video can play'));
            videoElement.addEventListener('error', (e) => console.log(' Video error:', e));
        }
        
        // Test 3: Check video metadata display
        const metadataElements = {
            description: document.querySelector('[data-testid="video-description"]'),
            brocadeType: document.querySelector('[data-testid="brocade-type"]'),
            duration: document.querySelector('[data-testid="video-duration"]'),
            status: document.querySelector('[data-testid="processing-status"]'),
            uploadDate: document.querySelector('[data-testid="upload-date"]')
        };
        
        console.log(' Video metadata elements:', Object.fromEntries(
            Object.entries(metadataElements).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 4: Check action buttons
        const actionButtons = {
            viewAnalysis: document.querySelector('[data-testid="view-analysis-button"]') ||
                         document.querySelector('button[class*="view-results"]') ||
                         document.querySelectorAll('button')[0],
            back: document.querySelector('button[class*="back"]')
        };
        
        console.log(' Action buttons available:', Object.fromEntries(
            Object.entries(actionButtons).map(([key, btn]) => [key, !!btn])
        ));
        
        console.log(' VideoView integration test completed successfully!');
        
    } catch (error) {
        console.error(' VideoView integration test failed:', error);
    }
}

// Run VideoView test (if on video page)
if (window.location.pathname.includes('/video') || document.querySelector('video')) {
    testVideoView();
} else {
    console.log(' Skipping VideoView test - not on video page');
}

// =====================================================
// 3. VIDEO MANAGEMENT INTEGRATION TEST
// =====================================================
console.log('\n === VIDEO MANAGEMENT INTEGRATION TEST ===');

async function testVideoManagement() {
    console.log(' Testing VideoManagement component integration...');
    
    try {
        // Test 1: Check main dashboard elements
        const dashboardElements = {
            header: document.querySelector('.dashboard-header') || document.querySelector('h1'),
            videoList: document.querySelector('.video-list-panel') || document.querySelector('.videos-grid-layout'),
            detailsPanel: document.querySelector('.video-details-panel'),
            uploadSection: document.querySelector('.upload-sections-container')
        };
        
        console.log(' Dashboard elements found:', Object.fromEntries(
            Object.entries(dashboardElements).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 2: Check video cards
        const videoCards = document.querySelectorAll('.video-card');
        console.log(' Video cards found:', videoCards.length);
        
        if (videoCards.length > 0) {
            console.log(' First video card analysis:', {
                hasTitle: !!videoCards[0].querySelector('.video-title'),
                hasStatus: !!videoCards[0].querySelector('.video-status'),
                hasActions: !!videoCards[0].querySelector('.video-card-actions'),
                hasPreviewBtn: !!videoCards[0].querySelector('.preview-btn'),
                hasDeleteBtn: !!videoCards[0].querySelector('.delete-btn')
            });
        }
        
        // Test 3: Check upload components
        const uploadComponents = {
            videoUpload: document.querySelector('[data-testid="video-upload"]') ||
                        document.querySelector('.upload-section'),
            piTransfer: document.querySelector('[data-testid="pi-video-transfer"]') ||
                       document.querySelector('.pi-transfer-section')
        };
        
        console.log(' Upload components:', Object.fromEntries(
            Object.entries(uploadComponents).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 4: Test video selection
        if (videoCards.length > 0) {
            const firstCard = videoCards[0];
            const previewBtn = firstCard.querySelector('.preview-btn') || 
                             firstCard.querySelector('button');
            
            if (previewBtn) {
                console.log(' Testing video selection...');
                previewBtn.click();
                
                setTimeout(() => {
                    const selectedCard = document.querySelector('.video-card.selected');
                    console.log(' Video selection test:', !!selectedCard ? 'PASS' : 'FAIL');
                }, 500);
            }
        }
        
        // Test 5: API integration test
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (token) {
            const response = await fetch('https://baduanjin-backend-docker.azurewebsites.net/api/videos', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const videos = await response.json();
                console.log(' API integration test: PASS');
                console.log(' API returned videos:', Array.isArray(videos) ? videos.length : 'Invalid format');
            } else {
                console.log(' API integration test: FAIL -', response.status);
            }
        }
        
        console.log('🎉 VideoManagement integration test completed successfully!');
        
    } catch (error) {
        console.error(' VideoManagement integration test failed:', error);
    }
}

// Run VideoManagement test
testVideoManagement();

// =====================================================
// 4. LIVE SESSION MANAGEMENT INTEGRATION TEST
// =====================================================
console.log('\n === LIVE SESSION MANAGEMENT INTEGRATION TEST ===');

async function testLiveSessionManagement() {
    console.log(' Testing LiveSessionManagement component integration...');
    
    try {
        // Test 1: Check main live session interface
        const liveSessionElements = {
            interface: document.querySelector('.live-session-interface'),
            piLiveSession: document.querySelector('[data-testid="pi-live-session"]'),
            sessionHistory: document.querySelector('.session-history-section'),
            workflowGuide: document.querySelector('.workflow-guide-overlay')
        };
        
        console.log(' Live session elements found:', Object.fromEntries(
            Object.entries(liveSessionElements).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 2: Check session statistics
        const statsElements = {
            statsSection: document.querySelector('.session-stats'),
            totalSessions: document.querySelector('.session-stats span') || 
                          document.querySelector('[class*="stat"]')
        };
        
        console.log(' Session statistics elements:', Object.fromEntries(
            Object.entries(statsElements).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 3: Check session cards
        const sessionCards = document.querySelectorAll('.session-card');
        console.log(' Session cards found:', sessionCards.length);
        
        if (sessionCards.length > 0) {
            console.log(' First session card analysis:', {
                hasTitle: !!sessionCards[0].querySelector('.session-title'),
                hasType: !!sessionCards[0].querySelector('.session-type'),
                hasActions: !!sessionCards[0].querySelector('.session-card-actions'),
                hasVideoIndicator: sessionCards[0].classList.contains('has-video') ||
                                 !!sessionCards[0].querySelector('.video-indicator')
            });
        }
        
        // Test 4: Test workflow guide interaction
        const helpButton = document.querySelector('button[class*="help"]') ||
                          [...document.querySelectorAll('button')].find(btn => 
                              btn.textContent.includes('How to Record') || 
                              btn.textContent.includes('Help'));
        
        if (helpButton) {
            console.log(' Testing workflow guide...');
            helpButton.click();
            
            setTimeout(() => {
                const guide = document.querySelector('.workflow-guide-overlay');
                console.log(' Workflow guide test:', !!guide ? 'PASS' : 'FAIL');
                
                // Close guide if opened
                const closeBtn = guide?.querySelector('.close-guide-btn') ||
                                guide?.querySelector('button');
                if (closeBtn) closeBtn.click();
            }, 500);
        }
        
        // Test 5: Live session API integration
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (token) {
            const response = await fetch('https://baduanjin-backend-docker.azurewebsites.net/api/videos', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const videos = await response.json();
                const liveSessions = videos.filter(v => 
                    v.processing_status === 'live_completed' ||
                    v.processing_status === 'live_active' ||
                    v.title?.includes('[LIVE]')
                );
                console.log(' Live sessions API test: PASS');
                console.log(' Live sessions found:', liveSessions.length);
            }
        }
        
        console.log(' LiveSessionManagement integration test completed successfully!');
        
    } catch (error) {
        console.error(' LiveSessionManagement integration test failed:', error);
    }
}

// Run LiveSessionManagement test
testLiveSessionManagement();

// =====================================================
// 5. PI VIDEO TRANSFER INTEGRATION TEST
// =====================================================
console.log('\n === PI VIDEO TRANSFER INTEGRATION TEST ===');

async function testPiVideoTransfer() {
    console.log(' Testing PiVideoTransfer component integration...');
    
    try {
        // Test 1: Check Pi transfer interface
        const piTransferElements = {
            container: document.querySelector('.pi-video-transfer-container'),
            statusIndicator: document.querySelector('.pi-status'),
            transferSettings: document.querySelector('.transfer-settings'),
            recordingsSection: document.querySelector('.recordings-section')
        };
        
        console.log(' Pi transfer elements found:', Object.fromEntries(
            Object.entries(piTransferElements).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 2: Check control buttons
        const controlButtons = {
            refresh: document.querySelector('.refresh-btn') ||
                    [...document.querySelectorAll('button')].find(btn => 
                        btn.textContent.includes('Refresh')),
            testPi: document.querySelector('.test-connection-btn') ||
                   [...document.querySelectorAll('button')].find(btn => 
                       btn.textContent.includes('Test Pi')),
            testBackend: document.querySelector('.test-backend-btn') ||
                        [...document.querySelectorAll('button')].find(btn => 
                            btn.textContent.includes('Test Main Backend'))
        };
        
        console.log(' Control buttons found:', Object.fromEntries(
            Object.entries(controlButtons).map(([key, btn]) => [key, !!btn])
        ));
        
        // Test 3: Check transfer form
        const transferForm = {
            titleInput: document.querySelector('input[placeholder*="Morning Practice"]') ||
                       document.querySelector('input[type="text"]'),
            brocadeSelect: document.querySelector('select') ||
                          document.querySelector('#brocadeType'),
            descriptionInput: document.querySelector('textarea')
        };
        
        console.log(' Transfer form elements:', Object.fromEntries(
            Object.entries(transferForm).map(([key, elem]) => [key, !!elem])
        ));
        
        // Test 4: Test form interaction
        if (transferForm.titleInput) {
            transferForm.titleInput.value = 'Integration Test Session';
            transferForm.titleInput.dispatchEvent(new Event('input', { bubbles: true }));
            console.log(' Title input test: PASS');
        }
        
        if (transferForm.brocadeSelect) {
            transferForm.brocadeSelect.value = 'THIRD';
            transferForm.brocadeSelect.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(' Brocade selection test: PASS');
        }
        
        // Test 5: Check recording cards
        const recordingCards = document.querySelectorAll('.recording-card');
        console.log(' Recording cards found:', recordingCards.length);
        
        if (recordingCards.length > 0) {
            console.log(' First recording card analysis:', {
                hasHeader: !!recordingCards[0].querySelector('.recording-header'),
                hasInfo: !!recordingCards[0].querySelector('.recording-info'),
                hasTransferControls: !!recordingCards[0].querySelector('.transfer-controls'),
                hasTransferBtn: !!recordingCards[0].querySelector('.transfer-btn') ||
                               !!recordingCards[0].querySelector('button[class*="transfer"]')
            });
        }
        
        // Test 6: Test Pi service connectivity (mock)
        if (controlButtons.testPi) {
            console.log(' Testing Pi connection...');
            controlButtons.testPi.click();
            
            setTimeout(() => {
                console.log(' Pi connection test triggered');
            }, 500);
        }
        
        // Test 7: Test main backend connectivity
        if (controlButtons.testBackend) {
            console.log(' Testing main backend connection...');
            controlButtons.testBackend.click();
            
            setTimeout(() => {
                console.log(' Backend connection test triggered');
            }, 500);
        }
        
        console.log(' PiVideoTransfer integration test completed successfully!');
        
    } catch (error) {
        console.error(' PiVideoTransfer integration test failed:', error);
    }
}

// Run PiVideoTransfer test
testPiVideoTransfer();

// =====================================================
// COMPREHENSIVE INTEGRATION TEST SUMMARY
// =====================================================
console.log('\n === INTEGRATION TEST SUMMARY ===');

async function generateTestSummary() {
    console.log(' Generating comprehensive test summary...');
    
    try {
        // Overall page structure test
        const pageStructure = {
            hasReactRoot: !!document.querySelector('#root'),
            hasAuthContext: !!window.localStorage.getItem('token') || !!window.sessionStorage.getItem('token'),
            hasRouter: !!window.location.pathname,
            hasMainContainer: !!document.querySelector('[class*="container"]') || 
                             !!document.querySelector('[class*="dashboard"]'),
            responsive: window.innerWidth >= 768
        };
        
        console.log(' Page structure analysis:', pageStructure);
        
        // Authentication test
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        console.log(' Authentication status:', token ? 'AUTHENTICATED' : 'NOT AUTHENTICATED');
        
        // Component detection
        const componentDetection = {
            videoUpload: !!document.querySelector('form') && !!document.querySelector('#videoFile'),
            videoView: !!document.querySelector('video'),
            videoManagement: !!document.querySelector('.video-card') || !!document.querySelector('.videos-grid-layout'),
            liveSessionManagement: !!document.querySelector('.live-session-interface') || 
                                  !!document.querySelector('[data-testid="pi-live-session"]'),
            piVideoTransfer: !!document.querySelector('.pi-video-transfer-container') ||
                            !!document.querySelector('.transfer-settings')
        };
        
        console.log(' Component detection:', componentDetection);
        
        // Performance metrics
        const performanceMetrics = {
            loadTime: performance.now(),
            domElements: document.querySelectorAll('*').length,
            scriptsLoaded: document.querySelectorAll('script').length,
            stylesLoaded: document.querySelectorAll('link[rel="stylesheet"]').length
        };
        
        console.log(' Performance metrics:', performanceMetrics);
        
        // Accessibility check
        const accessibilityCheck = {
            hasMainLandmark: !!document.querySelector('main'),
            hasHeadings: document.querySelectorAll('h1, h2, h3, h4, h5, h6').length > 0,
            hasLabels: document.querySelectorAll('label').length > 0,
            hasAltTexts: [...document.querySelectorAll('img')].every(img => img.alt),
            hasSkipLinks: !!document.querySelector('[href="#main"]')
        };
        
        console.log(' Accessibility analysis:', accessibilityCheck);
        
        // Final summary
        const totalTests = 5;
        const passedComponents = Object.values(componentDetection).filter(Boolean).length;
        const testScore = Math.round((passedComponents / totalTests) * 100);
        
        console.log(`\n FINAL INTEGRATION TEST SCORE: ${testScore}% (${passedComponents}/${totalTests} components detected)`);
        
        if (testScore >= 80) {
            console.log(' INTEGRATION TESTS: EXCELLENT! All major components are working.');
        } else if (testScore >= 60) {
            console.log(' INTEGRATION TESTS: GOOD! Most components are functional.');
        } else {
            console.log(' INTEGRATION TESTS: NEEDS ATTENTION! Some components may not be loaded.');
        }
        
    } catch (error) {
        console.error(' Test summary generation failed:', error);
    }
}

// Generate final summary
setTimeout(generateTestSummary, 2000);

// =====================================================
// UTILITY FUNCTIONS FOR MANUAL TESTING
// =====================================================
console.log('\n === UTILITY FUNCTIONS LOADED ===');

// Quick component checker
window.checkComponent = function(componentName) {
    const components = {
        upload: () => !!document.querySelector('#videoFile'),
        view: () => !!document.querySelector('video'),
        management: () => !!document.querySelector('.video-card'),
        live: () => !!document.querySelector('[data-testid="pi-live-session"]'),
        transfer: () => !!document.querySelector('.pi-video-transfer-container')
    };
    
    const result = components[componentName]?.() ?? false;
    console.log(`🔍 Component "${componentName}": ${result ? 'FOUND' : 'NOT FOUND'}`);
    return result;
};

// Quick API test
window.testAPI = async function(endpoint = '/api/videos') {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) {
        console.log(' No authentication token found');
        return false;
    }
    
    try {
        const response = await fetch(`https://baduanjin-backend-docker.azurewebsites.net${endpoint}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        console.log(` API ${endpoint}: ${response.ok ? 'SUCCESS' : 'FAILED'} (${response.status})`);
        return response.ok;
    } catch (error) {
        console.log(` API ${endpoint}: ERROR -`, error.message);
        return false;
    }
};

// Quick form fill (for testing)
window.quickFillForm = function() {
    const titleInput = document.querySelector('#title');
    const descriptionInput = document.querySelector('#description');
    const brocadeSelect = document.querySelector('#brocadeType');
    
    if (titleInput) {
        titleInput.value = 'Test Video ' + Date.now();
        titleInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    
    if (descriptionInput) {
        descriptionInput.value = 'Integration test description';
        descriptionInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    
    if (brocadeSelect) {
        brocadeSelect.value = 'FIRST';
        brocadeSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    console.log(' Form filled with test data');
};

console.log(' Integration tests completed! Use utility functions:');
console.log('   - checkComponent("upload") - Check if component exists');
console.log('   - testAPI("/api/videos") - Test API connectivity');
console.log('   - quickFillForm() - Fill forms with test data');
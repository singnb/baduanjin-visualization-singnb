// ========================================================================
// MASTER ACCOUNT INTEGRATION TESTS
// ========================================================================
// 
// Instructions:
// 1. Login to your application with a MASTER account
// 2. Navigate to your React application in the browser
// 3. Open Developer Tools (F12)
// 4. Go to Console tab
// 5. Paste this entire script and press Enter
// 6. The tests will run automatically and display results
//
// IMPORTANT: This test suite is designed for MASTER accounts only
// ========================================================================

(function() {
    'use strict';
    
    // Test Results Storage
    const testResults = {
        passed: 0,
        failed: 0,
        total: 0,
        details: []
    };

    // Utility Functions
    const utils = {
        log: (message, type = 'info') => {
            const styles = {
                info: 'color: blue; font-weight: bold;',
                success: 'color: green; font-weight: bold;',
                error: 'color: red; font-weight: bold;',
                header: 'color: purple; font-size: 16px; font-weight: bold; background: #f0f0f0; padding: 5px;'
            };
            console.log(`%c${message}`, styles[type] || styles.info);
        },

        sleep: (ms) => new Promise(resolve => setTimeout(resolve, ms)),

        waitForElement: async (selector, timeout = 5000) => {
            const startTime = Date.now();
            while (Date.now() - startTime < timeout) {
                const element = document.querySelector(selector);
                if (element) return element;
                await utils.sleep(100);
            }
            throw new Error(`Element ${selector} not found within ${timeout}ms`);
        },

        waitForText: async (text, timeout = 5000) => {
            const startTime = Date.now();
            while (Date.now() - startTime < timeout) {
                const elements = Array.from(document.querySelectorAll('*')).filter(el => 
                    el.textContent.includes(text) && el.children.length === 0
                );
                if (elements.length > 0) return elements[0];
                await utils.sleep(100);
            }
            throw new Error(`Text "${text}" not found within ${timeout}ms`);
        },

        clickElement: async (selector) => {
            const element = await utils.waitForElement(selector);
            element.click();
            await utils.sleep(500);
            return element;
        },

        getCurrentUrl: () => window.location.pathname + window.location.search,

        isElementVisible: (selector) => {
            const element = document.querySelector(selector);
            if (!element) return false;
            const style = window.getComputedStyle(element);
            return style.display !== 'none' && style.visibility !== 'hidden' && element.offsetHeight > 0;
        }
    };

    // Test Framework
    const test = {
        run: async (name, testFn) => {
            testResults.total++;
            try {
                utils.log(`Running: ${name}`, 'info');
                await testFn();
                testResults.passed++;
                testResults.details.push({ name, status: 'PASSED' });
                utils.log(`PASSED: ${name}`, 'success');
            } catch (error) {
                testResults.failed++;
                testResults.details.push({ name, status: 'FAILED', error: error.message });
                utils.log(`FAILED: ${name} - ${error.message}`, 'error');
            }
        },

        assert: {
            isTrue: (condition, message) => {
                if (!condition) throw new Error(message || 'Assertion failed');
            },
            
            exists: (selector, message) => {
                const element = document.querySelector(selector);
                if (!element) throw new Error(message || `Element ${selector} does not exist`);
            },
            
            notExists: (selector, message) => {
                const element = document.querySelector(selector);
                if (element && utils.isElementVisible(selector)) {
                    throw new Error(message || `Element ${selector} should not exist or be visible`);
                }
            },
            
            textExists: (text, message) => {
                const found = Array.from(document.querySelectorAll('*')).some(el => 
                    el.textContent.includes(text)
                );
                if (!found) throw new Error(message || `Text "${text}" not found`);
            },
            
            urlContains: (path, message) => {
                const currentUrl = utils.getCurrentUrl();
                if (!currentUrl.includes(path)) {
                    throw new Error(message || `Expected URL to contain "${path}", got "${currentUrl}"`);
                }
            }
        }
    };

    // ========================================================================
    // HEADER COMPONENT TESTS FOR MASTER ACCOUNT
    // ========================================================================

    const runHeaderTestsForMaster = async () => {
        utils.log('========================================', 'header');
        utils.log('HEADER COMPONENT TESTS - MASTER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        await test.run('Header - Should display application title', async () => {
            test.assert.exists('header .header-title h1', 'Header title should exist');
            const titleElement = document.querySelector('header .header-title h1');
            test.assert.isTrue(
                titleElement.textContent.includes('Baduanjin') || titleElement.textContent.length > 0,
                'Header should display a meaningful title'
            );
        });

        await test.run('Header - Should show master user information', async () => {
            test.assert.exists('.user-controls', 'User controls section should exist');
            test.assert.exists('.welcome-text', 'Welcome text should be visible for logged in master');
            test.assert.exists('.user-role', 'User role should be displayed');
            
            const userRole = document.querySelector('.user-role');
            test.assert.isTrue(
                userRole.textContent.toLowerCase().includes('master'),
                'User role should indicate "Master"'
            );
        });

        await test.run('Header - Should show master-specific navigation', async () => {
            test.assert.exists('.header-nav', 'Navigation menu should be visible for masters');
            test.assert.exists('.header-nav a[href*="live-sessions"]', 'Live Sessions link should exist');
            test.assert.exists('.header-nav a[href*="videos"]', 'Videos link should exist');
            test.assert.exists('.header-nav a[href*="learners"]', 'Learners link should exist for masters');
        });

        await test.run('Header - Should NOT show learner-specific navigation', async () => {
            test.assert.notExists('.header-nav a[href*="comparison"]', 'Comparison link should NOT exist for master accounts');
            test.assert.notExists('.header-nav a[href*="masters"]', 'Masters link should NOT exist for master accounts');
        });

        await test.run('Header - Should show logout button', async () => {
            test.assert.exists('.logout-button', 'Logout button should be visible');
        });
    };

    // ========================================================================
    // LEARNERS COMPONENT TESTS FOR MASTER ACCOUNT
    // ========================================================================

    const runLearnersTestsForMaster = async () => {
        utils.log('========================================', 'header');
        utils.log('LEARNERS COMPONENT TESTS - MASTER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        // Navigate to learners page
        const learnersLink = document.querySelector('a[href*="learners"]');
        if (learnersLink) {
            await utils.clickElement('a[href*="learners"]');
            await utils.sleep(2000);
        } else {
            throw new Error('Learners link not found - make sure you are logged in as a master');
        }

        await test.run('Learners - Should display page title and introduction', async () => {
            await utils.waitForText('Your Learners', 5000);
            test.assert.textExists('Your Learners', 'Page should display "Your Learners" title');
            test.assert.textExists('View and manage learners', 'Page should show descriptive text');
        });

        await test.run('Learners - Should handle loading and display learners data', async () => {
            await utils.sleep(3000); // Wait for data to load
            
            const learnersTable = document.querySelector('.learners-table');
            const emptyState = document.querySelector('.empty-state');
            const errorMessage = document.querySelector('.error-message');
            
            test.assert.isTrue(
                learnersTable || emptyState || errorMessage,
                'Should display learners table, empty state, or error message'
            );
            
            if (learnersTable) {
                utils.log('Learners table found - checking structure', 'info');
                test.assert.exists('.learners-table thead', 'Table should have header');
                test.assert.exists('.learners-table tbody', 'Table should have body');
                
                const learnerRows = document.querySelectorAll('.learners-table tbody tr');
                utils.log(`Found ${learnerRows.length} learners`, 'info');
            } else if (emptyState) {
                utils.log('No learners found - empty state displayed', 'info');
                test.assert.textExists('No learners are currently following', 'Empty state should show appropriate message');
            }
        });

        await test.run('Learners - Should allow learner selection and detail viewing', async () => {
            const learnerRows = document.querySelectorAll('.learners-table tbody tr');
            const viewButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('View Details')
            );
            
            if (learnerRows.length > 0 || viewButtons.length > 0) {
                let clicked = false;
                
                // Try clicking on a row first
                if (learnerRows.length > 0) {
                    learnerRows[0].click();
                    clicked = true;
                    await utils.sleep(1000);
                }
                
                // Or try clicking a view button
                if (viewButtons.length > 0 && !clicked) {
                    viewButtons[0].click();
                    clicked = true;
                    await utils.sleep(1000);
                }
                
                if (clicked) {
                    // Check if learner detail panel appears
                    const detailPanel = document.querySelector('.learner-detail');
                    const videosSection = document.querySelector('.learner-videos');
                    
                    test.assert.isTrue(
                        detailPanel || videosSection,
                        'Selecting learner should show detail panel or videos section'
                    );
                    
                    if (learnerRows.length > 0) {
                        test.assert.isTrue(
                            learnerRows[0].classList.contains('selected-row'),
                            'Selected row should have selected-row class'
                        );
                    }
                }
            } else {
                utils.log('No learners available to test selection', 'info');
            }
        });

        await test.run('Learners - Should display learner videos when available', async () => {
            const videosSection = document.querySelector('.learner-videos');
            const noVideosMessage = document.querySelector('.no-videos-message');
            const videoCards = document.querySelectorAll('.video-card');
            const videosLoading = document.querySelector('.loading-spinner');
            
            if (videosSection || noVideosMessage || videosLoading) {
                test.assert.isTrue(
                    videosSection || noVideosMessage || videosLoading,
                    'Should show videos section, no videos message, or loading state'
                );
                
                if (videoCards.length > 0) {
                    utils.log(`Found ${videoCards.length} learner videos`, 'info');
                    
                    // Check video card structure
                    test.assert.exists('.video-info', 'Video cards should have video info');
                    
                    // Check for action buttons
                    const viewVideoButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                        btn.textContent.includes('View Video')
                    );
                    const compareButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                        btn.textContent.includes('Compare')
                    );
                    
                    test.assert.isTrue(
                        viewVideoButtons.length > 0 || compareButtons.length > 0,
                        'Video cards should have action buttons'
                    );
                }
            } else {
                utils.log('No video section visible - might need to select a learner first', 'info');
            }
        });

        await test.run('Learners - Should handle video viewing modal', async () => {
            const viewVideoButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('View Video')
            );
            
            if (viewVideoButtons.length > 0) {
                viewVideoButtons[0].click();
                await utils.sleep(2000);
                
                // Check if modal opens
                const modal = document.querySelector('.video-modal');
                const modalOverlay = document.querySelector('.video-modal-overlay');
                
                test.assert.isTrue(
                    modal && modalOverlay,
                    'Video modal should open when view video button is clicked'
                );
                
                // Check for video players
                const videoPlayers = document.querySelectorAll('video');
                test.assert.isTrue(
                    videoPlayers.length > 0,
                    'Modal should contain video players'
                );
                
                // Test closing modal
                const closeButton = document.querySelector('.close-btn');
                if (closeButton) {
                    closeButton.click();
                    await utils.sleep(500);
                    
                    const modalAfterClose = document.querySelector('.video-modal');
                    test.assert.isTrue(
                        !modalAfterClose || !utils.isElementVisible('.video-modal'),
                        'Modal should close when close button is clicked'
                    );
                }
            } else {
                utils.log('No view video buttons found to test modal', 'info');
            }
        });

        await test.run('Learners - Should handle comparison navigation', async () => {
            const compareButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('Compare Performance')
            );
            
            if (compareButtons.length > 0) {
                const originalUrl = utils.getCurrentUrl();
                compareButtons[0].click();
                await utils.sleep(1000);
                
                const newUrl = utils.getCurrentUrl();
                test.assert.isTrue(
                    newUrl !== originalUrl || newUrl.includes('comparison'),
                    'Compare button should navigate to comparison page'
                );
                
                // Navigate back
                if (newUrl !== originalUrl) {
                    window.history.back();
                    await utils.sleep(1000);
                }
            } else {
                utils.log('No compare buttons found to test navigation', 'info');
            }
        });

        await test.run('Learners - Should show feedback functionality', async () => {
            const feedbackButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('Feedback')
            );
            
            if (feedbackButtons.length > 0) {
                // Store original alert
                const originalAlert = window.alert;
                let alertCalled = false;
                let alertMessage = '';
                window.alert = (msg) => { 
                    alertCalled = true; 
                    alertMessage = msg;
                };
                
                try {
                    feedbackButtons[0].click();
                    await utils.sleep(500);
                    
                    test.assert.isTrue(
                        alertCalled && alertMessage.includes('Feature coming soon'),
                        'Feedback button should show coming soon message'
                    );
                } finally {
                    window.alert = originalAlert;
                }
            } else {
                utils.log('No feedback buttons found to test', 'info');
            }
        });
    };

    // ========================================================================
    // VIDEOS COMPONENT TESTS FOR MASTER ACCOUNT
    // ========================================================================

    const runVideosTestsForMaster = async () => {
        utils.log('========================================', 'header');
        utils.log('VIDEOS COMPONENT TESTS - MASTER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        // Navigate to videos page
        const videosLink = document.querySelector('a[href*="videos"]');
        if (videosLink) {
            await utils.clickElement('a[href*="videos"]');
            await utils.sleep(2000);
        }

        await test.run('Videos - Should access videos page', async () => {
            test.assert.urlContains('videos', 'Should be on videos page');
        });

        await test.run('Videos - Should show master video management interface', async () => {
            await utils.sleep(2000);
            
            // Look for video management interface
            const videoInterface = document.querySelector('.videos-container, .page-container');
            const uploadButton = Array.from(document.querySelectorAll('button')).some(btn => 
                btn.textContent.toLowerCase().includes('upload')
            );
            
            test.assert.isTrue(
                videoInterface !== null,
                'Should display video management interface'
            );
            
            if (uploadButton) {
                utils.log('Upload functionality available', 'info');
            }
            
            // Check for master-specific video features
            const analysisButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.toLowerCase().includes('analysis') || 
                btn.textContent.toLowerCase().includes('extract')
            );
            
            if (analysisButtons.length > 0) {
                utils.log('Analysis functionality available for master', 'info');
            }
        });
    };

    // ========================================================================
    // LIVE SESSIONS TESTS FOR MASTER ACCOUNT
    // ========================================================================

    const runLiveSessionsTestsForMaster = async () => {
        utils.log('========================================', 'header');
        utils.log('LIVE SESSIONS TESTS - MASTER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        // Navigate to live sessions page
        const liveSessionsLink = document.querySelector('a[href*="live-sessions"]');
        if (liveSessionsLink) {
            await utils.clickElement('a[href*="live-sessions"]');
            await utils.sleep(2000);
        }

        await test.run('Live Sessions - Should access live sessions page', async () => {
            test.assert.urlContains('live-sessions', 'Should be on live sessions page');
        });

        await test.run('Live Sessions - Should show master live session interface', async () => {
            await utils.sleep(2000);
            
            // Look for live session interface
            const sessionInterface = document.querySelector('.live-sessions-container, .page-container');
            test.assert.isTrue(
                sessionInterface !== null,
                'Should display live sessions interface'
            );
            
            // Check for master-specific features like creating sessions
            const createButton = Array.from(document.querySelectorAll('button')).some(btn => 
                btn.textContent.toLowerCase().includes('create') ||
                btn.textContent.toLowerCase().includes('start')
            );
            
            if (createButton) {
                utils.log('Create session functionality available for master', 'info');
            }
        });
    };

    // ========================================================================
    // LOGOUT FUNCTIONALITY TEST
    // ========================================================================

    const runLogoutTest = async () => {
        utils.log('========================================', 'header');
        utils.log('LOGOUT FUNCTIONALITY TEST', 'header');
        utils.log('========================================', 'header');

        await test.run('Logout - Should handle logout process', async () => {
            // Navigate back to a main page before logout
            const homeLink = document.querySelector('a[href="/"], a[href*="dashboard"]') || 
                           document.querySelector('.header-title a') ||
                           document.querySelector('a[href*="learners"]');
            
            if (homeLink) {
                homeLink.click();
                await utils.sleep(1000);
            }
            
            const logoutButton = document.querySelector('.logout-button');
            test.assert.exists('.logout-button', 'Logout button should exist');
            
            const originalUrl = utils.getCurrentUrl();
            
            // Click logout
            logoutButton.click();
            await utils.sleep(2000);
            
            // Check if logout was successful
            const currentUrl = utils.getCurrentUrl();
            const hasLoginButton = document.querySelector('.login-button');
            const isOnLoginPage = currentUrl.includes('/login');
            const welcomeTextGone = !document.querySelector('.welcome-text');
            
            test.assert.isTrue(
                hasLoginButton || isOnLoginPage || welcomeTextGone || currentUrl !== originalUrl,
                'Logout should redirect to login page or remove user session'
            );
            
            utils.log('Logout test completed - session should be ended', 'info');
        });
    };

    // ========================================================================
    // MAIN TEST RUNNER FOR MASTER ACCOUNT
    // ========================================================================

    const runAllMasterTests = async () => {
        utils.log('Starting Master Account Integration Tests...', 'header');
        utils.log('Make sure you are logged in with a MASTER account', 'info');
        
        // Check if user is logged in as master
        await utils.sleep(1000);
        const userRole = document.querySelector('.user-role');
        if (!userRole || !userRole.textContent.toLowerCase().includes('master')) {
            utils.log('WARNING: Please ensure you are logged in as a MASTER account', 'error');
            utils.log('Current role detected: ' + (userRole ? userRole.textContent : 'Unknown'), 'error');
        }
        
        try {
            await runHeaderTestsForMaster();
            await utils.sleep(1000);
            
            await runLearnersTestsForMaster();
            await utils.sleep(1000);
            
            await runVideosTestsForMaster();
            await utils.sleep(1000);
            
            await runLiveSessionsTestsForMaster();
            await utils.sleep(1000);
            
            // Run logout test last since it will end the session
            await runLogoutTest();
            
        } catch (error) {
            utils.log(`Test execution error: ${error.message}`, 'error');
        } finally {
            // Display final results
            utils.log('========================================', 'header');
            utils.log('MASTER ACCOUNT TEST RESULTS SUMMARY', 'header');
            utils.log('========================================', 'header');
            
            utils.log(`Total Tests: ${testResults.total}`, 'info');
            utils.log(`Passed: ${testResults.passed}`, 'success');
            utils.log(`Failed: ${testResults.failed}`, testResults.failed > 0 ? 'error' : 'success');
            
            if (testResults.failed > 0) {
                utils.log('Failed Tests:', 'error');
                testResults.details.filter(test => test.status === 'FAILED').forEach(test => {
                    utils.log(`- ${test.name}: ${test.error}`, 'error');
                });
            }
            
            const successRate = ((testResults.passed / testResults.total) * 100).toFixed(1);
            utils.log(`Success Rate: ${successRate}%`, successRate > 80 ? 'success' : 'error');
            
            return testResults;
        }
    };

    // Auto-run the tests
    runAllMasterTests().then((results) => {
        window.masterTestResults = results;
        utils.log('Master integration tests completed! Results stored in window.masterTestResults', 'success');
        utils.log('Note: User session has been logged out as part of testing', 'info');
    });

})();
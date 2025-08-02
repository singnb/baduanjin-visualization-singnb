// ========================================================================
// LEARNER ACCOUNT INTEGRATION TESTS
// ========================================================================
// 
// Instructions:
// 1. Login to your application with a LEARNER account
// 2. Navigate to your React application in the browser
// 3. Open Developer Tools (F12)
// 4. Go to Console tab
// 5. Paste this entire script and press Enter
// 6. The tests will run automatically and display results
//
// IMPORTANT: This test suite is designed for LEARNER accounts only
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
    // HEADER COMPONENT TESTS FOR LEARNER ACCOUNT
    // ========================================================================

    const runHeaderTestsForLearner = async () => {
        utils.log('========================================', 'header');
        utils.log('HEADER COMPONENT TESTS - LEARNER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        await test.run('Header - Should display application title', async () => {
            test.assert.exists('header .header-title h1', 'Header title should exist');
            const titleElement = document.querySelector('header .header-title h1');
            test.assert.isTrue(
                titleElement.textContent.includes('Baduanjin') || titleElement.textContent.length > 0,
                'Header should display a meaningful title'
            );
        });

        await test.run('Header - Should show learner user information', async () => {
            test.assert.exists('.user-controls', 'User controls section should exist');
            test.assert.exists('.welcome-text', 'Welcome text should be visible for logged in learner');
            test.assert.exists('.user-role', 'User role should be displayed');
            
            const userRole = document.querySelector('.user-role');
            test.assert.isTrue(
                userRole.textContent.toLowerCase().includes('learner'),
                'User role should indicate "Learner"'
            );
        });

        await test.run('Header - Should show learner-specific navigation', async () => {
            test.assert.exists('.header-nav', 'Navigation menu should be visible for learners');
            test.assert.exists('.header-nav a[href*="live-sessions"]', 'Live Sessions link should exist');
            test.assert.exists('.header-nav a[href*="videos"]', 'Videos link should exist');
            test.assert.exists('.header-nav a[href*="comparison"]', 'Comparison link should exist for learners');
            test.assert.exists('.header-nav a[href*="masters"]', 'Masters link should exist for learners');
        });

        await test.run('Header - Should NOT show master-specific navigation', async () => {
            test.assert.notExists('.header-nav a[href*="learners"]', 'Learners link should NOT exist for learner accounts');
        });

        await test.run('Header - Should show logout button', async () => {
            test.assert.exists('.logout-button', 'Logout button should be visible');
        });
    };

    // ========================================================================
    // MASTERS COMPONENT TESTS FOR LEARNER ACCOUNT
    // ========================================================================

    const runMastersTestsForLearner = async () => {
        utils.log('========================================', 'header');
        utils.log('MASTERS COMPONENT TESTS - LEARNER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        // Navigate to masters page
        const mastersLink = document.querySelector('a[href*="masters"]');
        if (mastersLink) {
            await utils.clickElement('a[href*="masters"]');
            await utils.sleep(2000);
        }

        await test.run('Masters - Should display page title and introduction', async () => {
            await utils.waitForText('Baduanjin Masters', 5000);
            test.assert.textExists('Baduanjin Masters', 'Page should display "Baduanjin Masters" title');
            test.assert.textExists('Browse registered masters', 'Page should show descriptive text');
        });

        await test.run('Masters - Should handle loading and display masters', async () => {
            await utils.sleep(3000); // Wait for data to load
            
            const mastersGrid = document.querySelector('.masters-grid');
            const masterCards = document.querySelectorAll('.master-card');
            const errorMessage = document.querySelector('.error-message');
            const noMastersMessage = document.textContent && document.textContent.includes('No masters found');
            
            test.assert.isTrue(
                (mastersGrid && masterCards.length > 0) || errorMessage || noMastersMessage,
                'Should display masters grid, error message, or no masters message'
            );
            
            if (masterCards.length > 0) {
                utils.log(`Found ${masterCards.length} masters`, 'info');
            }
        });

        await test.run('Masters - Should allow following/unfollowing masters', async () => {
            const followButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('Follow') && !btn.textContent.includes('Following')
            );
            
            const followingButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('Following')
            );
            
            test.assert.isTrue(
                followButtons.length > 0 || followingButtons.length > 0,
                'Should have follow or following buttons available'
            );
            
            if (followButtons.length > 0) {
                utils.log('Testing follow functionality', 'info');
                const originalText = followButtons[0].textContent;
                followButtons[0].click();
                await utils.sleep(2000);
                
                // Check if button text changed or some feedback was given
                const newText = followButtons[0].textContent;
                test.assert.isTrue(
                    originalText !== newText || document.querySelector('.alert, .notification'),
                    'Following a master should provide feedback'
                );
            }
        });

        await test.run('Masters - Should allow viewing master videos', async () => {
            const viewVideosButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('View Videos')
            );
            
            if (viewVideosButtons.length > 0) {
                viewVideosButtons[0].click();
                await utils.sleep(3000);
                
                const videosSection = document.querySelector('.master-videos-section');
                const videosGrid = document.querySelector('.videos-grid');
                const noVideosMessage = document.querySelector('.no-videos-message');
                
                test.assert.isTrue(
                    videosSection || videosGrid || noVideosMessage,
                    'Should show videos section or no videos message after clicking view videos'
                );
                
                utils.log('Master videos section displayed', 'info');
            } else {
                utils.log('No view videos buttons found', 'info');
            }
        });

        await test.run('Masters - Should allow video viewing and comparison', async () => {
            const viewVideoButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('View Video')
            );
            
            if (viewVideoButtons.length > 0) {
                viewVideoButtons[0].click();
                await utils.sleep(2000);
                
                const modal = document.querySelector('.video-modal');
                test.assert.isTrue(modal !== null, 'Video modal should open');
                
                // Close modal
                const closeButton = document.querySelector('.close-btn');
                if (closeButton) {
                    closeButton.click();
                    await utils.sleep(500);
                }
            }
            
            // Test comparison functionality
            const compareButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                btn.textContent.includes('Compare')
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
            }
        });
    };

    // ========================================================================
    // COMPARISON COMPONENT TESTS FOR LEARNER ACCOUNT
    // ========================================================================

    const runComparisonTestsForLearner = async () => {
        utils.log('========================================', 'header');
        utils.log('COMPARISON COMPONENT TESTS - LEARNER ACCOUNT', 'header');
        utils.log('========================================', 'header');

        // Navigate to comparison page
        const comparisonLink = document.querySelector('a[href*="comparison"]');
        if (comparisonLink) {
            await utils.clickElement('a[href*="comparison"]');
            await utils.sleep(2000);
        }

        await test.run('Comparison - Should access comparison page', async () => {
            test.assert.urlContains('comparison', 'Should be on comparison page');
            
            // Look for comparison-related content
            const comparisonContent = document.querySelector('.comparison-container, .comparison-selection, .page-container');
            test.assert.isTrue(
                comparisonContent !== null,
                'Should display comparison interface'
            );
        });

        await test.run('Comparison - Should show learner video selection', async () => {
            await utils.sleep(2000);
            
            // Look for video selection interface
            const videoSelectors = document.querySelectorAll('select, .video-card, .video-list');
            const uploadSection = document.querySelector('.upload-section, .file-input');
            
            test.assert.isTrue(
                videoSelectors.length > 0 || uploadSection,
                'Should provide interface for selecting or uploading learner videos'
            );
        });
    };

    // ========================================================================
    // VIDEOS COMPONENT TESTS FOR LEARNER ACCOUNT
    // ========================================================================

    const runVideosTestsForLearner = async () => {
        utils.log('========================================', 'header');
        utils.log('VIDEOS COMPONENT TESTS - LEARNER ACCOUNT', 'header');
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

        await test.run('Videos - Should show learner video management interface', async () => {
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
                           document.querySelector('a[href*="masters"]');
            
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
    // MAIN TEST RUNNER FOR LEARNER ACCOUNT
    // ========================================================================

    const runAllLearnerTests = async () => {
        utils.log('Starting Learner Account Integration Tests...', 'header');
        utils.log('Make sure you are logged in with a LEARNER account', 'info');
        
        // Check if user is logged in as learner
        await utils.sleep(1000);
        const userRole = document.querySelector('.user-role');
        if (!userRole || !userRole.textContent.toLowerCase().includes('learner')) {
            utils.log('WARNING: Please ensure you are logged in as a LEARNER account', 'error');
            utils.log('Current role detected: ' + (userRole ? userRole.textContent : 'Unknown'), 'error');
        }
        
        try {
            await runHeaderTestsForLearner();
            await utils.sleep(1000);
            
            await runMastersTestsForLearner();
            await utils.sleep(1000);
            
            await runComparisonTestsForLearner();
            await utils.sleep(1000);
            
            await runVideosTestsForLearner();
            await utils.sleep(1000);
            
            // Run logout test last since it will end the session
            await runLogoutTest();
            
        } catch (error) {
            utils.log(`Test execution error: ${error.message}`, 'error');
        } finally {
            // Display final results
            utils.log('========================================', 'header');
            utils.log('LEARNER ACCOUNT TEST RESULTS SUMMARY', 'header');
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
    runAllLearnerTests().then((results) => {
        window.learnerTestResults = results;
        utils.log('Learner integration tests completed! Results stored in window.learnerTestResults', 'success');
        utils.log('Note: User session has been logged out as part of testing', 'info');
    });

})();
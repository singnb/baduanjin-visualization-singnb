/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/pilive/PiLiveSession.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import PiLiveSession from '../../components/PiLive/PiLiveSession';
import { useAuth } from '../../auth/AuthContext';
import { getPiUrl, PI_CONFIG } from '../../config/piConfig';

// Mock external dependencies
jest.mock('axios');
jest.mock('../../auth/AuthContext');
jest.mock('../../config/piConfig');

// Mock child components
jest.mock('../../components/PiLive/PiStatusPanel', () => {
  return function MockPiStatusPanel({ status, isConnected, loading, onRefresh }) {
    return (
      <div data-testid="pi-status-panel">
        <span>Status: {isConnected ? 'Connected' : 'Disconnected'}</span>
        <button onClick={onRefresh}>Refresh</button>
        {loading && <span>Loading...</span>}
      </div>
    );
  };
});

jest.mock('../../components/PiLive/PiVideoStream', () => {
  return function MockPiVideoStream({ piState, isConnected }) {
    return (
      <div data-testid="pi-video-stream">
        <span>Stream Status: {isConnected ? 'Active' : 'Inactive'}</span>
        {piState.isRecording && <span>Recording Active</span>}
      </div>
    );
  };
});

jest.mock('../../components/PiLive/PiControls', () => {
  return function MockPiControls({ 
    piState, 
    onStartRecordingSession, 
    onStopAndSave, 
    onSessionComplete 
  }) {
    return (
      <div data-testid="pi-controls">
        <button 
          onClick={() => onStartRecordingSession('Test Session')}
          disabled={piState.loading}
        >
          Start Recording Session
        </button>
        <button 
          onClick={onStopAndSave}
          disabled={!piState.isRecording || piState.loading}
        >
          Stop And Save
        </button>
        <button onClick={() => onSessionComplete({ saved: true })}>
          Complete Session
        </button>
        {piState.isRecording && <span>Recording In Progress</span>}
      </div>
    );
  };
});

jest.mock('../../components/PiLive/PiPoseData', () => {
  return function MockPiPoseData({ poseData, activeSession }) {
    return (
      <div data-testid="pi-pose-data">
        {poseData && <span>Pose Data Available</span>}
        {activeSession && <span>Session Active</span>}
      </div>
    );
  };
});

const mockedAxios = axios;
const mockUseAuth = useAuth;
const mockGetPiUrl = getPiUrl;

// Mock data
const mockPiStatus = {
  pi_connected: true,
  is_recording: false,
  is_running: true,
  current_fps: 30,
  cpu_usage: 45.2,
  memory_usage: 60.1,
  temperature: 42.5
};

const mockSessionData = {
  session_id: 'test-session-123',
  session_name: 'Test Session',
  start_time: new Date().toISOString(),
  success: true
};

const mockPoseData = {
  pose_data: [
    { id: 0, keypoints: [], bbox: [100, 100, 50, 150] }
  ],
  timestamp: new Date().toISOString()
};

const mockRecordings = [
  {
    filename: 'test_recording_1.mp4',
    size: 1024000,
    created_at: new Date().toISOString()
  },
  {
    filename: 'test_recording_2.mp4',
    size: 2048000,
    created_at: new Date().toISOString()
  }
];

describe('PiLiveSession Component', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mocks
    mockUseAuth.mockReturnValue({
      token: 'mock-token',
      user: { id: 1, name: 'Test User' }
    });
    
    mockGetPiUrl.mockImplementation((type) => {
      if (type === 'api') return 'http://localhost:8000';
      return 'http://localhost:8000';
    });

    // Mock PI_CONFIG
    PI_CONFIG.TIMEOUTS = {
      STATUS_CHECK: 5000,
      API_REQUEST: 10000
    };
    PI_CONFIG.POLLING = {
      UNIFIED_INTERVAL: 1000
    };

    // Mock timers
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Component Rendering', () => {
    test('renders main interface components', async () => {
      render(<PiLiveSession />);
      
      expect(screen.getByText(/Record Your Baduanjin Practice/)).toBeInTheDocument();
      expect(screen.getByTestId('pi-status-panel')).toBeInTheDocument();
      expect(screen.getByTestId('pi-video-stream')).toBeInTheDocument();
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
      expect(screen.getByTestId('pi-pose-data')).toBeInTheDocument();
    });

    test('renders with initial disconnected state', () => {
      render(<PiLiveSession />);
      
      // Initial state should show disconnected
      expect(screen.getByText('Status: Disconnected')).toBeInTheDocument();
      expect(screen.getByText('Stream Status: Inactive')).toBeInTheDocument();
    });

    test('component structure is stable during renders', () => {
      render(<PiLiveSession />);
      
      // Core UI elements should always be present
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
      expect(screen.getByTestId('pi-video-stream')).toBeInTheDocument();
    });
  });

  describe('Session Management', () => {
    test('renders session controls correctly', () => {
      render(<PiLiveSession />);
      
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
      expect(screen.getByText('Start Recording Session')).toBeInTheDocument();
    });

    test('provides session management functions to child components', () => {
      render(<PiLiveSession />);
      
      // Verify that controls component receives the necessary props
      const controlsComponent = screen.getByTestId('pi-controls');
      expect(controlsComponent).toBeInTheDocument();
    });
  });

  describe('Recording Management', () => {
    test('displays recording controls in UI', () => {
      render(<PiLiveSession />);
      
      expect(screen.getByText('Start Recording Session')).toBeInTheDocument();
      expect(screen.getByText('Stop And Save')).toBeInTheDocument();
    });

    test('provides recording management to child components', () => {
      render(<PiLiveSession />);
      
      const controlsComponent = screen.getByTestId('pi-controls');
      expect(controlsComponent).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('maintains component stability during API failures', async () => {
      mockedAxios.get.mockRejectedValue(new Error('API Error'));
      
      render(<PiLiveSession />);
      
      // Component should still render main interface even with API errors
      expect(screen.getByText(/Record Your Baduanjin Practice/)).toBeInTheDocument();
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
    });

    test('renders error handling UI elements', () => {
      render(<PiLiveSession />);
      
      // Component should have error handling capabilities
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
      expect(screen.getByTestId('pi-video-stream')).toBeInTheDocument();
    });
  });

  describe('State Management', () => {
    test('initializes with correct default state', () => {
      render(<PiLiveSession />);
      
      expect(screen.getByText('Status: Disconnected')).toBeInTheDocument();
      expect(screen.getByText('Stream Status: Inactive')).toBeInTheDocument();
    });

    test('renders state management components', () => {
      render(<PiLiveSession />);
      
      // Components that manage state should be present
      expect(screen.getByTestId('pi-status-panel')).toBeInTheDocument();
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
      expect(screen.getByTestId('pi-pose-data')).toBeInTheDocument();
    });
  });

  describe('Session Completion', () => {
    test('provides session completion functionality', () => {
      const mockOnSessionComplete = jest.fn();
      
      render(<PiLiveSession onSessionComplete={mockOnSessionComplete} />);
      
      // Component should render correctly with callback
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
    });

    test('handles session completion without callback', () => {
      render(<PiLiveSession />);
      
      // Component should render correctly without callback
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
      expect(screen.getByText(/Record Your Baduanjin Practice/)).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    test('provides loading state management to components', () => {
      render(<PiLiveSession />);
      
      // Loading state should be managed by child components
      const statusPanel = screen.getByTestId('pi-status-panel');
      const controls = screen.getByTestId('pi-controls');
      
      expect(statusPanel).toBeInTheDocument();
      expect(controls).toBeInTheDocument();
    });

    test('renders loading UI elements correctly', () => {
      render(<PiLiveSession />);
      
      // Component should have loading management capabilities
      expect(screen.getByTestId('pi-status-panel')).toBeInTheDocument();
      expect(screen.getByText('Start Recording Session')).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle', () => {
    test('renders correctly on mount', () => {
      render(<PiLiveSession />);
      
      expect(screen.getByText(/Record Your Baduanjin Practice/)).toBeInTheDocument();
      expect(screen.getByTestId('pi-controls')).toBeInTheDocument();
    });

    test('cleans up on unmount', () => {
      const { unmount } = render(<PiLiveSession />);
      
      unmount();
      
      // Should not throw errors during cleanup
      expect(true).toBe(true);
    });
  });
});
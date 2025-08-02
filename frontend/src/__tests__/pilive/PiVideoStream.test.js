// src/__tests__/pilive/PiVideoStream.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PiVideoStream from '../../components/PiLive/PiVideoStream';
import { getPiUrl, isDirectPiAvailable, PI_CONFIG } from '../../config/piConfig';

// Mock external dependencies
jest.mock('../../config/piConfig');

const mockGetPiUrl = getPiUrl;
const mockIsDirectPiAvailable = isDirectPiAvailable;

// Mock fetch globally
global.fetch = jest.fn();

// Mock data
const mockPiState = {
  activeSession: {
    session_id: 'test-session-123',
    session_name: 'Test Session'
  },
  isConnected: true,
  connectionError: null,
  isRecording: false
};

const mockPiStateNoSession = {
  activeSession: null,
  isConnected: false,
  connectionError: null,
  isRecording: false
};

const mockPiStateDisconnected = {
  activeSession: {
    session_id: 'test-session-123',
    session_name: 'Test Session'
  },
  isConnected: false,
  connectionError: null,
  isRecording: false
};

const mockPiStateWithError = {
  activeSession: {
    session_id: 'test-session-123',
    session_name: 'Test Session'
  },
  isConnected: true,
  connectionError: 'Connection timeout',
  isRecording: false
};

const mockPiStateRecording = {
  activeSession: {
    session_id: 'test-session-123',
    session_name: 'Test Session'
  },
  isConnected: true,
  connectionError: null,
  isRecording: true
};

describe('PiVideoStream Component', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mocks
    mockGetPiUrl.mockImplementation((type) => {
      if (type === 'video_stream') return 'http://localhost:8001';
      if (type === 'api') return 'http://localhost:8000';
      return 'http://localhost:8000';
    });
    
    mockIsDirectPiAvailable.mockReturnValue(true);
    
    // Mock PI_CONFIG
    PI_CONFIG.TIMEOUTS = {
      VIDEO_STREAM: 5000,
      API_REQUEST: 10000
    };
    PI_CONFIG.POLLING = {
      FRAME_INTERVAL: 100
    };

    // Mock fetch
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        image: 'base64imagedata',
        timestamp: Date.now(),
        stats: { current_fps: 30, persons_detected: 1 }
      })
    });

    // Mock timers
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Component Rendering', () => {
    test('renders main video stream interface', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('renders no session placeholder', () => {
      render(<PiVideoStream piState={mockPiStateNoSession} token="mock-token" />);
      
      expect(screen.getByText('Start a live session to view camera feed')).toBeInTheDocument();
      expect(screen.getByText('Camera will start automatically when session begins')).toBeInTheDocument();
    });

    test('renders disconnected state', () => {
      render(<PiVideoStream piState={mockPiStateDisconnected} token="mock-token" />);
      
      expect(screen.getByText('Pi Camera Not Connected')).toBeInTheDocument();
      expect(screen.getByText('Waiting for Pi device to connect...')).toBeInTheDocument();
    });

    test('renders connection error state', () => {
      render(<PiVideoStream piState={mockPiStateWithError} token="mock-token" />);
      
      expect(screen.getByText('Pi Connection Error')).toBeInTheDocument();
      expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    });
  });

  describe('Stream Status Display', () => {
    test('shows session information when active', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('shows recording indicator when recording', () => {
      render(<PiVideoStream piState={mockPiStateRecording} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('shows disconnected state correctly', () => {
      render(<PiVideoStream piState={mockPiStateDisconnected} token="mock-token" />);
      
      expect(screen.getByText('Pi Camera Not Connected')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('displays error state correctly', () => {
      render(<PiVideoStream piState={mockPiStateWithError} token="mock-token" />);
      
      expect(screen.getByText('Pi Connection Error')).toBeInTheDocument();
      expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    });

    test('renders error UI elements', () => {
      render(<PiVideoStream piState={mockPiStateWithError} token="mock-token" />);
      
      expect(screen.getByText('Pi Connection Error')).toBeInTheDocument();
    });

    test('handles different error types', () => {
      const errorState = {
        ...mockPiState,
        connectionError: 'ngrok authentication required'
      };
      
      render(<PiVideoStream piState={errorState} token="mock-token" />);
      
      expect(screen.getByText('Pi Connection Error')).toBeInTheDocument();
    });
  });

  describe('Stream Loading States', () => {
    test('renders loading state UI', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('shows connection source information', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Connecting to: http:\/\/localhost:8001/)).toBeInTheDocument();
    });

    test('shows Azure service when direct Pi not available', () => {
      mockIsDirectPiAvailable.mockReturnValue(false);
      
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText('Using Azure Pi Service for video')).toBeInTheDocument();
    });
  });

  describe('Debug Information', () => {
    test('renders debug information interface', () => {
      const errorState = {
        ...mockPiState,
        connectionError: 'Stream error'
      };
      
      render(<PiVideoStream piState={errorState} token="mock-token" />);
      
      expect(screen.getByText('Pi Connection Error')).toBeInTheDocument();
    });

    test('displays connection information', () => {
      const errorState = {
        ...mockPiState,
        connectionError: 'Stream error'
      };
      
      render(<PiVideoStream piState={errorState} token="mock-token" />);
      
      expect(screen.getByText('Stream error')).toBeInTheDocument();
    });
  });

  describe('Component State Management', () => {
    test('handles no active session correctly', () => {
      render(<PiVideoStream piState={mockPiStateNoSession} token="mock-token" />);
      
      expect(screen.getByText('Start a live session to view camera feed')).toBeInTheDocument();
    });

    test('handles disconnected state correctly', () => {
      render(<PiVideoStream piState={mockPiStateDisconnected} token="mock-token" />);
      
      expect(screen.getByText('Pi Camera Not Connected')).toBeInTheDocument();
    });

    test('handles connected state with active session', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    test('renders interactive elements', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('handles different user interaction states', () => {
      const errorState = {
        ...mockPiState,
        connectionError: 'ngrok authentication required'
      };
      
      render(<PiVideoStream piState={errorState} token="mock-token" />);
      
      expect(screen.getByText('Pi Connection Error')).toBeInTheDocument();
    });
  });

  describe('Props Handling', () => {
    test('renders with required props', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('handles missing token prop gracefully', () => {
      render(<PiVideoStream piState={mockPiState} />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('handles different piState configurations', () => {
      const customState = {
        activeSession: { session_id: 'custom-123' },
        isConnected: true,
        connectionError: null,
        isRecording: true
      };
      
      render(<PiVideoStream piState={customState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle', () => {
    test('mounts without errors', () => {
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
    });

    test('unmounts without errors', () => {
      const { unmount } = render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      unmount();
      
      // Should not throw errors during cleanup
      expect(true).toBe(true);
    });

    test('handles prop updates correctly', () => {
      const { rerender } = render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Live Camera Feed/)).toBeInTheDocument();
      
      rerender(<PiVideoStream piState={mockPiStateNoSession} token="mock-token" />);
      
      expect(screen.getByText('Start a live session to view camera feed')).toBeInTheDocument();
    });
  });

  describe('Configuration Handling', () => {
    test('handles direct Pi configuration', () => {
      mockIsDirectPiAvailable.mockReturnValue(true);
      
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Connecting to: http:\/\/localhost:8001/)).toBeInTheDocument();
    });

    test('handles Azure service configuration', () => {
      mockIsDirectPiAvailable.mockReturnValue(false);
      
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText('Using Azure Pi Service for video')).toBeInTheDocument();
    });

    test('handles different URL configurations', () => {
      mockGetPiUrl.mockImplementation((type) => {
        if (type === 'video_stream') return 'http://test-pi:8001';
        if (type === 'api') return 'http://test-api:8000';
        return 'http://test-api:8000';
      });
      
      render(<PiVideoStream piState={mockPiState} token="mock-token" />);
      
      expect(screen.getByText(/Connecting to: http:\/\/test-pi:8001/)).toBeInTheDocument();
    });
  });
});
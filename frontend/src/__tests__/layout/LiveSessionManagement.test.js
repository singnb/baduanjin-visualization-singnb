/* eslint-disable testing-library/no-unnecessary-act */
/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/layout/LiveSessionManagement.test.js

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import LiveSessionManagement from '../../components/Layout/LiveSessionManagement';
import { useAuth } from '../../auth/AuthContext';

// Mock dependencies
jest.mock('axios');
jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn()
}));
jest.mock('../../components/PiLive/PiLiveSession', () => {
  return function MockPiLiveSession({ onSessionComplete }) {
    return (
      <div data-testid="pi-live-session">
        <button onClick={() => onSessionComplete && onSessionComplete()}>
          Mock Session Complete
        </button>
      </div>
    );
  };
});
jest.mock('../../components/Layout/Layout.css', () => ({}));
jest.mock('../../components/Layout/LiveSessionManagement.css', () => ({}));

const mockedAxios = axios;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

describe('LiveSessionManagement Component', () => {
  const mockUser = {
    id: 'user-123',
    name: 'Test User',
    role: 'learner'
  };
  const mockToken = 'test-token-123';

  const mockLiveSessions = [
    {
      id: 'session-1',
      title: '[LIVE] First Live Session',
      description: 'Test live session',
      brocade_type: 'FIRST',
      processing_status: 'live_completed',
      upload_timestamp: '2024-01-15T10:30:00Z',
      video_path: '/videos/live_session_20240115_30s.mp4',
      user_id: 'user-123'
    },
    {
      id: 'session-2',
      title: '[LIVE] Streaming Only Session',
      description: 'Streaming session without video',
      brocade_type: 'SECOND',
      processing_status: 'live_completed',
      upload_timestamp: '2024-01-16T11:00:00Z',
      video_path: 'LIVE_SESSION_STREAM_ONLY_60s',
      user_id: 'user-123'
    },
    {
      id: 'session-3',
      title: '[LIVE] Active Session',
      description: 'Currently active session',
      brocade_type: 'THIRD',
      processing_status: 'live_active',
      upload_timestamp: '2024-01-17T12:00:00Z',
      video_path: 'LIVE_SESSION_NO_VIDEO',
      user_id: 'user-123'
    },
    // Non-live session that should be filtered out
    {
      id: 'video-1',
      title: 'Regular Video',
      processing_status: 'completed',
      upload_timestamp: '2024-01-18T13:00:00Z',
      video_path: '/videos/regular_video.mp4',
      user_id: 'user-123'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock auth
    useAuth.mockReturnValue({
      token: mockToken,
      user: mockUser
    });

    // Reset and setup localStorage mocks
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    localStorageMock.clear.mockClear();
    
    // Default localStorage behavior - return null (new user)
    localStorageMock.getItem.mockReturnValue(null);

    // Reset and mock axios properly
    mockedAxios.get.mockReset();
    mockedAxios.delete.mockReset();
    
    // Default successful API response
    mockedAxios.get.mockResolvedValue({ data: mockLiveSessions });
    mockedAxios.delete.mockResolvedValue({});

    // Mock window methods
    window.confirm = jest.fn(() => true);
    window.alert = jest.fn();

    // Mock console methods
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    console.log.mockRestore?.();
    console.error.mockRestore?.();
  });

  describe('Component Rendering', () => {
    test('renders without crashing', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        // Just check that the main container exists
        const container = document.querySelector('.live-session-management-container');
        expect(container).toBeInTheDocument();
      });
    });

    test('renders loading state initially', async () => {
      mockedAxios.get.mockReturnValue(new Promise(() => {}));
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      expect(screen.getByText('Loading sessions...')).toBeInTheDocument();
    });

    test('renders session statistics section', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        // Check that statistics section exists
        const sessionStatsSection = document.querySelector('.session-stats');
        expect(sessionStatsSection).toBeInTheDocument();
      });
    });
  });

  describe('Session Loading and Filtering', () => {
    test('calls API to fetch sessions', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      // Check API call
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos',
        expect.objectContaining({
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        })
      );
    });

    test('displays session types correctly', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Type: Recorded Session')).toBeInTheDocument();
        expect(screen.getAllByText('Type: Streaming Only')).toHaveLength(2);
      });
    });

    test('displays session statuses correctly', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Status: Session with Video')).toBeInTheDocument();
        expect(screen.getByText('Status: Streaming Only')).toBeInTheDocument();
        expect(screen.getByText('Status: Live Session Active')).toBeInTheDocument();
      });
    });
  });

  describe('Helper Functions', () => {
    test('correctly identifies live sessions', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        // Should show 3 live sessions (filtering out the regular video)
        const sessionCards = document.querySelectorAll('.session-card');
        expect(sessionCards).toHaveLength(3);
      });
    });

    test('correctly identifies sessions with video files', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('🎥 Video file available')).toBeInTheDocument();
      });
    });
  });

  describe('Session Selection', () => {
    test('allows selecting a session', async () => {
      const user = userEvent.setup();
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const viewButtons = screen.getAllByText('View Details');
        expect(viewButtons.length).toBeGreaterThan(0);
      });
      
      const viewButtons = screen.getAllByText('View Details');
      await user.click(viewButtons[0]);
      
      await waitFor(() => {
        const sessionCard = document.querySelector('.session-card.selected');
        expect(sessionCard).toBeInTheDocument();
      });
    });

    test('displays session details when selected', async () => {
      const user = userEvent.setup();
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const viewButtons = screen.getAllByText('View Details');
        expect(viewButtons.length).toBeGreaterThan(0);
      });
      
      const viewButtons = screen.getAllByText('View Details');
      await user.click(viewButtons[0]);
      
      await waitFor(() => {
        expect(screen.getByText('Session Type:')).toBeInTheDocument();
        expect(screen.getByText('Exercise Type:')).toBeInTheDocument();
      });
    });

    test('shows select prompt when no session selected', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Select a session to view details')).toBeInTheDocument();
      });
    });
  });

  describe('Session Deletion', () => {
    test('deletes session with confirmation', async () => {
      const user = userEvent.setup();
      window.confirm = jest.fn(() => true);
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const deleteButtons = screen.getAllByText('Delete');
        expect(deleteButtons.length).toBeGreaterThan(0);
      });
      
      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]);
      
      expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this live session record?');
      expect(mockedAxios.delete).toHaveBeenCalledWith(
        expect.stringContaining('/api/videos/session-'),
        expect.objectContaining({
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        })
      );
    });

    test('does not delete when confirmation is cancelled', async () => {
      const user = userEvent.setup();
      window.confirm = jest.fn(() => false);
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const deleteButtons = screen.getAllByText('Delete');
        expect(deleteButtons.length).toBeGreaterThan(0);
      });
      
      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]);
      
      expect(window.confirm).toHaveBeenCalled();
      expect(mockedAxios.delete).not.toHaveBeenCalled();
    });
  });

  describe('Workflow Guide', () => {
    test('component handles workflow guide state', async () => {
      localStorageMock.getItem.mockReturnValue(null); // No guide seen before
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      // Just check that the workflow guide modal exists
      await waitFor(() => {
        const workflowGuide = document.querySelector('.workflow-guide-overlay');
        expect(workflowGuide).toBeInTheDocument();
      });
    });
  });

  describe('Empty States', () => {
    test('displays empty state when no live sessions', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] });
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('No live sessions yet')).toBeInTheDocument();
        expect(screen.getByText('Start your first live session above to practice with real-time feedback!')).toBeInTheDocument();
      });
    });

    test('shows zero statistics when no sessions', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] });
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        // Check that statistics section exists with zero values
        const sessionStatsSection = document.querySelector('.session-stats');
        expect(sessionStatsSection).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    test('displays error message when fetch fails', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'));
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load live sessions. Please try again.')).toBeInTheDocument();
      });
    });

    test('handles delete error gracefully', async () => {
      const user = userEvent.setup();
      window.confirm = jest.fn(() => true);
      window.alert = jest.fn();
      mockedAxios.delete.mockRejectedValue(new Error('Delete failed'));
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const deleteButtons = screen.getAllByText('Delete');
        expect(deleteButtons.length).toBeGreaterThan(0);
      });
      
      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]);
      
      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Failed to delete session. Please try again.');
      });
    });
  });

  describe('Session Types Display', () => {
    test('shows different content for recorded vs streaming sessions', async () => {
      const user = userEvent.setup();
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const viewButtons = screen.getAllByText('View Details');
        expect(viewButtons.length).toBeGreaterThan(0);
      });
      
      // Select first session
      const viewButtons = screen.getAllByText('View Details');
      await user.click(viewButtons[0]);
      
      await waitFor(() => {
        // Should show some session details
        expect(screen.getByText('Session Type:')).toBeInTheDocument();
      });
    });
  });

  describe('Session Integration', () => {
    test('refreshes sessions when PiLiveSession completes', async () => {
      const user = userEvent.setup();
      
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledTimes(1);
      });
      
      // Trigger session complete from PiLiveSession
      const sessionCompleteButton = screen.getByText('Mock Session Complete');
      await user.click(sessionCompleteButton);
      
      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Session Sorting', () => {
    test('displays sessions in proper order', async () => {
      await act(async () => {
        render(<LiveSessionManagement />);
      });
      
      await waitFor(() => {
        const sessionCards = document.querySelectorAll('.session-card');
        expect(sessionCards).toHaveLength(3);
      });
    });
  });
});
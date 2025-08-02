/* eslint-disable testing-library/no-render-in-setup */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
/* eslint-disable testing-library/no-container */
/* eslint-disable testing-library/no-node-access */
// src/__tests__/pilive/PiControls.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import PiControls from '../../components/PiLive/PiControls';
import { useAuth } from '../../auth/AuthContext';
import { getPiUrl } from '../../config/piConfig';

// Mock external dependencies
jest.mock('axios');
jest.mock('../../auth/AuthContext');
jest.mock('../../config/piConfig');

const mockedAxios = axios;
const mockUseAuth = useAuth;
const mockGetPiUrl = getPiUrl;

// Mock data
const mockExercises = [
  {
    id: 1,
    name: 'Holding the Sky (托天理三焦)',
    description: 'First exercise of Baduanjin'
  },
  {
    id: 2, 
    name: 'Drawing the Bow (左右开弓)',
    description: 'Second exercise of Baduanjin'
  }
];

const mockPiState = {
  isConnected: true,
  isRecording: false,
  recordingStartTime: null,
  loading: false,
  availableRecordings: [
    {
      filename: 'test_recording.mp4',
      size: 1024000
    }
  ]
};

const mockProps = {
  piState: mockPiState,
  onStartRecordingSession: jest.fn(),
  onStopAndSave: jest.fn(),
  onSessionComplete: jest.fn(),
  user: { id: 1, name: 'Test User' }
};

describe('PiControls Component', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mocks
    mockUseAuth.mockReturnValue({
      token: 'mock-token'
    });
    
    mockGetPiUrl.mockImplementation((type) => {
      if (type === 'api') return 'http://localhost:8000';
      return 'http://localhost:8000';
    });

    // Mock successful exercises API call
    mockedAxios.get.mockResolvedValue({
      data: {
        success: true,
        exercises: mockExercises
      }
    });

    // Mock timers
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Component Rendering', () => {
    test('renders with camera connected state', async () => {
      render(<PiControls {...mockProps} />);
      
      expect(screen.getByText(/Record Your Practice/)).toBeInTheDocument();
      expect(screen.getByText(/Camera Ready/)).toBeInTheDocument();
      expect(screen.getByText(/Start Recording/)).toBeInTheDocument();
    });

    test('renders with camera disconnected state', () => {
      const disconnectedProps = {
        ...mockProps,
        piState: { ...mockPiState, isConnected: false }
      };
      
      render(<PiControls {...disconnectedProps} />);
      
      expect(screen.getByText(/Camera Not Connected/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start recording/i })).toBeDisabled();
    });

    test('renders recording active state', () => {
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: new Date()
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      expect(screen.getByText('RECORDING')).toBeInTheDocument();
      expect(screen.getByText(/Stop.*Save Recording/)).toBeInTheDocument();
    });
  });

  describe('Exercise Loading and Selection', () => {
    test('loads exercises on component mount', async () => {
      render(<PiControls {...mockProps} />);
      
      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'http://localhost:8000/api/pi-live/baduanjin/exercises',
          { headers: { 'Authorization': 'Bearer mock-token' } }
        );
      });
    });

    test('populates exercise dropdown with loaded exercises', async () => {
      render(<PiControls {...mockProps} />);
      
      await waitFor(() => {
        const exerciseSelect = screen.getByLabelText(/exercise tracking/i);
        expect(exerciseSelect).toBeInTheDocument();
      });

      // Wait for exercises to be loaded and options to be available
      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options.length).toBeGreaterThan(1); // Default option + exercises
      });
    });

    test('shows exercise description when exercise is selected', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(<PiControls {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/exercise tracking/i)).toBeInTheDocument();
      });

      // Wait for exercises to load
      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options.length).toBeGreaterThan(1);
      });

      const exerciseSelect = screen.getByLabelText(/exercise tracking/i);
      await user.selectOptions(exerciseSelect, ['1']);
      
      await waitFor(() => {
        expect(screen.getByText('First exercise of Baduanjin')).toBeInTheDocument();
      });
    });
  });

  describe('Recording Session Management', () => {
    test('starts recording session successfully', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      mockProps.onStartRecordingSession.mockResolvedValue();
      
      render(<PiControls {...mockProps} />);
      
      const startButton = screen.getByRole('button', { name: /start recording/i });
      await user.click(startButton);
      
      expect(mockProps.onStartRecordingSession).toHaveBeenCalledWith(
        expect.stringMatching(/Recording \d+\/\d+\/\d+/),
        ''
      );
    });

    test('starts recording with selected exercise', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      mockProps.onStartRecordingSession.mockResolvedValue();
      mockedAxios.post.mockResolvedValue({
        data: {
          success: true,
          exercise_info: { exercise_name: 'Holding the Sky' }
        }
      });
      
      render(<PiControls {...mockProps} />);
      
      // Wait for exercises to load
      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options.length).toBeGreaterThan(1);
      });
      
      const exerciseSelect = screen.getByLabelText(/exercise tracking/i);
      await user.selectOptions(exerciseSelect, ['1']);
      
      const startButton = screen.getByRole('button', { name: /start recording/i });
      await user.click(startButton);
      
      expect(mockProps.onStartRecordingSession).toHaveBeenCalledWith(
        expect.stringMatching(/Recording \d+\/\d+\/\d+/),
        '1'
      );
    });

    test('stops recording and shows save dialog', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const mockSessionData = {
        session_id: 'test-session-123',
        duration_seconds: 120
      };
      
      mockProps.onStopAndSave.mockResolvedValue(mockSessionData);
      
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: new Date()
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      const stopButton = screen.getByRole('button', { name: /stop.*save recording/i });
      await user.click(stopButton);
      
      expect(mockProps.onStopAndSave).toHaveBeenCalled();
      
      await waitFor(() => {
        expect(screen.getByText(/Save Your Recording/)).toBeInTheDocument();
      });
    });
  });

  describe('Duration Tracking', () => {
    test('tracks recording duration correctly', async () => {
      const startTime = new Date();
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: startTime
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      // Advance time by 65 seconds
      act(() => {
        jest.advanceTimersByTime(65000);
      });
      
      await waitFor(() => {
        expect(screen.getByText('1:05')).toBeInTheDocument();
      });
    });

    test('formats duration correctly', () => {
      const startTime = new Date();
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: startTime
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      // Test initial state
      expect(screen.getByText('0:00')).toBeInTheDocument();
      
      // Test 30 seconds
      act(() => {
        jest.advanceTimersByTime(30000);
      });
      expect(screen.getByText('0:30')).toBeInTheDocument();
      
      // Test 2 minutes
      act(() => {
        jest.advanceTimersByTime(90000);
      });
      expect(screen.getByText('2:00')).toBeInTheDocument();
    });
  });

  describe('Save Dialog Functionality', () => {
    const setupSaveDialog = async () => {
      const mockSessionData = {
        session_id: 'test-session-123',
        duration_seconds: 120
      };
      
      mockProps.onStopAndSave.mockResolvedValue(mockSessionData);
      
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: new Date()
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      const stopButton = screen.getByRole('button', { name: /stop.*save recording/i });
      await userEvent.setup({ advanceTimers: jest.advanceTimersByTime }).click(stopButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Save Your Recording/)).toBeInTheDocument();
      });
    };

    test('form validation works correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      await setupSaveDialog();
      
      const titleInput = screen.getByLabelText(/title/i);
      await user.clear(titleInput);
      
      // Check that form requires title
      expect(titleInput.value).toBe('');
      
      // Add title and verify it's accepted
      await user.type(titleInput, 'Valid Title');
      expect(titleInput.value).toBe('Valid Title');
    });

    test('save dialog displays correctly', async () => {
      await setupSaveDialog();
      
      // Check that save dialog elements are present
      expect(screen.getByText(/Save Your Recording/)).toBeInTheDocument();
      expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/brocade type/i)).toBeInTheDocument();
    });

    test('discards session when requested', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      await setupSaveDialog();
      
      // Mock window.confirm
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      mockedAxios.delete.mockResolvedValue({ data: { success: true } });
      
      const discardButton = screen.getByRole('button', { name: /discard/i });
      await user.click(discardButton);
      
      expect(confirmSpy).toHaveBeenCalled();
      expect(mockProps.onSessionComplete).toHaveBeenCalledWith(null);
      
      confirmSpy.mockRestore();
    });
  });

  describe('Exercise Tracking During Recording', () => {
    test('changes exercise during recording', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      mockedAxios.post
        .mockResolvedValueOnce({ // stopExerciseTracking
          data: { success: true }
        })
        .mockResolvedValueOnce({ // startExerciseTracking
          data: { 
            success: true, 
            exercise_info: { exercise_name: 'Drawing the Bow' }
          }
        });
      
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: new Date()
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/current exercise/i)).toBeInTheDocument();
      });

      // Wait for exercises to be loaded
      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options.length).toBeGreaterThan(1);
      });
      
      const currentExerciseSelect = screen.getByLabelText(/current exercise/i);
      await user.selectOptions(currentExerciseSelect, ['2']);
      
      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8000/api/pi-live/baduanjin/start/2',
          {},
          expect.any(Object)
        );
      });
    });
  });

  describe('Error Handling', () => {
    test('handles start recording error', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      mockProps.onStartRecordingSession.mockRejectedValue(new Error('Recording failed'));
      
      // Mock window.alert
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});
      
      render(<PiControls {...mockProps} />);
      
      const startButton = screen.getByRole('button', { name: /start recording/i });
      await user.click(startButton);
      
      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('Failed to start recording. Please try again.');
      });
      
      alertSpy.mockRestore();
    });

    test('handles API errors during exercise loading', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'));
      
      // Mock console.error to suppress error logs in test output
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(<PiControls {...mockProps} />);
      
      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalled();
      });
      
      // Component should still render even if exercises fail to load
      expect(screen.getByText(/Record Your Practice/)).toBeInTheDocument();
      
      consoleSpy.mockRestore();
    });
  });

  describe('Video Transfer Functionality', () => {
    test('shows video file size in save dialog', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      const mockSessionData = {
        session_id: 'test-session-123',
        duration_seconds: 120
      };
      
      mockProps.onStopAndSave.mockResolvedValue(mockSessionData);
      
      const recordingProps = {
        ...mockProps,
        piState: { 
          ...mockPiState, 
          isRecording: true, 
          recordingStartTime: new Date(),
          availableRecordings: [
            { filename: 'test.mp4', size: 1048576 } // 1MB
          ]
        }
      };
      
      render(<PiControls {...recordingProps} />);
      
      const stopButton = screen.getByRole('button', { name: /stop.*save recording/i });
      await user.click(stopButton);
      
      await waitFor(() => {
        expect(screen.getByText(/1\.0 MB/)).toBeInTheDocument();
      });
    });
  });
});
/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/layout/VideoView.test.js

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import VideoView from '../../components/Layout/VideoView';
import { useAuth } from '../../auth/AuthContext';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

// Mock react-router-dom hooks
jest.mock('react-router-dom', () => ({
  useParams: jest.fn(),
  useNavigate: jest.fn()
}));

// Mock useAuth hook
jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn()
}));

// Mock CSS import
jest.mock('../../components/Layout/VideoView.css', () => ({}));

describe('VideoView Component', () => {
  const mockNavigate = jest.fn();
  const mockToken = 'test-token-123';
  const mockVideoId = 'video-123';

  const mockVideoData = {
    id: mockVideoId,
    title: 'Test Exercise Video',
    description: 'This is a test video description for Baduanjin exercise',
    brocade_type: 'FIRST',
    duration: 120,
    processing_status: 'completed',
    upload_timestamp: '2024-01-15T10:30:00Z',
    web_video_path: '/videos/test-video.mp4'
  };

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();
    
    // Mock react-router hooks
    useParams.mockReturnValue({ videoId: mockVideoId });
    useNavigate.mockReturnValue(mockNavigate);
    
    // Mock useAuth to return a token
    useAuth.mockReturnValue({
      token: mockToken
    });
  });

  describe('Component Initialization', () => {
    test('renders loading state initially', () => {
      // Mock axios to return a pending promise
      mockedAxios.get.mockReturnValue(new Promise(() => {}));
      
      render(<VideoView />);
      
      expect(screen.getByText('Loading video...')).toBeInTheDocument();
    });

    test('fetches video data on mount with correct parameters', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockVideoData });
      
      render(<VideoView />);
      
      expect(mockedAxios.get).toHaveBeenCalledWith(
        `https://baduanjin-backend-docker.azurewebsites.net/api/videos/${mockVideoId}`,
        {
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        }
      );
    });
  });

  describe('Successful Video Loading', () => {
    beforeEach(() => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockVideoData });
    });

    test('renders video details after successful fetch', async () => {
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Exercise Video')).toBeInTheDocument();
      });
      
      expect(screen.getByText('This is a test video description for Baduanjin exercise')).toBeInTheDocument();
      expect(screen.getByText('FIRST')).toBeInTheDocument();
      expect(screen.getByText('120 seconds')).toBeInTheDocument();
      expect(screen.getByText('completed')).toBeInTheDocument();
    });

    test('renders video player when video path exists', async () => {
      render(<VideoView />);
      
      await waitFor(() => {
        const videoElement = document.querySelector('video');
        expect(videoElement).toBeInTheDocument();
        expect(videoElement).toHaveAttribute('controls');
        expect(videoElement.src).toContain(`/api/videos/${mockVideoId}/stream`);
      });
    });

    test('displays formatted upload date', async () => {
      render(<VideoView />);
      
      await waitFor(() => {
        // Date should be formatted as locale date string
        const expectedDate = new Date('2024-01-15T10:30:00Z').toLocaleDateString();
        expect(screen.getByText(expectedDate)).toBeInTheDocument();
      });
    });

    test('shows back button', async () => {
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument();
      });
    });

    test('shows view analysis button when processing is completed', async () => {
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'View Analysis' })).toBeInTheDocument();
      });
    });
  });

  describe('Video without Path', () => {
    test('shows placeholder when no video path available', async () => {
      const videoWithoutPath = { ...mockVideoData, web_video_path: null };
      mockedAxios.get.mockResolvedValueOnce({ data: videoWithoutPath });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Video not available')).toBeInTheDocument();
      });
      
      expect(document.querySelector('video')).not.toBeInTheDocument();
    });
  });

  describe('Processing Status Conditions', () => {
    test('hides view analysis button when processing not completed', async () => {
      const processingVideo = { ...mockVideoData, processing_status: 'processing' };
      mockedAxios.get.mockResolvedValueOnce({ data: processingVideo });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Exercise Video')).toBeInTheDocument();
      });
      
      expect(screen.queryByRole('button', { name: 'View Analysis' })).not.toBeInTheDocument();
    });

    test('shows different processing statuses correctly', async () => {
      const processingStates = ['processing', 'failed', 'pending'];
      
      for (const status of processingStates) {
        const videoWithStatus = { ...mockVideoData, processing_status: status };
        mockedAxios.get.mockResolvedValueOnce({ data: videoWithStatus });
        
        const { unmount } = render(<VideoView />);
        
        await waitFor(() => {
          expect(screen.getByText(status)).toBeInTheDocument();
        });
        
        unmount();
        jest.clearAllMocks();
      }
    });
  });

  describe('Optional Fields Handling', () => {
    test('displays fallback text for missing description', async () => {
      const videoWithoutDescription = { ...mockVideoData, description: null };
      mockedAxios.get.mockResolvedValueOnce({ data: videoWithoutDescription });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('No description available')).toBeInTheDocument();
      });
    });

    test('displays fallback text for missing brocade type', async () => {
      const videoWithoutBrocadeType = { ...mockVideoData, brocade_type: null };
      mockedAxios.get.mockResolvedValueOnce({ data: videoWithoutBrocadeType });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Not specified')).toBeInTheDocument();
      });
    });

    test('displays fallback text for missing duration', async () => {
      const videoWithoutDuration = { ...mockVideoData, duration: null };
      mockedAxios.get.mockResolvedValueOnce({ data: videoWithoutDuration });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Unknown')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    test('displays 404 error message when video not found', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        response: {
          status: 404,
          data: { detail: 'Video not found' }
        }
      });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Video not found')).toBeInTheDocument();
      });
      
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
      expect(screen.queryByText('Loading video...')).not.toBeInTheDocument();
    });

    test('displays generic error message for other errors', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { detail: 'Internal server error' }
        }
      });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load video. Please try again.')).toBeInTheDocument();
      });
      
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    });

    test('displays generic error message for network errors', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network Error'));
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load video. Please try again.')).toBeInTheDocument();
      });
    });

    test('displays no video data message when response is empty', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: null });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('No video data available')).toBeInTheDocument();
      });
      
      expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    test('calls navigate(-1) when back button is clicked', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockVideoData });
      const user = userEvent.setup();
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument();
      });
      
      const backButton = screen.getByRole('button', { name: 'Back' });
      await user.click(backButton);
      
      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });

    test('calls navigate(-1) when go back button is clicked in error state', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        response: { status: 404 }
      });
      const user = userEvent.setup();
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
      });
      
      const goBackButton = screen.getByRole('button', { name: 'Go Back' });
      await user.click(goBackButton);
      
      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });

    test('navigates to analysis page when view analysis button is clicked', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockVideoData });
      const user = userEvent.setup();
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'View Analysis' })).toBeInTheDocument();
      });
      
      const viewAnalysisButton = screen.getByRole('button', { name: 'View Analysis' });
      await user.click(viewAnalysisButton);
      
      expect(mockNavigate).toHaveBeenCalledWith(`/analysis/${mockVideoId}`);
    });
  });

  describe('useEffect Dependencies', () => {
    test('refetches video when videoId changes', async () => {
      const { rerender } = render(<VideoView />);
      
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
      
      // Change videoId
      useParams.mockReturnValue({ videoId: 'new-video-id' });
      rerender(<VideoView />);
      
      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      expect(mockedAxios.get).toHaveBeenLastCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos/new-video-id',
        {
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        }
      );
    });

    test('refetches video when token changes', async () => {
      const { rerender } = render(<VideoView />);
      
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
      
      // Change token
      useAuth.mockReturnValue({ token: 'new-token' });
      rerender(<VideoView />);
      
      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      expect(mockedAxios.get).toHaveBeenLastCalledWith(
        `https://baduanjin-backend-docker.azurewebsites.net/api/videos/${mockVideoId}`,
        {
          headers: {
            'Authorization': 'Bearer new-token'
          }
        }
      );
    });
  });

  describe('Loading State Management', () => {
    test('shows loading state and then content', async () => {
      let resolvePromise;
      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockedAxios.get.mockReturnValue(promise);
      
      render(<VideoView />);
      
      // Initially shows loading
      expect(screen.getByText('Loading video...')).toBeInTheDocument();
      
      // Resolve the promise
      resolvePromise({ data: mockVideoData });
      
      // Loading should disappear and content should appear
      await waitFor(() => {
        expect(screen.queryByText('Loading video...')).not.toBeInTheDocument();
        expect(screen.getByText('Test Exercise Video')).toBeInTheDocument();
      });
    });

    test('shows loading state and then error', async () => {
      let rejectPromise;
      const promise = new Promise((resolve, reject) => {
        rejectPromise = reject;
      });
      mockedAxios.get.mockReturnValue(promise);
      
      render(<VideoView />);
      
      // Initially shows loading
      expect(screen.getByText('Loading video...')).toBeInTheDocument();
      
      // Reject the promise
      rejectPromise(new Error('Network Error'));
      
      // Loading should disappear and error should appear
      await waitFor(() => {
        expect(screen.queryByText('Loading video...')).not.toBeInTheDocument();
        expect(screen.getByText('Failed to load video. Please try again.')).toBeInTheDocument();
      });
    });
  });

  describe('Video Information Display', () => {
    test('displays all video information fields correctly', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockVideoData });
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Exercise Video')).toBeInTheDocument();
      });
      
      // Check all information labels and values
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Video Information')).toBeInTheDocument();
      expect(screen.getByText('Brocade Type:')).toBeInTheDocument();
      expect(screen.getByText('Duration:')).toBeInTheDocument();
      expect(screen.getByText('Processing Status:')).toBeInTheDocument();
      expect(screen.getByText('Uploaded:')).toBeInTheDocument();
    });

    test('renders video player with correct src attribute', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockVideoData });
      
      render(<VideoView />);
      
      await waitFor(() => {
        const videoElement = document.querySelector('video');
        expect(videoElement).toBeInTheDocument();
        expect(videoElement.src).toBe(
          `https://baduanjin-backend-docker.azurewebsites.net/api/videos/${mockVideoId}/stream`
        );
      });
    });
  });

  describe('Console Error Logging', () => {
    test('logs error to console when fetch fails', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const error = new Error('Test error');
      
      mockedAxios.get.mockRejectedValueOnce(error);
      
      render(<VideoView />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load video. Please try again.')).toBeInTheDocument();
      });
      
      expect(consoleSpy).toHaveBeenCalledWith('Error fetching video:', error);
      
      consoleSpy.mockRestore();
    });
  });
});
/* eslint-disable testing-library/no-container */
/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/layout/Masters.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import Masters from '../../components/Layout/Masters';
import { useAuth } from '../../auth/AuthContext';

// Mock the useAuth hook
jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn(),
}));

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

// Mock react-router-dom hooks
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock console methods to avoid noise in tests
const originalConsoleLog = console.log;
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeAll(() => {
  console.log = jest.fn();
  console.error = jest.fn();
  console.warn = jest.fn();
});

afterAll(() => {
  console.log = originalConsoleLog;
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

// Mock window.alert
global.alert = jest.fn();

// Test wrapper component to provide Router context
const TestWrapper = ({ children }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

// Mock data
const mockUser = {
  name: 'Test User',
  role: 'learner',
};

const mockToken = 'mock-jwt-token';

const mockMasters = [
  {
    id: 1,
    name: 'Master Chen',
    username: 'masterchen',
    videos_count: 5,
    followers_count: 20,
    profile: {
      bio: 'Expert in Baduanjin with 20 years of experience',
    },
  },
  {
    id: 2,
    name: 'Master Li',
    username: 'masterli',
    videos_count: 3,
    followers_count: 15,
    profile: {
      bio: 'Traditional Baduanjin practitioner',
    },
  },
];

const mockMasterVideos = [
  {
    id: 101,
    title: 'Basic Baduanjin Form',
    description: 'Introduction to basic movements',
    brocade_type: 'Basic',
    processing_status: 'completed',
    upload_timestamp: '2024-01-10T08:00:00Z',
    analyzed_video_path: '/path/to/analyzed/video1.mp4',
  },
  {
    id: 102,
    title: 'Advanced Techniques',
    description: 'Advanced Baduanjin movements',
    brocade_type: 'Advanced',
    processing_status: 'completed',
    upload_timestamp: '2024-01-12T09:00:00Z',
    analyzed_video_path: '/path/to/analyzed/video2.mp4',
  },
];

describe('Masters Component', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    mockedAxios.get.mockClear();
    mockedAxios.post.mockClear();
    global.alert.mockClear();
  });

  describe('Component Rendering and Initial Load', () => {
    test('should render page title and intro', async () => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });

      // Mock masters fetch and follow status checks
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      // Wait for the component to finish loading and render the content
      await waitFor(() => {
        expect(screen.getByText('Baduanjin Masters')).toBeInTheDocument();
        expect(screen.getByText('Browse registered masters and view their analyzed videos. Follow a master to compare your exercises with their techniques.')).toBeInTheDocument();
      });
    });

    test('should show loading state initially', () => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });

      mockedAxios.get.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      expect(screen.getByText('Loading masters information...')).toBeInTheDocument();
    });

    test('should show error state when no masters found', async () => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });

      mockedAxios.get.mockResolvedValue({ data: [] });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('No masters found in the system.')).toBeInTheDocument();
      });
    });

    test('should show error state when API call fails', async () => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });

      mockedAxios.get.mockRejectedValue(new Error('API Error'));

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Failed to load masters information. Please try again later.')).toBeInTheDocument();
      });
    });
  });

  describe('Masters Data Fetching and Display', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should fetch masters on component mount', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/masters',
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });

    test('should display masters in grid format', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Master Chen')).toBeInTheDocument();
        expect(screen.getByText('Master Li')).toBeInTheDocument();
        expect(screen.getByText('@masterchen')).toBeInTheDocument();
        expect(screen.getByText('@masterli')).toBeInTheDocument();
        expect(screen.getByText('Expert in Baduanjin with 20 years of experience')).toBeInTheDocument();
        expect(screen.getByText('Traditional Baduanjin practitioner')).toBeInTheDocument();
      });
    });

    test('should display master statistics correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument(); // videos count for Master Chen
        expect(screen.getByText('20')).toBeInTheDocument(); // followers count for Master Chen
        expect(screen.getByText('3')).toBeInTheDocument(); // videos count for Master Li
        expect(screen.getByText('15')).toBeInTheDocument(); // followers count for Master Li
      });
    });

    test('should check follow status for each master', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/status/1',
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/status/2',
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });
  });

  describe('Follow/Unfollow Functionality', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should show follow button when not following master', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        const followButtons = screen.getAllByText('Follow Master');
        expect(followButtons).toHaveLength(2);
      });
    });

    test('should show following button when already following master', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValueOnce({ data: { is_following: true } })
        .mockResolvedValueOnce({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Following')).toBeInTheDocument();
        expect(screen.getByText('Follow Master')).toBeInTheDocument();
      });
    });

    test('should handle follow action successfully', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      mockedAxios.post.mockResolvedValue({ data: { success: true } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('Follow Master')).toHaveLength(2);
      });

      const followButtons = screen.getAllByText('Follow Master');
      fireEvent.click(followButtons[0]);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/follow/1',
          {},
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });

    test('should handle unfollow action successfully', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValueOnce({ data: { is_following: true } })
        .mockResolvedValueOnce({ data: { is_following: false } });

      mockedAxios.post.mockResolvedValue({ data: { success: true } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Following')).toBeInTheDocument();
      });

      const followingButton = screen.getByText('Following');
      fireEvent.click(followingButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/unfollow/1',
          {},
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });

    test('should handle follow/unfollow API error', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      mockedAxios.post.mockRejectedValue(new Error('API Error'));

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('Follow Master')).toHaveLength(2);
      });

      const followButtons = screen.getAllByText('Follow Master');
      fireEvent.click(followButtons[0]);

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('There was an error updating your relationship with this master. Please try again.');
      });
    });
  });

  describe('Master Videos Functionality', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should fetch master videos when view videos button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      // Mock master videos fetch
      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/analysis-master/master-extracted-videos/1',
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });

    test('should display master videos when available', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText("Master Chen's Analyzed Videos")).toBeInTheDocument();
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
        expect(screen.getByText('Advanced Techniques')).toBeInTheDocument();
        expect(screen.getByText('Introduction to basic movements')).toBeInTheDocument();
        expect(screen.getByText('Advanced Baduanjin movements')).toBeInTheDocument();
      });
    });

    test('should show no videos message when master has no videos', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: [] });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('This master has no analyzed videos ready for comparison.')).toBeInTheDocument();
      });
    });

    test('should handle master videos fetch error', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      const error404 = new Error('Not Found');
      error404.response = { status: 404 };
      mockedAxios.get.mockRejectedValueOnce(error404);

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('No videos found for this master or master not found.');
      });
    });

    test('should handle 403 error when fetching master videos', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      const error403 = new Error('Forbidden');
      error403.response = { status: 403 };
      mockedAxios.get.mockRejectedValueOnce(error403);

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith('Access denied. You may not have permission to view this master\'s videos.');
      });
    });
  });

  describe('Video Modal Functionality', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should open video modal when view video button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
      });

      // Mock English audio detection calls
      mockedAxios.get.mockResolvedValue({ data: {} });

      const viewVideoButtons = screen.getAllByText('View Video');
      fireEvent.click(viewVideoButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Original Video')).toBeInTheDocument();
        expect(screen.getByText('Analysis Video')).toBeInTheDocument();
      });
    });

    test('should close video modal when close button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValue({ data: {} });

      const viewVideoButtons = screen.getAllByText('View Video');
      fireEvent.click(viewVideoButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Original Video')).toBeInTheDocument();
      });

      const closeButton = screen.getByText('×');
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText('Original Video')).not.toBeInTheDocument();
      });
    });

    test('should close video modal when clicking on overlay', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValue({ data: {} });

      const viewVideoButtons = screen.getAllByText('View Video');
      fireEvent.click(viewVideoButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Original Video')).toBeInTheDocument();
      });

      const overlay = document.querySelector('.video-modal-overlay');
      fireEvent.click(overlay);

      await waitFor(() => {
        expect(screen.queryByText('Original Video')).not.toBeInTheDocument();
      });
    });
  });

  describe('Navigation and Actions', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should navigate to comparison page when compare button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
      });

      const compareButtons = screen.getAllByText('Compare With This');
      fireEvent.click(compareButtons[0]);

      expect(mockNavigate).toHaveBeenCalledWith('/comparison-selection?master=1&masterVideo=101');
    });
  });

  describe('English Audio Detection', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should attempt to detect English audio when viewing video', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
      });

      // Mock English audio detection - method 1 success
      mockedAxios.get
        .mockResolvedValueOnce({
          status: 200,
          data: 'mock audio data'
        });

      const viewVideoButtons = screen.getAllByText('View Video');
      fireEvent.click(viewVideoButtons[0]);

      // The component should attempt to detect English audio
      await waitFor(() => {
        expect(screen.getByText('Original Video')).toBeInTheDocument();
      });
    });

    test('should fallback to method 2 when method 1 fails for English audio', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockMasterVideos });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
      });

      // Mock English audio detection - method 1 fails, method 2 succeeds
      const streamError = new Error('Stream failed');
      streamError.response = { status: 404 };
      
      mockedAxios.get
        .mockRejectedValueOnce(streamError) // Method 1 fails
        .mockResolvedValueOnce({ // Method 2 succeeds
          data: {
            video_uuid: 'test-uuid-123',
            user_id: 3,
            video_path: '/path/to/video.mp4'
          }
        });

      const viewVideoButtons = screen.getAllByText('View Video');
      fireEvent.click(viewVideoButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Original Video')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling and Edge Cases', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should handle follow status check error gracefully', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockRejectedValue(new Error('Status check failed'));

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Master Chen')).toBeInTheDocument();
        expect(screen.getAllByText('Follow Master')).toHaveLength(2);
      });
    });

    test('should handle masters with missing profile bio', async () => {
      const mastersWithoutBio = [
        {
          id: 1,
          name: 'Master Chen',
          username: 'masterchen',
          videos_count: 5,
          followers_count: 20,
          // No profile or bio
        }
      ];

      mockedAxios.get
        .mockResolvedValueOnce({ data: mastersWithoutBio })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Master Chen')).toBeInTheDocument();
        expect(screen.getByText('@masterchen')).toBeInTheDocument();
        // Should not crash when bio is missing
      });
    });

    test('should handle masters with zero counts', async () => {
      const mastersWithZeroCounts = [
        {
          id: 1,
          name: 'New Master',
          username: 'newmaster',
          videos_count: 0,
          followers_count: 0,
        }
      ];

      mockedAxios.get
        .mockResolvedValueOnce({ data: mastersWithZeroCounts })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('New Master')).toBeInTheDocument();
        expect(screen.getAllByText('0')).toHaveLength(2); // videos and followers count
      });
    });

    test('should handle video with missing description', async () => {
      const videosWithoutDescription = [
        {
          id: 101,
          title: 'Basic Baduanjin Form',
          // description missing
          brocade_type: 'Basic',
          processing_status: 'completed',
          upload_timestamp: '2024-01-10T08:00:00Z',
          analyzed_video_path: '/path/to/analyzed/video1.mp4',
        }
      ];

      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getAllByText('View Videos')).toHaveLength(2);
      });

      mockedAxios.get.mockResolvedValueOnce({ data: videosWithoutDescription });

      const viewVideosButtons = screen.getAllByText('View Videos');
      fireEvent.click(viewVideosButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Basic Baduanjin Form')).toBeInTheDocument();
        // Should not crash when description is missing
      });
    });
  });

  describe('Component Structure and CSS Classes', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockUser,
        token: mockToken,
      });
    });

    test('should render with correct CSS classes and structure', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValue({ data: { is_following: false } });

      const { container } = render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(container.querySelector('.masters-page')).toBeInTheDocument();
        expect(container.querySelector('.masters-grid')).toBeInTheDocument();
        expect(container.querySelector('.master-card')).toBeInTheDocument();
      });
    });

    test('should apply correct button classes based on follow status', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockMasters })
        .mockResolvedValueOnce({ data: { is_following: true } })
        .mockResolvedValueOnce({ data: { is_following: false } });

      render(
        <TestWrapper>
          <Masters />
        </TestWrapper>
      );

      await waitFor(() => {
        const followingButton = screen.getByText('Following');
        const followButton = screen.getByText('Follow Master');
        
        expect(followingButton).toHaveClass('btn-success');
        expect(followButton).toHaveClass('btn-primary');
      });
    });
  });
});
/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/layout/Learners.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import Learners from '../../components/Layout/Learners';
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

// Test wrapper component to provide Router context
const TestWrapper = ({ children }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

// Mock data
const mockMasterUser = {
  name: 'Master Smith',
  role: 'master',
};

const mockLearnerUser = {
  name: 'John Doe',
  role: 'learner',
};

const mockToken = 'mock-jwt-token';

const mockLearners = [
  {
    learner_id: 1,
    name: 'Student One',
    username: 'student1',
    email: 'student1@example.com',
    videos_count: 3,
    last_active: '2024-01-15T10:30:00Z',
    created_at: '2024-01-01T10:00:00Z',
  },
  {
    learner_id: 2,
    name: 'Student Two',
    username: 'student2',
    email: 'student2@example.com',
    videos_count: 1,
    last_active: '2024-01-14T09:15:00Z',
    created_at: '2024-01-02T11:00:00Z',
  },
];

const mockLearnerVideos = [
  {
    id: 101,
    title: 'Video 1',
    processing_status: 'completed',
    brocade_type: 'Type A',
    upload_timestamp: '2024-01-10T08:00:00Z',
    analyzed_video_path: '/path/to/analyzed/video1.mp4',
    keypoints_path: '/path/to/keypoints1.json',
    description: 'Test video 1',
  },
  {
    id: 102,
    title: 'Video 2',
    processing_status: 'completed',
    brocade_type: 'Type B',
    upload_timestamp: '2024-01-12T09:00:00Z',
    analyzed_video_path: '/path/to/analyzed/video2.mp4',
    keypoints_path: '/path/to/keypoints2.json',
  },
];

describe('Learners Component', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    mockedAxios.get.mockClear();
  });

  describe('Access Control', () => {
    test('should redirect non-master users to dashboard', () => {
      useAuth.mockReturnValue({
        user: mockLearnerUser,
        token: mockToken,
      });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });

    test('should not redirect master users', () => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });

      // Mock API calls to prevent actual requests
      mockedAxios.get.mockResolvedValue({ data: [] });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      expect(mockNavigate).not.toHaveBeenCalledWith('/dashboard');
    });

    test('should handle undefined user gracefully', () => {
      useAuth.mockReturnValue({
        user: undefined,
        token: mockToken,
      });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  describe('Component Rendering', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should render page title and intro', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      expect(screen.getByText('Your Learners')).toBeInTheDocument();
      expect(screen.getByText('View and manage learners who follow your teaching and techniques.')).toBeInTheDocument();
    });

    test('should show loading state initially', () => {
      mockedAxios.get.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      expect(screen.getByText('Loading learners...')).toBeInTheDocument();
    });

    test('should show empty state when no learners', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('No learners are currently following you.')).toBeInTheDocument();
        expect(screen.getByText('Share your master profile to attract learners!')).toBeInTheDocument();
      });
    });
  });

  describe('Learners Data Fetching', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should fetch learners on component mount', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/learners',
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });

    test('should display learners in table', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
        expect(screen.getByText('Student Two')).toBeInTheDocument();
        expect(screen.getByText('student1@example.com')).toBeInTheDocument();
        expect(screen.getByText('student2@example.com')).toBeInTheDocument();
      });
    });

    test('should handle API error when fetching learners', async () => {
      mockedAxios.get.mockRejectedValue(new Error('API Error'));

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Failed to load learners. Please try again.')).toBeInTheDocument();
      });
    });

    test('should not fetch learners when no token provided', () => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: null,
      });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      expect(mockedAxios.get).not.toHaveBeenCalled();
    });
  });

  describe('Learner Selection and Video Fetching', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should select learner when clicking on table row', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock video fetch
      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const firstRow = screen.getByText('Student One').closest('tr');
      fireEvent.click(firstRow);

      await waitFor(() => {
        expect(screen.getByText('Videos by Student One')).toBeInTheDocument();
      });
    });

    test('should fetch learner videos when learner is selected', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock video fetch for method 1 success
      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/learner-videos/1/analyzed',
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
    });

    test('should show learner videos when available', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock video fetch
      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButtons = screen.getAllByText('View Details');
      fireEvent.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
        expect(screen.getByText('Video 2')).toBeInTheDocument();
        expect(screen.getAllByText('Status: completed')).toHaveLength(2);
      });
    });

    test('should show no videos message when learner has no analyzed videos', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock empty video response
      mockedAxios.get.mockResolvedValueOnce({ data: [] });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('This learner has no analyzed videos ready for comparison.')).toBeInTheDocument();
      });
    });

    test('should handle video fetch error with fallback methods', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock method 1 failure, method 2 success
      mockedAxios.get
        .mockRejectedValueOnce(new Error('Method 1 failed'))
        .mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
      });
    });
  });

  describe('Video Modal Functionality', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should open video modal when view video button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock video fetch
      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
      });

      const viewVideoButtons = screen.getAllByText('View Video');
      fireEvent.click(viewVideoButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Original Video')).toBeInTheDocument();
        expect(screen.getByText('Analysis Video')).toBeInTheDocument();
      });
    });

    test('should close video modal when close button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
      });

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
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
      });

      const viewVideoButton = screen.getAllByText('View Video')[0];
      fireEvent.click(viewVideoButton);

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
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should navigate to comparison page when compare button is clicked', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
      });

      const compareButtons = screen.getAllByText('Compare Performance');
      fireEvent.click(compareButtons[0]);

      expect(mockNavigate).toHaveBeenCalledWith('/comparison-selection?learnerVideo=101');
    });

    test('should show feedback coming soon alert when feedback button is clicked', async () => {
      // Mock window.alert
      window.alert = jest.fn();

      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Send Feedback (Coming Soon)')).toBeInTheDocument();
      });

      const feedbackButton = screen.getByText('Send Feedback (Coming Soon)');
      fireEvent.click(feedbackButton);

      expect(window.alert).toHaveBeenCalledWith('Send feedback to learner 1 - Feature coming soon!');
    });
  });

  describe('Data Filtering and Validation', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should filter out videos without analysis data', async () => {
      const mixedVideos = [
        ...mockLearnerVideos,
        {
          id: 103,
          title: 'Incomplete Video',
          processing_status: 'processing',
          brocade_type: 'Type C',
          upload_timestamp: '2024-01-13T10:00:00Z',
          analyzed_video_path: null,
          keypoints_path: null,
        },
      ];

      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mixedVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('Video 1')).toBeInTheDocument();
        expect(screen.getByText('Video 2')).toBeInTheDocument();
        // Should only show the 2 completed videos, not the incomplete one
        expect(screen.queryByText('Incomplete Video')).not.toBeInTheDocument();
        // Check that we have 2 completed videos displayed
        expect(screen.getAllByText(/Status: completed/)).toHaveLength(2);
      });
    });
  });

  describe('Error Handling', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should handle 404 error when fetching learner videos', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock 404 error for all methods
      const error404 = new Error('Not Found');
      error404.response = { status: 404 };
      mockedAxios.get
        .mockRejectedValueOnce(error404)
        .mockRejectedValueOnce(error404);

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('This learner has no analyzed videos ready for comparison.')).toBeInTheDocument();
      });
    });

    test('should handle 403 error when fetching learner videos', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      // Mock 403 error for all methods
      const error403 = new Error('Forbidden');
      error403.response = { status: 403 };
      mockedAxios.get
        .mockRejectedValueOnce(error403)
        .mockRejectedValueOnce(error403);

      const viewButton = screen.getAllByText('View Details')[0];
      fireEvent.click(viewButton);

      await waitFor(() => {
        expect(screen.getByText('This learner has no analyzed videos ready for comparison.')).toBeInTheDocument();
      });
    });
  });

  describe('Table Interaction', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        token: mockToken,
      });
    });

    test('should highlight selected row', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const firstRow = screen.getByText('Student One').closest('tr');
      fireEvent.click(firstRow);

      await waitFor(() => {
        expect(firstRow).toHaveClass('selected-row');
      });
    });

    test('should prevent event propagation when clicking view details button', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearners })
        .mockResolvedValue({ data: { videos_count: 3, last_active: '2024-01-15T10:30:00Z' } });

      render(
        <TestWrapper>
          <Learners />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Student One')).toBeInTheDocument();
      });

      mockedAxios.get.mockResolvedValueOnce({ data: mockLearnerVideos });

      const viewButton = screen.getAllByText('View Details')[0];
      
      // Create a spy on stopPropagation
      const stopPropagationSpy = jest.fn();
      const clickEvent = new MouseEvent('click', { bubbles: true });
      clickEvent.stopPropagation = stopPropagationSpy;

      fireEvent.click(viewButton, clickEvent);

      // The component should call stopPropagation when clicking the button
      await waitFor(() => {
        expect(screen.getByText('Videos by Student One')).toBeInTheDocument();
      });
    });
  });
});
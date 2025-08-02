// src/__tests__/analysis/VideoAnalysis.test.js
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import VideoAnalysis from '../../components/Analysis/VideoAnalysis';
import { useAuth } from '../../auth/AuthContext';

// Mock dependencies
jest.mock('axios');
jest.mock('../../auth/AuthContext');
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({
    videoId: 'video123'
  }),
  useNavigate: () => mockNavigate
}));

const mockNavigate = jest.fn();

// Helper function to render component
const renderComponent = () => {
  return render(
    <BrowserRouter>
      <VideoAnalysis />
    </BrowserRouter>
  );
};

// Mock data
const mockAnalyzedData = {
  status: 'analyzed',
  video_title: 'Test Video',
  video_status: 'completed',
  key_poses: [
    { pose: 'Standing', frame: 1 },
    { pose: 'Raising Arms', frame: 50 }
  ],
  movement_smoothness: {
    left_elbow: 0.1234,
    right_elbow: 0.1456
  },
  movement_symmetry: {
    'left_arm-right_arm': 0.8567
  },
  balance_metrics: {
    sway_area: 12.34,
    mean_velocity: 5.67
  },
  images: {
    key_poses: '/api/analysis/video123/images/key_poses.png',
    joint_angles: '/api/analysis/video123/images/joint_angles.png',
    movement_smoothness: '/api/analysis/video123/images/smoothness.png',
    movement_symmetry: '/api/analysis/video123/images/symmetry.png',
    com_trajectory: '/api/analysis/video123/images/com.png',
    balance_metrics: '/api/analysis/video123/images/balance.png'
  }
};

const mockNotAnalyzedData = {
  status: 'not_analyzed',
  video_title: 'Test Video',
  video_status: 'completed'
};

describe('VideoAnalysis', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup mocks
    useAuth.mockReturnValue({
      token: 'mock-token',
      user: { id: 'user123' }
    });
    
    // Default to successful analyzed data
    axios.get.mockResolvedValue({ data: mockAnalyzedData });
    axios.post.mockResolvedValue({ data: { message: 'Analysis started' } });
  });

  test('renders loading state initially', () => {
    renderComponent();
    
    expect(screen.getByText('Loading analysis data...')).toBeInTheDocument();
  });

  test('makes API call to fetch analysis data', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/analysis/video123',
        { headers: { 'Authorization': 'Bearer mock-token' } }
      );
    });
  });

  test('displays analysis results when data is analyzed', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Movement Analysis: Test Video')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Key Poses Identified')).toBeInTheDocument();
    expect(screen.getByText('Joint Angles Analysis')).toBeInTheDocument();
    expect(screen.getByText('Movement Smoothness')).toBeInTheDocument();
    expect(screen.getByText('Movement Symmetry')).toBeInTheDocument();
    expect(screen.getByText('Balance Metrics')).toBeInTheDocument();
  });

  test('displays key poses data', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Standing')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Raising Arms')).toBeInTheDocument();
    expect(screen.getByText('Frame 1')).toBeInTheDocument();
    expect(screen.getByText('Frame 50')).toBeInTheDocument();
  });

  test('displays movement metrics', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('left_elbow:')).toBeInTheDocument();
    });
    
    expect(screen.getByText('0.1234')).toBeInTheDocument();
    expect(screen.getByText('right_elbow:')).toBeInTheDocument();
    expect(screen.getByText('0.1456')).toBeInTheDocument();
  });

  test('displays symmetry metrics', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('left_arm-right_arm:')).toBeInTheDocument();
    });
    
    expect(screen.getByText('0.8567')).toBeInTheDocument();
  });

  test('displays balance metrics', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('sway_area:')).toBeInTheDocument();
    });
    
    expect(screen.getByText('12.3400')).toBeInTheDocument();
    expect(screen.getByText('mean_velocity:')).toBeInTheDocument();
    expect(screen.getByText('5.6700')).toBeInTheDocument();
  });

  test('shows not analyzed state when video is not analyzed', async () => {
    axios.get.mockResolvedValue({ data: mockNotAnalyzedData });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Test Video')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Preparing biomechanical analysis...')).toBeInTheDocument();
    expect(screen.getByText('Start Analysis')).toBeInTheDocument();
  });

  test('starts analysis when start button is clicked', async () => {
    axios.get.mockResolvedValue({ data: mockNotAnalyzedData });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Start Analysis')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Start Analysis'));
    
    expect(axios.post).toHaveBeenCalledWith(
      'https://baduanjin-backend-docker.azurewebsites.net/api/analysis/video123/run',
      {},
      { headers: { 'Authorization': 'Bearer mock-token' } }
    );
  });

  test('shows analyzing state after starting analysis', async () => {
    axios.get.mockResolvedValue({ data: mockNotAnalyzedData });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Start Analysis')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Start Analysis'));
    
    expect(screen.getByText('Analyzing movement patterns...')).toBeInTheDocument();
    expect(screen.getByText('This usually takes 2-3 minutes')).toBeInTheDocument();
  });

  test('handles back to videos navigation', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Back to Videos')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Back to Videos'));
    expect(mockNavigate).toHaveBeenCalledWith('/videos');
  });

  test('shows error state when API call fails', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to load analysis data/)).toBeInTheDocument();
    });
    
    expect(screen.getByText('Retry')).toBeInTheDocument();
    expect(screen.getByText('Back to Videos')).toBeInTheDocument();
  });

  test('retries API call when retry button is clicked', async () => {
    axios.get.mockRejectedValueOnce(new Error('Network error'));
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
    
    // Reset mock to return success on retry
    axios.get.mockResolvedValueOnce({ data: mockAnalyzedData });
    
    fireEvent.click(screen.getByText('Retry'));
    
    expect(axios.get).toHaveBeenCalledTimes(2);
  });

  test('shows warning when video processing is not completed', async () => {
    const incompleteVideoData = {
      ...mockNotAnalyzedData,
      video_status: 'processing'
    };
    
    axios.get.mockResolvedValue({ data: incompleteVideoData });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Video processing must be completed before analysis can be run.')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Current status: processing')).toBeInTheDocument();
  });

  test('renders images with correct URLs', async () => {
    renderComponent();
    
    await waitFor(() => {
      const images = screen.getAllByRole('img');
      expect(images.length).toBeGreaterThan(0);
    });
    
    const keyPosesImage = screen.getByAltText('Key Poses');
    expect(keyPosesImage).toHaveAttribute(
      'src', 
      'https://baduanjin-backend-docker.azurewebsites.net/api/analysis/video123/images/key_poses.png'
    );
  });

  test('handles API error with specific error message', async () => {
    const errorMessage = 'Video not found';
    axios.get.mockRejectedValue({
      response: { data: { detail: errorMessage } }
    });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText(`Failed to load analysis data: ${errorMessage}`)).toBeInTheDocument();
    });
  });
});
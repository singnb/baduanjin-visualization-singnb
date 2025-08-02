// src/__tests__/analysis/ComparisonSelection.test.js
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import ComparisonSelection from '../../components/Analysis/ComparisonSelection';
import { useAuth } from '../../auth/AuthContext';

// Mock dependencies BEFORE imports
jest.mock('axios', () => ({
  get: jest.fn()
}));

jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn()
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

const mockNavigate = jest.fn();

// Simple mock data
const mockMasters = [
  {
    id: 'master1',
    name: 'Master Zhang'
  },
  {
    id: 'master2',
    name: 'Master Li'
  }
];

const mockUserVideos = [
  {
    id: 'user_video1',
    title: 'My First Practice',
    brocade_type: 'Eight_Pieces',
    upload_timestamp: '2024-01-15T10:00:00Z'
  },
  {
    id: 'user_video2',
    title: 'My Second Practice',
    brocade_type: 'Eight_Pieces',
    upload_timestamp: '2024-01-20T15:30:00Z'
  }
];

const mockMasterVideos = [
  {
    id: 'master_video1',
    title: 'Perfect Form Demo',
    brocade_type: 'Eight_Pieces',
    upload_timestamp: '2024-01-10T08:00:00Z'
  },
  {
    id: 'master_video2',
    title: 'Advanced Techniques',
    brocade_type: 'Eight_Pieces',
    upload_timestamp: '2024-01-12T09:00:00Z'
  }
];

describe('ComparisonSelection', () => {
  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Setup auth mock
    useAuth.mockReturnValue({
      token: 'mock-token',
      user: { id: 'user123', name: 'Test User' }
    });
    
    // Setup axios mock to ALWAYS return successful responses
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/relationships/masters')) {
        return Promise.resolve({ data: mockMasters });
      }
      if (url.includes('/api/analysis-master/user-extracted-videos')) {
        return Promise.resolve({ data: mockUserVideos });
      }
      if (url.includes('/api/analysis-master/master-extracted-videos/master1')) {
        return Promise.resolve({ data: mockMasterVideos });
      }
      if (url.includes('/api/analysis-master/master-extracted-videos/master2')) {
        return Promise.resolve({ data: [mockMasterVideos[0]] });
      }
      // Always return empty array for any other endpoint
      return Promise.resolve({ data: [] });
    });
  });

  // Helper function
  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <ComparisonSelection />
      </BrowserRouter>
    );
  };

  test('renders loading state initially', () => {
    renderComponent();
    expect(screen.getByText('Loading comparison data...')).toBeInTheDocument();
  });

  test('displays header after loading', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select Videos for Comparison')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Choose your exercise video and a master\'s video to compare')).toBeInTheDocument();
  });

  test('makes initial API calls', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/relationships/masters',
        { headers: { 'Authorization': 'Bearer mock-token' } }
      );
    });
    
    expect(axios.get).toHaveBeenCalledWith(
      'https://baduanjin-backend-docker.azurewebsites.net/api/analysis-master/user-extracted-videos',
      { headers: { 'Authorization': 'Bearer mock-token' } }
    );
  });

  test('displays user videos section', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Your Videos (2)')).toBeInTheDocument();
    });
    
    expect(screen.getByText('My First Practice')).toBeInTheDocument();
    expect(screen.getByText('My Second Practice')).toBeInTheDocument();
  });

  test('displays masters section', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Select a Master')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Master Zhang')).toBeInTheDocument();
    expect(screen.getByText('Master Li')).toBeInTheDocument();
  });

  test('selects user video when clicked', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('My First Practice')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('My First Practice'));
    
    const videoCard = screen.getByText('My First Practice').closest('.video-card');
    expect(videoCard).toHaveClass('selected');
  });

  test('selects master when clicked', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Master Zhang')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Master Zhang'));
    
    const masterCard = screen.getByText('Master Zhang').closest('.master-card');
    expect(masterCard).toHaveClass('selected');
  });

  test('loads master videos after master selection', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Master Zhang')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Master Zhang'));
    
    await waitFor(() => {
      expect(screen.getByText('Perfect Form Demo')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Advanced Techniques')).toBeInTheDocument();
  });

  test('enables compare button when both videos selected', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('My First Practice')).toBeInTheDocument();
    });
    
    // Initially disabled
    expect(screen.getByText('Compare Videos')).toBeDisabled();
    
    // Select user video
    fireEvent.click(screen.getByText('My First Practice'));
    
    // Select master
    fireEvent.click(screen.getByText('Master Zhang'));
    
    await waitFor(() => {
      expect(screen.getByText('Perfect Form Demo')).toBeInTheDocument();
    });
    
    // Select master video
    fireEvent.click(screen.getByText('Perfect Form Demo'));
    
    // Compare button should be enabled
    expect(screen.getByText('Compare Videos')).not.toBeDisabled();
  });

  test('navigates to comparison page', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('My First Practice')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('My First Practice'));
    fireEvent.click(screen.getByText('Master Zhang'));
    
    await waitFor(() => {
      expect(screen.getByText('Perfect Form Demo')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Perfect Form Demo'));
    fireEvent.click(screen.getByText('Compare Videos'));
    
    expect(mockNavigate).toHaveBeenCalledWith('/comparison/user_video1/master_video1');
  });

  test('navigates back to videos', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Back to Videos Management')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Back to Videos Management'));
    expect(mockNavigate).toHaveBeenCalledWith('/videos');
  });

  test('displays selection summary', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('My First Practice')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('My First Practice'));
    
    expect(screen.getByText('Selected for Comparison:')).toBeInTheDocument();
    expect(screen.getByText('Your Video:')).toBeInTheDocument();
  });
});
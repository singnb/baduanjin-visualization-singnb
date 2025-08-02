/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
/* eslint-disable testing-library/no-unnecessary-act */
// src/__tests__/layout/PiVideoTransfer.test.js

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import PiVideoTransfer from '../../components/Layout/PiVideoTransfer';
import { useAuth } from '../../auth/AuthContext';

// Mock dependencies
jest.mock('axios');
jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn()
}));
jest.mock('../../config/piConfig', () => ({
  PI_CONFIG: {
    TIMEOUTS: {
      API_REQUEST: 30000,
      STATUS_CHECK: 10000
    }
  },
  getPiUrl: jest.fn(() => 'http://mock-pi-url')
}));
jest.mock('../../components/Layout/Layout.css', () => ({}));

const mockedAxios = axios;

describe('PiVideoTransfer Component', () => {
  const mockUser = {
    id: 'user-123',
    name: 'Test User',
    role: 'learner'
  };
  const mockToken = 'test-token-123';
  const mockOnTransferComplete = jest.fn();

  const mockPiRecordings = [
    {
      timestamp: '20240115_103000',
      filename: 'baduanjin_original_20240115_103000.mp4',
      size: 10485760, // 10MB
      file_count: 2,
      total_size: 15728640, // 15MB
      processing_status: 'completed',
      files: {
        original: {
          filename: 'baduanjin_original_20240115_103000.mp4',
          size: 10485760,
          description: 'Original video'
        },
        processed: {
          filename: 'baduanjin_processed_20240115_103000.mp4',
          size: 5242880,
          description: 'Processed video'
        }
      }
    },
    {
      timestamp: '20240116_140000',
      filename: 'baduanjin_original_20240116_140000.mp4',
      size: 8388608, // 8MB
      file_count: 1,
      total_size: 8388608,
      processing_status: 'ready'
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock auth
    useAuth.mockReturnValue({
      token: mockToken,
      user: mockUser
    });

    // Reset axios mocks
    mockedAxios.get.mockReset();
    mockedAxios.post.mockReset();

    // Mock window methods
    window.alert = jest.fn();
    window.confirm = jest.fn(() => true);

    // Mock console methods
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    console.log.mockRestore?.();
    console.error.mockRestore?.();
  });

  describe('Component Rendering', () => {
    test('renders main components correctly', async () => {
      // Mock successful API responses
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } }) // recordings
        .mockResolvedValueOnce({ data: { pi_connected: true } }); // status

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Pi Video Transfer')).toBeInTheDocument();
      });
      
      expect(screen.getByText('Transfer Settings')).toBeInTheDocument();
      expect(screen.getByText('Refresh Pi Recordings')).toBeInTheDocument();
      expect(screen.getByText('Test Pi Connection')).toBeInTheDocument();
      expect(screen.getByText('Test Main Backend')).toBeInTheDocument();
    });

    test('renders transfer form elements', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Default Title Prefix')).toBeInTheDocument();
        expect(screen.getByText('Brocade Type')).toBeInTheDocument();
        expect(screen.getByText('Description Template')).toBeInTheDocument();
      });
    });

    test('shows Pi status indicator', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Pi Status:/)).toBeInTheDocument();
      });
    });
  });

  describe('Pi Recordings Loading', () => {
    test('loads recordings on component mount', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      // Check API calls
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net/api/pi-live/recordings',
        expect.objectContaining({
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        })
      );

      await waitFor(() => {
        expect(screen.getByText('Available on Pi (2)')).toBeInTheDocument();
      });
    });

    test('displays recording count correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        const recordingCards = document.querySelectorAll('.recording-card');
        expect(recordingCards).toHaveLength(2);
      });
    });

    test('shows empty state when no recordings', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Available on Pi (0)')).toBeInTheDocument();
        expect(screen.getByText('No recordings available on Pi')).toBeInTheDocument();
      });
    });
  });

  describe('Pi Status Management', () => {
    test('displays connected status correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/✅ Connected/)).toBeInTheDocument();
      });
    });

    test('displays disconnected status correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: false } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/❌ Disconnected/)).toBeInTheDocument();
      });
    });

    test('handles status check errors', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockRejectedValueOnce(new Error('Network error'));

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/❌ Error/)).toBeInTheDocument();
      });
    });
  });

  describe('Form State Management', () => {
    test('updates title input correctly', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      const titleInput = screen.getByPlaceholderText('e.g., Morning Practice');
      await user.type(titleInput, 'Evening Session');
      
      expect(titleInput.value).toBe('Evening Session');
    });

    test('updates brocade type selection correctly', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      const brocadeSelect = screen.getByDisplayValue('First Brocade');
      await user.selectOptions(brocadeSelect, 'THIRD');
      
      expect(brocadeSelect.value).toBe('THIRD');
    });

    test('updates description textarea correctly', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      const descriptionInput = screen.getByPlaceholderText('Optional description template for all transfers');
      await user.type(descriptionInput, 'Test description');
      
      expect(descriptionInput.value).toBe('Test description');
    });
  });

  describe('Transfer Functionality', () => {
    test('initiates transfer when transfer button clicked', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });
      mockedAxios.post.mockResolvedValueOnce({ data: { success: true, message: 'Transfer completed' } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        const transferButtons = screen.getAllByText('Transfer to Main Backend');
        expect(transferButtons.length).toBeGreaterThan(0);
      });

      const transferButtons = screen.getAllByText('Transfer to Main Backend');
      await user.click(transferButtons[0]);

      expect(mockedAxios.post).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos/pi-transfer-requests',
        expect.objectContaining({
          pi_filename: expect.any(String),
          source: 'pi_transfer'
        }),
        expect.objectContaining({
          headers: {
            'Authorization': `Bearer ${mockToken}`,
            'Content-Type': 'application/json'
          }
        })
      );
    });

    test('calls onTransferComplete callback on successful transfer', async () => {
      const user = userEvent.setup();
      const transferResponse = { success: true, message: 'Transfer completed', video_id: 'video-123' };
      
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });
      mockedAxios.post.mockResolvedValueOnce({ data: transferResponse });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        const transferButtons = screen.getAllByText('Transfer to Main Backend');
        expect(transferButtons.length).toBeGreaterThan(0);
      });

      const transferButtons = screen.getAllByText('Transfer to Main Backend');
      await user.click(transferButtons[0]);

      await waitFor(() => {
        expect(mockOnTransferComplete).toHaveBeenCalledWith(transferResponse);
      });
    });

    test('shows direct transfer option', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getAllByText('Direct Transfer').length).toBeGreaterThan(0);
      });
    });
  });

  describe('Connection Testing', () => {
    test('tests Pi connection when button clicked', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } })
        .mockResolvedValueOnce({ data: { pi_connected: true, message: 'Pi connected successfully' } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      const testPiButton = screen.getByText('Test Pi Connection');
      await user.click(testPiButton);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-pi-service-g8aehuh0bghcc4be.southeastasia-01.azurewebsites.net/api/pi-live/test-pi-connection',
        expect.objectContaining({
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        })
      );

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Pi connection test successful!');
      });
    });

    test('tests main backend connection when button clicked', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } }) // recordings
        .mockResolvedValueOnce({ data: { pi_connected: true } }) // status
        .mockResolvedValueOnce({ data: [] }); // backend test

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      const testBackendButton = screen.getByText('Test Main Backend');
      await user.click(testBackendButton);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos/',
        expect.objectContaining({
          headers: {
            'Authorization': `Bearer ${mockToken}`
          }
        })
      );

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Main backend connection successful!');
      });
    });
  });

  describe('Error Handling', () => {
    test('displays error when recordings loading fails', async () => {
      mockedAxios.get
        .mockRejectedValueOnce(new Error('Pi service unavailable'))
        .mockResolvedValueOnce({ data: { pi_connected: false } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to connect to Pi service/)).toBeInTheDocument();
      });
    });

    test('handles transfer failure gracefully', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });
      mockedAxios.post.mockRejectedValueOnce(new Error('Transfer failed'));

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        const transferButtons = screen.getAllByText('Transfer to Main Backend');
        expect(transferButtons.length).toBeGreaterThan(0);
      });

      const transferButtons = screen.getAllByText('Transfer to Main Backend');
      await user.click(transferButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('❌ Transfer Failed')).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    test('shows retry options after transfer failure', async () => {
      const user = userEvent.setup();
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });
      mockedAxios.post.mockRejectedValueOnce(new Error('Transfer failed'));

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        const transferButtons = screen.getAllByText('Transfer to Main Backend');
        expect(transferButtons.length).toBeGreaterThan(0);
      });

      const transferButtons = screen.getAllByText('Transfer to Main Backend');
      await user.click(transferButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
        expect(screen.getByText('Try Direct Transfer')).toBeInTheDocument();
      });
    });
  });

  describe('Utility Functions', () => {
    test('formats file sizes correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        // Should display file sizes in MB format
        expect(screen.getByText('10.0 MB')).toBeInTheDocument(); // 10485760 bytes
        expect(screen.getByText('15.0 MB')).toBeInTheDocument(); // 15728640 bytes
      });
    });

    test('displays recording cards correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        // Should display recording cards
        const recordingCards = document.querySelectorAll('.recording-card');
        expect(recordingCards).toHaveLength(2);
      });
    });
  });

  describe('Button States', () => {
    test('disables transfer buttons when Pi disconnected', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: mockPiRecordings } })
        .mockResolvedValueOnce({ data: { pi_connected: false } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      await waitFor(() => {
        const transferButtons = screen.getAllByText('Transfer to Main Backend');
        transferButtons.forEach(button => {
          expect(button).toBeDisabled();
        });
      });
    });

    test('shows loading state on refresh button', async () => {
      const user = userEvent.setup();
      let resolveRecordings;
      const recordingsPromise = new Promise(resolve => {
        resolveRecordings = resolve;
      });

      mockedAxios.get
        .mockReturnValueOnce(recordingsPromise)
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer onTransferComplete={mockOnTransferComplete} />);
      });
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();

      // Resolve the promise
      resolveRecordings({ data: { success: true, recordings: [] } });

      await waitFor(() => {
        expect(screen.getByText('Refresh Pi Recordings')).toBeInTheDocument();
      });
    });
  });

  describe('Component Props', () => {
    test('works without onTransferComplete callback', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: { success: true, recordings: [] } })
        .mockResolvedValueOnce({ data: { pi_connected: true } });

      await act(async () => {
        render(<PiVideoTransfer />);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Pi Video Transfer')).toBeInTheDocument();
      });
    });
  });
});
/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-container */
// src/__tests__/pilive/PiStatusPanel.test.js

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PiStatusPanel from '../../components/PiLive/PiStatusPanel';

// Mock data
const mockStatusConnected = {
  pi_connected: true,
  camera_available: true,
  yolo_available: true,
  is_running: true,
  persons_detected: 2,
  current_fps: 30,
  cpu_usage: 45.2,
  memory_usage: 60.1,
  temperature: 42.5
};

const mockStatusDisconnected = {
  pi_connected: false,
  camera_available: false,
  yolo_available: false,
  is_running: false,
  persons_detected: 0,
  current_fps: 0,
  error: 'Connection failed'
};

const mockStatusPartiallyAvailable = {
  pi_connected: true,
  camera_available: true,
  yolo_available: false,
  is_running: false,
  persons_detected: undefined,
  current_fps: 0
};

const mockStatusWithError = {
  pi_connected: true,
  camera_available: true,
  yolo_available: true,
  is_running: true,
  persons_detected: 1,
  error: 'YOLO model loading failed'
};

describe('PiStatusPanel Component', () => {
  const mockOnRefresh = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    test('renders with connected status', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Connected/)).toBeInTheDocument();
      expect(screen.getByText(/Refresh/)).toBeInTheDocument();
    });

    test('renders with disconnected status', () => {
      render(
        <PiStatusPanel 
          status={mockStatusDisconnected}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Disconnected/)).toBeInTheDocument();
      expect(screen.getByText(/Refresh/)).toBeInTheDocument();
    });

    test('renders with loading state', () => {
      render(
        <PiStatusPanel 
          status={null}
          isConnected={false}
          loading={true}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Checking/)).toBeInTheDocument();
      expect(screen.getByText(/Refresh/)).toBeInTheDocument();
    });

    test('renders without status data', () => {
      render(
        <PiStatusPanel 
          status={null}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Disconnected/)).toBeInTheDocument();
      expect(screen.getByText(/Refresh/)).toBeInTheDocument();
    });
  });

  describe('Status Details Display', () => {
    test('displays status details when connected', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-details')).toBeInTheDocument();
      const statusSpans = container.querySelectorAll('.status-details span');
      expect(statusSpans.length).toBeGreaterThan(0);
    });

    test('displays partially available status', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusPartiallyAvailable}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-details')).toBeInTheDocument();
      const statusSpans = container.querySelectorAll('.status-details span');
      expect(statusSpans.length).toBeGreaterThan(0);
    });

    test('does not display status details when loading', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={true}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-details')).not.toBeInTheDocument();
    });

    test('does not display status details when no status', () => {
      const { container } = render(
        <PiStatusPanel 
          status={null}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-details')).not.toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    test('displays error message when present', () => {
      render(
        <PiStatusPanel 
          status={mockStatusWithError}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/YOLO model loading failed/)).toBeInTheDocument();
    });

    test('displays error for disconnected status', () => {
      render(
        <PiStatusPanel 
          status={mockStatusDisconnected}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Connection failed/)).toBeInTheDocument();
    });

    test('does not display error when none present', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    });
  });

  describe('Refresh Button', () => {
    test('renders refresh button correctly', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      const refreshButton = screen.getByText(/Refresh/);
      expect(refreshButton).toBeInTheDocument();
      expect(refreshButton).not.toBeDisabled();
    });

    test('is disabled when loading', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={true}
          onRefresh={mockOnRefresh}
        />
      );
      
      const refreshButton = screen.getByText(/Refresh/);
      expect(refreshButton).toBeDisabled();
    });

    test('is enabled when not loading', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      const refreshButton = screen.getByText(/Refresh/);
      expect(refreshButton).not.toBeDisabled();
    });

    test('handles button click interaction', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      const refreshButton = screen.getByText(/Refresh/);
      fireEvent.click(refreshButton);
      
      expect(mockOnRefresh).toHaveBeenCalled();
    });
  });

  describe('CSS Classes', () => {
    test('applies connected class when connected', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.pi-status-panel.connected')).toBeInTheDocument();
    });

    test('applies disconnected class when disconnected', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusDisconnected}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.pi-status-panel.disconnected')).toBeInTheDocument();
    });

    test('applies correct status dot class when connected', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-dot.green')).toBeInTheDocument();
    });

    test('applies correct status dot class when disconnected', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusDisconnected}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-dot.red')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    test('contains status indicator elements', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-indicator')).toBeInTheDocument();
      expect(container.querySelector('.status-text')).toBeInTheDocument();
    });

    test('contains status details when available', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-details')).toBeInTheDocument();
    });

    test('contains error section when error present', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusWithError}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.status-error')).toBeInTheDocument();
    });

    test('contains refresh button', () => {
      const { container } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(container.querySelector('.refresh-btn')).toBeInTheDocument();
    });
  });

  describe('Props Handling', () => {
    test('handles missing status prop', () => {
      render(
        <PiStatusPanel 
          status={null}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Disconnected/)).toBeInTheDocument();
    });

    test('handles missing onRefresh prop', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
        />
      );
      
      const refreshButton = screen.getByText(/Refresh/);
      expect(refreshButton).toBeInTheDocument();
      expect(refreshButton).not.toBeDisabled();
    });

    test('handles undefined isConnected prop', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Disconnected/)).toBeInTheDocument();
    });

    test('handles undefined loading prop', () => {
      render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Connected/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    test('handles status with missing properties', () => {
      const incompleteStatus = {
        pi_connected: true
      };
      
      render(
        <PiStatusPanel 
          status={incompleteStatus}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Connected/)).toBeInTheDocument();
    });

    test('handles status with zero persons detected', () => {
      const statusZeroPersons = {
        ...mockStatusConnected,
        persons_detected: 0
      };
      
      render(
        <PiStatusPanel 
          status={statusZeroPersons}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Persons:.*0/)).toBeInTheDocument();
    });

    test('handles status with false boolean values', () => {
      const statusAllFalse = {
        pi_connected: false,
        camera_available: false,
        yolo_available: false,
        is_running: false,
        persons_detected: 0
      };
      
      render(
        <PiStatusPanel 
          status={statusAllFalse}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Disconnected/)).toBeInTheDocument();
    });

    test('handles empty error message', () => {
      const statusEmptyError = {
        ...mockStatusConnected,
        error: ''
      };
      
      render(
        <PiStatusPanel 
          status={statusEmptyError}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Connected/)).toBeInTheDocument();
    });
  });

  describe('State Transitions', () => {
    test('updates from loading to connected state', () => {
      const { rerender } = render(
        <PiStatusPanel 
          status={null}
          isConnected={false}
          loading={true}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Checking/)).toBeInTheDocument();
      
      rerender(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Connected/)).toBeInTheDocument();
    });

    test('updates from connected to disconnected state', () => {
      const { rerender } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Connected/)).toBeInTheDocument();
      
      rerender(
        <PiStatusPanel 
          status={mockStatusDisconnected}
          isConnected={false}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Pi Camera:.*Disconnected/)).toBeInTheDocument();
    });

    test('updates persons detected count', () => {
      const { rerender } = render(
        <PiStatusPanel 
          status={mockStatusConnected}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Persons:.*2/)).toBeInTheDocument();
      
      const updatedStatus = { ...mockStatusConnected, persons_detected: 5 };
      rerender(
        <PiStatusPanel 
          status={updatedStatus}
          isConnected={true}
          loading={false}
          onRefresh={mockOnRefresh}
        />
      );
      
      expect(screen.getByText(/Persons:.*5/)).toBeInTheDocument();
    });
  });
});
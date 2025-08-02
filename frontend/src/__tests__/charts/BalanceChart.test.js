/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-wait-for-side-effects */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/charts/BalanceChart.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BalanceChart from '../../components/Charts/BalanceChart';
import { loadMasterData, loadLearnerData } from '../../services/dataLoader';

// Mock the data loader services
jest.mock('../../services/dataLoader', () => ({
  loadMasterData: jest.fn(),
  loadLearnerData: jest.fn(),
}));

// Mock react-plotly.js
jest.mock('react-plotly.js', () => {
  return function MockPlot({ data, layout }) {
    return (
      <div data-testid="plotly-chart">
        <div data-testid="plot-data">{JSON.stringify(data)}</div>
        <div data-testid="plot-layout">{JSON.stringify(layout)}</div>
      </div>
    );
  };
});

// Mock CSS import
jest.mock('../ChartCommon.css', () => ({}));

describe('BalanceChart Component', () => {
  const mockMasterData = {
    overallStability: 0.85,
    comTrajectory: {
      x: [360, 361, 362, 363, 364],
      y: [402, 403, 404, 403, 402]
    },
    balanceMetrics: {
      com_stability_x: 1.23,
      com_stability_y: 2.45
    }
  };

  const mockLearnerData = {
    overallStability: 0.72,
    comTrajectory: {
      x: [360.5, 361.5, 362.5, 363.5, 364.5],
      y: [402.5, 403.5, 404.5, 403.5, 402.5]
    },
    balanceMetrics: {
      com_stability_x: 1.67,
      com_stability_y: 2.89
    },
    keyPoseBalance: [
      {
        poseName: "Initial Position",
        comPosition: { x: 360.5, y: 402.5 }
      },
      {
        poseName: "Peak Position",
        comPosition: { x: 362.5, y: 404.5 }
      },
      {
        poseName: "Final Position",
        comPosition: { x: 364.5, y: 402.5 }
      }
    ]
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading States', () => {
    test('displays loading state initially', () => {
      loadMasterData.mockImplementation(() => new Promise(() => {})); // Never resolves
      loadLearnerData.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<BalanceChart />);
      
      expect(screen.getByText('Loading balance data...')).toBeInTheDocument();
    });

    test('displays error state when data loading fails', async () => {
      loadMasterData.mockRejectedValue(new Error('Network error'));
      loadLearnerData.mockRejectedValue(new Error('Network error'));

      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load balance data')).toBeInTheDocument();
      });
    });

    test('displays no data message when data is null', async () => {
      loadMasterData.mockResolvedValue(null);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('No balance data available')).toBeInTheDocument();
      });
    });
  });

  describe('Successful Data Loading and Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders chart with data successfully', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Balance and Stability Analysis')).toBeInTheDocument();
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });

    test('calculates and displays stability scores correctly', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        // Master stability: 0.85 * 100 = 85
        expect(screen.getByText('85')).toBeInTheDocument();
        // Learner stability: 0.72 * 100 = 72
        expect(screen.getByText('72')).toBeInTheDocument();
      });
    });

    test('displays stability metrics with correct decimal places', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('X: 1.23 Y: 2.45')).toBeInTheDocument();
        expect(screen.getByText('X: 1.67 Y: 2.89')).toBeInTheDocument();
      });
    });

    test('renders key poses section', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Key Poses (for learner)')).toBeInTheDocument();
        expect(screen.getByText('Starting')).toBeInTheDocument();
        expect(screen.getByText('Peak')).toBeInTheDocument();
        expect(screen.getByText('Final')).toBeInTheDocument();
      });
    });
  });

  describe('Display Mode Controls', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders display mode buttons', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Both Trajectories')).toBeInTheDocument();
        expect(screen.getByText('Master Only')).toBeInTheDocument();
        expect(screen.getByText('Learner Only')).toBeInTheDocument();
      });
    });

    test('both trajectories button is active by default', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const bothButton = screen.getByText('Both Trajectories');
        expect(bothButton).toHaveClass('active');
      });
    });

    test('can switch to master only mode', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        expect(masterOnlyButton).toHaveClass('active');
      });
    });

    test('can switch to learner only mode', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const learnerOnlyButton = screen.getByText('Learner Only');
        fireEvent.click(learnerOnlyButton);
        expect(learnerOnlyButton).toHaveClass('active');
      });
    });
  });

  describe('Body Position Toggle', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders body position toggle checkbox', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const checkbox = screen.getByLabelText('Show Body Position Context');
        expect(checkbox).toBeInTheDocument();
        expect(checkbox).toBeChecked(); // Default is true
      });
    });

    test('can toggle body position checkbox', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const checkbox = screen.getByLabelText('Show Body Position Context');
        fireEvent.click(checkbox);
        expect(checkbox).not.toBeChecked();
        
        fireEvent.click(checkbox);
        expect(checkbox).toBeChecked();
      });
    });
  });

  describe('Pose Selection Functionality', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('can select a pose by clicking on it', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const firstPose = screen.getByText('1');
        fireEvent.click(firstPose);
        
        // Check if the pose indicator has selected class
        expect(firstPose.closest('.pose-indicator').querySelector('.pose-circle')).toHaveClass('selected');
      });
    });

    test('can deselect a pose by clicking it again', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const firstPose = screen.getByText('1');
        
        // Select the pose
        fireEvent.click(firstPose);
        expect(firstPose.closest('.pose-indicator').querySelector('.pose-circle')).toHaveClass('selected');
        
        // Deselect the pose
        fireEvent.click(firstPose);
        expect(firstPose.closest('.pose-indicator').querySelector('.pose-circle')).not.toHaveClass('selected');
      });
    });

    test('selecting a different pose deselects the previous one', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const firstPose = screen.getByText('1');
        const secondPose = screen.getByText('2');
        
        // Select first pose
        fireEvent.click(firstPose);
        expect(firstPose.closest('.pose-indicator').querySelector('.pose-circle')).toHaveClass('selected');
        
        // Select second pose
        fireEvent.click(secondPose);
        expect(firstPose.closest('.pose-indicator').querySelector('.pose-circle')).not.toHaveClass('selected');
        expect(secondPose.closest('.pose-indicator').querySelector('.pose-circle')).toHaveClass('selected');
      });
    });
  });

  describe('Pose Name Conversion', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('converts pose names to short versions correctly', async () => {
      const testData = {
        ...mockLearnerData,
        keyPoseBalance: [
          { poseName: "Initial Position", comPosition: { x: 360, y: 402 } },
          { poseName: "Transition Phase", comPosition: { x: 361, y: 403 } },
          { poseName: "Peak Position", comPosition: { x: 362, y: 404 } },
          { poseName: "Holding Phase", comPosition: { x: 363, y: 403 } },
          { poseName: "Return Phase", comPosition: { x: 364, y: 402 } },
          { poseName: "Final Position", comPosition: { x: 365, y: 401 } },
          { poseName: "Stabilization Phase", comPosition: { x: 366, y: 402 } },
          { poseName: "Ready Position", comPosition: { x: 367, y: 403 } }
        ]
      };
      
      loadLearnerData.mockResolvedValue(testData);
      
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Starting')).toBeInTheDocument();
        expect(screen.getByText('Transition')).toBeInTheDocument();
        expect(screen.getByText('Peak')).toBeInTheDocument();
        expect(screen.getByText('Holding')).toBeInTheDocument();
        expect(screen.getByText('Return')).toBeInTheDocument();
        expect(screen.getByText('Final')).toBeInTheDocument();
        expect(screen.getByText('Stabilization')).toBeInTheDocument();
        expect(screen.getByText('Ending')).toBeInTheDocument();
      });
    });

    test('keeps original name for unknown poses', async () => {
      const testData = {
        ...mockLearnerData,
        keyPoseBalance: [
          { poseName: "Custom Pose Name", comPosition: { x: 360, y: 402 } }
        ]
      };
      
      loadLearnerData.mockResolvedValue(testData);
      
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Custom Pose Name')).toBeInTheDocument();
      });
    });
  });

  describe('Legend Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders legend with all items', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master')).toBeInTheDocument();
        expect(screen.getByText('Learner')).toBeInTheDocument();
        expect(screen.getByText('Key Poses')).toBeInTheDocument();
        expect(screen.getByText('Time Progression')).toBeInTheDocument();
      });
    });
  });

  describe('Component Props', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('accepts comparisonMode prop', async () => {
      render(<BalanceChart comparisonMode="masterOnly" />);
      
      await waitFor(() => {
        expect(screen.getByText('Balance and Stability Analysis')).toBeInTheDocument();
      });
    });

    test('accepts compact prop', async () => {
      render(<BalanceChart compact={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Balance and Stability Analysis')).toBeInTheDocument();
      });
    });
  });

  describe('Chart Data Structure', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('chart receives correct data structure', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const plotData = screen.getByTestId('plot-data');
        const dataContent = plotData.textContent;
        
        // Check that chart data contains master trajectory
        expect(dataContent).toContain('Master');
        expect(dataContent).toContain('Learner');
        expect(dataContent).toContain('#3498db'); // Master color
        expect(dataContent).toContain('#e74c3c'); // Learner color
      });
    });

    test('chart layout has correct configuration', async () => {
      render(<BalanceChart />);
      
      await waitFor(() => {
        const plotLayout = screen.getByTestId('plot-layout');
        const layoutContent = plotLayout.textContent;
        
        expect(layoutContent).toContain('"height":320');
        expect(layoutContent).toContain('"width":400');
        expect(layoutContent).toContain('"showlegend":false');
      });
    });
  });

  describe('Error Handling', () => {
    test('handles partial data loading failure gracefully', async () => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockRejectedValue(new Error('Learner data failed'));

      render(<BalanceChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load balance data')).toBeInTheDocument();
      });
    });

    test('handles missing trajectory data', async () => {
      const incompleteData = {
        ...mockMasterData,
        comTrajectory: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      // Should not crash when rendering
      expect(() => render(<BalanceChart />)).not.toThrow();
    });

    test('handles missing key pose data', async () => {
      const incompleteData = {
        ...mockLearnerData,
        keyPoseBalance: undefined
      };
      
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(incompleteData);

      // Should not crash when rendering
      expect(() => render(<BalanceChart />)).not.toThrow();
    });
  });
});
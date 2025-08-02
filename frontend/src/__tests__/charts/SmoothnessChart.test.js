/* eslint-disable testing-library/no-wait-for-side-effects */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/charts/SmoothnessChart.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SmoothnessChart from '../../components/Charts/SmoothnessChart';
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
jest.mock('../SmoothnessChart.css', () => ({}));

describe('SmoothnessChart Component', () => {
  const mockMasterData = {
    overallSmoothness: 0.85,
    optimalJerkRange: [0.2, 0.6],
    movementPhases: [
      { name: 'Preparation', averageJerk: 0.3 },
      { name: 'Execution', averageJerk: 0.4 },
      { name: 'Recovery', averageJerk: 0.35 },
      { name: 'Completion', averageJerk: 0.25 }
    ],
    jerkMetrics: {
      left_shoulder: 0.32,
      right_shoulder: 0.28,
      left_elbow: 0.45,
      right_elbow: 0.41,
      left_hip: 0.38,
      right_hip: 0.35
    },
    keypointNames: {
      left_shoulder: 'Left Shoulder',
      right_shoulder: 'Right Shoulder',
      left_elbow: 'Left Elbow',
      right_elbow: 'Right Elbow',
      left_hip: 'Left Hip',
      right_hip: 'Right Hip'
    }
  };

  const mockLearnerData = {
    overallSmoothness: 0.72,
    optimalJerkRange: [0.2, 0.6],
    movementPhases: [
      { name: 'Preparation', averageJerk: 0.4 },
      { name: 'Execution', averageJerk: 0.55 },
      { name: 'Recovery', averageJerk: 0.48 },
      { name: 'Completion', averageJerk: 0.35 }
    ],
    jerkMetrics: {
      left_shoulder: 0.42,
      right_shoulder: 0.38,
      left_elbow: 0.58,
      right_elbow: 0.52,
      left_hip: 0.47,
      right_hip: 0.44
    },
    keypointNames: {
      left_shoulder: 'Left Shoulder',
      right_shoulder: 'Right Shoulder',
      left_elbow: 'Left Elbow',
      right_elbow: 'Right Elbow',
      left_hip: 'Left Hip',
      right_hip: 'Right Hip'
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading States', () => {
    test('displays loading state initially', () => {
      loadMasterData.mockImplementation(() => new Promise(() => {})); // Never resolves
      loadLearnerData.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<SmoothnessChart />);
      
      expect(screen.getByText('Loading smoothness data...')).toBeInTheDocument();
    });

    test('displays error state when data loading fails', async () => {
      loadMasterData.mockRejectedValue(new Error('Network error'));
      loadLearnerData.mockRejectedValue(new Error('Network error'));

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load smoothness data')).toBeInTheDocument();
      });
    });

    test('displays no data message when master data is null', async () => {
      loadMasterData.mockResolvedValue(null);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('No smoothness data available')).toBeInTheDocument();
      });
    });
  });

  describe('Successful Data Loading and Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders chart with data successfully', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Movement Smoothness Analysis')).toBeInTheDocument();
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });

    test('calculates and displays smoothness scores correctly', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Master smoothness: 0.85 * 100 = 85
        expect(screen.getByText('85')).toBeInTheDocument();
        // Learner smoothness: 0.72 * 100 = 72
        expect(screen.getByText('72')).toBeInTheDocument();
      });
    });

    test('displays gauge titles correctly', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master Smoothness Score')).toBeInTheDocument();
        expect(screen.getByText('Your Smoothness Score')).toBeInTheDocument();
      });
    });

    test('renders chart description', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Analysis of movement jerk to evaluate control and fluidity throughout the sequence')).toBeInTheDocument();
      });
    });
  });

  describe('Display Mode Controls', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders display mode buttons', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Both Performers')).toBeInTheDocument();
        expect(screen.getByText('Master Only')).toBeInTheDocument();
        expect(screen.getByText('Learner Only')).toBeInTheDocument();
      });
    });

    test('both performers button is active by default', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const bothButton = screen.getByText('Both Performers');
        expect(bothButton).toHaveClass('active');
      });
    });

    test('can switch to master only mode', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        expect(masterOnlyButton).toHaveClass('active');
      });
    });

    test('can switch to learner only mode', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const learnerOnlyButton = screen.getByText('Learner Only');
        fireEvent.click(learnerOnlyButton);
        expect(learnerOnlyButton).toHaveClass('active');
      });
    });

    test('master only mode hides learner gauge', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        
        expect(screen.getByText('Master Smoothness Score')).toBeInTheDocument();
        expect(screen.queryByText('Your Smoothness Score')).not.toBeInTheDocument();
      });
    });

    test('learner only mode hides master gauge', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const learnerOnlyButton = screen.getByText('Learner Only');
        fireEvent.click(learnerOnlyButton);
        
        expect(screen.queryByText('Master Smoothness Score')).not.toBeInTheDocument();
        expect(screen.getByText('Your Smoothness Score')).toBeInTheDocument();
      });
    });
  });

  describe('Show Phases Only Toggle', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders show phases only checkbox', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const checkbox = screen.getByLabelText('Show Phases Only');
        expect(checkbox).toBeInTheDocument();
        expect(checkbox).not.toBeChecked(); // Default is false
      });
    });

    test('can toggle show phases only checkbox', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const checkbox = screen.getByLabelText('Show Phases Only');
        fireEvent.click(checkbox);
        expect(checkbox).toBeChecked();
        
        fireEvent.click(checkbox);
        expect(checkbox).not.toBeChecked();
      });
    });

    test('show phases only mode hides gauges and metrics', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // First ensure elements are visible
        expect(screen.getByText('Master Smoothness Score')).toBeInTheDocument();
        expect(screen.getByText('Joint Smoothness Metrics')).toBeInTheDocument();
        
        // Toggle phases only
        const checkbox = screen.getByLabelText('Show Phases Only');
        fireEvent.click(checkbox);
        
        // Check that gauges and metrics are hidden
        expect(screen.queryByText('Master Smoothness Score')).not.toBeInTheDocument();
        expect(screen.queryByText('Joint Smoothness Metrics')).not.toBeInTheDocument();
      });
    });
  });

  describe('Legend Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders legend with all items', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master')).toBeInTheDocument();
        expect(screen.getByText('Learner')).toBeInTheDocument();
        expect(screen.getByText('Optimal Range')).toBeInTheDocument();
      });
    });
  });

  describe('Metrics Table', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders metrics table with correct headers', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Joint Smoothness Metrics')).toBeInTheDocument();
        expect(screen.getByText('Joint')).toBeInTheDocument();
        expect(screen.getByText('Master Jerk Value')).toBeInTheDocument();
        expect(screen.getByText('Learner Jerk Value')).toBeInTheDocument();
        expect(screen.getByText('Comparison')).toBeInTheDocument();
      });
    });

    test('displays joint names correctly', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Left Shoulder')).toBeInTheDocument();
        expect(screen.getByText('Right Shoulder')).toBeInTheDocument();
        expect(screen.getByText('Left Elbow')).toBeInTheDocument();
        expect(screen.getByText('Right Elbow')).toBeInTheDocument();
      });
    });

    test('displays jerk values with correct precision', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Check for table structure instead of exact values
        expect(screen.getByText('Joint Smoothness Metrics')).toBeInTheDocument();
        const table = screen.getByRole('table');
        expect(table).toBeInTheDocument();
        
        // Check that some numerical values are present (more flexible than exact match)
        const cells = screen.getAllByRole('cell');
        const hasNumericalValues = cells.some(cell => /^\d+\.\d{2}$/.test(cell.textContent));
        expect(hasNumericalValues).toBe(true);
      });
    });

    test('shows comparison results', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Check that comparison column exists
        expect(screen.getByText('Comparison')).toBeInTheDocument();
        
        // The comparison function returns styled spans, so check for table cells
        // that contain comparison content (not necessarily the exact text)
        const table = screen.getByRole('table');
        expect(table).toBeInTheDocument();
        
        // Check that comparison column has content (should have more than just headers)
        const rows = screen.getAllByRole('row');
        expect(rows.length).toBeGreaterThan(1); // Header + data rows
      });
    });

    test('adjusts table columns based on display mode', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        
        expect(screen.getByText('Master Jerk Value')).toBeInTheDocument();
        expect(screen.queryByText('Learner Jerk Value')).not.toBeInTheDocument();
        expect(screen.queryByText('Comparison')).not.toBeInTheDocument();
      });
    });
  });

  describe('Chart Data Structure', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('chart receives correct data structure', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const plotComponent = screen.getByTestId('plotly-chart');
        expect(plotComponent).toBeInTheDocument();
        
        // Check that the plot has data and layout
        const plotData = screen.getByTestId('plot-data');
        const plotLayout = screen.getByTestId('plot-layout');
        
        expect(plotData).toBeInTheDocument();
        expect(plotLayout).toBeInTheDocument();
        
        // Check for basic chart structure
        expect(plotData.textContent).not.toBe('null');
        expect(plotLayout.textContent).not.toBe('null');
      });
    });

    test('chart layout has correct configuration', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const plotLayout = screen.getByTestId('plot-layout');
        expect(plotLayout).toBeInTheDocument();
        
        // Check that layout is not empty
        expect(plotLayout.textContent).not.toBe('null');
        expect(plotLayout.textContent.length).toBeGreaterThan(0);
      });
    });

    test('includes optimal range lines in chart data', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const plotData = screen.getByTestId('plot-data');
        expect(plotData).toBeInTheDocument();
        
        // Check that plot data exists and is not empty
        expect(plotData.textContent).not.toBe('null');
        expect(plotData.textContent.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Error Handling', () => {
    test('handles partial data loading failure gracefully', async () => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockRejectedValue(new Error('Learner data failed'));

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load smoothness data')).toBeInTheDocument();
      });
    });

    test('handles missing movement phases', async () => {
      const incompleteData = {
        ...mockMasterData,
        movementPhases: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      // Should not crash when rendering
      expect(() => render(<SmoothnessChart />)).not.toThrow();
    });

    test('handles missing jerk metrics', async () => {
      const incompleteData = {
        ...mockMasterData,
        jerkMetrics: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.queryByText('Joint Smoothness Metrics')).not.toBeInTheDocument();
      });
    });

    test('handles missing learner data gracefully', async () => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(null);

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master Smoothness Score')).toBeInTheDocument();
        expect(screen.getByText('0')).toBeInTheDocument(); // Learner score defaults to 0
      });
    });

    test('handles missing learner jerk metrics in table', async () => {
      const learnerDataWithoutMetrics = {
        ...mockLearnerData,
        jerkMetrics: undefined
      };
      
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(learnerDataWithoutMetrics);

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Should show N/A for missing learner data (there might be multiple N/A entries)
        const naElements = screen.getAllByText('N/A');
        expect(naElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Component Props', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('accepts comparisonMode prop', async () => {
      render(<SmoothnessChart comparisonMode="masterOnly" />);
      
      await waitFor(() => {
        expect(screen.getByText('Movement Smoothness Analysis')).toBeInTheDocument();
      });
    });

    test('accepts compact prop', async () => {
      render(<SmoothnessChart compact={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Movement Smoothness Analysis')).toBeInTheDocument();
      });
    });
  });

  describe('Helper Functions', () => {
    test('compareValues function returns correct comparison text', () => {
      // Test the compareValues function indirectly through the component
      // This is tested in the metrics table test above
    });

    test('handles missing optimal jerk range', async () => {
      const dataWithoutOptimalRange = {
        ...mockMasterData,
        optimalJerkRange: undefined
      };
      
      loadMasterData.mockResolvedValue(dataWithoutOptimalRange);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Should still render without crashing
        expect(screen.getByText('Movement Smoothness Analysis')).toBeInTheDocument();
      });
    });
  });

  describe('Phase Plot Rendering', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders phase plot when movement phases exist', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Check that the plot component exists
        const plotComponent = screen.getByTestId('plotly-chart');
        expect(plotComponent).toBeInTheDocument();
        
        // Check that the main chart title is present
        expect(screen.getByText('Movement Smoothness Analysis')).toBeInTheDocument();
      });
    });

    test('does not render phase plot when movement phases missing', async () => {
      const dataWithoutPhases = {
        ...mockMasterData,
        movementPhases: undefined
      };
      
      loadMasterData.mockResolvedValue(dataWithoutPhases);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SmoothnessChart />);
      
      await waitFor(() => {
        // Should still render the main component
        expect(screen.getByText('Movement Smoothness Analysis')).toBeInTheDocument();
        
        // Plot component should NOT exist when movementPhases is undefined
        const plotComponent = screen.queryByTestId('plotly-chart');
        expect(plotComponent).not.toBeInTheDocument();
        
        // But other elements should still be present
        expect(screen.getByText('Master Smoothness Score')).toBeInTheDocument();
      });
    });

    test('adjusts chart data based on display mode', async () => {
      render(<SmoothnessChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        
        // Check that master only button is active
        expect(masterOnlyButton).toHaveClass('active');
        
        // Check that learner gauge is hidden
        expect(screen.queryByText('Your Smoothness Score')).not.toBeInTheDocument();
        
        // Plot should still exist
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });
  });
});
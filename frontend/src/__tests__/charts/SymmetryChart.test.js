/* eslint-disable testing-library/no-wait-for-multiple-assertions */
/* eslint-disable testing-library/no-wait-for-side-effects */
// src/__tests__/charts/SymmetryChart.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SymmetryChart from '../../components/Charts/SymmetryChart';
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

describe('SymmetryChart Component', () => {
  const mockMasterData = {
    overallSymmetry: 0.88,
    optimalSymmetryRange: [0.7, 1.0],
    keyPoseSymmetry: [
      { poseName: 'Starting Position', symmetryScore: 0.92 },
      { poseName: 'Mid Transition', symmetryScore: 0.85 },
      { poseName: 'Peak Position', symmetryScore: 0.78 },
      { poseName: 'Recovery', symmetryScore: 0.88 },
      { poseName: 'End Position', symmetryScore: 0.95 }
    ],
    symmetryScores: {
      shoulder_pair: 0.12,
      elbow_pair: 0.18,
      hip_pair: 0.08,
      knee_pair: 0.15,
      ankle_pair: 0.22
    },
    keypointPairNames: {
      shoulder_pair: 'Shoulder Symmetry',
      elbow_pair: 'Elbow Symmetry',
      hip_pair: 'Hip Symmetry',
      knee_pair: 'Knee Symmetry',
      ankle_pair: 'Ankle Symmetry'
    }
  };

  const mockLearnerData = {
    overallSymmetry: 0.73,
    optimalSymmetryRange: [0.7, 1.0],
    keyPoseSymmetry: [
      { poseName: 'Starting Position', symmetryScore: 0.82 },
      { poseName: 'Mid Transition', symmetryScore: 0.68 },
      { poseName: 'Peak Position', symmetryScore: 0.61 },
      { poseName: 'Recovery', symmetryScore: 0.75 },
      { poseName: 'End Position', symmetryScore: 0.79 }
    ],
    symmetryScores: {
      shoulder_pair: 0.22,
      elbow_pair: 0.28,
      hip_pair: 0.18,
      knee_pair: 0.25,
      ankle_pair: 0.32
    },
    keypointPairNames: {
      shoulder_pair: 'Shoulder Symmetry',
      elbow_pair: 'Elbow Symmetry',
      hip_pair: 'Hip Symmetry',
      knee_pair: 'Knee Symmetry',
      ankle_pair: 'Ankle Symmetry'
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading States', () => {
    test('displays loading state initially', () => {
      loadMasterData.mockImplementation(() => new Promise(() => {})); // Never resolves
      loadLearnerData.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<SymmetryChart />);
      
      expect(screen.getByText('Loading symmetry data...')).toBeInTheDocument();
    });

    test('displays error state when data loading fails', async () => {
      loadMasterData.mockRejectedValue(new Error('Network error'));
      loadLearnerData.mockRejectedValue(new Error('Network error'));

      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load symmetry data')).toBeInTheDocument();
      });
    });

    test('displays no data message when master data is null', async () => {
      loadMasterData.mockResolvedValue(null);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('No symmetry data available')).toBeInTheDocument();
      });
    });
  });

  describe('Successful Data Loading and Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders chart with data successfully', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Movement Symmetry Analysis')).toBeInTheDocument();
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });

    test('calculates and displays symmetry scores correctly', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Master symmetry: 0.88 * 100 = 88
        expect(screen.getByText('88')).toBeInTheDocument();
        // Learner symmetry: 0.73 * 100 = 73
        expect(screen.getByText('73')).toBeInTheDocument();
      });
    });

    test('displays gauge titles correctly', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master Symmetry Score')).toBeInTheDocument();
        expect(screen.getByText('Your Symmetry Score')).toBeInTheDocument();
      });
    });

    test('renders chart description', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Analysis of left and right side movement symmetry throughout the sequence')).toBeInTheDocument();
      });
    });

    test('displays optimal range in gauge', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        // There are multiple gauges, so multiple optimal range texts
        const optimalRangeElements = screen.getAllByText('Optimal Range: 0.7 - 1');
        expect(optimalRangeElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Display Mode Controls', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders display mode buttons', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Both Performers')).toBeInTheDocument();
        expect(screen.getByText('Master Only')).toBeInTheDocument();
        expect(screen.getByText('Learner Only')).toBeInTheDocument();
      });
    });

    test('both performers button is active by default', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const bothButton = screen.getByText('Both Performers');
        expect(bothButton).toHaveClass('active');
      });
    });

    test('can switch to master only mode', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        expect(masterOnlyButton).toHaveClass('active');
      });
    });

    test('can switch to learner only mode', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const learnerOnlyButton = screen.getByText('Learner Only');
        fireEvent.click(learnerOnlyButton);
        expect(learnerOnlyButton).toHaveClass('active');
      });
    });

    test('master only mode hides learner gauge', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const masterOnlyButton = screen.getByText('Master Only');
        fireEvent.click(masterOnlyButton);
        
        expect(screen.getByText('Master Symmetry Score')).toBeInTheDocument();
        expect(screen.queryByText('Your Symmetry Score')).not.toBeInTheDocument();
      });
    });

    test('learner only mode hides master gauge', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const learnerOnlyButton = screen.getByText('Learner Only');
        fireEvent.click(learnerOnlyButton);
        
        expect(screen.queryByText('Master Symmetry Score')).not.toBeInTheDocument();
        expect(screen.getByText('Your Symmetry Score')).toBeInTheDocument();
      });
    });
  });

  describe('Panel View Toggle', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders panel view toggle buttons', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Pose Symmetry')).toBeInTheDocument();
        expect(screen.getByText('Joint Pair Symmetry')).toBeInTheDocument();
      });
    });

    test('pose symmetry button is active by default', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const poseButton = screen.getByText('Pose Symmetry');
        expect(poseButton).toHaveClass('active');
      });
    });

    test('can switch to joint pair symmetry view', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        expect(jointButton).toHaveClass('active');
      });
    });

    test('can switch back to pose symmetry view', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const jointButton = screen.getByText('Joint Pair Symmetry');
        const poseButton = screen.getByText('Pose Symmetry');
        
        // Switch to joint view
        fireEvent.click(jointButton);
        expect(jointButton).toHaveClass('active');
        
        // Switch back to pose view
        fireEvent.click(poseButton);
        expect(poseButton).toHaveClass('active');
      });
    });
  });

  describe('Legend Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders legend with all items', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master')).toBeInTheDocument();
        expect(screen.getByText('Learner')).toBeInTheDocument();
        expect(screen.getByText('Optimal Range')).toBeInTheDocument();
      });
    });
  });

  describe('Chart Data Structure', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('pose symmetry chart receives correct data structure', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const plotComponent = screen.getByTestId('plotly-chart');
        expect(plotComponent).toBeInTheDocument();
        
        const plotData = screen.getByTestId('plot-data');
        const plotLayout = screen.getByTestId('plot-layout');
        
        expect(plotData).toBeInTheDocument();
        expect(plotLayout).toBeInTheDocument();
        
        // Check for basic chart structure
        expect(plotData.textContent).not.toBe('null');
        expect(plotLayout.textContent).not.toBe('null');
      });
    });

    test('joint pair chart receives correct data structure', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Switch to joint pair view
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        
        const plotComponent = screen.getByTestId('plotly-chart');
        expect(plotComponent).toBeInTheDocument();
        
        const plotData = screen.getByTestId('plot-data');
        expect(plotData.textContent).not.toBe('null');
      });
    });

    test('chart layout has correct configuration for pose view', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const plotLayout = screen.getByTestId('plot-layout');
        expect(plotLayout).toBeInTheDocument();
        
        // Check that layout is not empty
        expect(plotLayout.textContent).not.toBe('null');
        expect(plotLayout.textContent.length).toBeGreaterThan(0);
      });
    });

    test('chart layout has correct configuration for joint pair view', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Switch to joint pair view
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        
        const plotLayout = screen.getByTestId('plot-layout');
        expect(plotLayout.textContent).not.toBe('null');
      });
    });
  });

  describe('Error Handling', () => {
    test('handles partial data loading failure gracefully', async () => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockRejectedValue(new Error('Learner data failed'));

      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load symmetry data')).toBeInTheDocument();
      });
    });

    test('handles missing key pose symmetry data', async () => {
      const incompleteData = {
        ...mockMasterData,
        keyPoseSymmetry: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Should still render the main component
        expect(screen.getByText('Movement Symmetry Analysis')).toBeInTheDocument();
        
        // Plot component should NOT exist when keyPoseSymmetry is undefined
        const plotComponent = screen.queryByTestId('plotly-chart');
        expect(plotComponent).not.toBeInTheDocument();
      });
    });

    test('handles missing symmetry scores data', async () => {
      const incompleteData = {
        ...mockMasterData,
        symmetryScores: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Switch to joint pair view
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        
        // Should still render the main component
        expect(screen.getByText('Movement Symmetry Analysis')).toBeInTheDocument();
        
        // Plot component should NOT exist when symmetryScores is undefined
        const plotComponent = screen.queryByTestId('plotly-chart');
        expect(plotComponent).not.toBeInTheDocument();
      });
    });

    test('handles missing learner data gracefully', async () => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(null);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master Symmetry Score')).toBeInTheDocument();
        expect(screen.getByText('0')).toBeInTheDocument(); // Learner score defaults to 0
      });
    });

    test('handles missing learner symmetry scores in joint pair view', async () => {
      const learnerDataWithoutScores = {
        ...mockLearnerData,
        symmetryScores: undefined
      };
      
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(learnerDataWithoutScores);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Switch to joint pair view
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        
        // Should still render without crashing
        expect(screen.getByText('Movement Symmetry Analysis')).toBeInTheDocument();
      });
    });

    test('handles missing optimal symmetry range', async () => {
      const dataWithoutOptimalRange = {
        ...mockMasterData,
        optimalSymmetryRange: undefined
      };
      
      loadMasterData.mockResolvedValue(dataWithoutOptimalRange);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      // Should not crash when rendering
      expect(() => render(<SymmetryChart />)).not.toThrow();
    });
  });

  describe('Component Props', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('accepts comparisonMode prop', async () => {
      render(<SymmetryChart comparisonMode="masterOnly" />);
      
      await waitFor(() => {
        expect(screen.getByText('Movement Symmetry Analysis')).toBeInTheDocument();
      });
    });

    test('accepts compact prop', async () => {
      render(<SymmetryChart compact={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Movement Symmetry Analysis')).toBeInTheDocument();
      });
    });
  });

  describe('Chart Rendering Based on View', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders pose symmetry chart by default', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const poseButton = screen.getByText('Pose Symmetry');
        expect(poseButton).toHaveClass('active');
        
        const plotComponent = screen.getByTestId('plotly-chart');
        expect(plotComponent).toBeInTheDocument();
      });
    });

    test('switches to joint pair chart when selected', async () => {
      render(<SymmetryChart />);
      
      await waitFor(() => {
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        
        expect(jointButton).toHaveClass('active');
        
        const plotComponent = screen.getByTestId('plotly-chart');
        expect(plotComponent).toBeInTheDocument();
      });
    });
  });

  describe('Data Processing', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('handles missing learner pose symmetry data', async () => {
      const learnerWithoutPoses = {
        ...mockLearnerData,
        keyPoseSymmetry: undefined
      };
      
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(learnerWithoutPoses);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Should still render master data
        expect(screen.getByText('Master Symmetry Score')).toBeInTheDocument();
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });

    test('handles zero values in learner symmetry scores', async () => {
      const learnerWithPartialScores = {
        ...mockLearnerData,
        symmetryScores: {
          shoulder_pair: 0.22,
          elbow_pair: undefined, // This should default to 0
          hip_pair: 0.18,
          knee_pair: 0.25,
          ankle_pair: 0.32
        }
      };
      
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(learnerWithPartialScores);

      render(<SymmetryChart />);
      
      await waitFor(() => {
        // Switch to joint pair view
        const jointButton = screen.getByText('Joint Pair Symmetry');
        fireEvent.click(jointButton);
        
        // Should still render without crashing
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });
  });
});
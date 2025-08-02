/* eslint-disable testing-library/no-wait-for-side-effects */
/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/charts/BalanceChart.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import JointAngleChart from '../../components/Charts/JointAngleChart';
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
jest.mock('../JointAngleChart.css', () => ({}));

describe('JointAngleChart Component', () => {
  const mockMasterData = {
    frames: [0, 100, 200, 300, 400],
    keyPoseFrames: [0, 100, 200, 300, 400],
    keyPoseNames: ['Initial', 'Mid1', 'Peak', 'Mid2', 'Final'],
    angles: {
      left_elbow: [90, 110, 130, 120, 95],
      right_elbow: [95, 115, 135, 125, 100],
      left_shoulder: [45, 60, 75, 65, 50],
      right_shoulder: [50, 65, 80, 70, 55],
      left_hip: [30, 45, 60, 50, 35],
      right_hip: [35, 50, 65, 55, 40],
      spine_top: [0, 10, 20, 15, 5],
      spine_bottom: [5, 15, 25, 20, 10]
    },
    rangeOfMotion: {
      left_elbow: { min: 85, max: 140, optimal: 115 },
      right_elbow: { min: 90, max: 145, optimal: 120 },
      left_shoulder: { min: 40, max: 85, optimal: 62.5 },
      right_shoulder: { min: 45, max: 90, optimal: 67.5 },
      left_hip: { min: 25, max: 70, optimal: 47.5 },
      right_hip: { min: 30, max: 75, optimal: 52.5 },
      spine_top: { min: -5, max: 25, optimal: 10 },
      spine_bottom: { min: 0, max: 30, optimal: 15 }
    }
  };

  const mockLearnerData = {
    frames: [0, 100, 200, 300, 400],
    keyPoseFrames: [0, 100, 200, 300, 400],
    keyPoseNames: ['Initial', 'Mid1', 'Peak', 'Mid2', 'Final'],
    angles: {
      left_elbow: [85, 105, 125, 115, 90],
      right_elbow: [90, 110, 130, 120, 95],
      left_shoulder: [40, 55, 70, 60, 45],
      right_shoulder: [45, 60, 75, 65, 50],
      left_hip: [25, 40, 55, 45, 30],
      right_hip: [30, 45, 60, 50, 35],
      spine_top: [5, 15, 25, 20, 10],
      spine_bottom: [10, 20, 30, 25, 15]
    },
    rangeOfMotion: {
      left_elbow: { min: 80, max: 135, optimal: 110 },
      right_elbow: { min: 85, max: 140, optimal: 115 },
      left_shoulder: { min: 35, max: 80, optimal: 57.5 },
      right_shoulder: { min: 40, max: 85, optimal: 62.5 },
      left_hip: { min: 20, max: 65, optimal: 42.5 },
      right_hip: { min: 25, max: 70, optimal: 47.5 },
      spine_top: { min: 0, max: 30, optimal: 15 },
      spine_bottom: { min: 5, max: 35, optimal: 20 }
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading States', () => {
    test('displays loading state initially', () => {
      loadMasterData.mockImplementation(() => new Promise(() => {})); // Never resolves
      loadLearnerData.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<JointAngleChart />);
      
      expect(screen.getByText('Loading joint angle data...')).toBeInTheDocument();
    });

    test('displays error state when data loading fails', async () => {
      loadMasterData.mockRejectedValue(new Error('Network error'));
      loadLearnerData.mockRejectedValue(new Error('Network error'));

      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load joint angle data. Please try again later.')).toBeInTheDocument();
      });
    });

    test('displays no data message when data is null', async () => {
      loadMasterData.mockResolvedValue(null);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('No joint angle data available')).toBeInTheDocument();
      });
    });
  });

  describe('Successful Data Loading and Display', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders chart with data successfully', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Joint Angle Analysis')).toBeInTheDocument();
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });

    test('renders joint selector with available joints', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Select Joints to Display:')).toBeInTheDocument();
        expect(screen.getByText('Elbow')).toBeInTheDocument();
        expect(screen.getByText('Shoulder')).toBeInTheDocument();
        expect(screen.getByText('Hip')).toBeInTheDocument();
        expect(screen.getByText('Spine Top')).toBeInTheDocument();
        expect(screen.getByText('Spine Bottom')).toBeInTheDocument();
      });
    });

    test('default selected joints are correct', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const elbowButton = screen.getByText('Elbow');
        const shoulderButton = screen.getByText('Shoulder');
        const hipButton = screen.getByText('Hip');
        
        expect(elbowButton).toHaveClass('selected');
        expect(shoulderButton).toHaveClass('selected');
        expect(hipButton).toHaveClass('selected');
      });
    });

    test('renders chart controls and legend', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Master')).toBeInTheDocument();
        expect(screen.getByText('Learner')).toBeInTheDocument();
        expect(screen.getByText('Problem Area')).toBeInTheDocument();
        expect(screen.getByText('Optimal Range')).toBeInTheDocument();
      });
    });

    test('renders focus range slider', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Focus Range: Frame 0')).toBeInTheDocument();
        const slider = screen.getByDisplayValue('1200');
        expect(slider).toBeInTheDocument();
        expect(slider).toHaveAttribute('type', 'range');
      });
    });

    test('renders height plot range slider', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Height Plot Range: 240px')).toBeInTheDocument();
        const slider = screen.getByDisplayValue('240');
        expect(slider).toBeInTheDocument();
        expect(slider).toHaveAttribute('type', 'range');
      });
    });
  });

  describe('Joint Selection Functionality', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('can select and deselect joints', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const spineTopButton = screen.getByText('Spine Top');
        
        // Initially not selected
        expect(spineTopButton).not.toHaveClass('selected');
        
        // Click to select
        fireEvent.click(spineTopButton);
        expect(spineTopButton).toHaveClass('selected');
        
        // Click to deselect
        fireEvent.click(spineTopButton);
        expect(spineTopButton).not.toHaveClass('selected');
      });
    });

    test('can select multiple joints', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const spineTopButton = screen.getByText('Spine Top');
        const spineBottomButton = screen.getByText('Spine Bottom');
        
        fireEvent.click(spineTopButton);
        fireEvent.click(spineBottomButton);
        
        expect(spineTopButton).toHaveClass('selected');
        expect(spineBottomButton).toHaveClass('selected');
      });
    });

    test('deselecting a joint removes it from selected list', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const elbowButton = screen.getByText('Elbow');
        
        // Initially selected
        expect(elbowButton).toHaveClass('selected');
        
        // Deselect
        fireEvent.click(elbowButton);
        expect(elbowButton).not.toHaveClass('selected');
      });
    });
  });

  describe('Slider Controls', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('focus range slider updates correctly', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const slider = screen.getByDisplayValue('1200');
        
        fireEvent.change(slider, { target: { value: '800' } });
        
        expect(screen.getByText('800')).toBeInTheDocument();
      });
    });

    test('height plot slider updates correctly', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const slider = screen.getByDisplayValue('240');
        
        fireEvent.change(slider, { target: { value: '300' } });
        
        expect(screen.getByText('Height Plot Range: 300px')).toBeInTheDocument();
      });
    });
  });

  describe('Joint Display Name Function', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('correctly formats joint display names', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Elbow')).toBeInTheDocument();
        expect(screen.getByText('Shoulder')).toBeInTheDocument();
        expect(screen.getByText('Hip')).toBeInTheDocument();
        expect(screen.getByText('Spine Top')).toBeInTheDocument();
        expect(screen.getByText('Spine Bottom')).toBeInTheDocument();
      });
    });
  });

  describe('Problem Areas Detection', () => {
    beforeEach(() => {
      // Create data with significant differences to trigger problem areas
      const masterDataWithProblems = {
        ...mockMasterData,
        angles: {
          ...mockMasterData.angles,
          left_hip: [30, 45, 60, 50, 35],
          right_hip: [35, 50, 65, 55, 40]
        }
      };
      
      const learnerDataWithProblems = {
        ...mockLearnerData,
        angles: {
          ...mockLearnerData.angles,
          left_hip: [10, 25, 40, 30, 15], // 20+ degree differences
          right_hip: [15, 30, 45, 35, 20]  // 20+ degree differences
        }
      };
      
      loadMasterData.mockResolvedValue(masterDataWithProblems);
      loadLearnerData.mockResolvedValue(learnerDataWithProblems);
    });

    test('detects and displays problem areas', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Areas Needing Improvement')).toBeInTheDocument();
      });
    });
  });

  describe('Range of Motion Table', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('renders range of motion table when not in compact mode', async () => {
      render(<JointAngleChart compact={false} />);
      
      await waitFor(() => {
        expect(screen.getByText('Range of Motion Analysis')).toBeInTheDocument();
        expect(screen.getByText('Joint')).toBeInTheDocument();
        expect(screen.getByText('Min (°)')).toBeInTheDocument();
        expect(screen.getByText('Max (°)')).toBeInTheDocument();
        expect(screen.getByText('Optimal (°)')).toBeInTheDocument();
      });
    });

    test('does not render range of motion table in compact mode', async () => {
      render(<JointAngleChart compact={true} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Range of Motion Analysis')).not.toBeInTheDocument();
      });
    });

    test('displays correct range of motion values', async () => {
      render(<JointAngleChart compact={false} />);
      
      await waitFor(() => {
        // Check for some specific values from our mock data
        expect(screen.getByText('115.0')).toBeInTheDocument(); // left elbow optimal
        expect(screen.getByText('120.0')).toBeInTheDocument(); // right elbow optimal
      });
    });
  });

  describe('Comparison Mode Handling', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('handles sideBySide comparison mode', async () => {
      render(<JointAngleChart comparisonMode="sideBySide" />);
      
      await waitFor(() => {
        expect(screen.getByText('Master')).toBeInTheDocument();
        expect(screen.getByText('Learner')).toBeInTheDocument();
      });
    });

    test('handles masterOnly comparison mode', async () => {
      render(<JointAngleChart comparisonMode="masterOnly" />);
      
      await waitFor(() => {
        expect(screen.getByText('Master')).toBeInTheDocument();
        expect(screen.queryByText('Learner')).not.toBeInTheDocument();
        expect(screen.queryByText('Problem Area')).not.toBeInTheDocument();
      });
    });
  });

  describe('Chart Data Structure', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('chart receives correct data structure', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const plotData = screen.getByTestId('plot-data');
        const dataContent = plotData.textContent;
        
        // Check that chart data contains the expected traces
        expect(dataContent).toContain('Master');
        expect(dataContent).toContain('Learner');
        expect(dataContent).toContain('#0066FF'); // Master color
        expect(dataContent).toContain('#FF3333'); // Learner color
      });
    });

    test('chart layout has correct configuration', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        const plotLayout = screen.getByTestId('plot-layout');
        const layoutContent = plotLayout.textContent;
        
        expect(layoutContent).toContain('"rows":3'); // Default 3 joints selected
        expect(layoutContent).toContain('"columns":1');
        expect(layoutContent).toContain('Frame');
      });
    });
  });

  describe('Error Handling', () => {
    test('handles partial data loading failure gracefully', async () => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockRejectedValue(new Error('Learner data failed'));

      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load joint angle data. Please try again later.')).toBeInTheDocument();
      });
    });

    test('handles missing angles data', async () => {
      const incompleteData = {
        ...mockMasterData,
        angles: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      // Should not crash when rendering
      expect(() => render(<JointAngleChart />)).not.toThrow();
    });

    test('handles missing range of motion data', async () => {
      const incompleteData = {
        ...mockMasterData,
        rangeOfMotion: undefined
      };
      
      loadMasterData.mockResolvedValue(incompleteData);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      render(<JointAngleChart compact={false} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Range of Motion Analysis')).not.toBeInTheDocument();
      });
    });

    test('handles missing frames data gracefully', async () => {
      const dataWithoutFrames = {
        ...mockMasterData,
        frames: undefined
      };
      
      loadMasterData.mockResolvedValue(dataWithoutFrames);
      loadLearnerData.mockResolvedValue(mockLearnerData);

      // Should not crash when rendering
      expect(() => render(<JointAngleChart />)).not.toThrow();
    });
  });

  describe('Data Interpolation Function', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('handles data with frames array', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        // Component should render successfully with frame-based data
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });

    test('handles data with keyPoseFrames array', async () => {
      const keyPoseData = {
        ...mockMasterData,
        frames: undefined, // Remove frames to force keyPose path
        keyPoseFrames: [0, 100, 200, 300, 400]
      };
      
      loadMasterData.mockResolvedValue(keyPoseData);
      
      render(<JointAngleChart />);
      
      await waitFor(() => {
        // Component should render successfully with keyPose-based data
        expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
      });
    });
  });

  describe('Available Joints Extraction', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('correctly extracts joint types from data', async () => {
      render(<JointAngleChart />);
      
      await waitFor(() => {
        // Should show all available joint types
        expect(screen.getByText('Elbow')).toBeInTheDocument();
        expect(screen.getByText('Shoulder')).toBeInTheDocument();
        expect(screen.getByText('Hip')).toBeInTheDocument();
        expect(screen.getByText('Spine Top')).toBeInTheDocument();
        expect(screen.getByText('Spine Bottom')).toBeInTheDocument();
      });
    });

    test('handles data with limited joint types', async () => {
      const limitedData = {
        ...mockMasterData,
        angles: {
          left_elbow: [90, 110, 130, 120, 95],
          right_elbow: [95, 115, 135, 125, 100],
          left_hip: [30, 45, 60, 50, 35],
          right_hip: [35, 50, 65, 55, 40]
        }
      };
      
      loadMasterData.mockResolvedValue(limitedData);
      
      render(<JointAngleChart />);
      
      await waitFor(() => {
        expect(screen.getByText('Elbow')).toBeInTheDocument();
        expect(screen.getByText('Hip')).toBeInTheDocument();
        expect(screen.queryByText('Shoulder')).not.toBeInTheDocument();
      });
    });
  });

  describe('Component Props', () => {
    beforeEach(() => {
      loadMasterData.mockResolvedValue(mockMasterData);
      loadLearnerData.mockResolvedValue(mockLearnerData);
    });

    test('accepts comparisonMode prop', async () => {
      render(<JointAngleChart comparisonMode="masterOnly" />);
      
      await waitFor(() => {
        expect(screen.getByText('Joint Angle Analysis')).toBeInTheDocument();
      });
    });

    test('accepts compact prop', async () => {
      render(<JointAngleChart compact={true} />);
      
      await waitFor(() => {
        expect(screen.getByText('Joint Angle Analysis')).toBeInTheDocument();
      });
    });
  });
});
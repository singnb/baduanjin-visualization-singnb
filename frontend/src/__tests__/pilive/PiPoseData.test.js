/* eslint-disable testing-library/no-node-access */
/* eslint-disable testing-library/no-container */
// src/__tests__/pilive/PiPoseData.test.js

import React from 'react';
import { render, screen } from '@testing-library/react';
import PiPoseData from '../../components/PiLive/PiPoseData';

// Mock data
const mockActiveSession = {
  session_id: 'test-session-123',
  session_name: 'Test Session'
};

const mockPoseDataEmpty = {
  pose_data: [],
  stats: {
    current_fps: 30,
    persons_detected: 0,
    total_frames: 100
  },
  timestamp: new Date('2023-01-01T10:00:00Z').toISOString()
};

const mockPoseDataWithPerson = {
  pose_data: [
    {
      keypoints: [
        [100, 200, 0.9],
        [110, 210, 0.8],
        [120, 220, 0.7]
      ],
      confidences: [0.9, 0.8, 0.7],
      bbox: [50, 100, 150, 200]
    }
  ],
  stats: {
    current_fps: 28,
    persons_detected: 1,
    total_frames: 150
  },
  timestamp: new Date('2023-01-01T10:05:00Z').toISOString()
};

const mockPoseDataLowConfidence = {
  pose_data: [
    {
      keypoints: [
        [100, 200, 0.3],
        [110, 210, 0.4],
        [120, 220, 0.2]
      ],
      confidences: [0.3, 0.4, 0.2],
      bbox: [50, 100, 150, 200]
    }
  ],
  stats: {
    current_fps: 25,
    persons_detected: 1,
    total_frames: 200
  },
  timestamp: new Date('2023-01-01T10:10:00Z').toISOString()
};

const mockPoseDataMultiplePersons = {
  pose_data: [
    {
      keypoints: [
        [100, 200, 0.9],
        [110, 210, 0.8]
      ],
      confidences: [0.9, 0.8],
      bbox: [50, 100, 150, 200]
    },
    {
      keypoints: [
        [300, 400, 0.7],
        [310, 410, 0.6]
      ],
      confidences: [0.7, 0.6],
      bbox: [250, 300, 350, 400]
    }
  ],
  stats: {
    current_fps: 26,
    persons_detected: 2,
    total_frames: 250
  },
  timestamp: new Date('2023-01-01T10:15:00Z').toISOString()
};

describe('PiPoseData Component', () => {
  describe('Component Rendering', () => {
    test('renders without active session', () => {
      render(<PiPoseData poseData={null} activeSession={null} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Start a session to see pose data')).toBeInTheDocument();
    });

    test('renders with active session but no pose data', () => {
      render(<PiPoseData poseData={null} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Waiting for pose data...')).toBeInTheDocument();
    });

    test('renders with active session and empty pose data', () => {
      render(<PiPoseData poseData={mockPoseDataEmpty} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Real-time Analysis')).toBeInTheDocument();
      expect(screen.getByText('FPS:')).toBeInTheDocument();
      expect(screen.getByText('Persons:')).toBeInTheDocument();
      expect(screen.getByText('Last Update:')).toBeInTheDocument();
    });

    test('renders with pose data containing person', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Real-time Analysis')).toBeInTheDocument();
      expect(screen.getByText('Person 1 Analysis:')).toBeInTheDocument();
      expect(screen.getByText(/Pose detected/)).toBeInTheDocument();
    });
  });

  describe('Stats Display', () => {
    test('displays FPS correctly', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('FPS:')).toBeInTheDocument();
      expect(screen.getByText('28')).toBeInTheDocument();
    });

    test('displays persons count correctly', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Persons:')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    test('displays last update time correctly', () => {
      // Use current time for more predictable results
      const currentTime = new Date();
      const poseDataWithCurrentTime = {
        ...mockPoseDataWithPerson,
        timestamp: currentTime.toISOString()
      };
      
      render(<PiPoseData poseData={poseDataWithCurrentTime} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Last Update:')).toBeInTheDocument();
      expect(screen.getByText(/\d{1,2}:\d{2}:\d{2}/)).toBeInTheDocument();
    });

    test('displays zero values when no stats available', () => {
      const poseDataNoStats = {
        pose_data: [],
        stats: null,
        timestamp: null
      };
      
      render(<PiPoseData poseData={poseDataNoStats} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('FPS:')).toBeInTheDocument();
      expect(screen.getByText('Last Update:')).toBeInTheDocument();
      expect(screen.getByText('N/A')).toBeInTheDocument(); // Last Update
    });

    test('displays multiple persons count correctly', () => {
      render(<PiPoseData poseData={mockPoseDataMultiplePersons} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Persons:')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  describe('Pose Details Display', () => {
    test('displays keypoints count', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Keypoints: 3')).toBeInTheDocument();
    });

    test('calculates and displays average confidence', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      // Average of [0.9, 0.8, 0.7] = 0.8 = 80%
      expect(screen.getByText('Avg Confidence: 80.0%')).toBeInTheDocument();
    });

    test('handles pose data without confidences', () => {
      const poseDataNoConfidences = {
        pose_data: [
          {
            keypoints: [
              [100, 200, 0.9],
              [110, 210, 0.8]
            ]
          }
        ],
        stats: {
          current_fps: 30,
          persons_detected: 1
        },
        timestamp: new Date().toISOString()
      };
      
      render(<PiPoseData poseData={poseDataNoConfidences} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Keypoints: 2')).toBeInTheDocument();
      expect(screen.queryByText(/Avg Confidence/)).not.toBeInTheDocument();
    });

    test('handles pose data without keypoints', () => {
      const poseDataNoKeypoints = {
        pose_data: [
          {
            confidences: [0.9, 0.8, 0.7]
          }
        ],
        stats: {
          current_fps: 30,
          persons_detected: 1
        },
        timestamp: new Date().toISOString()
      };
      
      render(<PiPoseData poseData={poseDataNoKeypoints} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Keypoints: 0')).toBeInTheDocument();
    });
  });

  describe('Live Feedback', () => {
    test('shows pose detected feedback', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(screen.getByText(/Pose detected/)).toBeInTheDocument();
    });

    test('shows low confidence warning', () => {
      render(<PiPoseData poseData={mockPoseDataLowConfidence} activeSession={mockActiveSession} />);
      
      expect(screen.getByText(/Pose detected/)).toBeInTheDocument();
      expect(screen.getByText(/Some keypoints have low confidence/)).toBeInTheDocument();
    });

    test('does not show warning for high confidence', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(screen.getByText(/Pose detected/)).toBeInTheDocument();
      expect(screen.queryByText(/Some keypoints have low confidence/)).not.toBeInTheDocument();
    });

    test('handles missing confidences gracefully', () => {
      const poseDataNoConfidences = {
        pose_data: [
          {
            keypoints: [
              [100, 200, 0.9],
              [110, 210, 0.8]
            ]
          }
        ],
        stats: {
          current_fps: 30,
          persons_detected: 1
        },
        timestamp: new Date().toISOString()
      };
      
      render(<PiPoseData poseData={poseDataNoConfidences} activeSession={mockActiveSession} />);
      
      expect(screen.getByText(/Pose detected/)).toBeInTheDocument();
      expect(screen.queryByText(/Some keypoints have low confidence/)).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    test('handles undefined pose data', () => {
      render(<PiPoseData poseData={undefined} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Waiting for pose data...')).toBeInTheDocument();
    });

    test('handles pose data with undefined pose_data property', () => {
      const poseDataUndefined = {
        pose_data: undefined,
        stats: { current_fps: 30 },
        timestamp: new Date().toISOString()
      };
      
      render(<PiPoseData poseData={poseDataUndefined} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Waiting for pose data...')).toBeInTheDocument();
    });

    test('handles empty active session', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={{}} />);
      
      expect(screen.getByText('Real-time Analysis')).toBeInTheDocument();
    });

    test('handles malformed timestamp', () => {
      const poseDataBadTimestamp = {
        ...mockPoseDataWithPerson,
        timestamp: 'invalid-timestamp'
      };
      
      render(<PiPoseData poseData={poseDataBadTimestamp} activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Real-time Analysis')).toBeInTheDocument();
      expect(screen.getByText('Last Update:')).toBeInTheDocument();
    });

    test('handles division by zero in confidence calculation', () => {
      const poseDataEmptyConfidences = {
        pose_data: [
          {
            keypoints: [
              [100, 200, 0.9]
            ],
            confidences: []
          }
        ],
        stats: {
          current_fps: 30,
          persons_detected: 1
        },
        timestamp: new Date().toISOString()
      };
      
      render(<PiPoseData poseData={poseDataEmptyConfidences} activeSession={mockActiveSession} />);
      
      expect(screen.getByText(/Pose detected/)).toBeInTheDocument();
      expect(screen.getByText(/Avg Confidence:/)).toBeInTheDocument();
    });
  });

  describe('Props Validation', () => {
    test('renders with minimal props', () => {
      render(<PiPoseData />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Start a session to see pose data')).toBeInTheDocument();
    });

    test('renders with only activeSession prop', () => {
      render(<PiPoseData activeSession={mockActiveSession} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Waiting for pose data...')).toBeInTheDocument();
    });

    test('renders with only poseData prop', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Start a session to see pose data')).toBeInTheDocument();
    });

    test('handles boolean activeSession prop', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={true} />);
      
      expect(screen.getByText('Real-time Analysis')).toBeInTheDocument();
    });

    test('handles false activeSession prop', () => {
      render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={false} />);
      
      expect(screen.getByText('Pose Analysis')).toBeInTheDocument();
      expect(screen.getByText('Start a session to see pose data')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    test('has correct CSS classes for empty state', () => {
      const { container } = render(<PiPoseData poseData={null} activeSession={null} />);
      
      expect(container.querySelector('.pi-pose-data.empty')).toBeInTheDocument();
    });

    test('has correct CSS classes for active state', () => {
      const { container } = render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(container.querySelector('.pi-pose-data')).toBeInTheDocument();
      expect(container.querySelector('.stats-grid')).toBeInTheDocument();
      expect(container.querySelector('.pose-details')).toBeInTheDocument();
    });

    test('contains stats grid elements', () => {
      const { container } = render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(container.querySelectorAll('.stat-item')).toHaveLength(3);
    });

    test('contains live feedback elements', () => {
      const { container } = render(<PiPoseData poseData={mockPoseDataWithPerson} activeSession={mockActiveSession} />);
      
      expect(container.querySelector('.live-feedback')).toBeInTheDocument();
      expect(container.querySelector('.feedback-item.good')).toBeInTheDocument();
    });
  });
});
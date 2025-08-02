// src/__tests__/services/dataLoader.test.js

import axios from 'axios';
import {
  loadMasterData,
  loadLearnerData,
  loadAnalysisData,
  loadUserVideos,
  loadRecommendations,
  loadComparisonData
} from '../../services/dataLoader';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

// Mock window.location
const mockLocation = {
  pathname: '/'
};
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true
});

// Mock console methods to avoid cluttering test output
global.console = {
  ...console,
  log: jest.fn(),
  error: jest.fn()
};

describe('dataLoader Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue('mock-token');
    window.location.pathname = '/';
  });

  describe('Authentication Header', () => {
    test('should include Authorization header when token exists', async () => {
      mockLocalStorage.getItem.mockReturnValue('test-token');
      mockedAxios.get.mockResolvedValue({ data: [] });

      await loadUserVideos();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos',
        {
          headers: { Authorization: 'Bearer test-token' }
        }
      );
    });

    test('should not include Authorization header when no token exists', async () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      mockedAxios.get.mockResolvedValue({ data: [] });

      await loadUserVideos();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos',
        {
          headers: {}
        }
      );
    });
  });

  describe('loadMasterData', () => {
    test('should load master data in comparison view', async () => {
      window.location.pathname = '/comparison/user123/master456';
      const mockData = { title: 'Master Joint Angles', frames: [] };
      mockedAxios.get.mockResolvedValue({ data: mockData });

      const result = await loadMasterData('jointAngles');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/analysis-master/data/master456/master_joint_angles.json',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(result).toEqual(mockData);
    });

    test('should return mock data when not in comparison view', async () => {
      window.location.pathname = '/videos';

      const result = await loadMasterData('jointAngles');

      expect(mockedAxios.get).not.toHaveBeenCalled();
      expect(result).toEqual({
        title: "Joint Angles Analysis",
        description: "No data available",
        frames: [],
        angles: {},
        keyPoseFrames: [],
        keyPoseNames: [],
        rangeOfMotion: {}
      });
    });

    test('should handle API errors and return mock data', async () => {
      window.location.pathname = '/comparison/user123/master456';
      mockedAxios.get.mockRejectedValue(new Error('Network error'));

      const result = await loadMasterData('smoothness');

      expect(result).toEqual({
        title: "Movement Smoothness",
        description: "No data available",
        jerkMetrics: {},
        keypointNames: {},
        movementPhases: [],
        overallSmoothness: 0,
        optimalJerkRange: [0.85, 0.95]
      });
    });

    test('should map different analysis types correctly', async () => {
      window.location.pathname = '/comparison/user123/master456';
      mockedAxios.get.mockResolvedValue({ data: {} });

      await loadMasterData('symmetry');
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('master_symmetry.json'),
        expect.any(Object)
      );

      await loadMasterData('balance');
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('master_balance.json'),
        expect.any(Object)
      );
    });
  });

  describe('loadLearnerData', () => {
    test('should load learner data in comparison view', async () => {
      window.location.pathname = '/comparison/user123/master456';
      const mockData = { title: 'Learner Joint Angles', frames: [] };
      mockedAxios.get.mockResolvedValue({ data: mockData });

      const result = await loadLearnerData('jointAngles');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/analysis-master/data/user123/learner_joint_angles.json',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(result).toEqual(mockData);
    });

    test('should return mock data when not in comparison view', async () => {
      window.location.pathname = '/analysis';

      const result = await loadLearnerData('balance');

      expect(mockedAxios.get).not.toHaveBeenCalled();
      expect(result).toEqual({
        title: "Balance Analysis",
        description: "No data available",
        balanceMetrics: {},
        comTrajectory: { x: [], y: [], sampleFrames: [] },
        keyPoseBalance: [],
        overallStability: 0,
        optimalStabilityRange: [0.85, 1.0]
      });
    });

    test('should handle API errors and return mock data', async () => {
      window.location.pathname = '/comparison/user123/master456';
      mockedAxios.get.mockRejectedValue(new Error('API error'));

      const result = await loadLearnerData('symmetry');

      expect(result).toEqual({
        title: "Movement Symmetry",
        description: "No data available",
        symmetryScores: {},
        keypointPairNames: {},
        keyPoseSymmetry: [],
        overallSymmetry: 0,
        optimalSymmetryRange: [0.90, 1.0]
      });
    });
  });

  describe('loadAnalysisData', () => {
    test('should load analysis data successfully', async () => {
      const mockAnalysisData = { frames: [], angles: {} };
      const mockResponse = {
        data: {
          jointAngles_data: mockAnalysisData
        }
      };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await loadAnalysisData('video123', 'jointAngles');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos/video123/analysis',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(result).toEqual(mockAnalysisData);
    });

    test('should return mock data when analysis type not found in response', async () => {
      const mockResponse = { data: {} };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await loadAnalysisData('video123', 'jointAngles');

      expect(result).toEqual({
        title: "Joint Angles Analysis",
        description: "No data available",
        frames: [],
        angles: {},
        keyPoseFrames: [],
        keyPoseNames: [],
        rangeOfMotion: {}
      });
    });

    test('should handle API errors and return mock data', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Server error'));

      const result = await loadAnalysisData('video123', 'smoothness');

      expect(result).toEqual({
        title: "Movement Smoothness",
        description: "No data available",
        jerkMetrics: {},
        keypointNames: {},
        movementPhases: [],
        overallSmoothness: 0,
        optimalJerkRange: [0.85, 0.95]
      });
    });
  });

  describe('loadUserVideos', () => {
    test('should load user videos successfully', async () => {
      const mockVideos = [
        { id: 1, title: 'Video 1' },
        { id: 2, title: 'Video 2' }
      ];
      mockedAxios.get.mockResolvedValue({ data: mockVideos });

      const result = await loadUserVideos();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(result).toEqual(mockVideos);
    });

    test('should return empty array on API error', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'));

      const result = await loadUserVideos();

      expect(result).toEqual([]);
    });
  });

  describe('loadRecommendations', () => {
    test('should load recommendations successfully', async () => {
      const mockRecommendations = {
        overall: "Improve posture alignment",
        specific: ["Focus on shoulder position"]
      };
      const mockResponse = {
        data: {
          recommendations: mockRecommendations
        }
      };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await loadRecommendations('video123');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://baduanjin-backend-docker.azurewebsites.net/api/videos/video123/analysis',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(result).toEqual(mockRecommendations);
    });

    test('should return default message when no recommendations in response', async () => {
      const mockResponse = { data: {} };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await loadRecommendations('video123');

      expect(result).toEqual({
        overall: "No recommendations available yet."
      });
    });

    test('should handle API errors and return default message', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Server error'));

      const result = await loadRecommendations('video123');

      expect(result).toEqual({
        overall: "No recommendations available yet."
      });
    });
  });

  describe('loadComparisonData', () => {
    test('should load comparison data successfully', async () => {
      const mockLearnerData = { title: 'Learner Data' };
      const mockMasterData = { title: 'Master Data' };
      
      mockedAxios.get
        .mockResolvedValueOnce({ data: mockLearnerData })
        .mockResolvedValueOnce({ data: mockMasterData });

      const result = await loadComparisonData('user123', 'master456', 'jointAngles');

      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      expect(mockedAxios.get).toHaveBeenNthCalledWith(1,
        'https://baduanjin-backend-docker.azurewebsites.net/api/analysis-master/data/user123/learner_joint_angles.json',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(mockedAxios.get).toHaveBeenNthCalledWith(2,
        'https://baduanjin-backend-docker.azurewebsites.net/api/analysis-master/data/master456/master_joint_angles.json',
        { headers: { Authorization: 'Bearer mock-token' } }
      );
      expect(result).toEqual({
        learnerData: mockLearnerData,
        masterData: mockMasterData
      });
    });

    test('should throw error when API calls fail', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'));

      await expect(
        loadComparisonData('user123', 'master456', 'smoothness')
      ).rejects.toThrow('Network error');
    });

    test('should map different data types correctly', async () => {
      mockedAxios.get
        .mockResolvedValueOnce({ data: {} })
        .mockResolvedValueOnce({ data: {} });

      await loadComparisonData('user123', 'master456', 'balance');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('learner_balance.json'),
        expect.any(Object)
      );
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('master_balance.json'),
        expect.any(Object)
      );
    });
  });

  describe('URL Path Parsing', () => {
    test('should correctly identify comparison paths with different structures', async () => {
      // Test short path
      window.location.pathname = '/comparison/user123';
      mockedAxios.get.mockResolvedValue({ data: {} });
      
      const result = await loadMasterData('jointAngles');
      expect(result.title).toBe("Joint Angles Analysis"); // Should return mock data

      // Test correct comparison path
      window.location.pathname = '/comparison/user123/master456';
      await loadMasterData('jointAngles');
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('master456/master_joint_angles.json'),
        expect.any(Object)
      );
    });

    test('should handle paths with extra segments', async () => {
      window.location.pathname = '/comparison/user123/master456/extra';
      mockedAxios.get.mockResolvedValue({ data: {} });

      await loadLearnerData('smoothness');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('user123/learner_smoothness.json'),
        expect.any(Object)
      );
    });
  });

  describe('Mock Data Generation', () => {
    test('should return appropriate mock data for unknown analysis type', async () => {
      const result = await loadMasterData('unknownType');

      expect(result).toEqual({ error: 'Unknown analysis type' });
    });

    test('should generate consistent mock data structure for all known types', async () => {
      const types = ['jointAngles', 'smoothness', 'symmetry', 'balance'];
      
      for (const type of types) {
        const result = await loadMasterData(type);
        expect(result).toHaveProperty('title');
        expect(result).toHaveProperty('description');
        expect(result.description).toBe('No data available');
      }
    });
  });
});
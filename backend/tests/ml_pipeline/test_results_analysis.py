# type: ignore
# /test/ml_pipeline/test_results_analysis.py
# Unit tests for ml_pipeline/results_analysis.py core functions

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import sys
import tempfile
import shutil
import json
import numpy as np
import pandas as pd

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the class we want to test
from ml_pipeline.results_analysis import BaduanjinAnalyzer

# Module-level fixtures that can be shared across test classes
@pytest.fixture
def valid_json_data():
    """Create valid MMPose 1.3.2 JSON structure"""
    return {
        "meta_info": {
            "dataset_name": "test_dataset",
            "keypoint_info": {
                "keypoint_0": "nose",
                "keypoint_1": "left_eye"
            },
            "skeleton_info": {}
        },
        "instance_info": [
            {
                "frame_id": 1,
                "instances": [
                    {
                        "keypoints": [[100, 200], [110, 210], [120, 220]],
                        "keypoint_scores": [0.9, 0.8, 0.7]
                    }
                ]
            },
            {
                "frame_id": 2,
                "instances": [
                    {
                        "keypoints": [[105, 205], [115, 215], [125, 225]],
                        "keypoint_scores": [0.95, 0.85, 0.75]
                    }
                ]
            }
        ]
    }

@pytest.fixture
def temp_json_file(valid_json_data):
    """Create temporary JSON file for testing"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(valid_json_data, temp_file)
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)

@pytest.fixture
def minimal_json_data():
    """Create minimal valid JSON data for testing"""
    return {
        "meta_info": {},
        "instance_info": [
            {
                "frame_id": 1,
                "instances": [
                    {
                        "keypoints": [[100, 200]],
                        "keypoint_scores": [0.9]
                    }
                ]
            }
        ]
    }

@pytest.fixture
def temp_json_file_minimal(minimal_json_data):
    """Create temporary JSON file with minimal data"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(minimal_json_data, temp_file)
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)

@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestBaduanjinAnalyzerInitialization:
    """Test BaduanjinAnalyzer initialization and JSON loading"""
    
    def test_initialization_success(self, temp_json_file):
        """Test successful initialization with valid JSON"""
        with patch('ml_pipeline.results_analysis.plt'):
            analyzer = BaduanjinAnalyzer(temp_json_file)
            
            assert analyzer.json_path == temp_json_file
            assert analyzer.video_path is None
            assert hasattr(analyzer, 'pose_data')
            assert hasattr(analyzer, 'meta_info')
            assert hasattr(analyzer, 'instance_info')
            assert hasattr(analyzer, 'keypoint_mapping')
    
    def test_initialization_with_video_path(self, temp_json_file):
        """Test initialization with video path"""
        video_path = "test_video.mp4"
        with patch('ml_pipeline.results_analysis.plt'):
            analyzer = BaduanjinAnalyzer(temp_json_file, video_path)
            
            assert analyzer.video_path == video_path
    
    def test_initialization_file_not_found(self):
        """Test initialization with non-existent file"""
        with pytest.raises(ValueError, match="Failed to load JSON file"):
            BaduanjinAnalyzer("non_existent_file.json")
    
    def test_initialization_invalid_json(self):
        """Test initialization with invalid JSON file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write("invalid json content")
        temp_file.close()
        
        try:
            with pytest.raises(ValueError, match="Failed to load JSON file"):
                BaduanjinAnalyzer(temp_file.name)
        finally:
            os.unlink(temp_file.name)
    
    def test_keypoint_mapping_exists(self, temp_json_file):
        """Test that keypoint mapping is properly initialized"""
        with patch('ml_pipeline.results_analysis.plt'):
            analyzer = BaduanjinAnalyzer(temp_json_file)
            
            assert isinstance(analyzer.keypoint_mapping, dict)
            assert 0 in analyzer.keypoint_mapping
            assert analyzer.keypoint_mapping[0] == "Nose"
            assert len(analyzer.keypoint_mapping) == 17  # COCO format


class TestJSONStructureValidation:
    """Test JSON structure validation methods"""
    
    def test_validate_json_structure_success(self, valid_json_data):
        """Test successful JSON structure validation"""
        with patch('builtins.open', mock_open(read_data=json.dumps(valid_json_data))):
            with patch('ml_pipeline.results_analysis.plt'):
                # Should not raise any exceptions
                analyzer = BaduanjinAnalyzer("test.json")
                assert analyzer.pose_data == valid_json_data
    
    def test_validate_json_structure_missing_meta_info(self):
        """Test validation with missing meta_info"""
        invalid_data = {
            "instance_info": []
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_data))):
            with pytest.raises(ValueError, match="Missing required key 'meta_info'"):
                BaduanjinAnalyzer("test.json")
    
    def test_validate_json_structure_missing_instance_info(self):
        """Test validation with missing instance_info"""
        invalid_data = {
            "meta_info": {}
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_data))):
            with pytest.raises(ValueError, match="Missing required key 'instance_info'"):
                BaduanjinAnalyzer("test.json")
    
    def test_validate_json_structure_invalid_instance_info_type(self):
        """Test validation with invalid instance_info type"""
        invalid_data = {
            "meta_info": {},
            "instance_info": "not a list"
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_data))):
            with pytest.raises(ValueError, match="'instance_info' should be a list"):
                BaduanjinAnalyzer("test.json")
    
    def test_validate_json_structure_empty_instance_info(self):
        """Test validation with empty instance_info"""
        invalid_data = {
            "meta_info": {},
            "instance_info": []
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_data))):
            with pytest.raises(ValueError, match="No frame data found"):
                BaduanjinAnalyzer("test.json")
    
    def test_validate_json_structure_missing_instances_in_frame(self):
        """Test validation with missing instances in frame data"""
        invalid_data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1
                    # Missing 'instances' key
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_data))):
            with pytest.raises(ValueError, match="No 'instances' found in frame data"):
                BaduanjinAnalyzer("test.json")


class TestKeypointNameConversion:
    """Test keypoint name conversion methods"""
    
    @pytest.fixture
    def analyzer(self, temp_json_file_minimal):
        """Create analyzer instance for testing"""
        with patch('ml_pipeline.results_analysis.plt'):
            return BaduanjinAnalyzer(temp_json_file_minimal)
    
    def test_get_keypoint_name_string_format(self, analyzer):
        """Test keypoint name conversion from string format"""
        assert analyzer._get_keypoint_name("keypoint_0") == "Nose"
        assert analyzer._get_keypoint_name("keypoint_5") == "Left Shoulder"
        assert analyzer._get_keypoint_name("keypoint_16") == "Right Ankle"
    
    def test_get_keypoint_name_integer_format(self, analyzer):
        """Test keypoint name conversion from integer format"""
        assert analyzer._get_keypoint_name(0) == "Nose"
        assert analyzer._get_keypoint_name(5) == "Left Shoulder"
        assert analyzer._get_keypoint_name(16) == "Right Ankle"
    
    def test_get_keypoint_name_invalid_format(self, analyzer):
        """Test keypoint name conversion with invalid formats"""
        assert analyzer._get_keypoint_name("invalid_format") == "invalid_format"
        assert analyzer._get_keypoint_name(99) == "keypoint_99"
        assert analyzer._get_keypoint_name("keypoint_abc") == "keypoint_abc"


class TestDataPreprocessing:
    """Test data preprocessing methods"""
    
    @pytest.fixture
    def analyzer_with_complex_data(self):
        """Create analyzer with complex test data"""
        complex_data = {
            "meta_info": {
                "dataset_name": "test_complex"
            },
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200], [110, 210], [120, 220], [130, 230]],
                            "keypoint_scores": [0.9, 0.8, 0.7, 0.6]
                        },
                        {
                            "keypoints": [[95, 195], [105, 205], [115, 215], [125, 225]],
                            "keypoint_scores": [0.95, 0.85, 0.75, 0.65]
                        }
                    ]
                },
                {
                    "frame_id": 2,
                    "instances": []  # Empty frame
                },
                {
                    "frame_id": 3,
                    "instances": [
                        {
                            "keypoints": [[102, 202], [112, 212]],
                            "keypoint_scores": [0.92, 0.82]
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(complex_data))):
            with patch('ml_pipeline.results_analysis.plt'):
                return BaduanjinAnalyzer("test.json")
    
    def test_preprocess_pose_data_success(self, analyzer_with_complex_data):
        """Test successful pose data preprocessing"""
        analyzer = analyzer_with_complex_data
        
        # Check that DataFrame was created
        assert hasattr(analyzer, 'pose_df')
        assert isinstance(analyzer.pose_df, pd.DataFrame)
        
        # Should have processed 2 frames (frame 2 was empty)
        assert len(analyzer.pose_df) == 2
        
        # Check that keypoint data is properly formatted
        assert 'keypoint_0' in analyzer.pose_df.columns
    
    def test_validate_keypoints_format_valid(self, analyzer_with_complex_data):
        """Test keypoints format validation with valid data"""
        analyzer = analyzer_with_complex_data
        
        keypoints = [[100, 200], [110, 210], [120, 220]]
        scores = [0.9, 0.8, 0.7]
        
        assert analyzer._validate_keypoints_format(keypoints, scores) is True
    
    def test_validate_keypoints_format_invalid(self, analyzer_with_complex_data):
        """Test keypoints format validation with invalid data"""
        analyzer = analyzer_with_complex_data
        
        # Test empty data
        assert analyzer._validate_keypoints_format([], []) is False
        
        # Test mismatched lengths
        keypoints = [[100, 200], [110, 210]]
        scores = [0.9]
        result = analyzer._validate_keypoints_format(keypoints, scores)
        # Should still work but with warning
        
        # Test invalid keypoint format
        invalid_keypoints = ["invalid", [110, 210]]
        scores = [0.9, 0.8]
        assert analyzer._validate_keypoints_format(invalid_keypoints, scores) is False


class TestJointAngleCalculation:
    """Test joint angle calculation methods"""
    
    @pytest.fixture
    def analyzer_with_smoothed_data(self):
        """Create analyzer with mocked smoothed data"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock smoothed data for angle calculation
                analyzer.smoothed_data = {}
                for i in range(17):
                    analyzer.smoothed_data[f'keypoint_{i}'] = {
                        'x': np.array([100 + i*10, 105 + i*10, 110 + i*10]),
                        'y': np.array([200 + i*5, 205 + i*5, 210 + i*5]),
                        'score': np.array([0.9, 0.8, 0.85])
                    }
                
                return analyzer
    
    def test_calculate_joint_angles_success(self, analyzer_with_smoothed_data):
        """Test successful joint angle calculation"""
        analyzer = analyzer_with_smoothed_data
        
        result = analyzer.calculate_joint_angles()
        
        assert isinstance(result, pd.DataFrame)
        assert hasattr(analyzer, 'joint_angles')
        assert len(analyzer.joint_angles) > 0
        
        # Check that angle columns exist
        expected_angles = ['Right Elbow', 'Left Elbow', 'Right Shoulder', 'Left Shoulder']
        for angle in expected_angles:
            assert angle in analyzer.joint_angles.columns
    
    def test_calculate_joint_angles_low_confidence(self):
        """Test joint angle calculation with low confidence scores"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200] for _ in range(17)],
                            "keypoint_scores": [0.1 for _ in range(17)]  # Low confidence
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock low confidence data
                analyzer.smoothed_data = {}
                for i in range(17):
                    analyzer.smoothed_data[f'keypoint_{i}'] = {
                        'x': np.array([100]),
                        'y': np.array([200]),
                        'score': np.array([0.1])  # Low confidence
                    }
                
                result = analyzer.calculate_joint_angles()
                
                # Should still create DataFrame but with NaN values
                assert isinstance(result, pd.DataFrame)
                # Most values should be NaN due to low confidence
                assert result.isna().sum().sum() > 0


class TestKeyPoseIdentification:
    """Test key pose identification methods"""
    
    @pytest.fixture
    def analyzer_with_angle_data(self):
        """Create analyzer with mocked joint angle data"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": i,
                    "instances": [
                        {
                            "keypoints": [[100, 200] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                } for i in range(1, 21)  # 20 frames
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock joint angles data
                frames = list(range(1, 21))
                angle_data = {
                    'Right Elbow': np.random.uniform(90, 180, 20),
                    'Left Elbow': np.random.uniform(90, 180, 20),
                    'Right Shoulder': np.random.uniform(45, 135, 20),
                    'Left Shoulder': np.random.uniform(45, 135, 20)
                }
                analyzer.joint_angles = pd.DataFrame(angle_data, index=frames)
                
                return analyzer
    
    def test_identify_key_poses_success(self, analyzer_with_angle_data):
        """Test successful key pose identification"""
        analyzer = analyzer_with_angle_data
        
        result = analyzer.identify_key_poses(n_poses=8)
        
        assert hasattr(analyzer, 'key_frames')
        assert isinstance(result, list)
        assert len(result) <= 8
        
        # Each key frame should be a tuple (frame_id, cluster_id)
        for frame_id, cluster_id in result:
            assert isinstance(frame_id, (int, np.integer))
            assert isinstance(cluster_id, (int, np.integer))
    
    def test_identify_key_poses_with_nan_data(self):
        """Test key pose identification with NaN values in angle data"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": i,
                    "instances": [
                        {
                            "keypoints": [[100, 200] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                } for i in range(1, 11)
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock angle data with many NaN values
                frames = list(range(1, 11))
                angle_data = {
                    'Right Elbow': [np.nan] * 8 + [90, 95],  # Mostly NaN
                    'Left Elbow': [85, 90] + [np.nan] * 8,   # Mostly NaN
                    'Good Angle': np.random.uniform(45, 135, 10)  # Good data
                }
                analyzer.joint_angles = pd.DataFrame(angle_data, index=frames)
                
                result = analyzer.identify_key_poses(n_poses=4)
                
                # Should still work with fallback method
                assert len(result) <= 4
    
    def test_identify_key_poses_clustering_failure(self, analyzer_with_angle_data):
        """Test key pose identification when clustering fails"""
        analyzer = analyzer_with_angle_data
        
        # Mock KMeans to raise an exception
        with patch('ml_pipeline.results_analysis.KMeans') as mock_kmeans:
            mock_kmeans.side_effect = Exception("Clustering failed")
            
            result = analyzer.identify_key_poses(n_poses=4)
            
            # Should fallback to evenly spaced frames
            assert len(result) == 4
            assert hasattr(analyzer, 'key_frames')


class TestMovementAnalysis:
    """Test movement analysis methods"""
    
    @pytest.fixture
    def analyzer_with_movement_data(self):
        """Create analyzer with movement data for testing"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": i,
                    "instances": [
                        {
                            "keypoints": [[100 + i, 200 + i] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                } for i in range(1, 21)
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock smoothed data with movement
                analyzer.smoothed_data = {}
                for i in range(17):
                    # Create realistic movement data
                    t = np.linspace(0, 2*np.pi, 20)
                    x_vals = 100 + i*10 + 10*np.sin(t)
                    y_vals = 200 + i*5 + 5*np.cos(t)
                    scores = np.random.uniform(0.7, 0.9, 20)
                    
                    analyzer.smoothed_data[f'keypoint_{i}'] = {
                        'x': x_vals,
                        'y': y_vals,
                        'score': scores
                    }
                
                return analyzer
    
    def test_analyze_movement_smoothness_success(self, analyzer_with_movement_data):
        """Test successful movement smoothness analysis"""
        analyzer = analyzer_with_movement_data
        
        result = analyzer.analyze_movement_smoothness()
        
        assert isinstance(result, dict)
        assert hasattr(analyzer, 'movement_smoothness')
        assert len(result) > 0
        
        # Check that jerk values are calculated
        for joint_name, jerk_value in result.items():
            assert isinstance(jerk_value, (float, np.floating))
            assert jerk_value >= 0  # Jerk magnitude should be non-negative
    
    def test_analyze_movement_smoothness_low_confidence(self, analyzer_with_movement_data):
        """Test movement smoothness with low confidence data"""
        analyzer = analyzer_with_movement_data
        
        # Set low confidence for some joints
        for joint_key in ['keypoint_9', 'keypoint_10']:
            if joint_key in analyzer.smoothed_data:
                analyzer.smoothed_data[joint_key]['score'] = np.ones(20) * 0.2  # Low confidence
        
        result = analyzer.analyze_movement_smoothness()
        
        # Should still return results but skip low confidence joints
        assert isinstance(result, dict)
    
    def test_analyze_movement_symmetry_success(self, analyzer_with_movement_data):
        """Test successful movement symmetry analysis"""
        analyzer = analyzer_with_movement_data
        
        result = analyzer.analyze_movement_symmetry()
        
        assert isinstance(result, dict)
        assert hasattr(analyzer, 'symmetry_metrics')
        assert len(result) > 0
        
        # Check symmetry scores
        for pair_name, symmetry_score in result.items():
            assert isinstance(symmetry_score, (float, np.floating))
            assert symmetry_score >= 0  # Distance should be non-negative
    
    def test_analyze_movement_symmetry_missing_reference(self):
        """Test movement symmetry without reference points"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock smoothed data without nose or shoulders (reference points)
                analyzer.smoothed_data = {
                    'keypoint_15': {'x': np.array([100]), 'y': np.array([200]), 'score': np.array([0.9])},
                    'keypoint_16': {'x': np.array([120]), 'y': np.array([200]), 'score': np.array([0.9])}
                }
                
                result = analyzer.analyze_movement_symmetry()
                
                # Should handle missing reference points gracefully
                assert isinstance(result, dict)


class TestBalanceAnalysis:
    """Test balance analysis methods"""
    
    @pytest.fixture
    def analyzer_with_balance_data(self):
        """Create analyzer with balance analysis data"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": i,
                    "instances": [
                        {
                            "keypoints": [[100 + i, 200 + i] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                } for i in range(1, 21)
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock comprehensive body keypoint data
                analyzer.smoothed_data = {}
                body_parts = {
                    0: (100, 50),   # nose (head)
                    5: (80, 100),   # left shoulder
                    6: (120, 100),  # right shoulder
                    11: (85, 200),  # left hip
                    12: (115, 200), # right hip
                    7: (70, 130),   # left elbow
                    8: (130, 130),  # right elbow
                    9: (60, 160),   # left wrist
                    10: (140, 160), # right wrist
                    13: (80, 250),  # left knee
                    14: (120, 250), # right knee
                    15: (75, 300),  # left ankle
                    16: (125, 300)  # right ankle
                }
                
                for kpt_id, (base_x, base_y) in body_parts.items():
                    # Add some movement over time
                    t = np.linspace(0, 2*np.pi, 20)
                    x_vals = base_x + 2*np.sin(t)
                    y_vals = base_y + 1*np.cos(t)
                    scores = np.random.uniform(0.8, 0.95, 20)
                    
                    analyzer.smoothed_data[f'keypoint_{kpt_id}'] = {
                        'x': x_vals,
                        'y': y_vals,
                        'score': scores
                    }
                
                return analyzer
    
    def test_calculate_balance_metrics_success(self, analyzer_with_balance_data):
        """Test successful balance metrics calculation"""
        analyzer = analyzer_with_balance_data
        
        result = analyzer.calculate_balance_metrics()
        
        assert isinstance(result, dict)
        assert hasattr(analyzer, 'balance_metrics')
        assert hasattr(analyzer, 'com_trajectory')
        assert len(result) > 0
        
        # Check expected metrics
        expected_metrics = ['CoM Stability X', 'CoM Stability Y', 'CoM Velocity Mean', 'CoM Velocity Std']
        for metric in expected_metrics:
            if metric in result:
                assert isinstance(result[metric], (float, np.floating))
    
    def test_calculate_balance_metrics_missing_keypoints(self):
        """Test balance calculation with missing keypoints"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200]],
                            "keypoint_scores": [0.9]
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock minimal keypoint data
                analyzer.smoothed_data = {
                    'keypoint_11': {'x': np.array([85]), 'y': np.array([200]), 'score': np.array([0.9])},
                    'keypoint_12': {'x': np.array([115]), 'y': np.array([200]), 'score': np.array([0.9])}
                }
                
                result = analyzer.calculate_balance_metrics()
                
                # Should fallback to hip midpoint
                assert isinstance(result, dict)


class TestReportGeneration:
    """Test analysis report generation methods"""
    
    @pytest.fixture
    def full_analyzer(self):
        """Create analyzer with all data for report generation"""
        data = {
            "meta_info": {"dataset_name": "test"},
            "instance_info": [
                {
                    "frame_id": i,
                    "instances": [
                        {
                            "keypoints": [[100 + i, 200 + i] for _ in range(17)],
                            "keypoint_scores": [0.9 for _ in range(17)]
                        }
                    ]
                } for i in range(1, 11)
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Mock all required data
                analyzer.smoothed_data = {}
                for i in range(17):
                    analyzer.smoothed_data[f'keypoint_{i}'] = {
                        'x': np.random.uniform(50, 150, 10),
                        'y': np.random.uniform(50, 250, 10),
                        'score': np.random.uniform(0.7, 0.9, 10)
                    }
                
                # Mock analysis results
                analyzer.joint_angles = pd.DataFrame({
                    'Right Elbow': np.random.uniform(90, 180, 10),
                    'Left Elbow': np.random.uniform(90, 180, 10)
                })
                
                analyzer.key_frames = [(1, 0), (5, 1), (10, 2)]
                analyzer.movement_smoothness = {'Right Wrist': 0.1, 'Left Wrist': 0.12}
                analyzer.symmetry_metrics = {'Left Shoulder - Right Shoulder': 5.2}
                analyzer.balance_metrics = {'CoM Stability X': 2.1, 'CoM Stability Y': 1.8}
                analyzer.com_trajectory = np.random.rand(10, 2)
                
                return analyzer
    
    def test_generate_analysis_report_success(self, full_analyzer, temp_output_dir):
        """Test successful analysis report generation"""
        analyzer = full_analyzer
        
        with patch('ml_pipeline.results_analysis.plt.figure'):
            with patch('ml_pipeline.results_analysis.plt.savefig'):
                with patch('ml_pipeline.results_analysis.plt.close'):
                    result = analyzer.generate_analysis_report(temp_output_dir)
                    
                    assert result == temp_output_dir
                    assert os.path.exists(temp_output_dir)
    
    def test_create_text_report(self, full_analyzer, temp_output_dir):
        """Test text report creation"""
        analyzer = full_analyzer
        
        analyzer._create_text_report(temp_output_dir)
        
        report_path = os.path.join(temp_output_dir, "analysis_report.txt")
        assert os.path.exists(report_path)
        
        with open(report_path, 'r') as f:
            content = f.read()
            assert "Baduanjin Movement Analysis Report" in content
            assert "Key Poses Detected" in content
            assert "Movement Smoothness" in content
    
    def test_visualize_key_poses_without_video(self, full_analyzer, temp_output_dir):
        """Test key poses visualization without video"""
        analyzer = full_analyzer
        
        with patch('ml_pipeline.results_analysis.plt.figure'):
            with patch('ml_pipeline.results_analysis.plt.savefig') as mock_savefig:
                with patch('ml_pipeline.results_analysis.plt.close'):
                    output_path = os.path.join(temp_output_dir, "test_poses.png")
                    result = analyzer.visualize_key_poses(output_path)
                    
                    assert result == output_path
                    mock_savefig.assert_called_once()
    
    def test_visualize_key_poses_with_video(self, full_analyzer, temp_output_dir):
        """Test key poses visualization with video"""
        analyzer = full_analyzer
        analyzer.video_path = "test_video.mp4"
        
        with patch('os.path.exists', return_value=True):
            with patch('cv2.VideoCapture') as mock_cap_class:
                mock_cap = Mock()
                mock_cap.get.return_value = 100  # Total frames
                mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
                mock_cap_class.return_value = mock_cap
                
                with patch('ml_pipeline.results_analysis.plt.figure'):
                    with patch('ml_pipeline.results_analysis.plt.savefig') as mock_savefig:
                        with patch('ml_pipeline.results_analysis.plt.close'):
                            output_path = os.path.join(temp_output_dir, "test_poses.png")
                            result = analyzer.visualize_key_poses(output_path)
                            
                            assert result == output_path
                            mock_savefig.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_smoothing_with_insufficient_frames(self):
        """Test smoothing with too few frames"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200]],
                            "keypoint_scores": [0.9]
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Should handle single frame gracefully
                assert hasattr(analyzer, 'smoothed_data')
                assert len(analyzer.smoothed_data) > 0
    
    def test_analysis_with_no_valid_data(self):
        """Test analysis methods with no valid data"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[0, 0]],
                            "keypoint_scores": [0.1]  # Very low confidence
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Set all scores to low values
                for key in analyzer.smoothed_data:
                    analyzer.smoothed_data[key]['score'] = np.array([0.1])
                
                # Should handle low confidence gracefully
                smoothness = analyzer.analyze_movement_smoothness()
                symmetry = analyzer.analyze_movement_symmetry()
                
                assert isinstance(smoothness, dict)
                assert isinstance(symmetry, dict)
    
    def test_print_keypoint_info(self):
        """Test keypoint information printing"""
        data = {
            "meta_info": {},
            "instance_info": [
                {
                    "frame_id": 1,
                    "instances": [
                        {
                            "keypoints": [[100, 200]],
                            "keypoint_scores": [0.9]
                        }
                    ]
                }
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Should not raise any exceptions
                analyzer.print_keypoint_info()


class TestIntegrationScenarios:
    """Test realistic usage scenarios"""
    
    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow"""
        # Create realistic test data
        data = {
            "meta_info": {
                "dataset_name": "baduanjin_test",
                "keypoint_info": {"keypoint_0": "nose"}
            },
            "instance_info": []
        }
        
        # Generate 50 frames of realistic pose data
        for frame_id in range(1, 51):
            instance = {
                "frame_id": frame_id,
                "instances": [
                    {
                        "keypoints": [[100 + np.sin(frame_id/10)*10, 200 + np.cos(frame_id/10)*5] for _ in range(17)],
                        "keypoint_scores": [np.random.uniform(0.7, 0.95) for _ in range(17)]
                    }
                ]
            }
            data["instance_info"].append(instance)
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                
                # Run complete analysis
                joint_angles = analyzer.calculate_joint_angles()
                key_poses = analyzer.identify_key_poses()
                smoothness = analyzer.analyze_movement_smoothness()
                symmetry = analyzer.analyze_movement_symmetry()
                balance = analyzer.calculate_balance_metrics()
                
                # Verify all analyses completed
                assert isinstance(joint_angles, pd.DataFrame)
                assert isinstance(key_poses, list)
                assert isinstance(smoothness, dict)
                assert isinstance(symmetry, dict)
                assert isinstance(balance, dict)
                
                # Check data consistency
                assert len(joint_angles) == 50
                assert len(key_poses) <= 8
    
    def test_memory_efficiency_large_dataset(self):
        """Test memory efficiency with large dataset"""
        # Simulate large dataset (1000 frames)
        data = {
            "meta_info": {},
            "instance_info": []
        }
        
        # Add many frames
        for frame_id in range(1, 101):  # 100 frames for testing
            instance = {
                "frame_id": frame_id,
                "instances": [
                    {
                        "keypoints": [[100, 200] for _ in range(17)],
                        "keypoint_scores": [0.9 for _ in range(17)]
                    }
                ]
            }
            data["instance_info"].append(instance)
        
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            with patch('ml_pipeline.results_analysis.plt'):
                # Should handle large dataset without memory errors
                analyzer = BaduanjinAnalyzer("test.json")
                
                assert len(analyzer.pose_df) == 100
                assert hasattr(analyzer, 'smoothed_data')


# Helper function to run tests
if __name__ == "__main__":
    print("Running results analysis unit tests...")
    
    # Quick test of core functionality
    test_data = {
        "meta_info": {},
        "instance_info": [
            {
                "frame_id": 1,
                "instances": [
                    {
                        "keypoints": [[100, 200]],
                        "keypoint_scores": [0.9]
                    }
                ]
            }
        ]
    }
    
    try:
        with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
            with patch('ml_pipeline.results_analysis.plt'):
                analyzer = BaduanjinAnalyzer("test.json")
                print("Basic initialization test passed!")
    except Exception as e:
        print(f"Basic test failed: {e}")
    
    print("Run with pytest for full test suite.")
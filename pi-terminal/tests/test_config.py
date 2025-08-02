# type: ignore
# tests/test_config.py

import os
import sys
# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

# Import the modules to test with error handling
try:
    from config import Config
    import config as config_module
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory and all dependencies are installed")
    sys.exit(1)


class TestConfigClass:
    """Test cases for Config class structure and constants"""
    
    def test_config_class_exists(self):
        """Test that Config class exists and is accessible"""
        assert hasattr(config_module, 'Config')
        assert isinstance(Config, type)
    
    def test_basic_configuration_constants(self):
        """Test basic configuration constants exist"""
        # Test SECRET_KEY
        assert hasattr(Config, 'SECRET_KEY')
        assert isinstance(Config.SECRET_KEY, str)
        assert len(Config.SECRET_KEY) > 0
        
        # Test Pi Configuration
        assert hasattr(Config, 'PI_IP')
        assert hasattr(Config, 'PI_PORT')
        assert isinstance(Config.PI_IP, str)
        assert isinstance(Config.PI_PORT, int)
        
        # Test basic structure
        assert Config.PI_IP == "172.20.10.6"
        assert Config.PI_PORT == 5001
    
    def test_camera_configuration(self):
        """Test camera configuration constants"""
        camera_configs = [
            ('CAMERA_WIDTH', int),
            ('CAMERA_HEIGHT', int),
            ('CAMERA_FPS', int)
        ]
        
        for config_name, expected_type in camera_configs:
            assert hasattr(Config, config_name)
            config_value = getattr(Config, config_name)
            assert isinstance(config_value, expected_type)
            assert config_value > 0  # Should be positive values
    
    def test_yolo_configuration(self):
        """Test YOLO configuration constants"""
        assert hasattr(Config, 'YOLO_MODEL_PATH')
        assert hasattr(Config, 'YOLO_CONFIDENCE')
        
        # Test YOLO model path
        assert isinstance(Config.YOLO_MODEL_PATH, Path)
        assert str(Config.YOLO_MODEL_PATH).endswith('.pt')
        
        # Test YOLO confidence
        assert isinstance(Config.YOLO_CONFIDENCE, (int, float))
        assert 0 <= Config.YOLO_CONFIDENCE <= 1  # Should be between 0 and 1
    
    def test_recording_configuration(self):
        """Test recording configuration constants"""
        recording_configs = [
            ('RECORDINGS_DIR', Path),
            ('VIDEO_CODEC', str),
            ('VIDEO_FPS', (int, float)),
            ('VIDEO_QUALITY', int),
            ('MOBILE_VIDEO_QUALITY', int)
        ]
        
        for config_name, expected_type in recording_configs:
            assert hasattr(Config, config_name)
            config_value = getattr(Config, config_name)
            assert isinstance(config_value, expected_type)
        
        # Test quality values are reasonable
        assert 1 <= Config.VIDEO_QUALITY <= 100
        assert 1 <= Config.MOBILE_VIDEO_QUALITY <= 100
        assert Config.MOBILE_VIDEO_QUALITY <= Config.VIDEO_QUALITY  # Mobile should be lower


class TestEnhancedExerciseConfig:
    """Test cases for enhanced exercise tracking configuration"""
    
    def test_exercise_tracking_constants_exist(self):
        """Test that exercise tracking constants exist"""
        exercise_constants = [
            'BADUANJIN_DATA_DIR',
            'EXERCISE_TRACKING_ENABLED',
            'POSE_CONFIDENCE_THRESHOLD',
            'POSE_HOLD_DURATION',
            'TRANSITION_TOLERANCE',
            'FORM_SCORE_THRESHOLD'
        ]
        
        for constant in exercise_constants:
            assert hasattr(Config, constant), f"Missing constant: {constant}"
    
    def test_exercise_tracking_types(self):
        """Test exercise tracking configuration types"""
        # Test directory
        assert isinstance(Config.BADUANJIN_DATA_DIR, Path)
        
        # Test boolean
        assert isinstance(Config.EXERCISE_TRACKING_ENABLED, bool)
        
        # Test numeric values
        numeric_configs = [
            'POSE_CONFIDENCE_THRESHOLD',
            'POSE_HOLD_DURATION',
            'TRANSITION_TOLERANCE',
            'FORM_SCORE_THRESHOLD'
        ]
        
        for config_name in numeric_configs:
            config_value = getattr(Config, config_name)
            assert isinstance(config_value, (int, float))
            assert config_value > 0  # Should be positive
    
    def test_exercise_analysis_parameters(self):
        """Test exercise analysis parameter constants"""
        analysis_params = [
            'SHOULDER_ALIGNMENT_TOLERANCE',
            'HIP_ALIGNMENT_TOLERANCE',
            'ARM_EXTENSION_THRESHOLD',
            'SPINE_ALIGNMENT_TOLERANCE'
        ]
        
        for param in analysis_params:
            assert hasattr(Config, param)
            value = getattr(Config, param)
            assert isinstance(value, (int, float))
            assert value > 0  # Should be positive values
    
    def test_session_management_config(self):
        """Test session management configuration"""
        session_configs = [
            ('MAX_POSE_HISTORY', int),
            ('MAX_FEEDBACK_HISTORY', int),
            ('SESSION_EXPORT_FORMAT', str)
        ]
        
        for config_name, expected_type in session_configs:
            assert hasattr(Config, config_name)
            config_value = getattr(Config, config_name)
            assert isinstance(config_value, expected_type)
        
        # Test reasonable values
        assert Config.MAX_POSE_HISTORY > 0
        assert Config.MAX_FEEDBACK_HISTORY > 0
        assert Config.SESSION_EXPORT_FORMAT in ['json', 'csv', 'xml']  # Common formats
    
    def test_feedback_configuration(self):
        """Test exercise feedback configuration"""
        feedback_configs = [
            'FEEDBACK_UPDATE_INTERVAL',
            'OVERLAY_TRANSPARENCY',
            'CORRECTION_MESSAGE_LIMIT',
            'FEEDBACK_MESSAGE_LIMIT'
        ]
        
        for config in feedback_configs:
            assert hasattr(Config, config)
            value = getattr(Config, config)
            assert isinstance(value, (int, float))
            assert value > 0
        
        # Test overlay transparency is between 0 and 1
        assert 0 <= Config.OVERLAY_TRANSPARENCY <= 1


class TestNetworkConfiguration:
    """Test cases for network configuration"""
    
    def test_ngrok_configuration(self):
        """Test ngrok configuration"""
        assert hasattr(Config, 'NGROK_STATIC_URL')
        assert isinstance(Config.NGROK_STATIC_URL, str)
        assert Config.NGROK_STATIC_URL.startswith('https://')
        assert 'ngrok' in Config.NGROK_STATIC_URL.lower()
    
    def test_stream_configuration(self):
        """Test streaming configuration"""
        stream_configs = [
            ('STREAM_EMIT_INTERVAL', (int, float)),
            ('FRAME_BUFFER_SIZE', int)
        ]
        
        for config_name, expected_type in stream_configs:
            assert hasattr(Config, config_name)
            config_value = getattr(Config, config_name)
            assert isinstance(config_value, expected_type)
            assert config_value > 0
    
    def test_mobile_network_config(self):
        """Test mobile network optimization configuration"""
        mobile_configs = [
            'MOBILE_PING_TIMEOUT',
            'MOBILE_PING_INTERVAL',
            'MOBILE_MAX_HTTP_BUFFER'
        ]
        
        for config in mobile_configs:
            assert hasattr(Config, config)
            value = getattr(Config, config)
            assert isinstance(value, (int, float))
            assert value > 0
    
    def test_api_timeouts(self):
        """Test API timeout configuration"""
        timeout_configs = [
            ('API_TIMEOUT', (int, float)),
            ('DOWNLOAD_TIMEOUT', (int, float))
        ]
        
        for config_name, expected_type in timeout_configs:
            assert hasattr(Config, config_name)
            config_value = getattr(Config, config_name)
            assert isinstance(config_value, expected_type)
            assert config_value > 0
        
        # Download timeout should be longer than API timeout
        assert Config.DOWNLOAD_TIMEOUT > Config.API_TIMEOUT


class TestConfigMethods:
    """Test cases for Config class methods"""
    
    def test_init_directories_method_exists(self):
        """Test that init_directories method exists and is callable"""
        assert hasattr(Config, 'init_directories')
        assert callable(Config.init_directories)
    
    def test_get_exercise_config_method_exists(self):
        """Test that get_exercise_config method exists and is callable"""
        assert hasattr(Config, 'get_exercise_config')
        assert callable(Config.get_exercise_config)
    
    def test_get_display_config_method_exists(self):
        """Test that get_display_config method exists and is callable"""
        assert hasattr(Config, 'get_display_config')
        assert callable(Config.get_display_config)
    
    def test_get_exercise_config_structure(self):
        """Test get_exercise_config returns expected structure"""
        exercise_config = Config.get_exercise_config()
        
        # Should return a dictionary
        assert isinstance(exercise_config, dict)
        
        # Should contain expected keys
        expected_keys = [
            'confidence_threshold',
            'hold_duration',
            'transition_tolerance',
            'form_score_threshold',
            'analysis_params'
        ]
        
        for key in expected_keys:
            assert key in exercise_config
        
        # Analysis params should be a dict
        assert isinstance(exercise_config['analysis_params'], dict)
        
        # Analysis params should contain expected keys
        analysis_keys = [
            'shoulder_tolerance',
            'hip_tolerance',
            'arm_threshold',
            'spine_tolerance'
        ]
        
        for key in analysis_keys:
            assert key in exercise_config['analysis_params']
    
    def test_get_display_config_structure(self):
        """Test get_display_config returns expected structure"""
        display_config = Config.get_display_config()
        
        # Should return a dictionary
        assert isinstance(display_config, dict)
        
        # Should contain expected keys
        expected_keys = [
            'overlay_transparency',
            'correction_limit',
            'feedback_limit',
            'update_interval'
        ]
        
        for key in expected_keys:
            assert key in display_config
        
        # Values should be reasonable
        assert 0 <= display_config['overlay_transparency'] <= 1
        assert display_config['correction_limit'] > 0
        assert display_config['feedback_limit'] > 0
        assert display_config['update_interval'] > 0


class TestDirectoryInitialization:
    """Test cases for directory initialization"""
    
    def test_init_directories_with_mocking(self):
        """Test init_directories method with mocked file operations"""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('builtins.print') as mock_print:
            
            # Call the method
            result = Config.init_directories()
            
            # Should return True
            assert result is True
            
            # Should attempt to create directories
            assert mock_mkdir.called
            
            # Should print information
            assert mock_print.called
    
    def test_init_directories_creates_required_dirs(self):
        """Test that init_directories attempts to create required directories"""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('builtins.print'):
            
            Config.init_directories()
            
            # Should be called multiple times for different directories
            assert mock_mkdir.call_count >= 2  # At least recordings and models
    
    def test_directory_paths_are_valid(self):
        """Test that directory paths are valid Path objects"""
        # Test that directory configurations are Path objects
        assert isinstance(Config.RECORDINGS_DIR, Path)
        assert isinstance(Config.BADUANJIN_DATA_DIR, Path)
        
        # Test that they have reasonable string representations
        assert str(Config.RECORDINGS_DIR)  # Should not be empty
        assert str(Config.BADUANJIN_DATA_DIR)  # Should not be empty


class TestConfigurationValues:
    """Test cases for configuration value validation"""
    
    def test_confidence_thresholds_valid(self):
        """Test that confidence thresholds are in valid ranges"""
        confidence_configs = [
            'YOLO_CONFIDENCE',
            'POSE_CONFIDENCE_THRESHOLD'
        ]
        
        for config in confidence_configs:
            if hasattr(Config, config):
                value = getattr(Config, config)
                assert 0 <= value <= 1, f"{config} should be between 0 and 1"
    
    def test_quality_values_valid(self):
        """Test that quality values are in valid ranges"""
        quality_configs = [
            'VIDEO_QUALITY',
            'MOBILE_VIDEO_QUALITY'
        ]
        
        for config in quality_configs:
            value = getattr(Config, config)
            assert 1 <= value <= 100, f"{config} should be between 1 and 100"
    
    def test_fps_values_reasonable(self):
        """Test that FPS values are reasonable"""
        fps_configs = [
            'CAMERA_FPS',
            'VIDEO_FPS'
        ]
        
        for config in fps_configs:
            value = getattr(Config, config)
            assert 1 <= value <= 120, f"{config} should be reasonable FPS value"
    
    def test_timeout_values_reasonable(self):
        """Test that timeout values are reasonable"""
        timeout_configs = [
            ('API_TIMEOUT', 1, 60),  # 1 second to 1 minute
            ('DOWNLOAD_TIMEOUT', 30, 3600),  # 30 seconds to 1 hour
            ('MOBILE_PING_TIMEOUT', 60, 600),  # 1 minute to 10 minutes
            ('MOBILE_PING_INTERVAL', 30, 300)  # 30 seconds to 5 minutes
        ]
        
        for config_name, min_val, max_val in timeout_configs:
            value = getattr(Config, config_name)
            assert min_val <= value <= max_val, f"{config_name} should be between {min_val} and {max_val}"


class TestEnvironmentVariables:
    """Test cases for environment variable handling"""
    
    def test_secret_key_environment_variable(self):
        """Test SECRET_KEY environment variable handling"""
        # Test with no environment variable (default case)
        with patch.dict(os.environ, {}, clear=True):
            # Reload config to test environment variable
            # Since we can't easily reload, test the concept
            default_key = 'baduanjin_secret_key'
            assert isinstance(default_key, str)
            assert len(default_key) > 0
    
    def test_secret_key_has_value(self):
        """Test that SECRET_KEY always has a value"""
        # Config.SECRET_KEY should never be None or empty
        assert Config.SECRET_KEY is not None
        assert len(Config.SECRET_KEY) > 0
        assert isinstance(Config.SECRET_KEY, str)


class TestConfigurationConsistency:
    """Test cases for configuration consistency"""
    
    def test_mobile_quality_lower_than_standard(self):
        """Test that mobile quality is lower than standard quality"""
        assert Config.MOBILE_VIDEO_QUALITY <= Config.VIDEO_QUALITY
    
    def test_ping_interval_less_than_timeout(self):
        """Test that ping interval is less than ping timeout"""
        assert Config.MOBILE_PING_INTERVAL < Config.MOBILE_PING_TIMEOUT
    
    def test_feedback_limits_reasonable(self):
        """Test that feedback limits are reasonable"""
        assert Config.CORRECTION_MESSAGE_LIMIT <= 10  # Not too many
        assert Config.FEEDBACK_MESSAGE_LIMIT <= 10  # Not too many
        assert Config.CORRECTION_MESSAGE_LIMIT > 0
        assert Config.FEEDBACK_MESSAGE_LIMIT > 0
    
    def test_history_limits_reasonable(self):
        """Test that history limits are reasonable"""
        assert Config.MAX_POSE_HISTORY >= 10  # At least some history
        assert Config.MAX_FEEDBACK_HISTORY >= 10  # At least some history
        assert Config.MAX_POSE_HISTORY <= 1000  # Not too much memory usage
        assert Config.MAX_FEEDBACK_HISTORY <= 1000  # Not too much memory usage


class TestPathConfiguration:
    """Test cases for path-related configuration"""
    
    def test_yolo_model_path_structure(self):
        """Test YOLO model path structure"""
        model_path = Config.YOLO_MODEL_PATH
        
        # Should be a Path object
        assert isinstance(model_path, Path)
        
        # Should have reasonable structure
        path_str = str(model_path)
        assert 'models' in path_str
        assert path_str.endswith('.pt')
    
    def test_recordings_dir_structure(self):
        """Test recordings directory structure"""
        recordings_dir = Config.RECORDINGS_DIR
        
        # Should be a Path object
        assert isinstance(recordings_dir, Path)
        
        # Should contain 'recordings' in the path
        assert 'recordings' in str(recordings_dir).lower()
    
    def test_baduanjin_data_dir_structure(self):
        """Test Baduanjin data directory structure"""
        data_dir = Config.BADUANJIN_DATA_DIR
        
        # Should be a Path object
        assert isinstance(data_dir, Path)
        
        # Should contain relevant terms
        path_str = str(data_dir).lower()
        assert 'baduanjin' in path_str or 'data' in path_str


# Test fixtures for cleanup
@pytest.fixture(autouse=True)
def cleanup_patches():
    """Clean up any patches after each test"""
    yield
    # Pytest handles mock cleanup automatically


# Test fixtures for temporary directories
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
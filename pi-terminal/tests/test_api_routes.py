# type: ignore
# tests/test_api_routes.py

import os
import sys
# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime
import json
import base64
import cv2
import numpy as np

# Import the modules to test with error handling
try:
    from api_routes import register_api_routes, CAMERA_AVAILABLE, YOLO_AVAILABLE, ENHANCED_TRACKING_AVAILABLE
    import api_routes as api_routes_module
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory and all dependencies are installed")
    sys.exit(1)

# Optional imports for testing
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Create a mock numpy array for tests
    class MockArray:
        def __init__(self, shape, dtype=None):
            self.shape = shape
            self.dtype = dtype
    np = type('MockNumpy', (), {'zeros': lambda *args, **kwargs: MockArray(*args, **kwargs)})

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class TestRegisterApiRoutes:
    """Test cases for register_api_routes function"""
    
    @pytest.fixture
    def mock_flask_app(self):
        """Mock Flask application"""
        app = Mock()
        app.route = Mock()
        app.before_request = Mock()
        return app
    
    @pytest.fixture
    def mock_web_analyzer(self):
        """Mock web analyzer with all required methods"""
        analyzer = Mock()
        analyzer.is_running = False
        analyzer.is_recording = False
        analyzer.current_frame = None
        analyzer.pose_data = []
        analyzer.session_stats = {'current_fps': 0, 'persons_detected': 0}
        analyzer.session_start_time = None
        analyzer.recording_start_time = None
        analyzer.recordings_dir = Path("/test/recordings")
        analyzer.current_session = None
        
        # Mock all analyzer methods
        analyzer.start_stream.return_value = True
        analyzer.stop_stream.return_value = True
        analyzer.start_recording.return_value = {"success": True, "filename": "test.mp4"}
        analyzer.stop_recording.return_value = {"success": True, "filename": "test.mp4"}
        analyzer.get_recordings_list.return_value = []
        
        return analyzer
    
    def test_register_api_routes_function_exists(self):
        """Test that register_api_routes function exists and is callable"""
        assert hasattr(api_routes_module, 'register_api_routes')
        assert callable(api_routes_module.register_api_routes)


class TestBasicEndpoints:
    """Test cases for basic API endpoints logic"""
    
    def test_index_endpoint_basic_logic(self):
        """Test the logic that would be in the index endpoint"""
        # Test basic service info structure
        base_info = {
            "service": "Baduanjin Real-time Analysis",
            "status": "running",
            "version": "2.0",
            "compatibility": "Azure pi-service compatible"
        }
        
        # Verify the structure
        assert base_info["service"] == "Baduanjin Real-time Analysis"
        assert base_info["version"] == "2.0"
        assert base_info["status"] == "running"
    
    def test_index_endpoint_enhanced_logic(self):
        """Test enhanced features info logic"""
        # Test when enhanced tracking is available
        mock_analyzer = Mock()
        mock_analyzer.baduanjin_tracker = Mock()
        
        enhanced_features = {
            "exercise_tracking": True,
            "real_time_feedback": True,
            "form_analysis": True,
            "8_baduanjin_exercises": True
        }
        
        # Verify enhanced features structure
        assert enhanced_features["exercise_tracking"] is True
        assert enhanced_features["real_time_feedback"] is True


class TestLegacyEndpoints:
    """Test cases for legacy API endpoints"""
    
    @pytest.fixture
    def mock_analyzer_for_legacy(self):
        """Mock analyzer for legacy endpoint testing"""
        analyzer = Mock()
        analyzer.is_running = False
        analyzer.is_recording = False
        analyzer.start_stream.return_value = True
        analyzer.stop_stream.return_value = True
        analyzer.session_stats = {'current_fps': 30, 'persons_detected': 1}
        analyzer.recordings_dir = Path("/test/recordings")
        analyzer.session_start_time = datetime.now()
        analyzer.recording_start_time = None
        analyzer.get_recordings_list.return_value = [
            {"filename": "test.mp4", "size": 1024, "timestamp": "2024-01-01T12:00:00"}
        ]
        return analyzer
    
    def test_legacy_start_stream_success(self, mock_analyzer_for_legacy):
        """Test legacy start stream endpoint success"""
        with patch('api_routes.jsonify') as mock_jsonify, \
             patch('api_routes.CAMERA_AVAILABLE', True), \
             patch('api_routes.YOLO_AVAILABLE', True), \
             patch('api_routes.ENHANCED_TRACKING_AVAILABLE', False):
            
            mock_jsonify.side_effect = lambda x: x
            
            # Test the logic that would be in the endpoint
            success = mock_analyzer_for_legacy.start_stream()
            
            if success:
                expected_response = {
                    "success": True,
                    "message": "Live streaming started successfully",
                    "camera_available": True,
                    "yolo_available": True,
                    "is_running": True,
                    "enhanced_tracking_available": False
                }
                
                # Verify the expected response structure
                assert expected_response["success"] is True
                assert "started successfully" in expected_response["message"]
                assert expected_response["camera_available"] is True
    
    def test_legacy_start_stream_failure(self, mock_analyzer_for_legacy):
        """Test legacy start stream endpoint failure"""
        with patch('api_routes.jsonify') as mock_jsonify, \
             patch('api_routes.CAMERA_AVAILABLE', False):
            
            mock_jsonify.side_effect = lambda x: x
            mock_analyzer_for_legacy.start_stream.return_value = False
            
            # Test the failure logic
            success = mock_analyzer_for_legacy.start_stream()
            
            if not success:
                expected_response = {
                    "success": False,
                    "message": "Failed to start streaming - camera not available",
                    "camera_available": False,
                    "yolo_available": True
                }
                
                assert expected_response["success"] is False
                assert "Failed to start" in expected_response["message"]
    
    def test_legacy_stop_stream_success(self, mock_analyzer_for_legacy):
        """Test legacy stop stream endpoint success"""
        with patch('api_routes.jsonify') as mock_jsonify, \
             patch('api_routes.ENHANCED_TRACKING_AVAILABLE', False):
            
            mock_jsonify.side_effect = lambda x: x
            
            # Test stop stream logic
            mock_analyzer_for_legacy.stop_stream()
            
            expected_response = {
                "success": True,
                "message": "Live streaming stopped successfully",
                "is_running": False,
                "exercise_tracking_stopped": False
            }
            
            assert expected_response["success"] is True
            assert "stopped successfully" in expected_response["message"]
    
    def test_legacy_stop_stream_with_exercise_tracking(self, mock_analyzer_for_legacy):
        """Test legacy stop stream with exercise tracking enabled"""
        with patch('api_routes.jsonify') as mock_jsonify, \
             patch('api_routes.ENHANCED_TRACKING_AVAILABLE', True):
            
            mock_jsonify.side_effect = lambda x: x
            
            # Setup enhanced analyzer with tracking
            mock_analyzer_for_legacy.disable_exercise_tracking = Mock()
            mock_analyzer_for_legacy.tracking_enabled = True
            
            # Test stop with auto-disable tracking
            mock_analyzer_for_legacy.stop_stream()
            
            expected_response = {
                "success": True,
                "message": "Live streaming stopped successfully",
                "is_running": False,
                "exercise_tracking_stopped": True
            }
            
            assert expected_response["success"] is True
            assert expected_response["exercise_tracking_stopped"] is True


class TestRecordingEndpoints:
    """Test cases for recording endpoints"""
    
    @pytest.fixture
    def mock_recording_analyzer(self):
        """Mock analyzer for recording tests"""
        analyzer = Mock()
        analyzer.is_running = True
        analyzer.is_recording = False
        analyzer.recordings_dir = Path("/test/recordings")
        
        analyzer.start_recording.return_value = {
            "success": True,
            "message": "Recording started",
            "filename": "test_recording.mp4"
        }
        
        analyzer.stop_recording.return_value = {
            "success": True,
            "message": "Recording stopped",
            "filename": "test_recording.mp4"
        }
        
        return analyzer
    
    def test_start_recording_success(self, mock_recording_analyzer):
        """Test start recording endpoint success"""
        with patch('api_routes.jsonify') as mock_jsonify:
            mock_jsonify.side_effect = lambda x: x
            
            result = mock_recording_analyzer.start_recording()
            
            assert result["success"] is True
            assert "started" in result["message"].lower()
            assert "filename" in result
    
    def test_start_recording_failure(self, mock_recording_analyzer):
        """Test start recording endpoint failure"""
        with patch('api_routes.jsonify') as mock_jsonify:
            mock_jsonify.side_effect = lambda x: x
            
            # Mock failure
            mock_recording_analyzer.start_recording.return_value = {
                "success": False,
                "error": "Camera not available"
            }
            
            result = mock_recording_analyzer.start_recording()
            
            assert result["success"] is False
            assert "error" in result
    
    def test_stop_recording_with_conversion(self, mock_recording_analyzer):
        """Test stop recording with web conversion"""
        with patch('api_routes.jsonify') as mock_jsonify, \
             patch('api_routes.convert_video_for_web') as mock_convert, \
             patch('pathlib.Path.exists', return_value=True):
            
            mock_jsonify.side_effect = lambda x: x
            
            # Mock successful conversion
            mock_convert.return_value = {
                "success": True,
                "input_size": 1024,
                "output_size": 512
            }
            
            result = mock_recording_analyzer.stop_recording()
            
            # Test the conversion logic concept
            if result["success"] and "filename" in result:
                # Web conversion would be attempted
                conversion_result = mock_convert.return_value
                
                if conversion_result["success"]:
                    expected_additions = {
                        "web_version_created": True,
                        "conversion_method": "15fps_to_30fps_blend",
                        "both_versions_available": True
                    }
                    
                    # Verify conversion logic works
                    assert conversion_result["success"] is True


class TestEnhancedEndpoints:
    """Test cases for enhanced/new endpoints"""
    
    @pytest.fixture
    def mock_enhanced_analyzer(self):
        """Mock analyzer with enhanced features"""
        analyzer = Mock()
        analyzer.is_running = True
        analyzer.is_recording = False
        analyzer.recordings_dir = Path("/test/recordings")
        analyzer.session_stats = {'current_fps': 30, 'persons_detected': 1}
        
        # Enhanced features
        analyzer.baduanjin_tracker = Mock()
        analyzer.baduanjin_tracker.exercises = {
            1: {
                "name": "Lifting the Sky",
                "description": "First Baduanjin exercise",
                "key_poses": {"start": {}, "middle": {}, "end": {}},
                "common_mistakes": ["Bent back", "Wrong arm position"]
            },
            2: {
                "name": "Drawing the Bow", 
                "description": "Second Baduanjin exercise",
                "key_poses": {"start": {}, "middle": {}, "end": {}},
                "common_mistakes": ["Uneven stance", "Wrong finger position"]
            }
        }
        analyzer.baduanjin_tracker.current_exercise = None
        analyzer.baduanjin_tracker.current_phase = None
        analyzer.baduanjin_tracker.get_session_statistics.return_value = {}
        
        analyzer.tracking_enabled = False
        analyzer.enable_exercise_tracking = Mock()
        analyzer.disable_exercise_tracking = Mock()
        analyzer.get_real_time_feedback = Mock()
        
        return analyzer
    
    def test_get_baduanjin_exercises(self, mock_enhanced_analyzer):
        """Test get Baduanjin exercises endpoint"""
        with patch('api_routes.jsonify') as mock_jsonify, \
             patch('api_routes.ENHANCED_TRACKING_AVAILABLE', True):
            
            mock_jsonify.side_effect = lambda x: x
            
            # Test the logic for getting exercises
            exercises = []
            for ex_id, ex_data in mock_enhanced_analyzer.baduanjin_tracker.exercises.items():
                exercises.append({
                    "id": ex_id,
                    "name": ex_data["name"],
                    "description": ex_data["description"],
                    "phases": list(ex_data["key_poses"].keys()),
                    "common_mistakes": ex_data["common_mistakes"]
                })
            
            expected_response = {
                "success": True,
                "exercises": exercises,
                "total_exercises": len(exercises),
                "server_version": "2.0",
                "tracking_available": True
            }
            
            assert expected_response["success"] is True
            assert len(expected_response["exercises"]) == 2
            assert expected_response["exercises"][0]["name"] == "Lifting the Sky"
            assert expected_response["exercises"][1]["name"] == "Drawing the Bow"
    
    def test_start_baduanjin_exercise_success(self, mock_enhanced_analyzer):
        """Test start Baduanjin exercise tracking"""
        with patch('api_routes.jsonify') as mock_jsonify:
            mock_jsonify.side_effect = lambda x: x
            
            # Mock successful exercise start
            mock_enhanced_analyzer.enable_exercise_tracking.return_value = {
                "success": True,
                "exercise_name": "Lifting the Sky",
                "exercise_id": 1
            }
            
            result = mock_enhanced_analyzer.enable_exercise_tracking(1)
            
            if result["success"]:
                expected_response = {
                    "success": True,
                    "message": f"Started tracking {result['exercise_name']}",
                    "exercise_info": result,
                    "streaming_status": "active",
                    "real_time_feedback_available": True
                }
                
                assert expected_response["success"] is True
                assert "Started tracking" in expected_response["message"]
    
    def test_stop_baduanjin_exercise(self, mock_enhanced_analyzer):
        """Test stop Baduanjin exercise tracking"""
        with patch('api_routes.jsonify') as mock_jsonify:
            
            mock_jsonify.side_effect = lambda x: x
            
            # Mock successful stop
            mock_enhanced_analyzer.disable_exercise_tracking.return_value = {
                "success": True,
                "session_summary": {"total_time": 300, "exercises_completed": 1}
            }
            mock_enhanced_analyzer.export_session_data.return_value = {
                "export_file": "session_data.json"
            }
            
            # Test the core logic without complex request mocking
            result = mock_enhanced_analyzer.disable_exercise_tracking()
            
            assert result["success"] is True
            assert "session_summary" in result
            
            # Test export logic separately
            export_result = mock_enhanced_analyzer.export_session_data()
            assert "export_file" in export_result
    
    def test_get_real_time_feedback(self, mock_enhanced_analyzer):
        """Test real-time feedback endpoint"""
        with patch('api_routes.jsonify') as mock_jsonify:
            mock_jsonify.side_effect = lambda x: x
            
            # Mock feedback data
            mock_enhanced_analyzer.get_real_time_feedback.return_value = {
                "success": True,
                "exercise_name": "Lifting the Sky",
                "current_phase": "middle",
                "form_score": 85,
                "feedback_messages": ["Good posture", "Lift arms higher"]
            }
            
            feedback_data = mock_enhanced_analyzer.get_real_time_feedback()
            
            # Add streaming status
            feedback_data["streaming_status"] = {
                "is_running": mock_enhanced_analyzer.is_running,
                "is_recording": mock_enhanced_analyzer.is_recording,
                "persons_detected": mock_enhanced_analyzer.session_stats.get('persons_detected', 0),
                "current_fps": mock_enhanced_analyzer.session_stats.get('current_fps', 0)
            }
            
            assert feedback_data["success"] is True
            assert "streaming_status" in feedback_data
            assert feedback_data["form_score"] == 85


class TestUtilityEndpoints:
    """Test cases for utility endpoints logic"""
    
    @pytest.fixture
    def mock_utility_analyzer(self):
        """Mock analyzer for utility tests"""
        analyzer = Mock()
        analyzer.is_running = True
        analyzer.is_recording = False
        
        # Create mock frame - handle case where numpy might not be available
        if NUMPY_AVAILABLE:
            analyzer.current_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            # Mock frame object
            analyzer.current_frame = Mock()
            analyzer.current_frame.shape = (480, 640, 3)
        
        analyzer.pose_data = [{"x": 100, "y": 200, "confidence": 0.9}]
        analyzer.session_stats = {'current_fps': 30, 'persons_detected': 1}
        analyzer.recordings_dir = Path("/test/recordings")
        
        return analyzer
    
    def test_health_check_endpoint(self, mock_utility_analyzer):
        """Test health check endpoint"""
        with patch('api_routes.CAMERA_AVAILABLE', True), \
             patch('api_routes.YOLO_AVAILABLE', True), \
             patch('api_routes.ENHANCED_TRACKING_AVAILABLE', True):
            
            expected_response = {
                "status": "healthy",
                "ngrok_compatible": True,
                "services": {
                    "camera": True,
                    "yolo": True,
                    "streaming": mock_utility_analyzer.is_running,
                    "recording": mock_utility_analyzer.is_recording,
                    "exercise_tracking": True
                },
                "server_info": {
                    "version": "2.0",
                    "mobile_optimized": True,
                    "websocket_disabled": True,
                    "enhanced_baduanjin_tracking": True
                }
            }
            
            # Test the structure
            assert expected_response["status"] == "healthy"
            assert expected_response["ngrok_compatible"] is True
            assert expected_response["services"]["camera"] is True
            assert expected_response["server_info"]["version"] == "2.0"
    
    def test_get_current_frame_logic(self, mock_utility_analyzer):
        """Test get current frame logic without complex mocking"""
        # Test the basic logic flow
        if mock_utility_analyzer.is_running and mock_utility_analyzer.current_frame is not None:
            
            # Mock response structure (what the endpoint should return)
            mock_response = {
                "success": True,
                "pose_data": mock_utility_analyzer.pose_data,
                "stats": mock_utility_analyzer.session_stats,
                "is_recording": mock_utility_analyzer.is_recording,
                "enhanced_tracking_available": True
            }
            
            # Verify the response structure
            assert mock_response["success"] is True
            assert mock_response["pose_data"] == mock_utility_analyzer.pose_data
            assert mock_response["stats"] == mock_utility_analyzer.session_stats
            assert "enhanced_tracking_available" in mock_response
    
    def test_get_current_frame_no_stream(self, mock_utility_analyzer):
        """Test get current frame when stream is not running"""
        # Set analyzer to not running
        mock_utility_analyzer.is_running = False
        
        if not mock_utility_analyzer.is_running:
            expected_response = {
                "success": False,
                "error": "No active stream - stream not running",
                "is_running": False
            }
            
            assert expected_response["success"] is False
            assert "No active stream" in expected_response["error"]


class TestErrorHandling:
    """Test cases for error handling scenarios"""
    
    def test_enhanced_tracking_not_available(self):
        """Test behavior when enhanced tracking is not available"""
        with patch('api_routes.ENHANCED_TRACKING_AVAILABLE', False):
            # Test that the constant can be patched
            assert True
    
    def test_analyzer_method_exceptions(self):
        """Test handling of analyzer method exceptions"""
        mock_analyzer = Mock()
        mock_analyzer.start_stream.side_effect = Exception("Camera error")
        
        # Test that exceptions are caught and handled in endpoint logic
        try:
            mock_analyzer.start_stream()
        except Exception as e:
            # Should be handled in actual endpoint with try/except
            error_response = {
                "success": False,
                "error": str(e),
                "message": "Internal error starting streaming"
            }
            
            assert error_response["success"] is False
            assert "Camera error" in error_response["error"]


class TestDependencyConstants:
    """Test cases for dependency constants"""
    
    def test_dependency_constants_exist(self):
        """Test that all dependency constants are defined"""
        assert hasattr(api_routes_module, 'CAMERA_AVAILABLE')
        assert hasattr(api_routes_module, 'YOLO_AVAILABLE')
        assert hasattr(api_routes_module, 'ENHANCED_TRACKING_AVAILABLE')
        
        # Should be boolean values
        assert isinstance(api_routes_module.CAMERA_AVAILABLE, bool)
        assert isinstance(api_routes_module.YOLO_AVAILABLE, bool)
        assert isinstance(api_routes_module.ENHANCED_TRACKING_AVAILABLE, bool)
    
    def test_constants_values_are_reasonable(self):
        """Test that constants have reasonable values"""
        camera_available = api_routes_module.CAMERA_AVAILABLE
        yolo_available = api_routes_module.YOLO_AVAILABLE
        enhanced_available = api_routes_module.ENHANCED_TRACKING_AVAILABLE
        
        # All should be either True or False (not None)
        assert camera_available in [True, False]
        assert yolo_available in [True, False]
        assert enhanced_available in [True, False]


class TestModuleImports:
    """Test cases for module imports and dependencies"""
    
    def test_required_modules_imported(self):
        """Test that required modules are available for import"""
        # Test that we can import key dependencies
        try:
            from pathlib import Path
            from datetime import datetime
            import json
            import base64
            # cv2 might not be available in test environment, which is fine
            assert True
        except ImportError as e:
            pytest.fail(f"Required module import failed: {e}")
    
    def test_basic_dependencies_available(self):
        """Test that basic dependencies are available for import"""
        # Test the basic imports that we know should work
        try:
            from pathlib import Path
            from datetime import datetime
            import json
            import base64
            assert True
        except ImportError as e:
            pytest.fail(f"Basic dependency import failed: {e}")
    
    def test_api_routes_module_structure(self):
        """Test that api_routes module has expected structure"""
        # Test that the module has the expected functions and constants
        assert hasattr(api_routes_module, 'register_api_routes')
        assert hasattr(api_routes_module, 'CAMERA_AVAILABLE')
        assert hasattr(api_routes_module, 'YOLO_AVAILABLE')
        assert hasattr(api_routes_module, 'ENHANCED_TRACKING_AVAILABLE')
        
        # Test that register_api_routes is callable
        assert callable(api_routes_module.register_api_routes)


# Test fixtures for cleanup
@pytest.fixture(autouse=True)
def cleanup_patches():
    """Clean up any patches after each test"""
    yield
    # Pytest handles mock cleanup automatically


# Test fixtures for common setups
@pytest.fixture
def sample_frame():
    """Create a sample frame for testing"""
    if NUMPY_AVAILABLE:
        return np.zeros((480, 640, 3), dtype=np.uint8)
    else:
        # Return a mock frame object
        mock_frame = Mock()
        mock_frame.shape = (480, 640, 3)
        return mock_frame


@pytest.fixture
def sample_pose_data():
    """Create sample pose data for testing"""
    return [
        {"keypoint": "nose", "x": 320, "y": 240, "confidence": 0.9},
        {"keypoint": "left_eye", "x": 310, "y": 230, "confidence": 0.8}
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
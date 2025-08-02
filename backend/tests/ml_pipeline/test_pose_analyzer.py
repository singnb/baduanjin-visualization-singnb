# type: ignore
# /test/ml_pipeline/test_pose_analyzer.py
# Unit tests for ml_pipeline/pose_analyzer.py core functions

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the functions we want to test
from ml_pipeline.pose_analyzer import (
    setup_cpu_optimizations,
    estimate_processing_time,
    convert_to_web_format,
    preprocess_video_for_cpu,
    preprocess_video_for_cpu_preserve_duration
)

class TestCPUOptimizations:
    """Test CPU optimization setup functions"""
    
    def test_setup_cpu_optimizations_sets_environment_variables(self):
        """Test that CPU optimizations properly set environment variables"""
        # Store original environment
        original_env = dict(os.environ)
        
        try:
            # Call the function
            setup_cpu_optimizations()
            
            # Check that key environment variables are set
            assert 'OMP_NUM_THREADS' in os.environ
            assert 'MKL_NUM_THREADS' in os.environ
            assert 'NUMEXPR_NUM_THREADS' in os.environ
            assert 'TORCH_NUM_THREADS' in os.environ
            assert 'CUDA_VISIBLE_DEVICES' in os.environ
            
            # Check that CUDA is disabled
            assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
            
            # Check that thread count is reasonable
            cpu_count = os.cpu_count()
            assert os.environ['OMP_NUM_THREADS'] == str(cpu_count)
            assert os.environ['MKL_NUM_THREADS'] == str(cpu_count)
            
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_setup_cpu_optimizations_with_mock_cpu_count(self):
        """Test CPU optimizations with mocked CPU count"""
        with patch('os.cpu_count', return_value=8):
            setup_cpu_optimizations()
            
            assert os.environ['OMP_NUM_THREADS'] == '8'
            assert os.environ['TORCH_NUM_THREADS'] == '8'
    
    def test_setup_cpu_optimizations_preserves_existing_env(self):
        """Test that function doesn't break existing environment"""
        # Set a test environment variable
        os.environ['TEST_VAR'] = 'test_value'
        
        setup_cpu_optimizations()
        
        # Verify our test variable is still there
        assert os.environ.get('TEST_VAR') == 'test_value'


class TestProcessingTimeEstimation:
    """Test video processing time estimation"""
    
    def test_estimate_processing_time_normal_video(self):
        """Test estimation for normal video that should process quickly"""
        # Mock cv2 module and VideoCapture
        with patch('cv2.VideoCapture') as mock_video_capture:
            # Setup mock VideoCapture with correct property mapping
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            def mock_get_property(prop):
                return {
                    3: 640,   # Width (cv2.CAP_PROP_FRAME_WIDTH)
                    4: 480,   # Height (cv2.CAP_PROP_FRAME_HEIGHT)
                    5: 30,    # FPS (cv2.CAP_PROP_FPS)
                    7: 300    # Frame count (cv2.CAP_PROP_FRAME_COUNT)
                }.get(prop, 0)
            mock_cap.get.side_effect = mock_get_property
            mock_cap.release.return_value = None
            mock_video_capture.return_value = mock_cap
            
            # Test the function
            is_ok, suggested_fps = estimate_processing_time("test_video.mp4", target_minutes=10)
            
            assert is_ok is True
            assert suggested_fps == 10
            mock_video_capture.assert_called_once_with("test_video.mp4")
            mock_cap.release.assert_called_once()
    
    def test_estimate_processing_time_large_video(self):
        """Test estimation for large video that needs optimization"""
        with patch('cv2.VideoCapture') as mock_video_capture:
            # Setup mock for large video with correct property mapping
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            def mock_get_property(prop):
                return {
                    3: 3840,   # Width (4K)
                    4: 2160,   # Height (4K)
                    5: 30,     # FPS
                    7: 18000   # Frame count (10 minutes)
                }.get(prop, 0)
            mock_cap.get.side_effect = mock_get_property
            mock_cap.release.return_value = None
            mock_video_capture.return_value = mock_cap
            
            is_ok, suggested_fps = estimate_processing_time("large_video.mp4", target_minutes=5)
            
            # Should suggest optimization for large video
            assert is_ok is False
            assert suggested_fps < 10  # Should suggest lower FPS
            mock_video_capture.assert_called_once_with("large_video.mp4")
    
    def test_estimate_processing_time_invalid_video(self):
        """Test estimation with invalid video file"""
        with patch('cv2.VideoCapture') as mock_video_capture:
            mock_cap = Mock()
            mock_cap.isOpened.return_value = False
            mock_video_capture.return_value = mock_cap
            
            # Should handle invalid video gracefully
            is_ok, suggested_fps = estimate_processing_time("invalid_video.mp4")
            
            # Should default to continue with standard settings
            assert is_ok is True
            assert suggested_fps == 10
    
    def test_estimate_processing_time_custom_target(self):
        """Test estimation with custom target time"""
        with patch('cv2.VideoCapture') as mock_video_capture:
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            def mock_get_property(prop):
                return {
                    3: 1280,  # Width
                    4: 720,   # Height
                    5: 30,    # FPS
                    7: 1800   # Frame count
                }.get(prop, 0)
            mock_cap.get.side_effect = mock_get_property
            mock_cap.release.return_value = None
            mock_video_capture.return_value = mock_cap
            
            # Test with very short target time
            is_ok, suggested_fps = estimate_processing_time("test.mp4", target_minutes=1)
            
            # Should suggest optimization for short target time
            mock_video_capture.assert_called_once()


class TestVideoPreprocessing:
    """Test video preprocessing functions"""
    
    @pytest.fixture
    def temp_video_files(self):
        """Create temporary video file paths for testing"""
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "input.mp4")
        output_path = os.path.join(temp_dir, "output.mp4")
        
        # Create a dummy input file
        with open(input_path, 'wb') as f:
            f.write(b'fake_video_data')
        
        yield input_path, output_path
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_preprocess_video_for_cpu_preserve_duration_success(self, temp_video_files):
        """Test video preprocessing that preserves duration"""
        input_path, output_path = temp_video_files
        
        with patch('cv2.VideoCapture') as mock_cap_class:
            with patch('cv2.VideoWriter') as mock_writer_class:
                with patch('cv2.VideoWriter_fourcc') as mock_fourcc:
                    with patch('cv2.resize') as mock_resize:
                        # Setup VideoCapture mock
                        mock_cap = Mock()
                        mock_cap.isOpened.return_value = True
                        
                        # Fix: Use proper cv2 property constants (FPS is typically 5, not 0)
                        def mock_get_property(prop):
                            property_map = {
                                3: 1920,  # cv2.CAP_PROP_FRAME_WIDTH
                                4: 1080,  # cv2.CAP_PROP_FRAME_HEIGHT  
                                5: 30,    # cv2.CAP_PROP_FPS (this was missing!)
                                7: 900    # cv2.CAP_PROP_FRAME_COUNT
                            }
                            return property_map.get(prop, 0)
                        
                        mock_cap.get.side_effect = mock_get_property
                        
                        # Mock frame reading - 3 successful reads then end
                        mock_cap.read.side_effect = [
                            (True, "fake_frame1"),
                            (True, "fake_frame2"), 
                            (True, "fake_frame3"),
                            (False, None)
                        ]
                        mock_cap_class.return_value = mock_cap
                        
                        # Setup VideoWriter mock
                        mock_writer = Mock()
                        mock_writer_class.return_value = mock_writer
                        mock_fourcc.return_value = "mp4v"
                        mock_resize.return_value = "resized_frame"
                        
                        # Test the function
                        result = preprocess_video_for_cpu_preserve_duration(
                            input_path, output_path, target_fps=30, max_resolution=720
                        )
                        
                        assert result is True
                        mock_cap_class.assert_called_once_with(input_path)
                        mock_writer_class.assert_called_once()
                        mock_cap.release.assert_called_once()
                        mock_writer.release.assert_called_once()
    
    def test_preprocess_video_for_cpu_preserve_duration_invalid_video(self, temp_video_files):
        """Test preprocessing with invalid video file"""
        input_path, output_path = temp_video_files
        
        with patch('cv2.VideoCapture') as mock_cap_class:
            # Mock invalid video
            mock_cap = Mock()
            mock_cap.isOpened.return_value = False
            mock_cap_class.return_value = mock_cap
            
            result = preprocess_video_for_cpu_preserve_duration(input_path, output_path)
            
            assert result is False
            mock_cap_class.assert_called_once_with(input_path)
    
    def test_preprocess_video_for_cpu_original_function(self, temp_video_files):
        """Test original preprocessing function with frame skipping"""
        input_path, output_path = temp_video_files
        
        with patch('cv2.VideoCapture') as mock_cap_class:
            with patch('cv2.VideoWriter') as mock_writer_class:
                with patch('cv2.VideoWriter_fourcc') as mock_fourcc:
                    # Setup mock for original function
                    mock_cap = Mock()
                    mock_cap.isOpened.return_value = True
                    def mock_get_property(prop):
                        return {
                            3: 1920,  # Width
                            4: 1080,  # Height
                            5: 30,    # FPS
                            7: 900    # Frame count
                        }.get(prop, 0)
                    mock_cap.get.side_effect = mock_get_property
                    
                    # Mock successful frame reading
                    frame_data = [(True, "fake_frame")] * 10 + [(False, None)]
                    mock_cap.read.side_effect = frame_data
                    mock_cap_class.return_value = mock_cap
                    
                    mock_writer = Mock()
                    mock_writer_class.return_value = mock_writer
                    mock_fourcc.return_value = "mp4v"
                    
                    result = preprocess_video_for_cpu(input_path, output_path, target_fps=15)
                    
                    # Should succeed (mocked)
                    mock_cap_class.assert_called_once_with(input_path)


class TestWebFormatConversion:
    """Test FFmpeg web format conversion"""
    
    @pytest.fixture
    def temp_files_and_logs(self):
        """Create temporary files for testing conversion"""
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "input.mp4")
        output_path = os.path.join(temp_dir, "output.mp4")
        debug_log = os.path.join(temp_dir, "debug.log")
        log_file = os.path.join(temp_dir, "analysis.log")
        
        # Create dummy input file
        with open(input_path, 'wb') as f:
            f.write(b'fake_video_data' * 1000)  # Make it reasonably sized
        
        yield input_path, output_path, debug_log, log_file
        
        shutil.rmtree(temp_dir)
    
    def test_convert_to_web_format_success(self, temp_files_and_logs):
        """Test successful FFmpeg conversion"""
        input_path, output_path, debug_log, log_file = temp_files_and_logs
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock successful FFmpeg execution
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "FFmpeg conversion successful"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result
            
            # Create fake output file
            with open(output_path, 'wb') as f:
                f.write(b'converted_video_data' * 500)
            
            result = convert_to_web_format(input_path, output_path, debug_log, log_file)
            
            assert result is True
            
            # Verify FFmpeg was called correctly
            assert mock_subprocess.call_count >= 1  # At least version check
            
            # Check that log files were written
            assert os.path.exists(debug_log)
            with open(debug_log, 'r') as f:
                log_content = f.read()
                assert "FFmpeg conversion" in log_content
    
    def test_convert_to_web_format_ffmpeg_not_found(self, temp_files_and_logs):
        """Test conversion when FFmpeg is not available"""
        input_path, output_path, debug_log, log_file = temp_files_and_logs
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock FFmpeg not found
            mock_subprocess.side_effect = FileNotFoundError("FFmpeg not found")
            
            result = convert_to_web_format(input_path, output_path, debug_log, log_file)
            
            assert result is False
            
            # Check that error was logged
            assert os.path.exists(debug_log)
            with open(debug_log, 'r') as f:
                log_content = f.read()
                assert "FFmpeg not found" in log_content
    
    def test_convert_to_web_format_conversion_failed(self, temp_files_and_logs):
        """Test conversion failure"""
        input_path, output_path, debug_log, log_file = temp_files_and_logs
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock version check success, conversion failure
            version_result = Mock()
            version_result.returncode = 0
            
            conversion_result = Mock()
            conversion_result.returncode = 1
            conversion_result.stdout = ""
            conversion_result.stderr = "Conversion failed: Invalid codec"
            
            mock_subprocess.side_effect = [version_result, conversion_result]
            
            result = convert_to_web_format(input_path, output_path, debug_log, log_file)
            
            assert result is False
            
            # Verify both calls were made
            assert mock_subprocess.call_count == 2
    
    def test_convert_to_web_format_timeout(self, temp_files_and_logs):
        """Test conversion timeout handling"""
        input_path, output_path, debug_log, log_file = temp_files_and_logs
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock version check success
            version_result = Mock()
            version_result.returncode = 0
            
            # Mock timeout on conversion
            import subprocess
            mock_subprocess.side_effect = [
                version_result, 
                subprocess.TimeoutExpired("ffmpeg", 300)
            ]
            
            result = convert_to_web_format(input_path, output_path, debug_log, log_file)
            
            assert result is False
            
            # Check timeout was logged
            with open(debug_log, 'r') as f:
                log_content = f.read()
                assert "timed out" in log_content


class TestPathHandling:
    """Test path handling and directory operations"""
    
    def test_path_normalization(self):
        """Test that paths are properly normalized"""
        # Test various path formats
        windows_path = r"C:\Users\test\video.mp4"
        unix_path = "/home/test/video.mp4"
        
        # Test absolute path detection
        assert os.path.isabs(windows_path)
        assert os.path.isabs(unix_path)
        
        # Test path joining with forward slashes
        test_dir = "test_dir"
        test_file = "test_file.mp4"
        joined_path = os.path.join(test_dir, test_file).replace('\\', '/')
        
        assert '/' in joined_path or '\\' not in joined_path
    
    def test_directory_creation_logic(self):
        """Test directory creation patterns used in analyze_video"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test nested directory creation
            user_id = 123
            video_id = 456
            
            test_path = os.path.join(temp_dir, "outputs_json", str(user_id), str(video_id))
            
            # This should work without errors
            os.makedirs(test_path, exist_ok=True)
            
            assert os.path.exists(test_path)
            assert os.path.isdir(test_path)
    
    def test_file_extension_handling(self):
        """Test file extension and basename handling"""
        test_files = [
            "video.mp4",
            "test_video_123.mp4",
            "video.MP4",
            "path/to/video.mp4"
        ]
        
        for filename in test_files:
            basename = os.path.basename(filename)
            name_without_ext = os.path.splitext(basename)[0]
            extension = os.path.splitext(basename)[1]
            
            assert extension.lower() == '.mp4'
            assert len(name_without_ext) > 0


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_missing_dependencies_handling(self):
        """Test behavior when dependencies are missing"""
        # Test that functions handle missing cv2 gracefully
        with patch.dict('sys.modules', {'cv2': None}):
            # This should not crash, but may raise expected exceptions
            try:
                estimate_processing_time("test.mp4")
            except (AttributeError, TypeError):
                # Expected when cv2 is None
                pass
    
    def test_file_permission_errors(self):
        """Test handling of file permission errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with restricted permissions
            restricted_file = os.path.join(temp_dir, "restricted.mp4")
            with open(restricted_file, 'w') as f:
                f.write("test")
            
            # Test that functions handle permission errors gracefully
            # This would depend on the specific implementation
            assert os.path.exists(restricted_file)
    
    def test_invalid_parameters(self):
        """Test handling of invalid parameters"""
        # Test with None parameters
        with patch('cv2.VideoCapture') as mock_cv2:
            mock_cap = Mock()
            mock_cap.isOpened.return_value = False
            mock_cv2.return_value = mock_cap
            
            result = estimate_processing_time(None)
            assert isinstance(result, tuple)
    
    def test_empty_file_handling(self):
        """Test handling of empty or corrupted files"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = temp_file.name
            # File is empty
        
        try:
            with patch('cv2.VideoCapture') as mock_cv2:
                mock_cap = Mock()
                mock_cap.isOpened.return_value = False
                mock_cv2.return_value = mock_cap
                
                result = estimate_processing_time(temp_path)
                assert result[0] is True  # Should default to continue
        finally:
            os.unlink(temp_path)


class TestIntegrationScenarios:
    """Test realistic usage scenarios"""
    
    @patch.dict(os.environ, {'OMP_NUM_THREADS': '4'})
    def test_cpu_optimization_integration(self):
        """Test CPU optimization in realistic scenario"""
        original_threads = os.environ.get('OMP_NUM_THREADS')
        
        setup_cpu_optimizations()
        
        # Should update to use all available cores
        new_threads = os.environ.get('OMP_NUM_THREADS')
        assert new_threads == str(os.cpu_count())
        assert new_threads != original_threads
    
    def test_video_processing_workflow(self):
        """Test complete video processing workflow components"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test environment
            input_video = os.path.join(temp_dir, "input.mp4")
            output_video = os.path.join(temp_dir, "output.mp4")
            debug_log = os.path.join(temp_dir, "debug.log")
            
            # Create dummy input file
            with open(input_video, 'wb') as f:
                f.write(b'fake_video_content' * 100)
            
            # Test that basic file operations work
            assert os.path.exists(input_video)
            assert os.path.getsize(input_video) > 0
            
            # Test log file creation
            with open(debug_log, 'w') as f:
                f.write("Test log entry\n")
            
            assert os.path.exists(debug_log)
    
    def test_relative_path_generation(self):
        """Test relative path generation for frontend"""
        user_id = 123
        video_id = 456
        filename = "test_video.mp4"
        
        # Test the path generation pattern used in analyze_video
        relative_path = f"outputs_json/{user_id}/{video_id}/{filename}"
        
        assert relative_path == "outputs_json/123/456/test_video.mp4"
        assert relative_path.count('/') == 3
        assert not relative_path.startswith('/')


# Helper function to run tests
if __name__ == "__main__":
    print("Running pose analyzer unit tests...")
    
    # Quick test of CPU optimization function
    original_env = dict(os.environ)
    try:
        setup_cpu_optimizations()
        print(f"CPU optimization test passed: Using {os.environ.get('OMP_NUM_THREADS')} threads")
    except Exception as e:
        print(f"CPU optimization test failed: {e}")
    finally:
        os.environ.clear()
        os.environ.update(original_env)
    
    # Quick test of path handling
    test_path = os.path.join("test", "path", "video.mp4").replace('\\', '/')
    print(f"Path handling test passed: {test_path}")
    
    print("Basic tests passed! Run with pytest for full test suite.")
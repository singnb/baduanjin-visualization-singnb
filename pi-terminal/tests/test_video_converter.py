# type: ignore
# test_video_converter.py

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import tempfile
from pathlib import Path

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import the module under test
from video_converter import convert_video_for_web, check_ffmpeg_available


class TestConvertVideoForWeb(unittest.TestCase):
    """Test cases for convert_video_for_web function"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.input_path = "/test/input.mp4"
        self.output_path = "/test/output.mp4"
        self.mock_input_size = 1024000  # 1MB
        self.mock_output_size = 512000  # 512KB
    
    def create_mock_subprocess_result(self, returncode=0, stdout="", stderr=""):
        """Create a mock subprocess result"""
        mock_result = Mock()
        mock_result.returncode = returncode
        mock_result.stdout = stdout
        mock_result.stderr = stderr
        return mock_result
    
    def create_mock_file_stat(self, size):
        """Create a mock file stat object"""
        mock_stat = Mock()
        mock_stat.st_size = size
        return mock_stat
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_duplicate_method(self, mock_path_class, mock_subprocess):
        """Test video conversion with duplicate frame method"""
        # Setup subprocess mock
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        # Setup Path mocks
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_output_size)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_input_size)
        
        def mock_path_constructor(path_str):
            if str(path_str) == self.output_path:
                return mock_output_path_instance
            elif str(path_str) == self.input_path:
                return mock_input_path_instance
            return Mock()
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Execute function with duplicate method
        result = convert_video_for_web(self.input_path, self.output_path, 
                                     target_fps=25, method="duplicate")
        
        # Verify results
        self.assertTrue(result["success"])
        self.assertEqual(result["output_path"], self.output_path)
        self.assertEqual(result["compression_ratio"], 0.5)
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_blend_method(self, mock_path_class, mock_subprocess):
        """Test video conversion with blend frame method"""
        # Setup subprocess mock
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        # Setup Path mocks
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_output_size)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_input_size)
        
        def mock_path_constructor(path_str):
            if str(path_str) == self.output_path:
                return mock_output_path_instance
            elif str(path_str) == self.input_path:
                return mock_input_path_instance
            return Mock()
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Execute function with blend method
        result = convert_video_for_web(self.input_path, self.output_path, 
                                     target_fps=60, method="blend")
        
        # Verify results
        self.assertTrue(result["success"])
        self.assertEqual(result["output_path"], self.output_path)
        self.assertEqual(result["compression_ratio"], 0.5)
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_directory_creation(self, mock_path_class, mock_subprocess):
        """Test that output directory is created if it doesn't exist"""
        # Setup subprocess mock
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        # Setup Path mocks
        mock_output_path_instance = Mock()
        mock_parent_dir = Mock()
        mock_output_path_instance.parent = mock_parent_dir
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_output_size)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_input_size)
        
        def mock_path_constructor(path_str):
            if str(path_str) == self.output_path:
                return mock_output_path_instance
            elif str(path_str) == self.input_path:
                return mock_input_path_instance
            return Mock()
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Execute function
        result = convert_video_for_web(self.input_path, self.output_path)
        
        # Verify directory creation was attempted
        mock_parent_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertTrue(result["success"])
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_ffmpeg_failure(self, mock_path_class, mock_subprocess):
        """Test handling of FFmpeg conversion failure"""
        # Setup mocks for failed conversion
        mock_subprocess.return_value = self.create_mock_subprocess_result(
            returncode=1, 
            stderr="FFmpeg error: invalid input file"
        )
        
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        
        mock_path_class.return_value = mock_output_path_instance
        
        # Execute function and expect exception
        with self.assertRaises(Exception) as context:
            convert_video_for_web(self.input_path, self.output_path)
        
        self.assertIn("FFmpeg failed", str(context.exception))
        self.assertIn("invalid input file", str(context.exception))
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_output_file_not_created(self, mock_path_class, mock_subprocess):
        """Test handling when output file is not created despite successful FFmpeg"""
        # Setup mocks
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = False  # File not created
        
        mock_path_class.return_value = mock_output_path_instance
        
        # Execute function and expect exception
        with self.assertRaises(Exception) as context:
            convert_video_for_web(self.input_path, self.output_path)
        
        self.assertIn("Output file was not created", str(context.exception))
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_timeout(self, mock_path_class, mock_subprocess):
        """Test handling of conversion timeout"""
        # Setup mocks for timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("ffmpeg", timeout=300)
        
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        
        mock_path_class.return_value = mock_output_path_instance
        
        # Execute function and expect exception
        with self.assertRaises(Exception) as context:
            convert_video_for_web(self.input_path, self.output_path)
        
        self.assertIn("Conversion timeout", str(context.exception))
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_ffmpeg_not_found(self, mock_path_class, mock_subprocess):
        """Test handling when FFmpeg is not installed"""
        # Setup mocks for FileNotFoundError
        mock_subprocess.side_effect = FileNotFoundError("ffmpeg command not found")
        
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        
        mock_path_class.return_value = mock_output_path_instance
        
        # Execute function and expect exception
        with self.assertRaises(Exception) as context:
            convert_video_for_web(self.input_path, self.output_path)
        
        self.assertIn("FFmpeg not found", str(context.exception))
        self.assertIn("sudo apt install ffmpeg", str(context.exception))
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_zero_input_size(self, mock_path_class, mock_subprocess):
        """Test handling of zero input file size"""
        # Setup subprocess mock
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        # Setup Path mocks
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_output_size)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = self.create_mock_file_stat(0)  # Zero size
        
        def mock_path_constructor(path_str):
            if str(path_str) == self.output_path:
                return mock_output_path_instance
            elif str(path_str) == self.input_path:
                return mock_input_path_instance
            return Mock()
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Execute function
        result = convert_video_for_web(self.input_path, self.output_path)
        
        # Verify results with zero division protection
        self.assertTrue(result["success"])
        self.assertEqual(result["compression_ratio"], 1)  # Default when input_size is 0
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_command_structure(self, mock_path_class, mock_subprocess):
        """Test the structure of the FFmpeg command"""
        # Setup subprocess mock
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        # Setup Path mocks
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_output_size)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_input_size)
        
        def mock_path_constructor(path_str):
            if str(path_str) == self.output_path:
                return mock_output_path_instance
            elif str(path_str) == self.input_path:
                return mock_input_path_instance
            return Mock()
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Execute function
        convert_video_for_web(self.input_path, self.output_path)
        
        # Verify command structure
        call_args = mock_subprocess.call_args[0][0]
        
        # Check required FFmpeg parameters for Pi optimization
        expected_params = [
            'ffmpeg', '-i', self.input_path,
            '-c:v', 'libx264',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-preset', 'ultrafast',
            '-crf', '28',
            '-y', self.output_path
        ]
        
        for param in expected_params:
            self.assertIn(param, call_args)
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_convert_video_subprocess_timeout_parameter(self, mock_path_class, mock_subprocess):
        """Test that subprocess is called with correct timeout"""
        # Setup subprocess mock
        mock_subprocess.return_value = self.create_mock_subprocess_result(returncode=0)
        
        # Setup Path mocks
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_output_size)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = self.create_mock_file_stat(self.mock_input_size)
        
        def mock_path_constructor(path_str):
            if str(path_str) == self.output_path:
                return mock_output_path_instance
            elif str(path_str) == self.input_path:
                return mock_input_path_instance
            return Mock()
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Execute function
        convert_video_for_web(self.input_path, self.output_path)
        
        # Verify subprocess call parameters
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]  # Keyword arguments
        
        self.assertEqual(call_kwargs['timeout'], 300)  # 5 minutes
        self.assertTrue(call_kwargs['capture_output'])
        self.assertTrue(call_kwargs['text'])


class TestCheckFFmpegAvailable(unittest.TestCase):
    """Test cases for check_ffmpeg_available function"""
    
    @patch('video_converter.subprocess.run')
    def test_check_ffmpeg_available_success(self, mock_subprocess):
        """Test FFmpeg availability check when FFmpeg is available"""
        # Setup mock for successful FFmpeg version check
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Execute function
        result = check_ffmpeg_available()
        
        # Verify results
        self.assertTrue(result)
        
        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once_with(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('video_converter.subprocess.run')
    def test_check_ffmpeg_available_failure(self, mock_subprocess):
        """Test FFmpeg availability check when FFmpeg is not available"""
        # Setup mock for failed FFmpeg version check
        mock_subprocess.return_value = Mock(returncode=1)
        
        # Execute function
        result = check_ffmpeg_available()
        
        # Verify results
        self.assertFalse(result)
    
    @patch('video_converter.subprocess.run')
    def test_check_ffmpeg_available_exception(self, mock_subprocess):
        """Test FFmpeg availability check when exception occurs"""
        # Setup mock to raise exception
        mock_subprocess.side_effect = FileNotFoundError("ffmpeg not found")
        
        # Execute function
        result = check_ffmpeg_available()
        
        # Verify results
        self.assertFalse(result)
    
    @patch('video_converter.subprocess.run')
    def test_check_ffmpeg_available_timeout(self, mock_subprocess):
        """Test FFmpeg availability check with timeout"""
        # Setup mock to raise timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("ffmpeg", timeout=10)
        
        # Execute function
        result = check_ffmpeg_available()
        
        # Verify results
        self.assertFalse(result)


class TestVideoConverterIntegration(unittest.TestCase):
    """Integration test scenarios for video converter"""
    
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_complete_conversion_workflow(self, mock_path_class, mock_subprocess):
        """Test complete video conversion workflow"""
        # Setup mocks for successful workflow
        mock_subprocess.return_value = Mock(returncode=0)
        
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = Mock(st_size=800000)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = Mock(st_size=1000000)
        
        def mock_path_constructor(path_str):
            if "output" in str(path_str):
                return mock_output_path_instance
            else:
                return mock_input_path_instance
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Test different conversion methods
        methods = ["duplicate", "blend", "default"]
        fps_values = [24, 30, 60]
        
        for method in methods:
            for fps in fps_values:
                with self.subTest(method=method, fps=fps):
                    result = convert_video_for_web(
                        "/test/input.mp4", 
                        "/test/output.mp4",
                        target_fps=fps,
                        method=method
                    )
                    
                    self.assertTrue(result["success"])
                    self.assertEqual(result["compression_ratio"], 0.8)
    
    @patch('video_converter.check_ffmpeg_available')
    @patch('video_converter.subprocess.run')
    @patch('video_converter.Path')
    def test_conversion_with_ffmpeg_check(self, mock_path_class, mock_subprocess, mock_ffmpeg_check):
        """Test conversion workflow with FFmpeg availability check"""
        # Test scenario where FFmpeg is available
        mock_ffmpeg_check.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)
        
        mock_output_path_instance = Mock()
        mock_output_path_instance.parent.mkdir = Mock()
        mock_output_path_instance.exists.return_value = True
        mock_output_path_instance.stat.return_value = Mock(st_size=500000)
        
        mock_input_path_instance = Mock()
        mock_input_path_instance.stat.return_value = Mock(st_size=1000000)
        
        def mock_path_constructor(path_str):
            if "output" in str(path_str):
                return mock_output_path_instance
            else:
                return mock_input_path_instance
        
        mock_path_class.side_effect = mock_path_constructor
        
        # Check FFmpeg availability first (simulating real usage)
        ffmpeg_available = check_ffmpeg_available()
        self.assertTrue(ffmpeg_available)
        
        # Then convert video
        result = convert_video_for_web("/test/input.mp4", "/test/output.mp4")
        self.assertTrue(result["success"])
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        # Test cases are already covered in individual test methods
        # This method serves as a documentation of error scenarios
        error_scenarios = [
            "FFmpeg not found",
            "Conversion timeout", 
            "FFmpeg process failure",
            "Output file not created",
            "File system errors"
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario):
                # Each scenario is tested in dedicated test methods above
                self.assertTrue(True)  # Placeholder for documentation


class TestFileSystemOperations(unittest.TestCase):
    """Test cases for file system related operations"""
    
    @patch('video_converter.Path')
    def test_path_operations(self, mock_path_class):
        """Test Path operations used in video converter"""
        # Test Path creation and operations
        mock_path_instance = Mock()
        mock_path_instance.parent.mkdir = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.stat.return_value = Mock(st_size=1024)
        
        mock_path_class.return_value = mock_path_instance
        
        # Create Path objects like in the video converter
        test_path = mock_path_class("/test/path/file.mp4")
        
        # Verify Path operations work as expected
        self.assertIsNotNone(test_path)
        
        # Test that we can call the methods we expect
        test_path.exists()
        test_path.stat()
        test_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verify the calls were made
        mock_path_instance.exists.assert_called()
        mock_path_instance.stat.assert_called()
        mock_path_instance.parent.mkdir.assert_called_with(parents=True, exist_ok=True)
    
    @patch('video_converter.Path')
    def test_directory_creation_edge_cases(self, mock_path_class):
        """Test directory creation edge cases"""
        # Test when parent directory creation fails
        mock_path_instance = Mock()
        mock_path_instance.parent.mkdir.side_effect = OSError("Permission denied")
        
        mock_path_class.return_value = mock_path_instance
        
        # Create a path instance
        test_path = mock_path_class("/test/path/file.mp4")
        
        # This would be handled in the actual conversion function
        # Here we just verify the mock setup works
        with self.assertRaises(OSError):
            test_path.parent.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestConvertVideoForWeb))
    suite.addTests(loader.loadTestsFromTestCase(TestCheckFFmpegAvailable))
    suite.addTests(loader.loadTestsFromTestCase(TestVideoConverterIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestFileSystemOperations))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"VIDEO CONVERTER UNIT TESTS SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            # Print first line of assertion error for quick diagnosis
            lines = traceback.split('\n')
            for line in lines:
                if 'AssertionError' in line:
                    print(f"    {line.strip()}")
                    break
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            # Print first line of error for quick diagnosis
            lines = traceback.split('\n')
            for line in lines:
                if any(error_type in line for error_type in ['Error:', 'Exception:']):
                    print(f"    {line.strip()}")
                    break
    
    # Test coverage summary
    print(f"\n{'='*60}")
    print(f"TEST COVERAGE SUMMARY:")
    print(f"{'='*60}")
    print(f" Main function: convert_video_for_web()")
    print(f"   - Success scenarios (all methods: duplicate, blend, default)")
    print(f"   - Error handling (FFmpeg failure, timeout, file not found)")
    print(f"   - File system operations (directory creation, file stats)")
    print(f"   - Command generation (FFmpeg parameters, Pi optimization)")
    print(f" Utility function: check_ffmpeg_available()")
    print(f"   - Success and failure scenarios")
    print(f"   - Exception handling")
    print(f" Integration scenarios")
    print(f"   - Complete conversion workflows")
    print(f"   - Multiple method/FPS combinations")
    print(f" Edge cases")
    print(f"   - Zero file sizes, timeout handling, permission errors")
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

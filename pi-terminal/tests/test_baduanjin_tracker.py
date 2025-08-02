# type: ignore
# test_baduanjin_tracker.py

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import time

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Mock dependencies before importing
sys.modules['numpy'] = Mock()

# Import numpy mock and set up array functionality
import numpy as np
np.array = lambda x: x  # Simple mock for array creation

# Now import the module under test
from baduanjin_tracker import (
    PoseKeypoints, ExerciseFeedback, SessionStats, BaduanjinTracker,
    create_baduanjin_tracker
)


class TestPoseKeypoints(unittest.TestCase):
    """Test cases for PoseKeypoints dataclass"""
    
    def test_pose_keypoints_initialization_default(self):
        """Test PoseKeypoints initialization with default values"""
        pose = PoseKeypoints()
        
        # All keypoints should default to (0, 0)
        self.assertEqual(pose.nose, (0, 0))
        self.assertEqual(pose.left_shoulder, (0, 0))
        self.assertEqual(pose.right_ankle, (0, 0))
    
    def test_pose_keypoints_initialization_custom(self):
        """Test PoseKeypoints initialization with custom values"""
        pose = PoseKeypoints(
            nose=(100, 200),
            left_shoulder=(150, 250),
            right_shoulder=(200, 250)
        )
        
        self.assertEqual(pose.nose, (100, 200))
        self.assertEqual(pose.left_shoulder, (150, 250))
        self.assertEqual(pose.right_shoulder, (200, 250))
        # Unspecified should still be default
        self.assertEqual(pose.left_ankle, (0, 0))
    
    def test_pose_keypoints_to_dict(self):
        """Test converting PoseKeypoints to dictionary"""
        pose = PoseKeypoints(nose=(100, 200), left_eye=(110, 210))
        pose_dict = asdict(pose)
        
        self.assertIn('nose', pose_dict)
        self.assertIn('left_eye', pose_dict)
        self.assertEqual(pose_dict['nose'], (100, 200))
        self.assertEqual(pose_dict['left_eye'], (110, 210))


class TestExerciseFeedback(unittest.TestCase):
    """Test cases for ExerciseFeedback dataclass"""
    
    def test_exercise_feedback_creation(self):
        """Test ExerciseFeedback creation with all fields"""
        feedback = ExerciseFeedback(
            exercise_id=1,
            exercise_name="Test Exercise",
            current_phase="start",
            completion_percentage=50.0,
            form_score=85.0,
            feedback_messages=["Good posture"],
            corrections=["Straighten back"],
            pose_quality={"alignment": 90.0},
            timestamp="2025-01-15T10:00:00"
        )
        
        self.assertEqual(feedback.exercise_id, 1)
        self.assertEqual(feedback.exercise_name, "Test Exercise")
        self.assertEqual(feedback.current_phase, "start")
        self.assertEqual(feedback.completion_percentage, 50.0)
        self.assertEqual(feedback.form_score, 85.0)
        self.assertEqual(len(feedback.feedback_messages), 1)
        self.assertEqual(len(feedback.corrections), 1)
        self.assertIn("alignment", feedback.pose_quality)


class TestSessionStats(unittest.TestCase):
    """Test cases for SessionStats dataclass"""
    
    def test_session_stats_creation(self):
        """Test SessionStats creation"""
        stats = SessionStats(
            total_exercises_attempted=5,
            exercises_completed=3,
            average_form_score=82.5,
            session_duration=300.0,
            movement_consistency=75.0,
            recommendations=["Keep practicing", "Focus on breathing"]
        )
        
        self.assertEqual(stats.total_exercises_attempted, 5)
        self.assertEqual(stats.exercises_completed, 3)
        self.assertEqual(stats.average_form_score, 82.5)
        self.assertEqual(stats.session_duration, 300.0)
        self.assertEqual(stats.movement_consistency, 75.0)
        self.assertEqual(len(stats.recommendations), 2)


class TestBaduanjinTracker(unittest.TestCase):
    """Test cases for BaduanjinTracker class"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock Path.mkdir to avoid filesystem operations
        with patch('pathlib.Path.mkdir'):
            self.tracker = BaduanjinTracker(output_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up after each test method"""
        # Clean up any created files
        pass
    
    def test_initialization(self):
        """Test BaduanjinTracker initialization"""
        self.assertIsNotNone(self.tracker.exercises)
        self.assertEqual(len(self.tracker.exercises), 8)  # 8 Baduanjin exercises
        self.assertIsNone(self.tracker.current_exercise)
        self.assertEqual(self.tracker.current_phase, "ready")
        self.assertEqual(self.tracker.pose_history, [])
        self.assertEqual(self.tracker.feedback_history, [])
        self.assertIsInstance(self.tracker.session_stats, dict)
    
    def test_define_baduanjin_exercises(self):
        """Test exercise definitions"""
        exercises = self.tracker._define_baduanjin_exercises()
        
        # Should have 8 exercises
        self.assertEqual(len(exercises), 8)
        
        # Check first exercise structure
        exercise_1 = exercises[1]
        self.assertIn("name", exercise_1)
        self.assertIn("description", exercise_1)
        self.assertIn("key_poses", exercise_1)
        self.assertIn("common_mistakes", exercise_1)
        
        # Check exercise 1 details
        self.assertEqual(exercise_1["name"], "Holding up the Sky (两手托天理三焦)")
        self.assertIn("start", exercise_1["key_poses"])
        self.assertIn("hold", exercise_1["key_poses"])
        self.assertIsInstance(exercise_1["common_mistakes"], list)
        
        # Check all exercises have required fields
        for ex_id, exercise in exercises.items():
            self.assertIn("name", exercise)
            self.assertIn("description", exercise)
            self.assertIn("key_poses", exercise)
            self.assertIn("common_mistakes", exercise)
            self.assertIsInstance(exercise["key_poses"], dict)
            self.assertIsInstance(exercise["common_mistakes"], list)
    
    def test_extract_pose_keypoints_valid(self):
        """Test extracting pose keypoints from valid YOLO data"""
        # Create sample YOLO keypoints (17 points with x,y coordinates)
        yolo_keypoints = [[i*10, i*20] for i in range(17)]
        confidences = [0.9] * 17
        
        pose = self.tracker.extract_pose_keypoints(yolo_keypoints, confidences)
        
        self.assertIsNotNone(pose)
        self.assertIsInstance(pose, PoseKeypoints)
        self.assertEqual(pose.nose, (0, 0))  # First keypoint
        self.assertEqual(pose.left_shoulder, (50, 100))  # 5th keypoint
        self.assertEqual(pose.right_ankle, (160, 320))  # Last keypoint
    
    def test_extract_pose_keypoints_insufficient_data(self):
        """Test extracting pose keypoints with insufficient data"""
        # Too few keypoints
        yolo_keypoints = [[i*10, i*20] for i in range(10)]  # Only 10 instead of 17
        confidences = [0.9] * 10
        
        pose = self.tracker.extract_pose_keypoints(yolo_keypoints, confidences)
        
        self.assertIsNone(pose)
    
    def test_extract_pose_keypoints_low_confidence(self):
        """Test extracting pose keypoints with low confidence"""
        yolo_keypoints = [[i*10, i*20] for i in range(17)]
        confidences = [0.3] * 17  # Below threshold (0.5)
        
        pose = self.tracker.extract_pose_keypoints(yolo_keypoints, confidences)
        
        self.assertIsNone(pose)
    
    def test_extract_pose_keypoints_mixed_confidence(self):
        """Test extracting pose keypoints with mixed confidence"""
        yolo_keypoints = [[i*10, i*20] for i in range(17)]
        confidences = [0.9, 0.8, 0.7, 0.6, 0.5, 0.9, 0.8, 0.7, 0.6] + [0.3] * 8
        
        pose = self.tracker.extract_pose_keypoints(yolo_keypoints, confidences)
        
        # Should work because 9 keypoints have confidence > 0.5 (need >= 8)
        self.assertIsNotNone(pose)
    
    def test_extract_pose_keypoints_exception_handling(self):
        """Test pose keypoint extraction with malformed data"""
        # Malformed keypoints (missing coordinates)
        yolo_keypoints = [[i*10] for i in range(17)]  # Missing y coordinates
        confidences = [0.9] * 17
        
        pose = self.tracker.extract_pose_keypoints(yolo_keypoints, confidences)
        
        self.assertIsNone(pose)
    
    def test_start_exercise_valid(self):
        """Test starting a valid exercise"""
        result = self.tracker.start_exercise(1)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["exercise_id"], 1)
        self.assertIn("exercise_name", result)
        self.assertIn("description", result)
        self.assertIn("phases", result)
        self.assertIn("common_mistakes", result)
        
        # Check tracker state
        self.assertEqual(self.tracker.current_exercise, 1)
        self.assertEqual(self.tracker.current_phase, "start")
        self.assertIsNotNone(self.tracker.exercise_start_time)
        self.assertEqual(self.tracker.session_stats["exercises_attempted"], 1)
    
    def test_start_exercise_invalid(self):
        """Test starting an invalid exercise"""
        result = self.tracker.start_exercise(999)
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIsNone(self.tracker.current_exercise)
    
    def test_end_exercise_with_active_session(self):
        """Test ending exercise with active session"""
        # Start an exercise first
        self.tracker.start_exercise(1)
        
        # Add some feedback to history
        sample_feedback = {
            "form_score": 85.0,
            "timestamp": time.time()
        }
        self.tracker.feedback_history.append(sample_feedback)
        
        result = self.tracker.end_exercise()
        
        self.assertTrue(result["success"])
        self.assertIn("summary", result)
        summary = result["summary"]
        self.assertEqual(summary["exercise_id"], 1)
        self.assertIn("final_form_score", summary)
        self.assertIn("duration", summary)
        
        # Check state reset
        self.assertIsNone(self.tracker.current_exercise)
        self.assertEqual(self.tracker.current_phase, "ready")
        self.assertIsNone(self.tracker.exercise_start_time)
    
    def test_end_exercise_no_active_session(self):
        """Test ending exercise without active session"""
        result = self.tracker.end_exercise()
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_analyze_holding_sky_exercise(self):
        """Test analyzing 'Holding up the Sky' exercise"""
        # Create sample pose for analysis
        pose = PoseKeypoints(
            left_shoulder=(100, 200),
            right_shoulder=(200, 200),
            left_wrist=(90, 50),   # Arms raised
            right_wrist=(210, 50)
        )
        
        score, messages, corrections = self.tracker._analyze_holding_sky(pose, "hold")
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertIsInstance(messages, list)
        self.assertIsInstance(corrections, list)
    
    def test_analyze_drawing_bow_exercise(self):
        """Test analyzing 'Drawing the Bow' exercise"""
        pose = PoseKeypoints(
            left_shoulder=(100, 200),
            right_shoulder=(200, 200),
            left_wrist=(50, 200),    # Left arm extended
            right_wrist=(250, 200)   # Right arm extended
        )
        
        score, messages, corrections = self.tracker._analyze_drawing_bow(pose, "draw_left")
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertIsInstance(messages, list)
        self.assertIsInstance(corrections, list)
    
    def test_analyze_pose_for_exercise_all_exercises(self):
        """Test pose analysis for all 8 exercises"""
        sample_pose = PoseKeypoints(
            nose=(150, 100),
            left_shoulder=(100, 200),
            right_shoulder=(200, 200),
            left_wrist=(90, 180),
            right_wrist=(210, 180),
            left_hip=(110, 300),
            right_hip=(190, 300)
        )
        
        for exercise_id in range(1, 9):  # Test all 8 exercises
            score, messages, corrections = self.tracker.analyze_pose_for_exercise(
                sample_pose, exercise_id, "start"
            )
            
            self.assertIsInstance(score, float, f"Exercise {exercise_id} should return float score")
            self.assertGreaterEqual(score, 0, f"Exercise {exercise_id} score should be >= 0")
            self.assertLessEqual(score, 100, f"Exercise {exercise_id} score should be <= 100")
            self.assertIsInstance(messages, list, f"Exercise {exercise_id} should return message list")
            self.assertIsInstance(corrections, list, f"Exercise {exercise_id} should return correction list")
    
    def test_analyze_pose_for_invalid_exercise(self):
        """Test pose analysis for invalid exercise"""
        pose = PoseKeypoints()
        score, messages, corrections = self.tracker.analyze_pose_for_exercise(pose, 999, "start")
        
        self.assertEqual(score, 0.0)
        self.assertIn("Unknown exercise", corrections)
    
    def test_process_real_time_pose_valid(self):
        """Test processing real-time pose data"""
        # Start an exercise first
        self.tracker.start_exercise(1)
        
        # Create sample YOLO pose data
        yolo_pose_data = [{
            'keypoints': [[i*10, i*20] for i in range(17)],
            'confidences': [0.9] * 17,
            'person_id': 0
        }]
        
        feedback = self.tracker.process_real_time_pose(yolo_pose_data)
        
        self.assertIsNotNone(feedback)
        self.assertIsInstance(feedback, ExerciseFeedback)
        self.assertEqual(feedback.exercise_id, 1)
        self.assertIn("Holding up the Sky", feedback.exercise_name)
        self.assertIsInstance(feedback.form_score, float)
        self.assertIsInstance(feedback.completion_percentage, float)
        self.assertIsInstance(feedback.feedback_messages, list)
        self.assertIsInstance(feedback.corrections, list)
        self.assertIsInstance(feedback.pose_quality, dict)
        
        # Check that feedback was stored
        self.assertEqual(len(self.tracker.feedback_history), 1)
        self.assertEqual(len(self.tracker.pose_history), 1)
    
    def test_process_real_time_pose_no_exercise(self):
        """Test processing pose data without active exercise"""
        yolo_pose_data = [{
            'keypoints': [[i*10, i*20] for i in range(17)],
            'confidences': [0.9] * 17
        }]
        
        feedback = self.tracker.process_real_time_pose(yolo_pose_data)
        
        self.assertIsNone(feedback)
    
    def test_process_real_time_pose_poor_detection(self):
        """Test processing pose data with poor detection"""
        self.tracker.start_exercise(1)
        
        # Low confidence pose data
        yolo_pose_data = [{
            'keypoints': [[i*10, i*20] for i in range(17)],
            'confidences': [0.2] * 17  # Low confidence
        }]
        
        feedback = self.tracker.process_real_time_pose(yolo_pose_data)
        
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.form_score, 0.0)
        self.assertIn("not clearly detected", feedback.feedback_messages[0])
    
    def test_calculate_completion_percentage(self):
        """Test completion percentage calculation"""
        # No exercise started
        self.tracker.exercise_start_time = None
        completion = self.tracker._calculate_completion_percentage()
        self.assertEqual(completion, 0.0)
        
        # Exercise just started
        self.tracker.exercise_start_time = time.time()
        completion = self.tracker._calculate_completion_percentage()
        self.assertGreaterEqual(completion, 0.0)
        self.assertLessEqual(completion, 100.0)
        
        # Mock time progression
        self.tracker.exercise_start_time = time.time() - 10  # 10 seconds ago
        completion = self.tracker._calculate_completion_percentage()
        self.assertGreater(completion, 0.0)
        self.assertLessEqual(completion, 100.0)
    
    def test_calculate_pose_quality_metrics(self):
        """Test pose quality metrics calculation"""
        pose = PoseKeypoints(
            left_shoulder=(100, 200),
            right_shoulder=(200, 200),  # Level shoulders
            left_hip=(110, 300),
            right_hip=(190, 300),       # Level hips
            left_wrist=(90, 180),
            right_wrist=(210, 180)
        )
        
        metrics = self.tracker._calculate_pose_quality_metrics(pose)
        
        self.assertIsInstance(metrics, dict)
        self.assertIn("shoulder_alignment", metrics)
        self.assertIn("hip_alignment", metrics)
        self.assertIn("spine_alignment", metrics)
        self.assertIn("stability", metrics)
        
        # All metrics should be 0-100
        for metric_name, value in metrics.items():
            self.assertGreaterEqual(value, 0, f"{metric_name} should be >= 0")
            self.assertLessEqual(value, 100, f"{metric_name} should be <= 100")
    
    def test_calculate_movement_consistency(self):
        """Test movement consistency calculation"""
        # No scores
        consistency = self.tracker._calculate_movement_consistency()
        self.assertEqual(consistency, 0.0)
        
        # Add some scores
        self.tracker.session_stats["total_form_scores"] = [80, 85, 82, 88, 84]
        consistency = self.tracker._calculate_movement_consistency()
        
        self.assertIsInstance(consistency, float)
        self.assertGreaterEqual(consistency, 0.0)
        self.assertLessEqual(consistency, 100.0)
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        # No scores - should still return recommendations
        recommendations = self.tracker._generate_recommendations()
        self.assertIsInstance(recommendations, list)
        
        # Low average score
        self.tracker.session_stats["total_form_scores"] = [40, 45, 50]
        recommendations = self.tracker._generate_recommendations()
        self.assertIn("Focus on basic posture", " ".join(recommendations))
        
        # High average score
        self.tracker.session_stats["total_form_scores"] = [85, 90, 88, 92]
        recommendations = self.tracker._generate_recommendations()
        self.assertIn("Excellent form", " ".join(recommendations))
    
    def test_get_session_statistics(self):
        """Test getting session statistics"""
        # Add some data to session
        self.tracker.session_stats["exercises_attempted"] = 3
        self.tracker.session_stats["exercises_completed"] = 2
        self.tracker.session_stats["total_form_scores"] = [80, 85, 82]
        
        stats = self.tracker.get_session_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn("total_exercises_attempted", stats)
        self.assertIn("exercises_completed", stats)
        self.assertIn("average_form_score", stats)
        self.assertIn("session_duration", stats)
        self.assertIn("movement_consistency", stats)
        self.assertIn("recommendations", stats)
        
        self.assertEqual(stats["total_exercises_attempted"], 3)
        self.assertEqual(stats["exercises_completed"], 2)
        self.assertIsInstance(stats["average_form_score"], float)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_export_session_data_default_filename(self, mock_json_dump, mock_file):
        """Test exporting session data with default filename"""
        # Add some test data
        self.tracker.feedback_history = [{"test": "data"}]
        self.tracker.pose_history = [{"pose": "data"}]
        
        with patch('pathlib.Path.mkdir'):
            result = self.tracker.export_session_data()
        
        # Should return a filename
        self.assertIsInstance(result, str)
        self.assertIn("baduanjin_session_", result)
        
        # Verify file operations
        mock_file.assert_called_once()
        mock_json_dump.assert_called_once()
        
        # Check data structure
        call_args = mock_json_dump.call_args[0][0]
        self.assertIn("session_info", call_args)
        self.assertIn("session_statistics", call_args)
        self.assertIn("exercise_history", call_args)
        self.assertIn("pose_history", call_args)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_export_session_data_custom_filename(self, mock_json_dump, mock_file):
        """Test exporting session data with custom filename"""
        custom_filename = "test_export.json"
        
        with patch('pathlib.Path.mkdir'):
            result = self.tracker.export_session_data(custom_filename)
        
        self.assertIn(custom_filename, result)
        mock_file.assert_called_once()
        mock_json_dump.assert_called_once()
    
    def test_pose_history_management(self):
        """Test that pose history is managed properly"""
        self.tracker.start_exercise(1)
        
        # Add many poses to test buffer management
        for i in range(150):  # More than the 100 limit
            pose_dict = {
                "test_pose": i,
                "timestamp": time.time(),
                "phase": "test"
            }
            self.tracker.pose_history.append(pose_dict)
        
        # Should be trimmed to 50 (as per the logic in process_real_time_pose)
        yolo_pose_data = [{
            'keypoints': [[i*10, i*20] for i in range(17)],
            'confidences': [0.9] * 17
        }]
        
        # Process one pose to trigger trimming
        self.tracker.process_real_time_pose(yolo_pose_data)
        
        # History should be managed (trimmed)
        self.assertLessEqual(len(self.tracker.pose_history), 100)


class TestPositionVarianceCalculation(unittest.TestCase):
    """Test cases for position variance calculation"""
    
    def setUp(self):
        with patch('pathlib.Path.mkdir'):
            self.tracker = BaduanjinTracker()
    
    def test_calculate_position_variance_empty_poses(self):
        """Test variance calculation with empty pose list"""
        variance = self.tracker._calculate_position_variance([])
        self.assertEqual(variance, 0)
    
    def test_calculate_position_variance_single_pose(self):
        """Test variance calculation with single pose"""
        poses = [{"left_shoulder": (100, 200), "right_shoulder": (200, 200)}]
        variance = self.tracker._calculate_position_variance(poses)
        self.assertEqual(variance, 0)
    
    def test_calculate_position_variance_multiple_poses(self):
        """Test variance calculation with multiple poses"""
        poses = [
            {"left_shoulder": (100, 200), "right_shoulder": (200, 200), 
             "left_hip": (110, 300), "right_hip": (190, 300)},
            {"left_shoulder": (105, 205), "right_shoulder": (195, 195),
             "left_hip": (115, 305), "right_hip": (185, 295)},
            {"left_shoulder": (95, 195), "right_shoulder": (205, 205),
             "left_hip": (105, 295), "right_hip": (195, 305)}
        ]
        
        variance = self.tracker._calculate_position_variance(poses)
        
        self.assertIsInstance(variance, float)
        self.assertGreaterEqual(variance, 0)
    
    def test_calculate_position_variance_missing_joints(self):
        """Test variance calculation with missing joint data"""
        poses = [
            {"left_shoulder": (100, 200)},  # Missing other joints
            {"right_shoulder": (200, 200)}, # Different joints
        ]
        
        variance = self.tracker._calculate_position_variance(poses)
        
        # Should handle missing data gracefully
        self.assertIsInstance(variance, float)
        self.assertGreaterEqual(variance, 0)


class TestFactoryFunction(unittest.TestCase):
    """Test cases for factory function"""
    
    @patch('pathlib.Path.mkdir')
    def test_create_baduanjin_tracker(self, mock_mkdir):
        """Test factory function creates proper tracker instance"""
        tracker = create_baduanjin_tracker()
        
        self.assertIsInstance(tracker, BaduanjinTracker)
        self.assertIsNotNone(tracker.exercises)
        self.assertEqual(len(tracker.exercises), 8)
        self.assertIsNone(tracker.current_exercise)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios for complete workflows"""
    
    def setUp(self):
        with patch('pathlib.Path.mkdir'):
            self.tracker = BaduanjinTracker()
    
    def test_complete_exercise_session_workflow(self):
        """Test complete exercise session from start to finish"""
        # 1. Start exercise
        start_result = self.tracker.start_exercise(1)
        self.assertTrue(start_result["success"])
        self.assertEqual(start_result["exercise_id"], 1)
        
        # 2. Process multiple poses
        yolo_pose_data = [{
            'keypoints': [[i*10, i*20] for i in range(17)],
            'confidences': [0.9] * 17
        }]
        
        feedback_list = []
        for _ in range(5):  # Process 5 poses
            feedback = self.tracker.process_real_time_pose(yolo_pose_data)
            self.assertIsNotNone(feedback)
            feedback_list.append(feedback)
        
        # 3. Check session state
        self.assertEqual(len(self.tracker.feedback_history), 5)
        self.assertEqual(len(self.tracker.pose_history), 5)
        
        # 4. Get session statistics during exercise
        stats = self.tracker.get_session_statistics()
        self.assertIsInstance(stats, dict)
        self.assertGreater(stats["average_form_score"], 0)
        
        # 5. End exercise
        end_result = self.tracker.end_exercise()
        self.assertTrue(end_result["success"])
        self.assertIn("summary", end_result)
        
        # 6. Export session data
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                export_path = self.tracker.export_session_data()
                self.assertIsInstance(export_path, str)
                mock_file.assert_called_once()
                mock_json_dump.assert_called_once()
    
    def test_multiple_exercise_session(self):
        """Test session with multiple exercises"""
        exercises_to_test = [1, 2, 3]  # Test first 3 exercises
        
        for exercise_id in exercises_to_test:
            # Start exercise
            start_result = self.tracker.start_exercise(exercise_id)
            self.assertTrue(start_result["success"])
            
            # Process some poses
            yolo_pose_data = [{
                'keypoints': [[i*10, i*20] for i in range(17)],
                'confidences': [0.9] * 17
            }]
            
            for _ in range(3):
                feedback = self.tracker.process_real_time_pose(yolo_pose_data)
                self.assertIsNotNone(feedback)
                self.assertEqual(feedback.exercise_id, exercise_id)
            
            # End exercise
            end_result = self.tracker.end_exercise()
            self.assertTrue(end_result["success"])
        
        # Check final session stats
        stats = self.tracker.get_session_statistics()
        self.assertEqual(stats["total_exercises_attempted"], 3)
        self.assertEqual(stats["exercises_completed"], 3)
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        # 1. Invalid exercise ID
        result = self.tracker.start_exercise(999)
        self.assertFalse(result["success"])
        
        # 2. End exercise without starting
        result = self.tracker.end_exercise()
        self.assertFalse(result["success"])
        
        # 3. Process pose without exercise
        yolo_pose_data = [{'keypoints': [[0]*2]*17, 'confidences': [0.9]*17}]
        feedback = self.tracker.process_real_time_pose(yolo_pose_data)
        self.assertIsNone(feedback)
        
        # 4. Malformed pose data
        self.tracker.start_exercise(1)
        malformed_data = [{'keypoints': [], 'confidences': []}]  # Empty data
        feedback = self.tracker.process_real_time_pose(malformed_data)
        self.assertIsNotNone(feedback)  # Should return feedback indicating poor detection
        self.assertEqual(feedback.form_score, 0.0)
    
    def test_session_statistics_evolution(self):
        """Test how session statistics evolve over time"""
        # Initial state
        initial_stats = self.tracker.get_session_statistics()
        self.assertEqual(initial_stats["total_exercises_attempted"], 0)
        self.assertEqual(initial_stats["exercises_completed"], 0)
        
        # Start and complete exercise
        self.tracker.start_exercise(1)
        
        # Add varying scores to test average calculation
        self.tracker.session_stats["total_form_scores"] = [70, 80, 85, 90, 75]
        
        end_stats = self.tracker.get_session_statistics()
        self.assertEqual(end_stats["total_exercises_attempted"], 1)
        self.assertEqual(end_stats["average_form_score"], 80.0)  # Average of the scores
        
        # Movement consistency should be calculated
        self.assertIsInstance(end_stats["movement_consistency"], float)
        self.assertGreaterEqual(end_stats["movement_consistency"], 0)
        
        # Should have recommendations
        self.assertIsInstance(end_stats["recommendations"], list)
        self.assertGreater(len(end_stats["recommendations"]), 0)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestPoseKeypoints))
    suite.addTests(loader.loadTestsFromTestCase(TestExerciseFeedback))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionStats))
    suite.addTests(loader.loadTestsFromTestCase(TestBaduanjinTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestPositionVarianceCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestFactoryFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"BADUANJIN TRACKER UNIT TESTS SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, trace in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n💥 ERRORS ({len(result.errors)}):")
        for test, trace in result.errors:
            print(f"  - {test}")
    
    if result.wasSuccessful():
        print(f"\n🎉 ALL TESTS PASSED! The Baduanjin Tracker is working perfectly!")
    
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
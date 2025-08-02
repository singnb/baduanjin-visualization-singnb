# type: ignore
# /tests/services/test_video_processor.py
# Unit tests for service/test_video_processor.pyy core functions

import os
import sys
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from sqlalchemy.orm import Session

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import models
from services.video_processor import (
    process_video,
    analyze_video_data,
    process_joint_angles,
    process_balance_metrics,
    process_smoothness,
    process_symmetry,
    generate_recommendations
)


class TestVideoProcessor:
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_video(self):
        """Mock video upload object"""
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.video_path = "/test/path/video.mp4"
        video.processing_status = "uploaded"
        video.brocade_type = "lifting_the_sky"
        video.json_path = None
        return video
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Mock analysis result object"""
        analysis = Mock(spec=models.AnalysisResult)
        analysis.video_id = 1
        analysis.joint_angle_data = "{}"
        analysis.balance_data = "{}"
        analysis.smoothness_data = "{}"
        analysis.symmetry_data = "{}"
        analysis.recommendations = "[]"
        return analysis
    
    @pytest.fixture
    def sample_pose_data(self):
        """Sample pose data for testing"""
        return {
            "frames": [
                {
                    "keypoints": [[100, 200, 0.9], [150, 250, 0.8]],
                    "frame_id": 0
                },
                {
                    "keypoints": [[102, 202, 0.9], [152, 252, 0.8]],
                    "frame_id": 1
                }
            ]
        }


class TestProcessVideo:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_video(self):
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.video_path = "/test/path/video.mp4"
        video.processing_status = "uploaded"
        video.brocade_type = "lifting_the_sky"
        video.json_path = None
        return video
    
    def test_process_video_not_found(self, mock_db):
        """Test processing when video not found in database"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Should not raise exception, just log error
        process_video(999, mock_db)
        
        # Verify database was queried
        mock_db.query.assert_called_once_with(models.VideoUpload)
    
    @patch('services.video_processor.analyze_video_data')
    @patch('subprocess.run')
    @patch('os.listdir')
    @patch('os.makedirs')
    def test_process_video_success(self, mock_makedirs, mock_listdir, mock_subprocess, mock_analyze, mock_db, mock_video):
        """Test successful video processing"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        mock_subprocess.return_value.returncode = 0
        mock_listdir.return_value = ["predictions.json"]
        
        # Execute
        process_video(1, mock_db)
        
        # Verify status updates
        assert mock_video.processing_status == "completed"
        assert mock_video.json_path is not None
        mock_db.commit.assert_called()
        mock_analyze.assert_called_once_with(1, mock_db)
    
    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_process_video_subprocess_failure(self, mock_makedirs, mock_subprocess, mock_db, mock_video):
        """Test processing when subprocess fails"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Processing error"
        
        # Execute
        process_video(1, mock_db)
        
        # Verify failure handling
        assert mock_video.processing_status == "failed"
        mock_db.commit.assert_called()
    
    @patch('subprocess.run')
    @patch('os.listdir')
    @patch('os.makedirs')
    def test_process_video_no_json_generated(self, mock_makedirs, mock_listdir, mock_subprocess, mock_db, mock_video):
        """Test processing when no JSON files are generated"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        mock_subprocess.return_value.returncode = 0
        mock_listdir.return_value = []  # No JSON files
        
        # Execute
        process_video(1, mock_db)
        
        # Verify failure handling
        assert mock_video.processing_status == "failed"
        mock_db.commit.assert_called()
    
    @patch('services.video_processor.analyze_video_data')
    @patch('subprocess.run')
    @patch('os.listdir')
    @patch('os.makedirs')
    def test_process_video_exception_handling(self, mock_makedirs, mock_listdir, mock_subprocess, mock_analyze, mock_db, mock_video):
        """Test exception handling during processing"""
        # Setup mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        mock_subprocess.side_effect = Exception("Subprocess error")
        
        # Execute
        process_video(1, mock_db)
        
        # Verify error handling - should attempt to update status
        mock_db.query.assert_called()


class TestAnalyzeVideoData:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_video(self):
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.json_path = "/test/path/predictions.json"
        video.brocade_type = "lifting_the_sky"
        return video
    
    @pytest.fixture
    def sample_pose_data(self):
        return {
            "frames": [
                {"keypoints": [[100, 200, 0.9]], "frame_id": 0},
                {"keypoints": [[102, 202, 0.8]], "frame_id": 1}
            ]
        }
    
    def test_analyze_video_data_video_not_found(self, mock_db):
        """Test analysis when video not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        analyze_video_data(999, mock_db)
        
        mock_db.query.assert_called_once_with(models.VideoUpload)
    
    def test_analyze_video_data_no_json_path(self, mock_db, mock_video):
        """Test analysis when video has no JSON path"""
        mock_video.json_path = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        analyze_video_data(1, mock_db)
        
        # Should exit early without processing
        mock_db.query.assert_called_once()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_analyze_video_data_create_new_analysis(self, mock_file, mock_exists, mock_db, mock_video, sample_pose_data):
        """Test creating new analysis result"""
        # Setup mocks
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_pose_data)
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_video, None]  # Video exists, analysis doesn't
        
        # Execute
        analyze_video_data(1, mock_db)
        
        # Verify new analysis was added
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_analyze_video_data_json_parse_error(self, mock_file, mock_exists, mock_db, mock_video):
        """Test handling of JSON parsing errors"""
        # Setup mocks
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        # Execute - should handle exception gracefully
        analyze_video_data(1, mock_db)
        
        # Should not crash, error should be logged


class TestAnalysisFunctions:
    
    @pytest.fixture
    def sample_pose_data(self):
        return {
            "frames": [
                {"keypoints": [[100, 200, 0.9]], "frame_id": i}
                for i in range(10)
            ]
        }
    
    def test_process_joint_angles(self, sample_pose_data):
        """Test joint angle processing"""
        result = process_joint_angles(sample_pose_data, "lifting_the_sky")
        
        assert "angles" in result
        assert isinstance(result["angles"], list)
        assert len(result["angles"]) > 0
        
        # Check structure of angle data
        angle_item = result["angles"][0]
        assert "frame" in angle_item
        assert "knee" in angle_item
        assert "elbow" in angle_item
    
    def test_process_balance_metrics(self, sample_pose_data):
        """Test balance metrics processing"""
        result = process_balance_metrics(sample_pose_data, "lifting_the_sky")
        
        assert "stability" in result
        assert isinstance(result["stability"], list)
        assert len(result["stability"]) > 0
        
        # Check structure of balance data
        balance_item = result["stability"][0]
        assert "frame" in balance_item
        assert "value" in balance_item
        assert 0 <= balance_item["value"] <= 1  # Stability should be normalized
    
    def test_process_smoothness(self, sample_pose_data):
        """Test smoothness processing"""
        result = process_smoothness(sample_pose_data, "lifting_the_sky")
        
        assert "jerk" in result
        assert isinstance(result["jerk"], list)
        assert len(result["jerk"]) > 0
        
        # Check structure of smoothness data
        jerk_item = result["jerk"][0]
        assert "frame" in jerk_item
        assert "value" in jerk_item
        assert jerk_item["value"] >= 0  # Jerk should be non-negative
    
    def test_process_symmetry(self, sample_pose_data):
        """Test symmetry processing"""
        result = process_symmetry(sample_pose_data, "lifting_the_sky")
        
        assert "leftRight" in result
        assert isinstance(result["leftRight"], list)
        assert len(result["leftRight"]) > 0
        
        # Check structure of symmetry data
        symmetry_item = result["leftRight"][0]
        assert "frame" in symmetry_item
        assert "value" in symmetry_item
        assert 0 <= symmetry_item["value"] <= 1  # Symmetry should be normalized
    
    def test_analysis_functions_with_different_brocade_types(self, sample_pose_data):
        """Test analysis functions with different brocade types"""
        brocade_types = ["lifting_the_sky", "drawing_bow", "single_whip"]
        
        for brocade_type in brocade_types:
            joint_result = process_joint_angles(sample_pose_data, brocade_type)
            balance_result = process_balance_metrics(sample_pose_data, brocade_type)
            smoothness_result = process_smoothness(sample_pose_data, brocade_type)
            symmetry_result = process_symmetry(sample_pose_data, brocade_type)
            
            assert joint_result["angles"]
            assert balance_result["stability"]
            assert smoothness_result["jerk"]
            assert symmetry_result["leftRight"]


class TestGenerateRecommendations:
    
    @pytest.fixture
    def sample_analysis_data(self):
        return {
            "joint_angle_data": {"angles": [{"frame": i, "knee": 120, "elbow": 90} for i in range(100)]},
            "balance_data": {"stability": [{"frame": i, "value": 0.7} for i in range(100)]},
            "smoothness_data": {"jerk": [{"frame": i, "value": 0.5} for i in range(100)]},
            "symmetry_data": {"leftRight": [{"frame": i, "value": 0.6} for i in range(100)]}
        }
    
    def test_generate_recommendations_knee_flexion_issue(self, sample_analysis_data):
        """Test recommendations for knee flexion issues"""
        recommendations = generate_recommendations(
            sample_analysis_data["joint_angle_data"],
            sample_analysis_data["balance_data"],
            sample_analysis_data["smoothness_data"],
            sample_analysis_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate knee flexion recommendation (avg knee angle 120 < 130)
        knee_rec = next((r for r in recommendations if r["issue"] == "knee_flexion"), None)
        assert knee_rec is not None
        assert knee_rec["category"] == "joint_angle"
        assert "knee angle" in knee_rec["message"]
    
    def test_generate_recommendations_balance_issue(self, sample_analysis_data):
        """Test recommendations for balance issues"""
        recommendations = generate_recommendations(
            sample_analysis_data["joint_angle_data"],
            sample_analysis_data["balance_data"],
            sample_analysis_data["smoothness_data"],
            sample_analysis_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate balance recommendation (avg stability 0.7 < 0.8)
        balance_rec = next((r for r in recommendations if r["issue"] == "stability"), None)
        assert balance_rec is not None
        assert balance_rec["category"] == "balance"
        assert "balance" in balance_rec["message"]
    
    def test_generate_recommendations_smoothness_issue(self, sample_analysis_data):
        """Test recommendations for smoothness issues"""
        recommendations = generate_recommendations(
            sample_analysis_data["joint_angle_data"],
            sample_analysis_data["balance_data"],
            sample_analysis_data["smoothness_data"],
            sample_analysis_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate smoothness recommendation (avg jerk 0.5 > 0.4)
        smoothness_rec = next((r for r in recommendations if r["issue"] == "jerkiness"), None)
        assert smoothness_rec is not None
        assert smoothness_rec["category"] == "smoothness"
        assert "fluid" in smoothness_rec["message"]
    
    def test_generate_recommendations_symmetry_issue(self, sample_analysis_data):
        """Test recommendations for symmetry issues"""
        recommendations = generate_recommendations(
            sample_analysis_data["joint_angle_data"],
            sample_analysis_data["balance_data"],
            sample_analysis_data["smoothness_data"],
            sample_analysis_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate symmetry recommendation (avg symmetry 0.6 < 0.7)
        symmetry_rec = next((r for r in recommendations if r["issue"] == "imbalance"), None)
        assert symmetry_rec is not None
        assert symmetry_rec["category"] == "symmetry"
        assert "both sides" in symmetry_rec["message"]
    
    def test_generate_recommendations_no_issues(self):
        """Test recommendations when no issues are detected"""
        # Perfect data - no issues
        perfect_data = {
            "joint_angle_data": {"angles": [{"frame": i, "knee": 150, "elbow": 90} for i in range(100)]},
            "balance_data": {"stability": [{"frame": i, "value": 0.9} for i in range(100)]},
            "smoothness_data": {"jerk": [{"frame": i, "value": 0.1} for i in range(100)]},
            "symmetry_data": {"leftRight": [{"frame": i, "value": 0.8} for i in range(100)]}
        }
        
        recommendations = generate_recommendations(
            perfect_data["joint_angle_data"],
            perfect_data["balance_data"],
            perfect_data["smoothness_data"],
            perfect_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate no recommendations
        assert len(recommendations) == 0
    
    def test_generate_recommendations_all_issues(self):
        """Test recommendations when all issues are present"""
        # Poor performance data - all issues
        poor_data = {
            "joint_angle_data": {"angles": [{"frame": i, "knee": 100, "elbow": 45} for i in range(100)]},
            "balance_data": {"stability": [{"frame": i, "value": 0.5} for i in range(100)]},
            "smoothness_data": {"jerk": [{"frame": i, "value": 0.8} for i in range(100)]},
            "symmetry_data": {"leftRight": [{"frame": i, "value": 0.4} for i in range(100)]}
        }
        
        recommendations = generate_recommendations(
            poor_data["joint_angle_data"],
            poor_data["balance_data"],
            poor_data["smoothness_data"],
            poor_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate all 4 types of recommendations
        assert len(recommendations) == 4
        categories = [r["category"] for r in recommendations]
        assert "joint_angle" in categories
        assert "balance" in categories
        assert "smoothness" in categories
        assert "symmetry" in categories
    
    def test_generate_recommendations_different_brocade_types(self, sample_analysis_data):
        """Test recommendations work with different brocade types"""
        brocade_types = ["lifting_the_sky", "drawing_bow", "single_whip"]
        
        for brocade_type in brocade_types:
            recommendations = generate_recommendations(
                sample_analysis_data["joint_angle_data"],
                sample_analysis_data["balance_data"],
                sample_analysis_data["smoothness_data"],
                sample_analysis_data["symmetry_data"],
                brocade_type
            )
            
            # Should generate recommendations regardless of brocade type
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0


class TestErrorHandling:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    def test_analyze_video_data_file_read_error(self, mock_db):
        """Test handling of file read errors during analysis"""
        mock_video = Mock()
        mock_video.json_path = "/nonexistent/path.json"
        mock_video.brocade_type = "lifting_the_sky"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=IOError("File read error")):
            
            # Should handle file read error gracefully
            analyze_video_data(1, mock_db)
    
    def test_analysis_functions_empty_data(self):
        """Test analysis functions with empty data"""
        empty_data = {"frames": []}
        
        # Should handle empty data gracefully
        joint_result = process_joint_angles(empty_data, "lifting_the_sky")
        balance_result = process_balance_metrics(empty_data, "lifting_the_sky")
        smoothness_result = process_smoothness(empty_data, "lifting_the_sky")
        symmetry_result = process_symmetry(empty_data, "lifting_the_sky")
        
        # All should return valid structures even with empty input
        assert isinstance(joint_result, dict)
        assert isinstance(balance_result, dict)
        assert isinstance(smoothness_result, dict)
        assert isinstance(symmetry_result, dict)


class TestIntegrationScenarios:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_video(self):
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.video_path = "/test/path/video.mp4"
        video.processing_status = "uploaded"
        video.brocade_type = "lifting_the_sky"
        video.json_path = None
        return video
    
    @patch('services.video_processor.analyze_video_data')
    @patch('subprocess.run')
    @patch('os.listdir')
    @patch('os.makedirs')
    def test_complete_processing_workflow(self, mock_makedirs, mock_listdir, mock_subprocess, mock_analyze, mock_db, mock_video):
        """Test complete video processing workflow"""
        # Setup successful processing
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        mock_subprocess.return_value.returncode = 0
        mock_listdir.return_value = ["predictions.json"]
        
        # Execute processing
        process_video(1, mock_db)
        
        # Verify complete workflow
        assert mock_video.processing_status == "completed"
        assert mock_video.json_path is not None
        mock_analyze.assert_called_once_with(1, mock_db)
        mock_db.commit.assert_called()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_complete_analysis_workflow(self, mock_file, mock_exists, mock_db):
        """Test complete analysis workflow"""
        # Setup video and pose data
        mock_video = Mock()
        mock_video.id = 1
        mock_video.json_path = "/test/predictions.json"
        mock_video.brocade_type = "lifting_the_sky"
        
        sample_data = {"frames": [{"keypoints": [[100, 200, 0.9]], "frame_id": 0}]}
        
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_data)
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_video, None]
        
        # Execute analysis
        analyze_video_data(1, mock_db)
        
        # Verify analysis workflow
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestPerformanceAndEdgeCases:
    
    def test_large_pose_data_processing(self):
        """Test processing with large pose data"""
        # Create large dataset
        large_data = {
            "frames": [
                {"keypoints": [[i, i+100, 0.9]], "frame_id": i}
                for i in range(1000)  # 1000 frames
            ]
        }
        
        # Should handle large datasets efficiently
        joint_result = process_joint_angles(large_data, "lifting_the_sky")
        assert len(joint_result["angles"]) > 0
    
    def test_malformed_pose_data(self):
        """Test handling of malformed pose data"""
        malformed_data = {
            "frames": [
                {"invalid_key": "invalid_value"},
                {"keypoints": "not_a_list"},
                {"keypoints": [[]], "frame_id": "not_a_number"}
            ]
        }
        
        # Should handle malformed data gracefully without crashing
        try:
            process_joint_angles(malformed_data, "lifting_the_sky")
            process_balance_metrics(malformed_data, "lifting_the_sky")
            process_smoothness(malformed_data, "lifting_the_sky")
            process_symmetry(malformed_data, "lifting_the_sky")
        except Exception as e:
            pytest.fail(f"Functions should handle malformed data gracefully, but raised: {e}")
    
    def test_extreme_analysis_values(self):
        """Test recommendation generation with extreme values"""
        extreme_data = {
            "joint_angle_data": {"angles": [{"frame": i, "knee": 0, "elbow": 0} for i in range(10)]},
            "balance_data": {"stability": [{"frame": i, "value": 0.0} for i in range(10)]},
            "smoothness_data": {"jerk": [{"frame": i, "value": 1.0} for i in range(10)]},
            "symmetry_data": {"leftRight": [{"frame": i, "value": 0.0} for i in range(10)]}
        }
        
        recommendations = generate_recommendations(
            extreme_data["joint_angle_data"],
            extreme_data["balance_data"],
            extreme_data["smoothness_data"],
            extreme_data["symmetry_data"],
            "lifting_the_sky"
        )
        
        # Should generate recommendations for all issues
        assert len(recommendations) == 4
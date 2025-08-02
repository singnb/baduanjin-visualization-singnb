# type: ignore
# /test/routers/test_analysis_with_master.py
# Unit tests for routers/analysis_with_master.py core functions

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the modules to test
from routers.analysis_with_master import (
    router,
    read_json_file_azure_local,
    json_file_exists,
    run_extract_json_files,
    run_results_analysis,
    get_master_videos,
    get_user_extracted_videos,
    get_master_extracted_videos,
    extract_json_files,
    analyze_video_with_results_analysis,
    get_master_data,
    get_analysis_data_file,
    compare_analysis,
    generate_comparison_recommendations
)
import models
import database

class TestLocalJSONOperations:
    """Test local JSON file operations without Azure"""
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.path.exists')
    @patch('routers.analysis_with_master.os.getenv')
    @patch('builtins.open', create=True)
    async def test_read_json_file_local_success(self, mock_open, mock_getenv, mock_exists):
        """Test reading JSON file from local storage"""
        # Mock no Azure connection
        mock_getenv.return_value = None
        
        # Mock local file exists
        mock_exists.return_value = True
        
        # Mock file content
        test_data = {"test": "data", "values": [1, 2, 3]}
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_data)
        
        result = await read_json_file_azure_local(1, 1, "test.json")
        
        assert result == test_data
        mock_open.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.path.exists')
    @patch('routers.analysis_with_master.os.getenv')
    async def test_read_json_file_not_found(self, mock_getenv, mock_exists):
        """Test reading JSON file when it doesn't exist"""
        # Mock no Azure connection
        mock_getenv.return_value = None
        
        # Mock local file doesn't exist
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            await read_json_file_azure_local(1, 1, "nonexistent.json")
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.path.exists')
    @patch('routers.analysis_with_master.os.getenv')
    async def test_json_file_exists_local_true(self, mock_getenv, mock_exists):
        """Test checking if JSON file exists locally - true case"""
        # Mock no Azure connection
        mock_getenv.return_value = None
        
        # Mock local file exists
        mock_exists.return_value = True
        
        result = await json_file_exists(1, 1, "test.json")
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.path.exists')
    @patch('routers.analysis_with_master.os.getenv')
    async def test_json_file_exists_local_false(self, mock_getenv, mock_exists):
        """Test checking if JSON file exists locally - false case"""
        # Mock no Azure connection
        mock_getenv.return_value = None
        
        # Mock local file doesn't exist
        mock_exists.return_value = False
        
        result = await json_file_exists(1, 1, "test.json")
        
        assert result is False

class TestScriptExecution:
    """Test script execution functions"""
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.subprocess.run')
    @patch('routers.analysis_with_master.os.path.join')
    @patch('routers.analysis_with_master.os.getcwd')
    async def test_run_extract_json_files_success(self, mock_getcwd, mock_join, mock_subprocess):
        """Test successful extraction of JSON files"""
        mock_getcwd.return_value = "/app"
        mock_join.side_effect = lambda *args: "/".join(args)
        
        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Extraction completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = await run_extract_json_files(
            "input/dir", "output/dir", 1, 1, "master"
        )
        
        assert result is True
        mock_subprocess.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.subprocess.run')
    @patch('routers.analysis_with_master.os.getcwd')
    async def test_run_extract_json_files_failure(self, mock_getcwd, mock_subprocess):
        """Test failed extraction of JSON files"""
        mock_getcwd.return_value = "/app"
        
        # Mock failed subprocess
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Extraction failed"
        mock_subprocess.return_value = mock_result
        
        result = await run_extract_json_files(
            "input/dir", "output/dir", 1, 1, "master"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.subprocess.run')
    @patch('routers.analysis_with_master.os.listdir')
    @patch('routers.analysis_with_master.os.path.join')
    @patch('routers.analysis_with_master.os.getcwd')
    async def test_run_results_analysis_success(self, mock_getcwd, mock_join, mock_listdir, mock_subprocess):
        """Test successful results analysis"""
        mock_getcwd.return_value = "/app"
        mock_join.side_effect = lambda *args: "/".join(args)
        
        # Mock directory contents
        mock_listdir.return_value = ["results_123.json", "video.mp4", "other_file.txt"]
        
        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = await run_results_analysis(1, 1)
        
        assert result is True
        mock_subprocess.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.listdir')
    @patch('routers.analysis_with_master.os.getcwd')
    async def test_run_results_analysis_no_results(self, mock_getcwd, mock_listdir):
        """Test results analysis when no results files found"""
        mock_getcwd.return_value = "/app"
        
        # Mock directory with no results files
        mock_listdir.return_value = ["video.mp4", "other_file.txt"]
        
        result = await run_results_analysis(1, 1)
        
        assert result is False

class TestMasterVideoEndpoints:
    """Test master video related endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_master(self):
        master = Mock()
        master.id = 2
        master.role = "master"
        return master
    
    @pytest.fixture
    def mock_videos(self):
        videos = []
        for i in range(3):
            video = Mock()
            video.id = i + 1
            video.user_id = 2  # Master's videos
            video.title = f"Master Video {i + 1}"
            video.processing_status = "completed"
            video.analyzed_video_path = f"/path/to/analyzed_{i + 1}.mp4"
            videos.append(video)
        return videos
    
    @pytest.mark.asyncio
    async def test_get_master_videos_success(self, mock_db, mock_user, mock_master, mock_videos):
        """Test successful retrieval of master videos"""
        # Mock master query
        master_query = Mock()
        master_query.filter.return_value = master_query
        master_query.first.return_value = mock_master
        
        # Mock videos query
        videos_query = Mock()
        videos_query.filter.return_value = videos_query
        videos_query.all.return_value = mock_videos
        
        # Setup query side effect
        def mock_query_side_effect(model):
            if model == models.User:
                return master_query
            elif model == models.VideoUpload:
                return videos_query
            return Mock()
        
        mock_db.query.side_effect = mock_query_side_effect
        
        result = await get_master_videos(master_id=2, current_user=mock_user, db=mock_db)
        
        assert len(result) == 3
        assert result[0].title == "Master Video 1"
    
    @pytest.mark.asyncio
    async def test_get_master_videos_not_found(self, mock_db, mock_user):
        """Test master videos when master not found"""
        # Mock master query returning None
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_master_videos(master_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Master not found" in str(exc_info.value.detail)

class TestUserExtractedVideos:
    """Test user extracted videos endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_learner(self):
        user = Mock()
        user.id = 1
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_videos(self):
        videos = []
        for i in range(2):
            video = Mock()
            video.id = i + 1
            video.user_id = 1
            video.title = f"User Video {i + 1}"
            video.processing_status = "completed"
            videos.append(video)
        return videos
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.json_file_exists')
    async def test_get_user_extracted_videos_success(self, mock_json_exists, mock_db, mock_learner, mock_videos):
        """Test successful retrieval of user extracted videos"""
        # Mock videos query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_videos
        mock_db.query.return_value = mock_query
        
        # Mock that JSON files exist for first video only
        mock_json_exists.side_effect = [True, False]
        
        result = await get_user_extracted_videos(current_user=mock_learner, db=mock_db)
        
        assert len(result) == 1
        assert result[0].title == "User Video 1"
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.json_file_exists')
    async def test_get_master_extracted_videos_success(self, mock_json_exists, mock_db, mock_learner):
        """Test successful retrieval of master extracted videos"""
        # Mock master
        mock_master = Mock()
        mock_master.id = 2
        mock_master.role = "master"
        
        # Mock master videos
        mock_videos = [Mock(id=1, user_id=2, title="Master Video 1", processing_status="completed")]
        
        # Setup query side effects
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            if model == models.User:
                mock_query.first.return_value = mock_master
            elif model == models.VideoUpload:
                mock_query.all.return_value = mock_videos
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock JSON file exists
        mock_json_exists.return_value = True
        
        result = await get_master_extracted_videos(master_id=2, current_user=mock_learner, db=mock_db)
        
        assert len(result) == 1
        assert result[0].title == "Master Video 1"

class TestExtractEndpoint:
    """Test JSON extraction endpoint"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock()
        video.id = 1
        video.user_id = 1
        video.title = "Test Video"
        video.processing_status = "completed"
        return video
    
    @pytest.mark.asyncio
    async def test_extract_json_files_video_not_found(self, mock_db, mock_user):
        """Test extraction when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await extract_json_files(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_extract_json_files_not_completed(self, mock_db, mock_user, mock_video):
        """Test extraction when video not completed"""
        mock_video.processing_status = "processing"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await extract_json_files(video_id=1, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 400
        assert "must be completed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.path.exists')
    async def test_extract_json_files_no_analysis_dir(self, mock_exists, mock_db, mock_user, mock_video):
        """Test extraction when no analysis directory exists"""
        # Mock video owner query
        mock_owner = Mock()
        mock_owner.role = "learner"
        
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            if model == models.VideoUpload:
                mock_query.first.return_value = mock_video
            elif model == models.User:
                mock_query.first.return_value = mock_owner
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock that analysis directory doesn't exist
        mock_exists.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await extract_json_files(video_id=1, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 400
        assert "No video analysis found" in str(exc_info.value.detail)

class TestAnalysisEndpoint:
    """Test analysis endpoint"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock()
        video.id = 1
        video.user_id = 1
        video.title = "Test Video"
        video.processing_status = "completed"
        return video
    
    @pytest.mark.asyncio
    async def test_analyze_video_not_found(self, mock_db, mock_user):
        """Test analysis when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await analyze_video_with_results_analysis(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.os.path.exists')
    async def test_analyze_video_already_analyzed(self, mock_exists, mock_db, mock_user, mock_video):
        """Test analysis when already analyzed"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock that analysis report already exists
        mock_exists.return_value = True
        
        result = await analyze_video_with_results_analysis(video_id=1, current_user=mock_user, db=mock_db)
        
        assert result["status"] == "already_analyzed"
        assert "already analyzed" in result["message"]

class TestDataRetrieval:
    """Test data retrieval endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock()
        video.id = 1
        video.user_id = 2
        video.title = "Master Video"
        video.brocade_type = "BROCADE_1"
        return video
    
    @pytest.fixture
    def mock_master(self):
        master = Mock()
        master.id = 2
        master.name = "Master User"
        master.email = "master@example.com"
        master.role = "master"
        return master
    
    @pytest.mark.asyncio
    async def test_get_master_data_video_not_found(self, mock_db, mock_user):
        """Test getting master data when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_master_data(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.read_json_file_azure_local')
    async def test_get_master_data_success(self, mock_read_json, mock_db, mock_user, mock_video, mock_master):
        """Test successful master data retrieval"""
        # Setup query side effects
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            if model == models.VideoUpload:
                mock_query.first.return_value = mock_video
            elif model == models.User:
                mock_query.first.return_value = mock_master
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock JSON file reading
        mock_read_json.side_effect = [
            {"angles": "data"},
            {"smoothness": "data"},
            {"symmetry": "data"},
            {"balance": "data"},
            {"recommendations": "data"}
        ]
        
        result = await get_master_data(video_id=1, current_user=mock_user, db=mock_db)
        
        assert "masterData" in result
        assert "videoData" in result
        assert "analysisData" in result
        assert result["masterData"]["name"] == "Master User"
        assert result["videoData"]["title"] == "Master Video"
    
    @pytest.mark.asyncio
    async def test_get_analysis_data_file_not_found(self, mock_db, mock_user):
        """Test getting analysis data file when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_data_file(video_id=999, file_name="test.json", current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)

class TestComparison:
    """Test comparison functionality"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        return user
    
    @pytest.fixture
    def mock_user_video(self):
        video = Mock()
        video.id = 1
        video.user_id = 1
        video.title = "User Video"
        return video
    
    @pytest.fixture
    def mock_master_video(self):
        video = Mock()
        video.id = 2
        video.user_id = 2
        video.title = "Master Video"
        return video
    
    @pytest.mark.asyncio
    async def test_compare_analysis_user_video_not_found(self, mock_db, mock_user):
        """Test comparison when user video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await compare_analysis(user_video_id=999, master_video_id=1, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "User video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.read_json_file_azure_local')
    async def test_compare_analysis_success(self, mock_read_json, mock_db, mock_user, mock_user_video, mock_master_video):
        """Test successful analysis comparison"""
        # Setup query side effects
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            # Return appropriate video based on which query is called
            if hasattr(mock_query.filter, 'call_count'):
                if mock_query.filter.call_count == 1:
                    mock_query.first.return_value = mock_user_video
                else:
                    mock_query.first.return_value = mock_master_video
            else:
                mock_query.first.return_value = mock_user_video
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock JSON file reading for user and master data
        mock_read_json.side_effect = [
            {"joint_angles": "user_data"},    # user joint_angles
            {"smoothness": "user_data"},       # user smoothness
            {"symmetry": "user_data"},         # user symmetry
            {"balance": "user_data"},          # user balance
            {"joint_angles": "master_data"},   # master joint_angles
            {"smoothness": "master_data"},     # master smoothness
            {"symmetry": "master_data"},       # master symmetry
            {"balance": "master_data"}         # master balance
        ]
        
        result = await compare_analysis(user_video_id=1, master_video_id=2, current_user=mock_user, db=mock_db)
        
        assert "userJointAngles" in result
        assert "masterJointAngles" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

class TestComparisonRecommendations:
    """Test comparison recommendations generation"""
    
    def test_generate_comparison_recommendations_basic(self):
        """Test basic recommendation generation"""
        user_data = {
            'smoothness': {'overallSmoothness': 1.5},
            'symmetry': {'overallSymmetry': 0.8},
            'balance': {'overallStability': 0.7}
        }
        
        master_data = {
            'smoothness': {'overallSmoothness': 0.9},
            'symmetry': {'overallSymmetry': 0.95},
            'balance': {'overallStability': 0.9}
        }
        
        recommendations = generate_comparison_recommendations(user_data, master_data)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should include recommendations for smoothness, symmetry, and balance
        smoothness_rec = any("smoothness" in rec.lower() for rec in recommendations)
        symmetry_rec = any("symmetry" in rec.lower() for rec in recommendations)
        balance_rec = any("balance" in rec.lower() or "stability" in rec.lower() for rec in recommendations)
        
        assert smoothness_rec
        assert symmetry_rec  
        assert balance_rec
    
    def test_generate_comparison_recommendations_good_performance(self):
        """Test recommendations when user performance is good"""
        user_data = {
            'smoothness': {'overallSmoothness': 0.85},
            'symmetry': {'overallSymmetry': 0.95},
            'balance': {'overallStability': 0.92}
        }
        
        master_data = {
            'smoothness': {'overallSmoothness': 0.9},
            'symmetry': {'overallSymmetry': 0.95},
            'balance': {'overallStability': 0.9}
        }
        
        recommendations = generate_comparison_recommendations(user_data, master_data)
        
        # Should still include general recommendations
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 4  # At least the 4 general recommendations
        
        # Should include general advice
        general_advice = any("master's key pose" in rec.lower() for rec in recommendations)
        assert general_advice
    
    def test_generate_comparison_recommendations_joint_angles(self):
        """Test recommendations with joint angle data"""
        user_data = {
            'smoothness': {'overallSmoothness': 0.9},
            'symmetry': {'overallSymmetry': 0.9},
            'balance': {'overallStability': 0.9},
            'joint_angles': {
                'rangeOfMotion': {
                    'shoulder_left': {'min': 10, 'max': 80},
                    'shoulder_right': {'min': 15, 'max': 85}
                }
            }
        }
        
        master_data = {
            'smoothness': {'overallSmoothness': 0.9},
            'symmetry': {'overallSymmetry': 0.95},
            'balance': {'overallStability': 0.9},
            'joint_angles': {
                'rangeOfMotion': {
                    'shoulder_left': {'min': 5, 'max': 95},  # Larger range
                    'shoulder_right': {'min': 5, 'max': 95}  # Larger range
                }
            }
        }
        
        recommendations = generate_comparison_recommendations(user_data, master_data)
        
        # Should include range of motion recommendations
        rom_rec = any("range of motion" in rec.lower() for rec in recommendations)
        assert rom_rec

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        return user
    
    @pytest.mark.asyncio
    async def test_extract_json_files_database_error(self, mock_db, mock_user):
        """Test extraction when database query fails"""
        mock_db.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception):
            await extract_json_files(video_id=1, current_user=mock_user, db=mock_db)
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.read_json_file_azure_local')
    async def test_get_master_data_json_error(self, mock_read_json, mock_db, mock_user):
        """Test master data retrieval when JSON reading fails"""
        # Mock video and master
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 2
        mock_video.title = "Test Video"
        mock_video.brocade_type = "BROCADE_1"
        
        mock_master = Mock()
        mock_master.id = 2
        mock_master.name = "Master"
        mock_master.email = "master@test.com"
        mock_master.role = "master"
        
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            if model == models.VideoUpload:
                mock_query.first.return_value = mock_video
            elif model == models.User:
                mock_query.first.return_value = mock_master
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock JSON reading to fail
        mock_read_json.side_effect = Exception("JSON read error")
        
        result = await get_master_data(video_id=1, current_user=mock_user, db=mock_db)
        
        # Should still return basic data even if JSON fails
        assert "masterData" in result
        assert "videoData" in result
        assert "analysisData" in result
        assert result["analysisData"] == {}  # Empty due to errors

class TestIntegrationScenarios:
    """Test integration scenarios and workflows"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.mark.asyncio
    @patch('routers.analysis_with_master.read_json_file_azure_local')
    async def test_master_data_retrieval_workflow(self, mock_read_json, mock_db, mock_user):
        """Test master data retrieval workflow"""
        # Mock video and master
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 2
        mock_video.title = "Master Video"
        mock_video.brocade_type = "BROCADE_1"
        
        mock_master = Mock()
        mock_master.id = 2
        mock_master.name = "Master User"
        mock_master.email = "master@example.com"
        mock_master.role = "master"
        
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            if model == models.VideoUpload:
                mock_query.first.return_value = mock_video
            elif model == models.User:
                mock_query.first.return_value = mock_master
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock successful JSON reading
        mock_read_json.return_value = {"test": "data"}
        
        result = await get_master_data(video_id=1, current_user=mock_user, db=mock_db)
        
        assert "masterData" in result
        assert "videoData" in result
        assert result["masterData"]["name"] == "Master User"

class TestPerformanceAndEdgeCases:
    """Test performance considerations and edge cases"""
    
    @pytest.mark.asyncio
    async def test_json_file_operations_with_special_characters(self):
        """Test JSON operations with special characters in filenames"""
        with patch('routers.analysis_with_master.os.getenv', return_value=None):
            with patch('routers.analysis_with_master.os.path.exists', return_value=False):
                # Should handle special characters gracefully
                result = await json_file_exists(1, 1, "test_file_with_unicode_测试.json")
                assert result is False
    
    def test_generate_recommendations_with_missing_data(self):
        """Test recommendation generation with missing data fields"""
        user_data = {'smoothness': {'overallSmoothness': 1.0}}
        master_data = {}  # Empty master data
        
        recommendations = generate_comparison_recommendations(user_data, master_data)
        
        # Should still generate basic recommendations
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 4  # At least general recommendations
    
    def test_comparison_edge_cases(self):
        """Test comparison functionality edge cases"""
        # Test with minimal data
        user_data = {}
        master_data = {}
        
        recommendations = generate_comparison_recommendations(user_data, master_data)
        
        # Should handle empty data gracefully
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 4  # Should have general recommendations
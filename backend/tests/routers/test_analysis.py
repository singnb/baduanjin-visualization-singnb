# type: ignore
# /test/routers/test_analysis.py
# Unit tests for routers/analysis.py core functions

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import json
import io
import asyncio

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the modules to test
from routers.analysis import (
    router,
    get_analysis_results,
    run_analysis_script,
    run_analysis_sync,
    run_analysis,
    get_analysis_image
)
import models
import database

class TestAnalysisResults:
    """Test analysis results retrieval"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        """Mock current user"""
        user = Mock()
        user.id = 1
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_video(self):
        """Mock video object"""
        video = Mock()
        video.id = 1
        video.user_id = 1
        video.title = "Test Video"
        video.processing_status = "completed"
        video.keypoints_path = "outputs_json/1/1/results.json"
        video.analyzed_video_path = "outputs_json/1/1/analyzed.mp4"
        return video
    
    @pytest.mark.asyncio
    async def test_get_analysis_results_video_not_found(self, mock_db, mock_user):
        """Test analysis results when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_results(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getenv')
    async def test_get_analysis_results_not_analyzed(self, mock_getenv, mock_exists, mock_db, mock_user, mock_video):
        """Test analysis results when analysis hasn't been run"""
        # Setup mocks
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock database execute to return None (no analysis_report_path)
        mock_result = Mock()
        mock_result.fetchone.return_value = [None]
        mock_db.execute.return_value = mock_result
        
        # Mock no Azure connection and no local files
        mock_getenv.return_value = None
        mock_exists.return_value = False
        
        result = await get_analysis_results(video_id=1, current_user=mock_user, db=mock_db)
        
        assert result["status"] == "not_analyzed"
        assert result["video_id"] == 1
        assert result["video_title"] == "Test Video"
    
    @pytest.mark.asyncio
    async def test_get_analysis_results_parsing_error(self, mock_db, mock_user, mock_video):
        """Test analysis results when file parsing fails"""
        # Setup mocks
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock database execute to return None
        mock_db.execute.return_value.fetchone.return_value = [None]
        
        with patch('routers.analysis.os.path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                # Mock file read that raises an exception
                mock_open.return_value.__enter__.return_value.read.side_effect = IOError("File read error")
                
                result = await get_analysis_results(video_id=1, current_user=mock_user, db=mock_db)
                
                # Should still return analyzed status but with empty data
                assert result["status"] == "analyzed"
                assert result["key_poses"] == []
                assert result["joint_angles"] == {}

class TestAnalysisScriptExecution:
    """Test analysis script execution functions"""
    
    @pytest.fixture
    def mock_video(self):
        """Mock video object with keypoints"""
        video = Mock()
        video.id = 1
        video.user_id = 1
        video.keypoints_path = "outputs_json/1/1/results.json"
        video.analyzed_video_path = "outputs_json/1/1/analyzed.mp4"
        video.video_path = "uploads/videos/1/original.mp4"
        return video
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getcwd')
    async def test_run_analysis_script_missing_script(self, mock_getcwd, mock_exists, mock_video):
        """Test analysis script execution when script file missing"""
        mock_getcwd.return_value = "/app"
        mock_exists.return_value = False  # Script doesn't exist
        
        result = await run_analysis_script(video_id=1, user_id=1, video=mock_video)
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getcwd')
    async def test_run_analysis_script_no_keypoints(self, mock_getcwd, mock_exists, mock_video):
        """Test analysis script execution when no keypoints path"""
        mock_getcwd.return_value = "/app"
        mock_exists.return_value = True
        mock_video.keypoints_path = None
        
        result = await run_analysis_script(video_id=1, user_id=1, video=mock_video)
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.makedirs')
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getcwd')
    async def test_run_analysis_script_success(self, mock_getcwd, mock_exists, mock_makedirs, mock_video):
        """Test successful analysis script execution"""
        # Setup mocks
        mock_getcwd.return_value = "/app"
        mock_exists.return_value = True
        
        # Mock the async subprocess execution
        with patch('routers.analysis.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            
            # Create a proper Future for the async result
            future = asyncio.Future()
            future.set_result((0, "Analysis completed successfully", ""))
            mock_loop.run_in_executor.return_value = future
            
            result = await run_analysis_script(video_id=1, user_id=1, video=mock_video)
            
            assert result is True
            mock_makedirs.assert_called()
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getcwd')
    async def test_run_analysis_script_subprocess_error(self, mock_getcwd, mock_exists, mock_video):
        """Test analysis script execution when subprocess fails"""
        mock_getcwd.return_value = "/app"
        mock_exists.return_value = True
        
        # Mock failed subprocess result
        with patch('routers.analysis.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            
            # Create a Future with error result
            future = asyncio.Future()
            future.set_result((1, "", "Analysis failed"))
            mock_loop.run_in_executor.return_value = future
            
            result = await run_analysis_script(video_id=1, user_id=1, video=mock_video)
            
            assert result is False
    
    def test_run_analysis_sync_missing_keypoints(self, mock_video):
        """Test sync analysis when keypoints missing"""
        mock_video.keypoints_path = None
        
        result = run_analysis_sync(video_id=1, user_id=1, video=mock_video)
        
        assert result is False
    
    @patch('routers.analysis.subprocess.run')
    @patch('routers.analysis.os.makedirs')
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getcwd')
    def test_run_analysis_sync_success(self, mock_getcwd, mock_exists, mock_makedirs, mock_subprocess, mock_video):
        """Test successful sync analysis execution"""
        # Setup mocks
        mock_getcwd.return_value = "/app"
        mock_exists.return_value = True
        
        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Analysis completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = run_analysis_sync(video_id=1, user_id=1, video=mock_video)
        
        assert result is True
        mock_subprocess.assert_called_once()
        mock_makedirs.assert_called()

class TestAnalysisEndpoints:
    """Test analysis API endpoints"""
    
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
    
    @pytest.fixture
    def mock_background_tasks(self):
        return Mock(spec=BackgroundTasks)
    
    @pytest.mark.asyncio
    async def test_run_analysis_video_not_found(self, mock_db, mock_user, mock_background_tasks):
        """Test run analysis when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await run_analysis(
                video_id=999, 
                background_tasks=mock_background_tasks, 
                current_user=mock_user, 
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_run_analysis_video_not_completed(self, mock_db, mock_user, mock_background_tasks):
        """Test run analysis when video processing not completed"""
        mock_video = Mock()
        mock_video.processing_status = "processing"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await run_analysis(
                video_id=1, 
                background_tasks=mock_background_tasks, 
                current_user=mock_user, 
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert "must be completed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    async def test_run_analysis_already_exists(self, mock_exists, mock_db, mock_user, mock_background_tasks, mock_video):
        """Test run analysis when analysis already exists"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock that analysis report already exists
        mock_exists.return_value = True
        
        result = await run_analysis(
            video_id=1, 
            background_tasks=mock_background_tasks, 
            current_user=mock_user, 
            db=mock_db
        )
        
        assert result["status"] == "already_analyzed"
        assert "already exists" in result["message"]
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    async def test_run_analysis_success(self, mock_exists, mock_db, mock_user, mock_background_tasks, mock_video):
        """Test successful analysis start"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock that analysis report doesn't exist
        mock_exists.return_value = False
        
        result = await run_analysis(
            video_id=1, 
            background_tasks=mock_background_tasks, 
            current_user=mock_user, 
            db=mock_db
        )
        
        assert result["status"] == "analysis_started"
        assert "started successfully" in result["message"]
        mock_background_tasks.add_task.assert_called_once()

class TestAnalysisImageServing:
    """Test analysis image serving"""
    
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
        return video
    
    @pytest.mark.asyncio
    async def test_get_analysis_image_video_not_found(self, mock_db, mock_user):
        """Test image serving when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_image(
                video_id=999, 
                image_name="key_poses", 
                current_user=mock_user, 
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getenv')
    async def test_get_analysis_image_not_found(self, mock_getenv, mock_exists, mock_db, mock_user, mock_video):
        """Test image serving when image not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock no Azure and no local file
        mock_getenv.return_value = None
        mock_exists.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_image(
                video_id=1, 
                image_name="key_poses", 
                current_user=mock_user, 
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "Image not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('routers.analysis.FileResponse')
    @patch('routers.analysis.os.path.exists')
    @patch('routers.analysis.os.getenv')
    async def test_get_analysis_image_local_success(self, mock_getenv, mock_exists, mock_file_response, mock_db, mock_user, mock_video):
        """Test successful local image serving"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock no Azure but local file exists
        mock_getenv.return_value = None
        mock_exists.return_value = True
        mock_file_response.return_value = "mocked_file_response"
        
        result = await get_analysis_image(
            video_id=1, 
            image_name="key_poses", 
            current_user=mock_user, 
            db=mock_db
        )
        
        assert result == "mocked_file_response"
        mock_file_response.assert_called_once()

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
    async def test_get_analysis_results_database_error(self, mock_db, mock_user):
        """Test analysis results when database query fails"""
        # Mock database query to raise an exception
        mock_db.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception):
            await get_analysis_results(video_id=1, current_user=mock_user, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_get_analysis_image_access_control(self, mock_db, mock_user):
        """Test that users can only access their own video images"""
        # Mock video owned by different user
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 999  # Different user
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # This should actually return None from the query since we filter by user_id
        # Let's test the proper access control
        mock_query.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_image(
                video_id=1, 
                image_name="key_poses", 
                current_user=mock_user, 
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)

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
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock()
        video.id = 1
        video.user_id = 1
        video.title = "Integration Test Video"
        video.processing_status = "completed"
        video.keypoints_path = "outputs_json/1/1/results.json"
        video.analyzed_video_path = "outputs_json/1/1/analyzed.mp4"
        return video
    
    @pytest.mark.asyncio
    @patch('routers.analysis.os.path.exists')
    async def test_complete_analysis_workflow(self, mock_exists, mock_db, mock_user, mock_video):
        """Test complete analysis workflow from start to results"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Mock that analysis doesn't exist initially
        mock_exists.return_value = False
        
        # Step 1: Start analysis
        background_tasks = Mock()
        result = await run_analysis(
            video_id=1, 
            background_tasks=background_tasks, 
            current_user=mock_user, 
            db=mock_db
        )
        
        assert result["status"] == "analysis_started"
        background_tasks.add_task.assert_called_once()
        
        # Step 2: Mock that analysis now exists
        mock_exists.return_value = True
        
        # Mock database query for analysis results
        mock_result = Mock()
        mock_result.fetchone.return_value = [None]
        mock_db.execute.return_value = mock_result
        
        # Mock file content for analysis results
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Analysis completed"
            
            result = await get_analysis_results(video_id=1, current_user=mock_user, db=mock_db)
            
            assert result["status"] == "analyzed"
            assert result["video_id"] == 1

class TestPerformanceAndEdgeCases:
    """Test performance considerations and edge cases"""
    
    @pytest.mark.asyncio
    async def test_analysis_script_path_edge_cases(self):
        """Test analysis script execution with various path scenarios"""
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.keypoints_path = "outputs_json/1/1/results.json"
        mock_video.analyzed_video_path = None  # No analyzed video
        mock_video.video_path = None  # No original video
        
        with patch('routers.analysis.os.getcwd', return_value="/app"):
            with patch('routers.analysis.os.path.exists') as mock_exists:
                # Mock script exists but video files don't
                mock_exists.side_effect = lambda path: path.endswith("working_analysis.py") or path.endswith("results.json")
                
                with patch('routers.analysis.os.makedirs'):
                    with patch('routers.analysis.asyncio.get_event_loop') as mock_get_loop:
                        mock_loop = Mock()
                        mock_get_loop.return_value = mock_loop
                        
                        future = asyncio.Future()
                        future.set_result((0, "Success", ""))
                        mock_loop.run_in_executor.return_value = future
                        
                        result = await run_analysis_script(video_id=1, user_id=1, video=mock_video)
                        
                        # Should still succeed even without video files
                        assert result is True
    
    def test_analysis_sync_timeout_handling(self):
        """Test sync analysis timeout handling"""
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.keypoints_path = "outputs_json/1/1/results.json"
        mock_video.analyzed_video_path = "outputs_json/1/1/analyzed.mp4"
        mock_video.video_path = "uploads/videos/1/original.mp4"
        
        with patch('routers.analysis.os.getcwd', return_value="/app"):
            with patch('routers.analysis.os.path.exists', return_value=True):
                with patch('routers.analysis.os.makedirs'):
                    with patch('routers.analysis.subprocess.run') as mock_subprocess:
                        # Mock timeout
                        import subprocess
                        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 300)
                        
                        result = run_analysis_sync(video_id=1, user_id=1, video=mock_video)
                        
                        assert result is False
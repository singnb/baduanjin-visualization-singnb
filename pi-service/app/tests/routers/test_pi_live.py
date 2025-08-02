# type: ignore
# /tests/routers/test_pi_live.py
# Unit tests for routers/pi_live.py core functions
# test/routers/test_pi_live.py

import os
import sys
# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException
import tempfile
import json

# Import the modules to test with error handling
try:
    from routers.pi_live import (
        EnhancedPiService, 
        router, 
        pi_service,
        transfer_file_background,
        RECORDINGS_DIR,
        VIDEOS_DIR
    )
    from models import User, VideoUpload
    from database import get_db
    from auth.router import get_current_user
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory and all dependencies are installed")
    sys.exit(1)


class TestEnhancedPiService:
    """Test cases for EnhancedPiService class"""
    
    @pytest.fixture
    def pi_service_instance(self):
        """Create a fresh instance of EnhancedPiService for testing"""
        return EnhancedPiService()
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient - safer import handling"""
        with patch('routers.pi_live.httpx') as mock_httpx:
            # Create a mock AsyncClient that can be used in context manager
            mock_client_instance = AsyncMock()
            mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client_instance
            mock_httpx.AsyncClient.return_value.__aexit__.return_value = None
            
            # Also mock the exception classes
            mock_httpx.TimeoutException = Exception
            mock_httpx.ConnectError = ConnectionError
            
            yield mock_httpx
    
    @pytest.mark.asyncio
    async def test_check_pi_status_success(self, pi_service_instance, mock_httpx_client):
        """Test successful Pi status check"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "camera_available": True,
            "yolo_available": True,
            "is_running": False,
            "is_recording": False,
            "persons_detected": 0
        }
        
        mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
        mock_client_instance.get.return_value = mock_response
        
        result = await pi_service_instance.check_pi_status()
        
        assert result["connected"] is True
        assert result["data"]["camera_available"] is True
        assert result["ngrok_status"] == "active"
        assert result["connection_method"] == "static_ngrok"
    
    @pytest.mark.asyncio
    async def test_check_pi_status_timeout(self, pi_service_instance, mock_httpx_client):
        """Test Pi status check timeout"""
        mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
        mock_client_instance.get.side_effect = mock_httpx_client.TimeoutException("Timeout")
        
        result = await pi_service_instance.check_pi_status()
        
        assert result["connected"] is False
        assert "timeout" in result["error"].lower()
        assert result["ngrok_status"] == "timeout"
       
    @pytest.mark.asyncio
    async def test_start_pi_streaming_success(self, pi_service_instance, mock_httpx_client):
        """Test successful Pi streaming start"""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "message": "Streaming started"}
        
        mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
        mock_client_instance.post.return_value = mock_response
        
        result = await pi_service_instance.start_pi_streaming()
        
        assert result["success"] is True
        assert "started" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_start_pi_streaming_error(self, pi_service_instance, mock_httpx_client):
        """Test Pi streaming start error"""
        mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
        mock_client_instance.post.side_effect = Exception("Connection error")
        
        result = await pi_service_instance.start_pi_streaming()
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_pi_recordings_success(self, pi_service_instance, mock_httpx_client):
        """Test successful Pi recordings retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "recordings": [
                {"filename": "test1.mp4", "size": 1024},
                {"filename": "test2.mp4", "size": 2048}
            ]
        }
        
        mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
        mock_client_instance.get.return_value = mock_response
        
        result = await pi_service_instance.get_pi_recordings()
        
        assert result["success"] is True
        assert len(result["recordings"]) == 2
        assert result["recordings"][0]["filename"] == "test1.mp4"
    
    @pytest.mark.asyncio
    async def test_download_pi_recording_success(self, pi_service_instance, mock_httpx_client):
        """Test successful Pi recording download"""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "test_download.mp4"
            
            # Mock status check
            mock_status_response = Mock()
            mock_status_response.status_code = 200
            mock_status_response.json.return_value = {"exists": True, "size": 1024}
            
            # Mock download response
            mock_download_response = Mock()
            mock_download_response.status_code = 200
            mock_download_response.content = b"fake video content"
            
            mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
            mock_client_instance.get.side_effect = [mock_status_response, mock_download_response]
            
            result = await pi_service_instance.download_pi_recording("test.mp4", local_path)
            
            assert result["success"] is True
            assert result["filename"] == "test.mp4"
            assert local_path.exists()
    
    @pytest.mark.asyncio
    async def test_download_pi_recording_file_not_exists(self, pi_service_instance, mock_httpx_client):
        """Test Pi recording download when file doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "test_download.mp4"
            
            # Mock status check - file doesn't exist
            mock_status_response = Mock()
            mock_status_response.status_code = 200
            mock_status_response.json.return_value = {"exists": False}
            
            mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
            mock_client_instance.get.return_value = mock_status_response
            
            result = await pi_service_instance.download_pi_recording("nonexistent.mp4", local_path)
            
            assert result["success"] is False
            assert "does not exist" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_pi_pose_data_success(self, pi_service_instance, mock_httpx_client):
        """Test successful Pi pose data retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "pose_data": [
                {"keypoint": "nose", "x": 100, "y": 200, "confidence": 0.9}
            ]
        }
        
        mock_client_instance = mock_httpx_client.AsyncClient.return_value.__aenter__.return_value
        mock_client_instance.get.return_value = mock_response
        
        result = await pi_service_instance.get_pi_pose_data()
        
        assert "pose_data" in result
        assert len(result["pose_data"]) == 1
        assert result["pose_data"][0]["keypoint"] == "nose"


class TestPiLiveRouterEndpoints:
    """Test cases for Pi Live router endpoints"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_video_upload(self):
        """Mock VideoUpload model"""
        video = Mock(spec=VideoUpload)
        video.id = 1
        video.user_id = 1
        video.title = "Test Video"
        video.description = "Test Description"
        video.brocade_type = "FIRST"
        video.video_path = ""
        video.processing_status = "live_active"
        video.upload_timestamp = datetime.now()
        return video
    
    # Note: Direct function testing instead of HTTP client testing
    # to avoid httpx compatibility issues
    
    @pytest.mark.asyncio
    async def test_check_pi_connection_success(self, mock_db_session, mock_current_user):
        """Test successful Pi connection check endpoint"""
        with patch.object(pi_service, 'check_pi_status') as mock_check_status, \
             patch.object(pi_service, 'get_pi_recordings') as mock_get_recordings:
            
            # Mock successful Pi status
            mock_check_status.return_value = {
                "connected": True,
                "data": {
                    "camera_available": True,
                    "yolo_available": True,
                    "is_running": False,
                    "is_recording": False,
                    "persons_detected": 0
                }
            }
            
            # Mock recordings
            mock_get_recordings.return_value = {
                "success": True,
                "recordings": [{"filename": "test.mp4"}]
            }
            
            # Import the endpoint function directly
            from routers.pi_live import check_pi_connection
            
            result = await check_pi_connection()
            
            assert result["pi_connected"] is True
            assert result["camera_available"] is True
            assert result["recordings_available"] == 1
    
    @pytest.mark.asyncio
    async def test_check_pi_connection_failed(self, mock_db_session, mock_current_user):
        """Test failed Pi connection check endpoint"""
        with patch.object(pi_service, 'check_pi_status') as mock_check_status:
            
            # Mock failed Pi status
            mock_check_status.return_value = {
                "connected": False,
                "error": "Connection timeout"
            }
            
            from routers.pi_live import check_pi_connection
            
            result = await check_pi_connection()
            
            assert result["pi_connected"] is False
            assert "timeout" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_start_live_session_success(self, mock_db_session, mock_current_user, mock_video_upload):
        """Test successful live session start"""
        with patch.object(pi_service, 'check_pi_status') as mock_check_status, \
             patch.object(pi_service, 'start_pi_streaming') as mock_start_streaming, \
             patch('routers.pi_live.text') as mock_text:
            
            # Mock successful Pi status
            mock_check_status.return_value = {"connected": True}
            
            # Mock successful streaming start
            mock_start_streaming.return_value = {"success": True}
            
            # Mock database operations
            mock_result = Mock()
            mock_result.fetchone.return_value = [1]  # Return session ID
            mock_db_session.execute.return_value = mock_result
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_video_upload
            
            from routers.pi_live import start_live_session
            
            session_data = {"session_name": "Test Session"}
            result = await start_live_session(session_data, mock_current_user, mock_db_session)
            
            assert result["success"] is True
            assert "session_id" in result
            assert result["session_name"] == "Test Session"
    
    @pytest.mark.asyncio
    async def test_start_live_session_pi_unavailable(self, mock_db_session, mock_current_user):
        """Test live session start when Pi is unavailable"""
        with patch.object(pi_service, 'check_pi_status') as mock_check_status:
            
            # Mock failed Pi status
            mock_check_status.return_value = {
                "connected": False,
                "error": "Pi not reachable"
            }
            
            from routers.pi_live import start_live_session
            
            session_data = {"session_name": "Test Session"}
            
            with pytest.raises(HTTPException) as exc_info:
                await start_live_session(session_data, mock_current_user, mock_db_session)
            
            assert exc_info.value.status_code == 503
            assert "Pi not available" in str(exc_info.value.detail)
     
    @pytest.mark.asyncio
    async def test_start_session_recording_success(self, mock_current_user):
        """Test successful session recording start"""
        with patch.object(pi_service, 'start_pi_recording') as mock_start_recording:
            
            # Mock successful recording start
            mock_start_recording.return_value = {"success": True}
            
            # Setup active session
            session_id = "live_1"
            pi_service.active_sessions[session_id] = {
                "user_id": 1,
                "recording_files": []
            }
            
            from routers.pi_live import start_session_recording
            
            result = await start_session_recording(session_id, mock_current_user)
            
            assert result["success"] is True
            assert result["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_start_session_recording_unauthorized(self, mock_current_user):
        """Test session recording start with unauthorized user"""
        # Setup active session with different user
        session_id = "live_1"
        pi_service.active_sessions[session_id] = {
            "user_id": 999,  # Different user ID
            "recording_files": []
        }
        
        from routers.pi_live import start_session_recording
        
        with pytest.raises(HTTPException) as exc_info:
            await start_session_recording(session_id, mock_current_user)
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_available_recordings_success(self, mock_current_user):
        """Test successful recordings retrieval"""
        with patch.object(pi_service, 'get_pi_recordings') as mock_get_recordings:
            
            # Mock successful recordings retrieval
            mock_get_recordings.return_value = {
                "success": True,
                "recordings": [
                    {"filename": "test1.mp4", "size": 1024},
                    {"filename": "test2.mp4", "size": 2048}
                ]
            }
            
            from routers.pi_live import get_available_recordings
            
            result = await get_available_recordings(mock_current_user)
            
            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["recordings"]) == 2
    
    @pytest.mark.asyncio
    async def test_transfer_video_from_pi_success(self, mock_current_user):
        """Test successful video transfer initiation"""
        with patch.object(pi_service, 'get_pi_recordings') as mock_get_recordings, \
             patch('routers.pi_live.BackgroundTasks') as mock_background_tasks:
            
            # Mock successful recordings check
            mock_get_recordings.return_value = {
                "success": True,
                "recordings": [{"filename": "test.mp4"}]
            }
            
            mock_background_tasks_instance = Mock()
            filename = "test.mp4"
            
            from routers.pi_live import transfer_video_from_pi
            
            result = await transfer_video_from_pi(
                filename, 
                mock_background_tasks_instance, 
                mock_current_user
            )
            
            assert result["success"] is True
            assert result["filename"] == filename
            assert filename in pi_service.transfer_queue
    
    @pytest.mark.asyncio
    async def test_transfer_video_invalid_filename(self, mock_current_user):
        """Test video transfer with invalid filename"""
        from routers.pi_live import transfer_video_from_pi
        
        filename = "test.txt"  # Not an MP4 file
        mock_background_tasks = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await transfer_video_from_pi(filename, mock_background_tasks, mock_current_user)
        
        assert exc_info.value.status_code == 400
        assert "MP4" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_transfer_status_found(self, mock_current_user):
        """Test transfer status retrieval for existing transfer"""
        filename = "test.mp4"
        
        # Setup transfer in queue
        pi_service.transfer_queue[filename] = {
            "status": "completed",
            "user_id": 1,
            "start_time": datetime.now(),
            "completion_time": datetime.now(),
            "size": 1024,
            "local_path": Path("/tmp/test.mp4")
        }
        
        from routers.pi_live import get_transfer_status_enhanced
        
        result = await get_transfer_status_enhanced(filename, mock_current_user)
        
        assert result["filename"] == filename
        assert result["status"] == "completed"
        assert "duration_seconds" in result
    
    @pytest.mark.asyncio
    async def test_get_transfer_status_not_found(self, mock_current_user):
        """Test transfer status retrieval for non-existent transfer"""
        with patch.object(pi_service, 'get_pi_recordings') as mock_get_recordings:
            
            mock_get_recordings.return_value = {
                "success": True,
                "recordings": []
            }
            
            from routers.pi_live import get_transfer_status_enhanced
            
            result = await get_transfer_status_enhanced("nonexistent.mp4", mock_current_user)
            
            assert result["transfer_found"] is False
            assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_current_pose_success(self, mock_current_user):
        """Test successful current pose data retrieval"""
        with patch.object(pi_service, 'get_pi_pose_data') as mock_get_pose:
            
            # Mock successful pose data
            mock_get_pose.return_value = {
                "pose_data": [
                    {"keypoint": "nose", "x": 100, "y": 200, "confidence": 0.9}
                ]
            }
            
            from routers.pi_live import get_current_pose
            
            result = await get_current_pose(mock_current_user)
            
            assert result["success"] is True
            assert result["user_id"] == 1
            assert len(result["pose_data"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, mock_current_user):
        """Test active sessions retrieval"""
        # Setup active sessions
        pi_service.active_sessions = {
            "live_1": {
                "db_id": 1,
                "user_id": 1,
                "start_time": datetime.now(),
                "status": "active",
                "recording_files": []
            },
            "live_2": {
                "db_id": 2,
                "user_id": 999,  # Different user
                "start_time": datetime.now(),
                "status": "active",
                "recording_files": []
            }
        }
        
        from routers.pi_live import get_active_sessions
        
        result = await get_active_sessions(mock_current_user)
        
        assert result["active_sessions"] == 1  # Only user's own sessions
        assert len(result["sessions"]) == 1
        assert result["sessions"][0]["session_id"] == "live_1"


class TestBackgroundTasks:
    """Test cases for background task functions"""
    
    @pytest.mark.asyncio
    async def test_transfer_file_background_success(self):
        """Test successful background file transfer"""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "test.mp4"
            filename = "test.mp4"
            user_id = 1
            
            # Setup transfer queue
            pi_service.transfer_queue[filename] = {
                "status": "transferring",
                "user_id": user_id,
                "local_path": local_path,
                "start_time": datetime.now()
            }
            
            with patch.object(pi_service, 'download_pi_recording') as mock_download:
                
                # Mock successful download
                mock_download.return_value = {
                    "success": True,
                    "size": 1024,
                    "filename": filename
                }
                
                await transfer_file_background(filename, local_path, user_id)
                
                assert pi_service.transfer_queue[filename]["status"] == "completed"
                assert pi_service.transfer_queue[filename]["size"] == 1024
    
    @pytest.mark.asyncio
    async def test_transfer_file_background_failure(self):
        """Test failed background file transfer"""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "test.mp4"
            filename = "test.mp4"
            user_id = 1
            
            # Setup transfer queue
            pi_service.transfer_queue[filename] = {
                "status": "transferring",
                "user_id": user_id,
                "local_path": local_path,
                "start_time": datetime.now()
            }
            
            with patch.object(pi_service, 'download_pi_recording') as mock_download:
                
                # Mock failed download
                mock_download.return_value = {
                    "success": False,
                    "error": "Download failed"
                }
                
                await transfer_file_background(filename, local_path, user_id)
                
                assert pi_service.transfer_queue[filename]["status"] == "failed"
                assert "Download failed" in pi_service.transfer_queue[filename]["error"]


class TestUtilityFunctions:
    """Test cases for utility functions and setup"""
    
    def test_directories_creation(self):
        """Test that required directories are created"""
        # These should exist after import
        assert VIDEOS_DIR.exists()
        assert RECORDINGS_DIR.exists()
    
    def test_pi_service_initialization(self):
        """Test that pi_service is properly initialized"""
        assert hasattr(pi_service, 'active_sessions')
        assert hasattr(pi_service, 'transfer_queue')
        assert isinstance(pi_service.active_sessions, dict)
        assert isinstance(pi_service.transfer_queue, dict)


# Test fixtures for integration testing
@pytest.fixture
def clean_pi_service():
    """Clean pi_service state before each test"""
    original_sessions = pi_service.active_sessions.copy()
    original_queue = pi_service.transfer_queue.copy()
    
    # Clear state
    pi_service.active_sessions.clear()
    pi_service.transfer_queue.clear()
    
    yield pi_service
    
    # Restore state
    pi_service.active_sessions = original_sessions
    pi_service.transfer_queue = original_queue


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing"""
    with patch('routers.pi_live.aiofiles.open'), \
         patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.stat') as mock_stat:
        
        mock_stat.return_value.st_size = 1024
        yield


if __name__ == "__main__":
    # Run tests with proper async support
    # Usage: python -m pytest test/routers/test_pi_live.py -v
    # Or: python test/routers/test_pi_live.py
    pytest.main([__file__, "-v", "--tb=short"])
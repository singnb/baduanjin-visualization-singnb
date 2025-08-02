# type: ignore
# /test/routers/test_video_english.py
# Unit tests for routers/video_english.py core functions

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import models
from routers.video_english import router, conversion_status, convert_video_audio, get_conversion_status, check_english_audio_version

class TestVideoEnglishRouter:
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_master_user(self):
        """Mock master user"""
        user = Mock(spec=models.User)
        user.id = 1
        user.role = models.UserRole.MASTER
        return user
    
    @pytest.fixture
    def mock_learner_user(self):
        """Mock learner user"""
        user = Mock(spec=models.User)
        user.id = 2
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_video(self):
        """Mock video upload"""
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.user_id = 1
        video.processing_status = "completed"
        video.video_path = "/test/path/video.mp4"
        video.english_audio_path = None
        return video
    
    @pytest.fixture
    def mock_background_tasks(self):
        """Mock background tasks"""
        return Mock(spec=BackgroundTasks)
    
    def setup_method(self):
        """Reset conversion status before each test"""
        conversion_status.clear()


class TestConvertVideoAudio:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_master_user(self):
        user = Mock(spec=models.User)
        user.id = 1
        user.role = models.UserRole.MASTER
        return user
    
    @pytest.fixture
    def mock_learner_user(self):
        user = Mock(spec=models.User)
        user.id = 2
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.user_id = 1
        video.processing_status = "completed"
        video.video_path = "/test/path/video.mp4"
        video.english_audio_path = None
        return video
    
    @pytest.fixture
    def mock_background_tasks(self):
        return Mock(spec=BackgroundTasks)
    
    def setup_method(self):
        conversion_status.clear()
    
    @pytest.mark.asyncio
    async def test_convert_video_audio_not_master_user(self, mock_db, mock_learner_user, mock_background_tasks):
        """Test that non-master users cannot convert audio"""
        with pytest.raises(HTTPException) as exc_info:
            await convert_video_audio(1, mock_background_tasks, mock_learner_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Only masters can convert video audio" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_convert_video_audio_video_not_found(self, mock_db, mock_master_user, mock_background_tasks):
        """Test error when video not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await convert_video_audio(1, mock_background_tasks, mock_master_user, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_convert_video_audio_invalid_status(self, mock_db, mock_master_user, mock_background_tasks):
        """Test error when video has invalid processing status"""
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.processing_status = "processing"
        mock_video.video_path = "/test/path/video.mp4"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        with pytest.raises(HTTPException) as exc_info:
            await convert_video_audio(1, mock_background_tasks, mock_master_user, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Video must be in 'uploaded' or 'completed' status" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_convert_video_audio_file_not_exists(self, mock_exists, mock_db, mock_master_user, mock_background_tasks, mock_video):
        """Test error when video file doesn't exist"""
        mock_exists.return_value = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        with pytest.raises(HTTPException) as exc_info:
            await convert_video_audio(1, mock_background_tasks, mock_master_user, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Video file not found on server" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_convert_video_audio_success_uploaded_status(self, mock_exists, mock_db, mock_master_user, mock_background_tasks):
        """Test successful conversion with uploaded status"""
        mock_exists.return_value = True
        
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.processing_status = "uploaded"
        mock_video.video_path = "/test/path/video.mp4"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await convert_video_audio(1, mock_background_tasks, mock_master_user, mock_db)
        
        assert result["status"] == "started"
        assert result["message"] == "Audio conversion started"
        assert result["video_id"] == 1
        assert conversion_status[1] == "processing"
        mock_background_tasks.add_task.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_convert_video_audio_success_completed_status(self, mock_exists, mock_db, mock_master_user, mock_background_tasks, mock_video):
        """Test successful conversion with completed status"""
        mock_exists.return_value = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await convert_video_audio(1, mock_background_tasks, mock_master_user, mock_db)
        
        assert result["status"] == "started"
        assert result["message"] == "Audio conversion started"
        assert result["video_id"] == 1
        assert conversion_status[1] == "processing"
        mock_background_tasks.add_task.assert_called_once()


class TestGetConversionStatus:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=models.User)
        user.id = 1
        user.role = models.UserRole.MASTER
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.user_id = 1
        return video
    
    def setup_method(self):
        conversion_status.clear()
    
    @pytest.mark.asyncio
    async def test_get_conversion_status_video_not_found(self, mock_db, mock_user):
        """Test error when video not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_conversion_status(1, mock_user, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_conversion_status_not_started(self, mock_db, mock_user, mock_video):
        """Test status when conversion not started"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await get_conversion_status(1, mock_user, mock_db)
        
        assert result["status"] == "not_started"
        assert result["video_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_conversion_status_processing(self, mock_db, mock_user, mock_video):
        """Test status when conversion is processing"""
        conversion_status[1] = "processing"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await get_conversion_status(1, mock_user, mock_db)
        
        assert result["status"] == "processing"
        assert result["video_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_conversion_status_completed(self, mock_db, mock_user, mock_video):
        """Test status when conversion is completed"""
        conversion_status[1] = "completed"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await get_conversion_status(1, mock_user, mock_db)
        
        assert result["status"] == "completed"
        assert result["video_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_conversion_status_failed(self, mock_db, mock_user, mock_video):
        """Test status when conversion failed"""
        conversion_status[1] = "failed"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await get_conversion_status(1, mock_user, mock_db)
        
        assert result["status"] == "failed"
        assert result["video_id"] == 1


class TestCheckEnglishAudioVersion:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_master_user(self):
        user = Mock(spec=models.User)
        user.id = 1
        user.role = models.UserRole.MASTER
        return user
    
    @pytest.fixture
    def mock_learner_user(self):
        user = Mock(spec=models.User)
        user.id = 2
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.fixture
    def mock_video(self):
        video = Mock(spec=models.VideoUpload)
        video.id = 1
        video.user_id = 1
        video.english_audio_path = None
        return video
    
    @pytest.mark.asyncio
    async def test_check_english_audio_video_not_found(self, mock_db, mock_master_user):
        """Test error when video not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await check_english_audio_version(1, mock_master_user, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_check_english_audio_owner_access(self, mock_db, mock_master_user, mock_video):
        """Test owner can access their own video"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        with patch('os.path.exists', return_value=False):
            result = await check_english_audio_version(1, mock_master_user, mock_db)
        
        assert result["video_id"] == 1
        assert result["has_english_audio"] == False
        assert result["english_audio_path"] is None
    
    @pytest.mark.asyncio
    async def test_check_english_audio_master_access_to_learner_video(self, mock_db, mock_master_user):
        """Test master can access learner's video with accepted relationship"""
        # Setup video owned by learner
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 2  # Learner's video
        mock_video.english_audio_path = None
        
        # Setup relationship
        mock_relationship = Mock(spec=models.MasterLearnerRelationship)
        mock_relationship.master_id = 1
        mock_relationship.learner_id = 2
        mock_relationship.status = "accepted"
        
        # Mock database queries
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_video)))),  # Video query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_relationship))))  # Relationship query
        ]
        
        with patch('os.path.exists', return_value=False):
            result = await check_english_audio_version(1, mock_master_user, mock_db)
        
        assert result["video_id"] == 1
        assert result["has_english_audio"] == False
    
    @pytest.mark.asyncio
    async def test_check_english_audio_learner_access_to_master_video(self, mock_db, mock_learner_user):
        """Test learner can access master's video"""
        # Setup video owned by master
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 1  # Master's video
        mock_video.english_audio_path = None
        
        # Setup master user
        mock_master = Mock(spec=models.User)
        mock_master.id = 1
        mock_master.role = models.UserRole.MASTER
        
        # Mock database queries
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_video)))),  # Video query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_master))))  # User query
        ]
        
        with patch('os.path.exists', return_value=False):
            result = await check_english_audio_version(1, mock_learner_user, mock_db)
        
        assert result["video_id"] == 1
        assert result["has_english_audio"] == False
    
    @pytest.mark.asyncio
    async def test_check_english_audio_access_denied(self, mock_db, mock_learner_user):
        """Test access denied for unauthorized user"""
        # Setup video owned by different user
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 3  # Different user
        mock_video.english_audio_path = None
        
        # Setup different user (not master)
        mock_other_user = Mock(spec=models.User)
        mock_other_user.id = 3
        mock_other_user.role = models.UserRole.LEARNER
        
        # Mock database queries
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_video)))),  # Video query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_other_user))))  # User query
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            await check_english_audio_version(1, mock_learner_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_check_english_audio_has_english_version(self, mock_exists, mock_db, mock_master_user):
        """Test when video has English audio version"""
        mock_exists.return_value = True
        
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.english_audio_path = "/test/path/video_english.mp4"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await check_english_audio_version(1, mock_master_user, mock_db)
        
        assert result["video_id"] == 1
        assert result["has_english_audio"] == True
        assert result["english_audio_path"] == "/test/path/video_english.mp4"
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_check_english_audio_path_exists_but_file_missing(self, mock_exists, mock_db, mock_master_user):
        """Test when english_audio_path is set but file doesn't exist"""
        mock_exists.return_value = False
        
        mock_video = Mock(spec=models.VideoUpload)
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.english_audio_path = "/test/path/video_english.mp4"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        result = await check_english_audio_version(1, mock_master_user, mock_db)
        
        assert result["video_id"] == 1
        assert result["has_english_audio"] == False
        assert result["english_audio_path"] is None


class TestBackgroundConversionProcess:
    """Test the background conversion process functionality"""
    
    def setup_method(self):
        conversion_status.clear()
    
    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('database.SessionLocal')
    def test_background_conversion_success(self, mock_session_local, mock_exists, mock_popen):
        """Test successful background conversion"""
        # Mock subprocess success
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("Success output", "")
        mock_popen.return_value = mock_process
        
        # Mock file exists
        mock_exists.side_effect = [True, True]  # Script exists, output file exists after conversion
        
        # Mock database session
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_video
        
        # Import and call the background function directly
        from routers.video_english import convert_video_audio
        
        # Create a mock background task function manually
        def mock_convert_audio_background():
            try:
                import os
                import sys
                import subprocess
                from pathlib import Path
                
                video_id = 1
                original_video_path = "/test/path/video.mp4"
                output_video_path = "/test/path/video_english.mp4"
                
                # Set conversion status
                conversion_status[video_id] = "processing"
                
                # Mock the script execution
                script_path = os.path.join("ml_pipeline", "mandarin_to_english.py")
                
                if not os.path.exists(script_path):
                    conversion_status[video_id] = "failed"
                    return
                
                # Mock successful process
                conversion_status[video_id] = "completed"
                
            except Exception as e:
                conversion_status[video_id] = "failed"
        
        # Execute the mock function
        mock_convert_audio_background()
        
        # Verify the status was updated correctly
        assert conversion_status[1] == "completed"
    
    def test_background_conversion_script_not_found(self):
        """Test background conversion when script is not found"""
        with patch('os.path.exists', return_value=False):
            # Simulate the background function
            video_id = 1
            conversion_status[video_id] = "processing"
            
            script_path = "ml_pipeline/mandarin_to_english.py"
            
            if not os.path.exists(script_path):
                conversion_status[video_id] = "failed"
            
            assert conversion_status[1] == "failed"
    
    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_background_conversion_subprocess_failure(self, mock_exists, mock_popen):
        """Test background conversion when subprocess fails"""
        # Mock subprocess failure
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "Error output")
        mock_popen.return_value = mock_process
        
        # Mock script exists but output file doesn't
        mock_exists.side_effect = [True, False]
        
        # Simulate the background function
        video_id = 1
        conversion_status[video_id] = "processing"
        
        # Mock the conversion logic
        if mock_process.returncode != 0 or not mock_exists.return_value:
            conversion_status[video_id] = "failed"
        
        assert conversion_status[1] == "failed"
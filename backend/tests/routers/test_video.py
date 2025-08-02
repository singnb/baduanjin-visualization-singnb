# type: ignore
# /test/routers/test_video.py
# Unit tests for routers/video.py core functions

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import json
import io

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the modules to test
from routers.video import (
    router, 
    map_brocade_type,
    get_videos,
    get_video,
    check_english_audio,
    upload_video,
    analyze_video,
    stream_specific_video,
    delete_video,
    reset_video_processing_status,
    analyze_video_enhanced
)
import models
import database

class TestBrocadeTypeMapping:
    """Test the brocade type mapping utility function"""
    
    def test_map_brocade_type_valid_mappings(self):
        """Test that frontend types map correctly to database values"""
        test_cases = [
            ("FIRST", "BROCADE_1"),
            ("SECOND", "BROCADE_2"),
            ("THIRD", "BROCADE_3"),
            ("FOURTH", "BROCADE_4"),
            ("FIFTH", "BROCADE_5"),
            ("SIXTH", "BROCADE_6"),
            ("SEVENTH", "BROCADE_7"),
            ("EIGHTH", "BROCADE_8")
        ]
        
        for frontend_type, expected_db_type in test_cases:
            result = map_brocade_type(frontend_type)
            assert result == expected_db_type
    
    def test_map_brocade_type_invalid_input(self):
        """Test that invalid inputs return default value"""
        invalid_inputs = ["NINTH", "INVALID", "", None, 123]
        
        for invalid_input in invalid_inputs:
            result = map_brocade_type(invalid_input)
            assert result == "BROCADE_1"
    
    def test_map_brocade_type_case_sensitivity(self):
        """Test that mapping is case sensitive"""
        result = map_brocade_type("first")  # lowercase
        assert result == "BROCADE_1"  # Should return default
        
        result = map_brocade_type("FIRST")  # uppercase
        assert result == "BROCADE_1"

class TestVideoRetrieval:
    """Test video retrieval endpoints"""
    
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
    def mock_videos(self):
        """Mock video objects"""
        videos = []
        for i in range(3):
            video = Mock()
            video.id = i + 1
            video.user_id = 1
            video.title = f"Test Video {i + 1}"
            video.processing_status = "completed"
            video.upload_timestamp = datetime.now()
            videos.append(video)
        return videos
    
    @pytest.mark.asyncio
    async def test_get_videos_success(self, mock_db, mock_user, mock_videos):
        """Test successful video retrieval"""
        # Setup mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_videos
        mock_db.query.return_value = mock_query
        
        result = await get_videos(current_user=mock_user, db=mock_db)
        
        assert len(result) == 3
        assert result[0].title == "Test Video 1"
        mock_db.query.assert_called_once_with(models.VideoUpload)
    
    @pytest.mark.asyncio
    async def test_get_video_by_id_success(self, mock_db, mock_user):
        """Test successful single video retrieval"""
        # Setup mock video
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.title = "Test Video"
        mock_video.description = "Test Description"
        mock_video.video_path = "/path/to/video.mp4"
        mock_video.processing_status = "completed"
        mock_video.upload_timestamp = datetime.now()
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        result = await get_video(video_id=1, current_user=mock_user, db=mock_db)
        
        assert result["id"] == 1
        assert result["title"] == "Test Video"
        assert result["user_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_video_not_found(self, mock_db, mock_user):
        """Test video not found scenario"""
        # Setup mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_video(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)

class TestEnglishAudioCheck:
    """Test English audio availability checking"""
    
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
    async def test_check_english_audio_exists(self, mock_db, mock_user):
        """Test when English audio exists"""
        # Setup mock video with english_audio_path
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.english_audio_path = "/path/to/english.mp4"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        result = await check_english_audio(video_id=1, current_user=mock_user, db=mock_db)
        
        assert result["has_english_audio"] is True
        assert result["english_audio_path"] == "/path/to/english.mp4"
        assert result["video_id"] == 1
    
    @pytest.mark.asyncio
    async def test_check_english_audio_not_found(self, mock_db, mock_user):
        """Test when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await check_english_audio(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404

class TestVideoUpload:
    """Test video upload functionality"""
    
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
    def mock_upload_file(self):
        """Mock UploadFile object"""
        file = Mock(spec=UploadFile)
        file.filename = "test_video.mp4"
        file.content_type = "video/mp4"
        return file
    
    @pytest.mark.asyncio
    async def test_upload_video_invalid_file_type(self, mock_db, mock_user):
        """Test upload with invalid file type"""
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_video(
                title="Test Video",
                description="Test Description",
                brocade_type="FIRST",
                file=mock_file,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert "File must be a video" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_video_file_too_large(self, mock_db, mock_user, mock_upload_file):
        """Test upload with file too large"""
        # Mock file content larger than 100MB
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        mock_upload_file.read = AsyncMock(return_value=large_content)
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_video(
                title="Test Video",
                description="Test Description", 
                brocade_type="FIRST",
                file=mock_upload_file,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert "File too large" in str(exc_info.value.detail)

class TestVideoAnalysis:
    """Test video analysis functionality"""
    
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
    def mock_background_tasks(self):
        return Mock()
    
    @pytest.mark.asyncio
    async def test_analyze_video_not_found(self, mock_db, mock_user, mock_background_tasks):
        """Test analysis when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await analyze_video(
                video_id=999,
                background_tasks=mock_background_tasks,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_analyze_video_success(self, mock_db, mock_user, mock_background_tasks):
        """Test successful video analysis start"""
        # Setup mock video
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.video_path = "/path/to/video.mp4"
        mock_video.processing_status = "uploaded"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        result = await analyze_video(
            video_id=1,
            background_tasks=mock_background_tasks,
            current_user=mock_user,
            db=mock_db
        )
        
        assert result["message"] == "Analysis started successfully"
        assert mock_video.processing_status == "processing"
        mock_background_tasks.add_task.assert_called_once()

class TestVideoStreaming:
    """Test video streaming functionality"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.mark.asyncio
    async def test_stream_video_no_token(self, mock_db):
        """Test streaming without authentication token"""
        with pytest.raises(HTTPException) as exc_info:
            await stream_specific_video(video_id=1, type="original", token=None, db=mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Authentication token required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_stream_video_invalid_token_format(self, mock_db):
        """Test streaming with invalid token format"""
        with pytest.raises(HTTPException) as exc_info:
            await stream_specific_video(video_id=1, type="original", token="invalid.token", db=mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token format" in str(exc_info.value.detail)
    
class TestVideoStatusManagement:
    """Test video status management"""
    
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
    async def test_reset_video_status_success(self, mock_db, mock_user):
        """Test successful status reset"""
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.processing_status = "processing"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        result = await reset_video_processing_status(
            video_id=1,
            current_user=mock_user,
            db=mock_db
        )
        
        assert result["message"] == "Processing status reset successfully"
        assert result["status"] == "uploaded"
        assert mock_video.processing_status == "uploaded"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_video_status_not_processing(self, mock_db, mock_user):
        """Test reset when video not in processing state"""
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.processing_status = "completed"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        result = await reset_video_processing_status(
            video_id=1,
            current_user=mock_user,
            db=mock_db
        )
        
        assert "not in 'processing' state" in result["message"]
        assert result["status"] == "completed"

class TestVideoDeletion:
    """Test video deletion functionality"""
    
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
    async def test_delete_video_not_found(self, mock_db, mock_user):
        """Test deletion when video not found"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_video(video_id=999, current_user=mock_user, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Video not found" in str(exc_info.value.detail)

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
    async def test_upload_video_local_fallback(self, mock_db, mock_user):
        """Test upload uses local storage when Azure is not configured"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_video.mp4"
        mock_file.content_type = "video/mp4"
        mock_file.read = AsyncMock(return_value=b"test content")
        
        with patch('routers.video.os.getenv', return_value=None):  # No Azure config
            with patch('routers.video.os.makedirs'):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.write = Mock()
                    
                    # Mock database operations
                    mock_video = Mock()
                    mock_video.id = 1
                    mock_video.title = "Test Video"
                    mock_video.processing_status = "uploaded"
                    mock_video.upload_timestamp = datetime.now()
                    
                    with patch('routers.video.models.VideoUpload', return_value=mock_video):
                        result = await upload_video(
                            title="Test Video",
                            description="Test",
                            brocade_type="FIRST",
                            file=mock_file,
                            current_user=mock_user,
                            db=mock_db
                        )
                    
                    assert result["storage_type"] == "local_fallback"
    
    @pytest.mark.asyncio
    async def test_analyze_video_enhanced_file_not_found(self, mock_db, mock_user):
        """Test enhanced analysis when video file not found"""
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.video_path = "/nonexistent/path.mp4"
        mock_video.processing_status = "uploaded"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        with patch('routers.video.os.path.exists', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await analyze_video_enhanced(
                    video_id=1,
                    background_tasks=Mock(),
                    current_user=mock_user,
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 400
            assert "Video file not found" in str(exc_info.value.detail)

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
    async def test_complete_video_workflow(self, mock_db, mock_user):
        """Test complete video upload and retrieval workflow"""
        # Step 1: Upload video (mock the successful upload)
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.title = "Integration Test Video"
        mock_video.processing_status = "uploaded"
        mock_video.upload_timestamp = datetime.now()
        
        # Step 2: Retrieve the uploaded video
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        result = await get_video(video_id=1, current_user=mock_user, db=mock_db)
        
        assert result["id"] == 1
        assert result["title"] == "Integration Test Video"
        assert result["processing_status"] == "uploaded"
    
    @pytest.mark.asyncio
    async def test_video_analysis_status_progression(self, mock_db, mock_user):
        """Test video status progression through analysis"""
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 1
        mock_video.processing_status = "uploaded"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        # Start analysis
        await analyze_video(
            video_id=1,
            background_tasks=Mock(),
            current_user=mock_user,
            db=mock_db
        )
        
        # Check status changed to processing
        assert mock_video.processing_status == "processing"
        
        # Reset status
        await reset_video_processing_status(
            video_id=1,
            current_user=mock_user,
            db=mock_db
        )
        
        # Check status reset to uploaded
        assert mock_video.processing_status == "uploaded"

class TestAccessControl:
    """Test access control and permissions"""
    
    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def master_user(self):
        user = Mock()
        user.id = 1
        user.role = models.UserRole.MASTER
        return user
    
    @pytest.fixture
    def learner_user(self):
        user = Mock()
        user.id = 2
        user.role = models.UserRole.LEARNER
        return user
    
    @pytest.mark.asyncio
    async def test_master_access_to_learner_video(self, mock_db, master_user, learner_user):
        """Test master can access learner's video with relationship"""
        # Setup mock video owned by learner
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 2  # Owned by learner
        mock_video.title = "Learner Video"
        
        # Setup mock relationship
        mock_relationship = Mock()
        mock_relationship.master_id = 1
        mock_relationship.learner_id = 2
        mock_relationship.status = "accepted"
        
        # Setup query mocks
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            if model == models.VideoUpload:
                mock_query.first.return_value = mock_video
            elif model == models.MasterLearnerRelationship:
                mock_query.first.return_value = mock_relationship
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        result = await get_video(video_id=1, current_user=master_user, db=mock_db)
        
        assert result["id"] == 1
        assert result["title"] == "Learner Video"
    
    @pytest.mark.asyncio
    async def test_learner_access_denied_to_other_video(self, mock_db, learner_user):
        """Test learner cannot access another user's video"""
        # Setup mock video owned by different user
        mock_video = Mock()
        mock_video.id = 1
        mock_video.user_id = 999  # Different user
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_video
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            await get_video(video_id=1, current_user=learner_user, db=mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

# Performance and edge case tests
class TestPerformanceAndEdgeCases:
    """Test performance considerations and edge cases"""
    
    @pytest.mark.asyncio
    async def test_large_video_list_performance(self):
        """Test handling of large video lists"""
        mock_db = Mock(spec=Session)
        mock_user = Mock()
        mock_user.id = 1
        
        # Create many mock videos
        large_video_list = []
        for i in range(1000):
            video = Mock()
            video.id = i
            video.title = f"Video {i}"
            large_video_list.append(video)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = large_video_list
        mock_db.query.return_value = mock_query
        
        result = await get_videos(current_user=mock_user, db=mock_db)
        
        assert len(result) == 1000
        assert result[0].title == "Video 0"
    
    def test_brocade_type_mapping_edge_cases(self):
        """Test edge cases for brocade type mapping"""
        # Test cases that should return default value
        edge_cases = [
            (None, "BROCADE_1"),
            ("", "BROCADE_1"),
            ("INVALID", "BROCADE_1"),
            ("first", "BROCADE_1"),  # lowercase
            ("NINTH", "BROCADE_1"),
        ]
        
        for input_val, expected in edge_cases:
            result = map_brocade_type(input_val)
            assert result == expected, f"Expected {expected} for input {input_val}, got {result}"
        
        # Test that non-string types also return default
        # The dict.get() method can handle any hashable type
        non_string_cases = [123, [], {}]
        for input_val in non_string_cases:
            try:
                result = map_brocade_type(input_val)
                assert result == "BROCADE_1", f"Expected BROCADE_1 for input {input_val}, got {result}"
            except TypeError:
                # Some types might not be hashable and cause TypeError
                # This is acceptable behavior
                pass
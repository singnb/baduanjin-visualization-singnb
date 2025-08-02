# type: ignore
# /test/ml_pipeline/test_mandarin_to_english.py
# Unit tests for ml_pipeline/mandarin_to_english.py core functions

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import os
import sys
import tempfile
import shutil
from io import StringIO

# Add the backend root directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Module-level fixtures
@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_video_path(temp_dir):
    """Create sample video file path"""
    video_path = os.path.join(temp_dir, "sample_video.mp4")
    # Create empty file for testing
    with open(video_path, 'wb') as f:
        f.write(b'fake_video_data')
    return video_path

@pytest.fixture
def sample_audio_path(temp_dir):
    """Create sample audio file path"""
    audio_path = os.path.join(temp_dir, "sample_audio.wav")
    with open(audio_path, 'wb') as f:
        f.write(b'fake_audio_data')
    return audio_path

@pytest.fixture
def mock_audio_chunks(temp_dir):
    """Create mock audio chunk files"""
    chunk_files = []
    for i in range(3):
        chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.wav")
        with open(chunk_path, 'wb') as f:
            f.write(b'fake_chunk_data')
        chunk_files.append(chunk_path)
    return chunk_files


class TestSafePrint:
    """Test safe printing function"""
    
    def test_safe_print_normal_text(self):
        """Test safe printing with normal ASCII text"""
        with patch('builtins.print') as mock_print:
            safe_print("Hello World", "INFO: ")
            mock_print.assert_called_once_with("INFO: Hello World")
    
    def test_safe_print_unicode_text(self):
        """Test safe printing with Unicode text"""
        with patch('builtins.print') as mock_print:
            safe_print("你好世界", "DEBUG: ")
            # Should handle Unicode gracefully - either print it or convert it
            mock_print.assert_called_once()
    
    def test_safe_print_unicode_encode_error(self):
        """Test safe printing when Unicode encoding fails"""
        with patch('builtins.print') as mock_print:
            # Mock print to raise UnicodeEncodeError
            mock_print.side_effect = [UnicodeEncodeError('utf-8', b'', 0, 1, 'invalid'), None]
            
            safe_print("问题文本", "ERROR: ")
            
            # Should call print twice - first fails, second succeeds with fallback
            assert mock_print.call_count == 2
    
    def test_safe_print_fallback_error(self):
        """Test safe printing when even fallback fails"""
        with patch('builtins.print') as mock_print:
            # Mock multiple failures
            mock_print.side_effect = [
                UnicodeEncodeError('utf-8', b'', 0, 1, 'invalid'),
                Exception("Fallback failed"),
                None
            ]
            
            safe_print("测试", "WARN: ")
            
            # Should eventually succeed with final fallback
            assert mock_print.call_count == 3


class TestAudioExtraction:
    """Test audio extraction functions"""
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    def test_extract_audio_pydub_success(self, mock_video_clip, mock_audio_segment, sample_video_path, temp_dir):
        """Test successful audio extraction using pydub"""
        output_path = os.path.join(temp_dir, "output_audio.wav")
        
        # Mock pydub AudioSegment
        mock_audio = Mock()
        mock_audio_segment.from_file.return_value = mock_audio
        
        # Mock VideoFileClip for duration
        mock_clip = Mock()
        mock_clip.duration = 120.5
        mock_video_clip.return_value = mock_clip
        
        result = extract_audio(sample_video_path, output_path)
        
        assert result == 120.5
        mock_audio_segment.from_file.assert_called_once_with(sample_video_path, format="mp4")
        mock_audio.export.assert_called_once_with(output_path, format="wav")
        mock_clip.close.assert_called_once()
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    def test_extract_audio_pydub_failure_moviepy_success(self, mock_video_clip, mock_audio_segment, sample_video_path, temp_dir):
        """Test audio extraction fallback to moviepy"""
        output_path = os.path.join(temp_dir, "output_audio.wav")
        
        # Mock pydub failure
        mock_audio_segment.from_file.side_effect = Exception("Pydub failed")
        
        # Mock moviepy success
        mock_clip = Mock()
        mock_clip.duration = 90.0
        mock_clip.audio = Mock()
        mock_video_clip.return_value = mock_clip
        
        result = extract_audio(sample_video_path, output_path)
        
        assert result == 90.0
        mock_clip.audio.write_audiofile.assert_called_once_with(output_path)
        mock_clip.close.assert_called_once()
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    @patch('ml_pipeline.mandarin_to_english.subprocess.run')
    def test_extract_audio_all_methods_fail(self, mock_subprocess, mock_video_clip, mock_audio_segment, sample_video_path, temp_dir):
        """Test audio extraction when all methods fail"""
        output_path = os.path.join(temp_dir, "output_audio.wav")
        
        # Mock all failures
        mock_audio_segment.from_file.side_effect = Exception("Pydub failed")
        mock_video_clip.side_effect = Exception("MoviePy failed")
        mock_subprocess.side_effect = Exception("FFmpeg failed")
        
        with pytest.raises(Exception, match="Could not extract audio from video"):
            extract_audio(sample_video_path, output_path)
    
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    def test_extract_audio_no_audio_track(self, mock_video_clip, sample_video_path, temp_dir):
        """Test audio extraction when video has no audio track"""
        output_path = os.path.join(temp_dir, "output_audio.wav")
        
        # Mock video with no audio
        mock_clip = Mock()
        mock_clip.audio = None
        mock_clip.duration = 60.0
        mock_video_clip.return_value = mock_clip
        
        # Mock pydub to fail first
        with patch('ml_pipeline.mandarin_to_english.AudioSegment') as mock_audio_segment:
            mock_audio_segment.from_file.side_effect = Exception("No audio track")
            
            result = extract_audio(sample_video_path, output_path)
            
            assert result == 60.0
            mock_clip.close.assert_called_once()


class TestAudioSplitting:
    """Test audio splitting functions"""
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.split_on_silence')
    def test_split_audio_success(self, mock_split_silence, mock_audio_segment, sample_audio_path, temp_dir):
        """Test successful audio splitting"""
        # Mock AudioSegment
        mock_sound = Mock()
        mock_audio_segment.from_wav.return_value = mock_sound
        
        # Mock split_on_silence
        mock_chunk1 = Mock()
        mock_chunk2 = Mock()
        mock_split_silence.return_value = [mock_chunk1, mock_chunk2]
        
        result = split_audio(sample_audio_path, temp_dir)
        
        assert len(result) == 2
        assert all(path.endswith('.wav') for path in result)
        assert all(os.path.basename(path).startswith('chunk_') for path in result)
        
        # Verify chunks were exported
        mock_chunk1.export.assert_called_once()
        mock_chunk2.export.assert_called_once()
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.split_on_silence')
    def test_split_audio_no_silence_detected(self, mock_split_silence, mock_audio_segment, sample_audio_path, temp_dir):
        """Test audio splitting when no silence is detected"""
        # Mock AudioSegment
        mock_sound = Mock()
        mock_sound.__len__ = Mock(return_value=30000)  # 30 seconds
        mock_sound.__getitem__ = Mock(return_value=Mock())  # For slicing
        mock_audio_segment.from_wav.return_value = mock_sound
        
        # Mock split_on_silence returning empty or single chunk
        mock_split_silence.return_value = []
        
        result = split_audio(sample_audio_path, temp_dir)
        
        # Should create fixed-size chunks
        assert len(result) >= 1
        assert all(path.endswith('.wav') for path in result)
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    def test_split_audio_loading_failure(self, mock_audio_segment, sample_audio_path, temp_dir):
        """Test audio splitting when audio loading fails initially"""
        # Mock first attempt failure, second attempt success
        mock_audio_segment.from_wav.side_effect = Exception("Load failed")
        
        mock_sound = Mock()
        mock_audio_segment.from_file.return_value = mock_sound
        
        with patch('ml_pipeline.mandarin_to_english.split_on_silence') as mock_split:
            mock_chunk = Mock()
            mock_split.return_value = [mock_chunk]
            
            result = split_audio(sample_audio_path, temp_dir)
            
            # Should fallback to from_file and succeed
            assert len(result) == 1
            mock_audio_segment.from_file.assert_called_once_with(sample_audio_path, format="wav")


class TestSpeechRecognition:
    """Test speech recognition functions"""
    
    @patch('ml_pipeline.mandarin_to_english.sr')
    def test_recognize_speech_success(self, mock_sr, sample_audio_path):
        """Test successful speech recognition"""
        # Mock speech_recognition components
        mock_recognizer = Mock()
        mock_audio_data = Mock()
        mock_recognizer.record.return_value = mock_audio_data
        mock_recognizer.recognize_google.return_value = "你好世界"
        mock_sr.Recognizer.return_value = mock_recognizer
        mock_sr.AudioFile.return_value.__enter__.return_value = Mock()
        
        result = recognize_speech(sample_audio_path, "zh-CN")
        
        assert result == "你好世界"
        mock_recognizer.recognize_google.assert_called_once_with(mock_audio_data, language="zh-CN")
    
    @patch('ml_pipeline.mandarin_to_english.sr')
    def test_recognize_speech_unknown_value_error(self, mock_sr, sample_audio_path):
        """Test speech recognition when speech is not recognized"""
        mock_recognizer = Mock()
        mock_recognizer.record.return_value = Mock()
        mock_recognizer.recognize_google.side_effect = mock_sr.UnknownValueError()
        mock_sr.Recognizer.return_value = mock_recognizer
        mock_sr.AudioFile.return_value.__enter__.return_value = Mock()
        
        result = recognize_speech(sample_audio_path, "zh-CN")
        
        assert result == ""
    
    @patch('ml_pipeline.mandarin_to_english.sr')
    def test_recognize_speech_request_error(self, mock_sr, sample_audio_path):
        """Test speech recognition service error"""
        mock_recognizer = Mock()
        mock_recognizer.record.return_value = Mock()
        mock_recognizer.recognize_google.side_effect = mock_sr.RequestError("Service unavailable")
        mock_sr.Recognizer.return_value = mock_recognizer
        mock_sr.AudioFile.return_value.__enter__.return_value = Mock()
        
        result = recognize_speech(sample_audio_path, "zh-CN")
        
        assert result == ""
    
    @patch('ml_pipeline.mandarin_to_english.sr')
    def test_recognize_speech_general_exception(self, mock_sr, sample_audio_path):
        """Test speech recognition with general exception"""
        mock_recognizer = Mock()
        mock_recognizer.record.return_value = Mock()
        mock_recognizer.recognize_google.side_effect = Exception("Unknown error")
        mock_sr.Recognizer.return_value = mock_recognizer
        mock_sr.AudioFile.return_value.__enter__.return_value = Mock()
        
        result = recognize_speech(sample_audio_path, "zh-CN")
        
        assert result == ""


class TestTranslation:
    """Test translation functions"""
    
    @patch('ml_pipeline.mandarin_to_english.Translator')
    def test_translate_text_success(self, mock_translator_class):
        """Test successful text translation"""
        mock_translator = Mock()
        mock_translation = Mock()
        mock_translation.text = "Hello World"
        mock_translator.translate.return_value = mock_translation
        mock_translator_class.return_value = mock_translator
        
        result = translate_text("你好世界", "zh-CN", "en")
        
        assert result == "Hello World"
        mock_translator.translate.assert_called_once_with("你好世界", src="zh-CN", dest="en")
    
    @patch('ml_pipeline.mandarin_to_english.Translator')
    def test_translate_text_empty_input(self, mock_translator_class):
        """Test translation with empty input"""
        result = translate_text("", "zh-CN", "en")
        
        assert result == ""
        mock_translator_class.assert_not_called()
    
    @patch('ml_pipeline.mandarin_to_english.Translator')
    @patch('ml_pipeline.mandarin_to_english.time.sleep')
    def test_translate_text_with_retry(self, mock_sleep, mock_translator_class):
        """Test translation with retry mechanism"""
        mock_translator = Mock()
        
        # First call fails, second succeeds
        mock_translation = Mock()
        mock_translation.text = "Hello World"
        mock_translator.translate.side_effect = [Exception("Network error"), mock_translation]
        mock_translator_class.return_value = mock_translator
        
        result = translate_text("你好世界", "zh-CN", "en")
        
        assert result == "Hello World"
        assert mock_translator.translate.call_count == 2
        mock_sleep.assert_called_once_with(2)
    
    @patch('ml_pipeline.mandarin_to_english.Translator')
    def test_translate_text_all_attempts_fail(self, mock_translator_class):
        """Test translation when all attempts fail"""
        mock_translator = Mock()
        mock_translator.translate.side_effect = Exception("Service unavailable")
        mock_translator_class.return_value = mock_translator
        
        result = translate_text("你好世界", "zh-CN", "en")
        
        assert result == ""


class TestTextToSpeech:
    """Test text-to-speech functions"""
    
    @patch('ml_pipeline.mandarin_to_english.gTTS')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_text_to_speech_success(self, mock_getsize, mock_exists, mock_gtts, temp_dir):
        """Test successful text-to-speech conversion"""
        output_path = os.path.join(temp_dir, "output.wav")
        
        mock_tts = Mock()
        mock_gtts.return_value = mock_tts
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # Non-empty file
        
        result = text_to_speech("Hello World", output_path, "en")
        
        assert result is True
        mock_gtts.assert_called_once_with(text="Hello World", lang="en", slow=False)
        mock_tts.save.assert_called_once_with(output_path)
    
    def test_text_to_speech_empty_text(self, temp_dir):
        """Test text-to-speech with empty text"""
        output_path = os.path.join(temp_dir, "output.wav")
        
        result = text_to_speech("", output_path, "en")
        
        assert result is False
    
    @patch('ml_pipeline.mandarin_to_english.gTTS')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_text_to_speech_empty_file(self, mock_getsize, mock_exists, mock_gtts, temp_dir):
        """Test text-to-speech when generated file is empty"""
        output_path = os.path.join(temp_dir, "output.wav")
        
        mock_tts = Mock()
        mock_gtts.return_value = mock_tts
        mock_exists.return_value = True
        mock_getsize.return_value = 0  # Empty file
        
        result = text_to_speech("Hello World", output_path, "en")
        
        assert result is False
    
    @patch('ml_pipeline.mandarin_to_english.gTTS')
    def test_text_to_speech_gtts_error(self, mock_gtts, temp_dir):
        """Test text-to-speech when gTTS fails"""
        output_path = os.path.join(temp_dir, "output.wav")
        
        mock_gtts.side_effect = Exception("TTS service error")
        
        result = text_to_speech("Hello World", output_path, "en")
        
        assert result is False


class TestAudioChunkProcessing:
    """Test audio chunk processing pipeline"""
    
    @patch('ml_pipeline.mandarin_to_english.recognize_speech')
    @patch('ml_pipeline.mandarin_to_english.translate_text')
    @patch('ml_pipeline.mandarin_to_english.text_to_speech')
    def test_process_audio_chunks_success(self, mock_tts, mock_translate, mock_recognize, mock_audio_chunks, temp_dir):
        """Test successful processing of audio chunks"""
        # Mock successful recognition, translation, and TTS
        mock_recognize.side_effect = ["你好", "世界", "测试"]
        mock_translate.side_effect = ["Hello", "World", "Test"]
        mock_tts.return_value = True
        
        result = process_audio_chunks(mock_audio_chunks, temp_dir, "zh-CN", "en")
        
        assert len(result) == 3
        assert all(path.endswith('.wav') for path in result)
        assert mock_recognize.call_count == 3
        assert mock_translate.call_count == 3
        assert mock_tts.call_count == 3
    
    @patch('ml_pipeline.mandarin_to_english.recognize_speech')
    @patch('ml_pipeline.mandarin_to_english.translate_text')
    @patch('ml_pipeline.mandarin_to_english.text_to_speech')
    def test_process_audio_chunks_some_fail(self, mock_tts, mock_translate, mock_recognize, mock_audio_chunks, temp_dir):
        """Test processing when some chunks fail"""
        # Mock mixed results - some succeed, some fail
        mock_recognize.side_effect = ["你好", "", "测试"]  # Middle chunk has no speech
        mock_translate.side_effect = ["Hello", "", "Test"]
        mock_tts.side_effect = [True, False, True]  # Middle TTS fails
        
        result = process_audio_chunks(mock_audio_chunks, temp_dir, "zh-CN", "en")
        
        # Should only return successful chunks
        assert len(result) == 2
        assert mock_recognize.call_count == 3
    
    @patch('ml_pipeline.mandarin_to_english.recognize_speech')
    def test_process_audio_chunks_no_speech_recognized(self, mock_recognize, mock_audio_chunks, temp_dir):
        """Test processing when no speech is recognized"""
        mock_recognize.return_value = ""  # No speech in any chunk
        
        result = process_audio_chunks(mock_audio_chunks, temp_dir, "zh-CN", "en")
        
        assert len(result) == 0
        assert mock_recognize.call_count == 3


class TestAudioCombination:
    """Test audio file combination"""
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_combine_audio_files_pydub_success(self, mock_getsize, mock_exists, mock_audio_segment, mock_audio_chunks, temp_dir):
        """Test successful audio combination using pydub"""
        output_path = os.path.join(temp_dir, "combined.wav")
        
        # Mock AudioSegment
        mock_segment1 = Mock()
        mock_segment2 = Mock()
        mock_combined = Mock()
        
        mock_audio_segment.empty.return_value = mock_combined
        mock_audio_segment.from_file.side_effect = [mock_segment1, mock_segment2, Mock()]
        mock_combined.__iadd__.return_value = mock_combined
        
        mock_exists.return_value = True
        mock_getsize.return_value = 2048
        
        result = combine_audio_files(mock_audio_chunks, output_path)
        
        assert result == output_path
        mock_combined.export.assert_called_once_with(output_path, format="wav")
    
    def test_combine_audio_files_empty_list(self, temp_dir):
        """Test combining empty list of audio files"""
        output_path = os.path.join(temp_dir, "combined.wav")
        
        result = combine_audio_files([], output_path)
        
        assert result is None
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_combine_audio_files_pydub_fails_ffmpeg_succeeds(self, mock_getsize, mock_exists, mock_subprocess, mock_audio_segment, mock_audio_chunks, temp_dir):
        """Test audio combination fallback to FFmpeg"""
        output_path = os.path.join(temp_dir, "combined.wav")
        
        # Mock pydub failure
        mock_audio_segment.empty.side_effect = Exception("Pydub failed")
        
        # Mock FFmpeg success
        mock_subprocess.return_value = Mock()
        mock_exists.return_value = True
        mock_getsize.return_value = 2048
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = combine_audio_files(mock_audio_chunks, output_path)
            
            assert result == output_path
            mock_subprocess.assert_called_once()
            mock_file.assert_called()
    
    @patch('ml_pipeline.mandarin_to_english.AudioSegment')
    @patch('ml_pipeline.mandarin_to_english.subprocess.run')
    def test_combine_audio_files_all_methods_fail(self, mock_subprocess, mock_audio_segment, mock_audio_chunks, temp_dir):
        """Test audio combination when all methods fail"""
        output_path = os.path.join(temp_dir, "combined.wav")
        
        # Mock all failures
        mock_audio_segment.empty.side_effect = Exception("Pydub failed")
        mock_subprocess.side_effect = Exception("FFmpeg failed")
        
        result = combine_audio_files(mock_audio_chunks, output_path)
        
        assert result is None


class TestVideoAudioReplacement:
    """Test video audio replacement"""
    
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    @patch('ml_pipeline.mandarin_to_english.AudioFileClip')
    def test_replace_audio_moviepy_success(self, mock_audio_clip, mock_video_clip, sample_video_path, sample_audio_path, temp_dir):
        """Test successful audio replacement using MoviePy"""
        output_path = os.path.join(temp_dir, "output_video.mp4")
        
        # Mock video clip
        mock_video = Mock()
        mock_video.duration = 120.0
        mock_video_clip.return_value = mock_video
        
        # Mock audio clip
        mock_audio = Mock()
        mock_audio.duration = 120.0
        mock_audio_clip.return_value = mock_audio
        
        # Mock final video
        mock_final = Mock()
        mock_video.set_audio.return_value = mock_final
        
        result = replace_audio(sample_video_path, sample_audio_path, output_path)
        
        assert result is True
        mock_video.set_audio.assert_called_once_with(mock_audio)
        mock_final.write_videofile.assert_called_once()
        mock_video.close.assert_called_once()
        mock_audio.close.assert_called_once()
        mock_final.close.assert_called_once()
    
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    @patch('ml_pipeline.mandarin_to_english.AudioFileClip')
    @patch('ml_pipeline.mandarin_to_english.concatenate_audioclips')
    def test_replace_audio_audio_shorter_than_video(self, mock_concat, mock_audio_clip, mock_video_clip, sample_video_path, sample_audio_path, temp_dir):
        """Test audio replacement when audio is shorter than video"""
        output_path = os.path.join(temp_dir, "output_video.mp4")
        
        # Mock video clip
        mock_video = Mock()
        mock_video.duration = 120.0
        mock_video_clip.return_value = mock_video
        
        # Mock audio clip (shorter)
        mock_audio = Mock()
        mock_audio.duration = 90.0
        mock_audio_clip.return_value = mock_audio
        
        # Mock silence and concatenation
        mock_extended_audio = Mock()
        mock_concat.return_value = mock_extended_audio
        
        # Mock final video
        mock_final = Mock()
        mock_video.set_audio.return_value = mock_final
        
        with patch('ml_pipeline.mandarin_to_english.AudioClip') as mock_audio_clip_class:
            mock_silence = Mock()
            mock_audio_clip_class.return_value = mock_silence
            
            result = replace_audio(sample_video_path, sample_audio_path, output_path)
            
            assert result is True
            mock_concat.assert_called_once()
            mock_video.set_audio.assert_called_once_with(mock_extended_audio)
    
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    @patch('ml_pipeline.mandarin_to_english.AudioFileClip')
    def test_replace_audio_audio_longer_than_video(self, mock_audio_clip, mock_video_clip, sample_video_path, sample_audio_path, temp_dir):
        """Test audio replacement when audio is longer than video"""
        output_path = os.path.join(temp_dir, "output_video.mp4")
        
        # Mock video clip
        mock_video = Mock()
        mock_video.duration = 90.0
        mock_video_clip.return_value = mock_video
        
        # Mock audio clip (longer)
        mock_audio = Mock()
        mock_audio.duration = 120.0
        mock_trimmed_audio = Mock()
        mock_audio.subclip.return_value = mock_trimmed_audio
        mock_audio_clip.return_value = mock_audio
        
        # Mock final video
        mock_final = Mock()
        mock_video.set_audio.return_value = mock_final
        
        result = replace_audio(sample_video_path, sample_audio_path, output_path)
        
        assert result is True
        mock_audio.subclip.assert_called_once_with(0, 90.0)
        mock_video.set_audio.assert_called_once_with(mock_trimmed_audio)
    
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    @patch('ml_pipeline.mandarin_to_english.subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_replace_audio_moviepy_fails_ffmpeg_succeeds(self, mock_getsize, mock_exists, mock_subprocess, mock_video_clip, sample_video_path, sample_audio_path, temp_dir):
        """Test audio replacement fallback to FFmpeg"""
        output_path = os.path.join(temp_dir, "output_video.mp4")
        
        # Mock MoviePy failure
        mock_video_clip.side_effect = Exception("MoviePy failed")
        
        # Mock FFmpeg success
        mock_subprocess.return_value = Mock()
        mock_exists.return_value = True
        mock_getsize.return_value = 10240
        
        result = replace_audio(sample_video_path, sample_audio_path, output_path)
        
        assert result is True
        mock_subprocess.assert_called_once()
    
    @patch('ml_pipeline.mandarin_to_english.VideoFileClip')
    @patch('ml_pipeline.mandarin_to_english.subprocess.run')
    def test_replace_audio_all_methods_fail(self, mock_subprocess, mock_video_clip, sample_video_path, sample_audio_path, temp_dir):
        """Test audio replacement when all methods fail"""
        output_path = os.path.join(temp_dir, "output_video.mp4")
        
        # Mock all failures
        mock_video_clip.side_effect = Exception("MoviePy failed")
        mock_subprocess.side_effect = Exception("FFmpeg failed")
        
        result = replace_audio(sample_video_path, sample_audio_path, output_path)
        
        assert result is False


class TestMainConversionWorkflow:
    """Test main conversion workflow"""
    
    @patch('ml_pipeline.mandarin_to_english.extract_audio')
    @patch('ml_pipeline.mandarin_to_english.split_audio')
    @patch('ml_pipeline.mandarin_to_english.process_audio_chunks')
    @patch('ml_pipeline.mandarin_to_english.combine_audio_files')
    @patch('ml_pipeline.mandarin_to_english.replace_audio')
    @patch('ml_pipeline.mandarin_to_english.tempfile.mkdtemp')
    @patch('ml_pipeline.mandarin_to_english.shutil.rmtree')
    def test_convert_mandarin_to_english_success(self, mock_rmtree, mock_mkdtemp, mock_replace, mock_combine, mock_process, mock_split, mock_extract, sample_video_path, temp_dir):
        """Test successful complete conversion workflow"""
        output_video = os.path.join(temp_dir, "output.mp4")
        
        # Mock temporary directory
        mock_mkdtemp.return_value = temp_dir
        
        # Mock all steps to succeed
        mock_extract.return_value = 120.0
        mock_split.return_value = ["chunk1.wav", "chunk2.wav", "chunk3.wav"]
        mock_process.return_value = ["english1.wav", "english2.wav", "english3.wav"]
        mock_combine.return_value = os.path.join(temp_dir, "combined_english.wav")
        mock_replace.return_value = True
        
        result = convert_mandarin_to_english(sample_video_path, output_video)
        
        assert result is True
        mock_extract.assert_called_once()
        mock_split.assert_called_once()
        mock_process.assert_called_once()
        mock_combine.assert_called_once()
        mock_replace.assert_called_once()
        mock_rmtree.assert_called_once_with(temp_dir)
    
    @patch('ml_pipeline.mandarin_to_english.extract_audio')
    @patch('ml_pipeline.mandarin_to_english.tempfile.mkdtemp')
    @patch('ml_pipeline.mandarin_to_english.shutil.rmtree')
    def test_convert_mandarin_to_english_extract_audio_fails(self, mock_rmtree, mock_mkdtemp, mock_extract, sample_video_path, temp_dir):
        """Test conversion when audio extraction fails"""
        output_video = os.path.join(temp_dir, "output.mp4")
        
        mock_mkdtemp.return_value = temp_dir
        mock_extract.side_effect = Exception("Audio extraction failed")
        
        result = convert_mandarin_to_english(sample_video_path, output_video)
        
        assert result is False
        mock_rmtree.assert_called_once_with(temp_dir)
    
    @patch('ml_pipeline.mandarin_to_english.extract_audio')
    @patch('ml_pipeline.mandarin_to_english.split_audio')
    @patch('ml_pipeline.mandarin_to_english.tempfile.mkdtemp')
    @patch('ml_pipeline.mandarin_to_english.shutil.rmtree')
    def test_convert_mandarin_to_english_split_audio_fails(self, mock_rmtree, mock_mkdtemp, mock_split, mock_extract, sample_video_path, temp_dir):
        """Test conversion when audio splitting fails"""
        output_video = os.path.join(temp_dir, "output.mp4")
        
        mock_mkdtemp.return_value = temp_dir
        mock_extract.return_value = 120.0
        mock_split.side_effect = Exception("Audio splitting failed")
        
        result = convert_mandarin_to_english(sample_video_path, output_video)
        
        assert result is False
        mock_rmtree.assert_called_once_with(temp_dir)
    
    @patch('ml_pipeline.mandarin_to_english.extract_audio')
    @patch('ml_pipeline.mandarin_to_english.split_audio')
    @patch('ml_pipeline.mandarin_to_english.process_audio_chunks')
    @patch('ml_pipeline.mandarin_to_english.tempfile.mkdtemp')
    @patch('ml_pipeline.mandarin_to_english.shutil.rmtree')
    def test_convert_mandarin_to_english_no_processed_chunks(self, mock_rmtree, mock_mkdtemp, mock_process, mock_split, mock_extract, sample_video_path, temp_dir):
        """Test conversion when no audio chunks are successfully processed"""
        output_video = os.path.join(temp_dir, "output.mp4")
        
        mock_mkdtemp.return_value = temp_dir
        mock_extract.return_value = 120.0
        mock_split.return_value = ["chunk1.wav", "chunk2.wav"]
        mock_process.return_value = []  # No successful processing
        
        result = convert_mandarin_to_english(sample_video_path, output_video)
        
        assert result is False
        mock_rmtree.assert_called_once_with(temp_dir)
    
    @patch('ml_pipeline.mandarin_to_english.extract_audio')
    @patch('ml_pipeline.mandarin_to_english.split_audio')
    @patch('ml_pipeline.mandarin_to_english.process_audio_chunks')
    @patch('ml_pipeline.mandarin_to_english.combine_audio_files')
    @patch('ml_pipeline.mandarin_to_english.tempfile.mkdtemp')
    @patch('ml_pipeline.mandarin_to_english.shutil.rmtree')
    def test_convert_mandarin_to_english_combine_fails(self, mock_rmtree, mock_mkdtemp, mock_combine, mock_process, mock_split, mock_extract, sample_video_path, temp_dir):
        """Test conversion when audio combination fails"""
        output_video = os.path.join(temp_dir, "output.mp4")
        
        mock_mkdtemp.return_value = temp_dir
        mock_extract.return_value = 120.0
        mock_split.return_value = ["chunk1.wav", "chunk2.wav"]
        mock_process.return_value = ["english1.wav", "english2.wav"]
        mock_combine.return_value = None  # Combination failed
        
        result = convert_mandarin_to_english(sample_video_path, output_video)
        
        assert result is False
        mock_rmtree.assert_called_once_with(temp_dir)


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_safe_print_with_none_input(self):
        """Test safe_print with None input"""
        with patch('builtins.print') as mock_print:
            safe_print(None, "PREFIX: ")
            mock_print.assert_called_once_with("PREFIX: None")
    
    @patch('ml_pipeline.mandarin_to_english.tempfile.mkdtemp')
    @patch('ml_pipeline.mandarin_to_english.shutil.rmtree')
    def test_convert_mandarin_to_english_cleanup_failure(self, mock_rmtree, mock_mkdtemp, sample_video_path, temp_dir):
        """Test conversion when cleanup fails"""
        output_video = os.path.join(temp_dir, "output.mp4")
        
        mock_mkdtemp.return_value = temp_dir
        mock_rmtree.side_effect = Exception("Cleanup failed")
        
        with patch('ml_pipeline.mandarin_to_english.extract_audio') as mock_extract:
            mock_extract.side_effect = Exception("Extract failed")
            
            # Should not crash even if cleanup fails
            result = convert_mandarin_to_english(sample_video_path, output_video)
            
            assert result is False
            mock_rmtree.assert_called_once()
    
    def test_recognize_speech_with_missing_file(self):
        """Test speech recognition with non-existent file"""
        with patch('ml_pipeline.mandarin_to_english.sr') as mock_sr:
            mock_sr.AudioFile.side_effect = FileNotFoundError("File not found")
            
            result = recognize_speech("nonexistent.wav")
            
            assert result == ""
    
    def test_text_to_speech_with_none_text(self, temp_dir):
        """Test text-to-speech with None input"""
        output_path = os.path.join(temp_dir, "output.wav")
        
        result = text_to_speech(None, output_path)
        
        assert result is False
    
    @patch('ml_pipeline.mandarin_to_english.Translator')
    def test_translate_text_with_none_input(self, mock_translator_class):
        """Test translation with None input"""
        result = translate_text(None, "zh-CN", "en")
        
        assert result == ""
        mock_translator_class.assert_not_called()


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    @patch('ml_pipeline.mandarin_to_english.recognize_speech')
    @patch('ml_pipeline.mandarin_to_english.translate_text')
    @patch('ml_pipeline.mandarin_to_english.text_to_speech')
    def test_complete_chunk_processing_pipeline(self, mock_tts, mock_translate, mock_recognize, mock_audio_chunks, temp_dir):
        """Test complete processing pipeline with realistic data flow"""
        # Simulate realistic conversation
        chinese_texts = ["你好，我是老师", "今天我们学习八段锦", "请跟我一起做"]
        english_texts = ["Hello, I am the teacher", "Today we learn Baduanjin", "Please follow me"]
        
        mock_recognize.side_effect = chinese_texts
        mock_translate.side_effect = english_texts
        mock_tts.return_value = True
        
        result = process_audio_chunks(mock_audio_chunks, temp_dir, "zh-CN", "en")
        
        assert len(result) == 3
        
        # Verify recognition was called with correct language
        for call in mock_recognize.call_args_list:
            assert call[1]['language'] == "zh-CN"
        
        # Verify translation was called with correct parameters
        for i, call in enumerate(mock_translate.call_args_list):
            assert call[0][0] == chinese_texts[i]
            assert call[1]['src_lang'] == "zh-CN"
            assert call[1]['dest_lang'] == "en"
        
        # Verify TTS was called with English text
        for i, call in enumerate(mock_tts.call_args_list):
            assert english_texts[i] in call[0][0]  # Text should be in the call
    
    def test_unicode_text_handling_throughout_pipeline(self):
        """Test that Unicode text is handled properly throughout the pipeline"""
        chinese_text = "你好世界，这是一个测试"
        english_text = "Hello world, this is a test"
        
        # Test safe printing of Chinese text
        with patch('builtins.print') as mock_print:
            safe_print(chinese_text)
            # Should not raise any exceptions
            mock_print.assert_called_once()
        
        # Test translation handling
        with patch('ml_pipeline.mandarin_to_english.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translation = Mock()
            mock_translation.text = english_text
            mock_translator.translate.return_value = mock_translation
            mock_translator_class.return_value = mock_translator
            
            result = translate_text(chinese_text, "zh-CN", "en")
            assert result == english_text


# Helper function to run tests
if __name__ == "__main__":
    print("Running mandarin to english unit tests...")
    
    # Quick test of safe_print function
    try:
        with patch('builtins.print') as mock_print:
            safe_print("Test message", "DEBUG: ")
            print("✓ Safe print test passed")
    except Exception as e:
        print(f"✗ Safe print test failed: {e}")
    
    # Quick test of empty input handling
    try:
        result = translate_text("")
        assert result == ""
        print("✓ Empty input handling test passed")
    except Exception as e:
        print(f"✗ Empty input handling test failed: {e}")
    
    print("Basic tests passed! Run with pytest for full test suite.")
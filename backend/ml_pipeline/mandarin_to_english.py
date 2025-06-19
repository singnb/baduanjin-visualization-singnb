# ml_pipeline/mandarin_to_english.py
# Modified version with better encoding handling

import sys
import os
import tempfile
import time
import subprocess
import shutil

# Set console encoding explicitly for better Unicode handling
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import speech_recognition as sr
except ImportError:
    print("Error: speech_recognition package is missing. Install it with:")
    print("pip install SpeechRecognition")
    sys.exit(1)

try:
    from googletrans import Translator
except ImportError:
    print("Error: googletrans package is missing. Install it with:")
    print("pip install googletrans==4.0.0-rc1")
    sys.exit(1)

try:
    from gtts import gTTS
except ImportError:
    print("Error: gTTS package is missing. Install it with:")
    print("pip install gTTS")
    sys.exit(1)

try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
except ImportError:
    print("Error: pydub package is missing. Install it with:")
    print("pip install pydub")
    sys.exit(1)

try:
    import moviepy.editor as mp
    VideoFileClip = mp.VideoFileClip
    AudioFileClip = mp.AudioFileClip
    concatenate_audioclips = mp.concatenate_audioclips
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.audio.AudioClip import concatenate_audioclips
    except ImportError:
        print("Error: moviepy package is not installed correctly. Try reinstalling it with:")
        print("pip uninstall moviepy")
        print("pip install moviepy")
        sys.exit(1)

def safe_print(text, prefix=""):
    """Print text safely, handling encoding errors"""
    try:
        print(f"{prefix}{text}")
    except UnicodeEncodeError:
        # If we can't print the whole text, try to print parts or a placeholder
        try:
            # Try to print ASCII parts
            printable = ''.join(c if ord(c) < 128 else '?' for c in text)
            print(f"{prefix}[Encoded text: {printable}]")
        except:
            print(f"{prefix}[Text contains non-displayable characters]")

def extract_audio(video_path, output_audio_path):
    """Extract audio from video file."""
    print(f"Extracting audio from {video_path}...")
    
    # Check if ffmpeg is available (used by both moviepy and pydub)
    try:
        # Try using pydub directly for extraction
        video = AudioSegment.from_file(video_path, format="mp4")
        video.export(output_audio_path, format="wav")
        
        # Get duration
        video_clip = VideoFileClip(video_path)
        duration = video_clip.duration
        video_clip.close()
        
        return duration
    except Exception as e:
        print(f"  Pydub extraction failed: {e}")
        
        # Fallback to moviepy
        try:
            video = VideoFileClip(video_path)
            if video.audio is None:
                print("  No audio track found in video")
                return video.duration
                
            # Try simplified parameter set
            video.audio.write_audiofile(output_audio_path)
            duration = video.duration
            video.close()
            return duration
        except Exception as e2:
            print(f"  MoviePy extraction failed: {e2}")
            
            # Last resort: try using ffmpeg directly
            try:
                cmd = ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", output_audio_path, "-y"]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Get duration with ffprobe
                duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
                result = subprocess.run(duration_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                duration = float(result.stdout.decode('utf-8').strip())
                
                return duration
            except Exception as e3:
                print(f"  Direct ffmpeg extraction failed: {e3}")
                raise Exception("Could not extract audio from video")

def split_audio(audio_path, output_dir, min_silence_len=700, silence_thresh=-40):
    """Split audio file into chunks based on silence."""
    print("Splitting audio into chunks based on silence...")
    try:
        sound = AudioSegment.from_wav(audio_path)
    except Exception as e:
        print(f"Error loading audio file: {e}")
        # Try forcing the format
        try:
            sound = AudioSegment.from_file(audio_path, format="wav")
        except Exception as e2:
            print(f"Second attempt to load audio failed: {e2}")
            raise
    
    # Split on silence
    try:
        chunks = split_on_silence(
            sound,
            min_silence_len=min_silence_len,  # minimum silence length in ms
            silence_thresh=silence_thresh,    # silence threshold in dB
            keep_silence=300                  # keep some silence at the beginning and end
        )
    except Exception as e:
        print(f"Error splitting on silence: {e}")
        chunks = []
    
    # If no chunks were detected or only one large chunk, create fixed-size chunks
    if len(chunks) <= 1:
        print("No silence detected or split_on_silence failed. Using fixed-size chunks...")
        chunk_length_ms = 10000  # 10 seconds
        chunks = [sound[i:i+chunk_length_ms] for i in range(0, len(sound), chunk_length_ms)]
    
    # Export chunks
    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_file = os.path.join(output_dir, f"chunk_{i:03d}.wav")
        chunk.export(chunk_file, format="wav")
        chunk_files.append(chunk_file)
    
    print(f"Created {len(chunk_files)} audio chunks")
    return chunk_files

def recognize_speech(audio_file, language="zh-CN"):
    """Recognize speech in audio file using Google's speech recognition."""
    recognizer = sr.Recognizer()
    
    # Adjust recognizer parameters
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language=language)
            return text
        except sr.UnknownValueError:
            print(f"  Speech not recognized in {os.path.basename(audio_file)}")
            return ""
        except sr.RequestError as e:
            print(f"  Google Speech Recognition service error: {e}")
            return ""
        except Exception as e:
            print(f"  Error in speech recognition: {e}")
            return ""

def translate_text(text, src_lang="zh-CN", dest_lang="en"):
    """Translate text using Google Translate."""
    if not text:
        return ""
    
    try:
        translator = Translator()
        translation = translator.translate(text, src=src_lang, dest=dest_lang)
        return translation.text
    except Exception as e:
        print(f"  Translation error: {e}")
        # Retry once with a delay
        try:
            time.sleep(2)
            translator = Translator()
            translation = translator.translate(text, src=src_lang, dest=dest_lang)
            return translation.text
        except:
            print(f"  Translation retry failed")
            return ""

def text_to_speech(text, output_path, lang="en"):
    """Convert text to speech using Google Text-to-Speech."""
    if not text:
        return False
    
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        # Save as WAV instead of MP3 to avoid potential format issues
        tts.save(output_path)
        
        # Verify the file exists and is not empty
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            print(f"  Generated audio file is empty or does not exist")
            return False
    except Exception as e:
        print(f"  Text-to-speech error: {e}")
        return False

def process_audio_chunks(chunk_files, temp_dir, src_lang="zh-CN", dest_lang="en"):
    """Process each audio chunk: recognize, translate, synthesize."""
    english_audio_files = []
    
    total_chunks = len(chunk_files)
    for i, chunk_file in enumerate(chunk_files):
        print(f"Processing chunk {i+1}/{total_chunks}: {os.path.basename(chunk_file)}")
        
        # Speech recognition
        chinese_text = recognize_speech(chunk_file, language=src_lang)
        if not chinese_text:
            print(f"  No speech recognized in chunk {i+1}, skipping...")
            continue
        
        # MODIFIED: Handle Chinese text printing safely
        try:
            # Try to print with truncation if too long
            if len(chinese_text) > 50:
                print(f"  Recognized text: {chinese_text[:50]}...")
            else:
                print(f"  Recognized text: {chinese_text}")
        except UnicodeEncodeError:
            print("  Recognized text: [Chinese characters - not displayable in console]")
        
        # Translation
        english_text = translate_text(chinese_text, src_lang=src_lang, dest_lang=dest_lang)
        if not english_text:
            print(f"  Translation failed for chunk {i+1}, skipping...")
            continue
        
        # MODIFIED: Safely print translated text
        try:
            # Try to print with truncation if too long
            if len(english_text) > 50:
                print(f"  Translated text: {english_text[:50]}...")
            else:
                print(f"  Translated text: {english_text}")
        except UnicodeEncodeError:
            print("  Translated text: [Some characters not displayable in console]")
        
        # Text to speech - save as WAV instead of MP3
        english_audio_file = os.path.join(temp_dir, f"english_chunk_{i:03d}.wav")
        if text_to_speech(english_text, english_audio_file, lang=dest_lang[:2]):
            english_audio_files.append(english_audio_file)
        else:
            print(f"  Text-to-speech failed for chunk {i+1}, skipping...")
    
    return english_audio_files

def combine_audio_files(audio_files, output_path):
    """Combine multiple audio files into one."""
    print(f"Combining {len(audio_files)} audio chunks...")
    
    if not audio_files:
        return None
    
    try:
        # Method 1: Using pydub
        combined = AudioSegment.empty()
        for audio_file in audio_files:
            segment = AudioSegment.from_file(audio_file)
            combined += segment
        
        # Export as WAV format to avoid potential issues with MP3
        combined.export(output_path, format="wav")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        else:
            raise Exception("Generated combined audio file is empty or does not exist")
            
    except Exception as e:
        print(f"Error combining audio with pydub: {e}")
        
        try:
            # Method 2: Using FFmpeg directly to concatenate
            temp_list_file = os.path.join(os.path.dirname(output_path), "file_list.txt")
            with open(temp_list_file, 'w') as f:
                for audio_file in audio_files:
                    f.write(f"file '{os.path.abspath(audio_file)}'\n")
            
            # Use ffmpeg to concatenate files
            cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", temp_list_file, "-c", "copy", output_path, "-y"]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Clean up
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
                
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                raise Exception("Generated combined audio file is empty or does not exist")
                
        except Exception as e2:
            print(f"Error combining audio with FFmpeg: {e2}")
            return None

def replace_audio(video_path, audio_path, output_path):
    """Replace the audio in a video with a new audio track."""
    print(f"Creating final video with English audio...")
    
    try:
        # Method 1: Using MoviePy
        try:
            video = VideoFileClip(video_path)
            
            # Ensure audio file is readable
            try:
                audio = AudioFileClip(audio_path)
            except Exception as e:
                print(f"Error loading audio with MoviePy: {e}")
                # Convert audio to proper format if needed
                fixed_audio = audio_path + "_fixed.wav"
                cmd = ["ffmpeg", "-i", audio_path, "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", fixed_audio, "-y"]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                audio = AudioFileClip(fixed_audio)
            
            # Adjust audio length to match video
            if audio.duration < video.duration:
                print(f"  Audio ({audio.duration:.2f}s) is shorter than video ({video.duration:.2f}s). Adding silence...")
                # Create a silence clip
                try:
                    from moviepy.audio.AudioClip import AudioClip
                except ImportError:
                    AudioClip = getattr(mp, 'AudioClip', None)
                    if AudioClip is None:
                        from moviepy.audio.AudioClip import AudioClip
                    
                silence = AudioClip(lambda t: 0, duration=video.duration - audio.duration)
                audio = concatenate_audioclips([audio, silence])
            elif audio.duration > video.duration:
                print(f"  Audio ({audio.duration:.2f}s) is longer than video ({video.duration:.2f}s). Trimming...")
                audio = audio.subclip(0, video.duration)
            
            # Set the audio to the video
            final_video = video.set_audio(audio)
            
            # Write the result to a file - try with minimal parameters
            print(f"  Writing final video to {output_path}...")
            try:
                # Try with minimal parameters first
                final_video.write_videofile(output_path)
            except TypeError:
                # If that fails, try specifying codecs without verbose
                final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            # Close the clips to release resources
            video.close()
            audio.close()
            final_video.close()
            
            return True
            
        except Exception as e:
            print(f"MoviePy method failed: {e}")
            raise
            
    except Exception as moviepy_error:
        print(f"Error with MoviePy approach: {moviepy_error}")
        
        # Method 2: Direct FFmpeg approach
        try:
            print("Trying direct FFmpeg approach...")
            cmd = ["ffmpeg", "-i", video_path, "-i", audio_path, "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", 
                  "-shortest", output_path, "-y"]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"  Successfully created video using FFmpeg")
                return True
            else:
                raise Exception("Generated video file is empty or does not exist")
                
        except Exception as e:
            print(f"Direct FFmpeg approach failed: {e}")
            return False

def convert_mandarin_to_english(input_video, output_video):
    """Convert Mandarin audio in a video to English."""
    print(f"\n=== Starting language conversion from Mandarin to English ===")
    print(f"Input: {input_video}")
    print(f"Output: {output_video}")
    
    # Create a temporary directory that will exist until the function completes
    temp_dir = tempfile.mkdtemp()
    try:
        # Step 1: Extract audio from video
        original_audio = os.path.join(temp_dir, "original_audio.wav")
        try:
            video_duration = extract_audio(input_video, original_audio)
        except Exception as e:
            print(f"Failed to extract audio: {e}")
            return False
        
        # Step 2: Split audio into chunks
        try:
            chunk_files = split_audio(original_audio, temp_dir)
        except Exception as e:
            print(f"Failed to split audio: {e}")
            return False
        
        # Step 3: Process audio chunks
        english_audio_files = process_audio_chunks(chunk_files, temp_dir)
        
        if not english_audio_files:
            print("No audio chunks were successfully processed. Exiting.")
            return False
        
        # Step 4: Combine processed audio chunks
        combined_audio = os.path.join(temp_dir, "combined_english.wav")  # Using WAV instead of MP3
        combined_audio_path = combine_audio_files(english_audio_files, combined_audio)
        
        if not combined_audio_path:
            print("Failed to combine audio files. Exiting.")
            return False
        
        # Step 5: Replace audio in the original video
        success = replace_audio(input_video, combined_audio_path, output_video)
        
        if success:
            print(f"\nSuccess! Video with English audio saved to: {output_video}")
            return True
        else:
            print("\nFailed to create the final video.")
            return False
    finally:
        # Clean up the temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Note: Failed to clean up temporary directory: {e}")

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python.exe script.py input.mp4 output.mp4")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    
    # Check if input file exists
    if not os.path.exists(input_video):
        print(f"Error: Input file '{input_video}' does not exist")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_video)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Run the conversion
    start_time = time.time()
    success = convert_mandarin_to_english(input_video, output_video)
    end_time = time.time()
    
    print(f"\nTotal processing time: {end_time - start_time:.2f} seconds")
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
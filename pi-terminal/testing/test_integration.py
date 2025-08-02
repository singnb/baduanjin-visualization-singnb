"""
analyzer_integration.py - Enhanced Baduanjin Analyzer with Exercise Tracking
This inherits from your existing BaduanjinWebAnalyzer and adds exercise tracking capabilities
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import cv2
import numpy as np

# Import your existing analyzer
from analyzer import BaduanjinWebAnalyzer

# Import the new tracker (will gracefully handle if not available)
try:
    from baduanjin_tracker import BaduanjinTracker, ExerciseFeedback
    BADUANJIN_TRACKER_AVAILABLE = True
    print("✅ Baduanjin exercise tracker available")
except ImportError as e:
    print(f"⚠️ Baduanjin tracker not available: {e}")
    BADUANJIN_TRACKER_AVAILABLE = False
    BaduanjinTracker = None
    ExerciseFeedback = None

from config import Config

class EnhancedBaduanjinAnalyzer(BaduanjinWebAnalyzer):
    """Enhanced analyzer that adds exercise tracking to your existing system"""
    
    def __init__(self):
        # Initialize the base analyzer (your existing system)
        super().__init__()
        
        # Initialize Baduanjin tracker if available
        if BADUANJIN_TRACKER_AVAILABLE:
            try:
                self.baduanjin_tracker = BaduanjinTracker(output_dir=str(Config.BADUANJIN_DATA_DIR))
                self.tracking_enabled = False
                self.current_feedback = None
                self.feedback_buffer = []
                self.real_time_data_file = Config.REAL_TIME_FEEDBACK_FILE
                print("✅ Enhanced Baduanjin Analyzer initialized with exercise tracking")
            except Exception as e:
                print(f"⚠️ Error initializing exercise tracker: {e}")
                self.baduanjin_tracker = None
                self.tracking_enabled = False
        else:
            self.baduanjin_tracker = None
            self.tracking_enabled = False
            print("✅ Enhanced Baduanjin Analyzer initialized without exercise tracking")
    
    def enable_exercise_tracking(self, exercise_id: int) -> Dict:
        """Enable real-time exercise tracking for specific Baduanjin exercise"""
        try:
            if not BADUANJIN_TRACKER_AVAILABLE or not self.baduanjin_tracker:
                return {"success": False, "error": "Exercise tracker not available"}
            
            result = self.baduanjin_tracker.start_exercise(exercise_id)
            if result["success"]:
                self.tracking_enabled = True
                self.current_feedback = None
                self.feedback_buffer = []
                print(f"🎯 Exercise tracking enabled: {result['exercise_name']}")
            return result
        except Exception as e:
            print(f"❌ Error enabling tracking: {e}")
            return {"success": False, "error": str(e)}
    
    def disable_exercise_tracking(self) -> Dict:
        """Disable exercise tracking and get summary"""
        try:
            if not self.tracking_enabled or not self.baduanjin_tracker:
                return {"success": False, "message": "No active tracking"}
            
            summary = self.baduanjin_tracker.end_exercise()
            self.tracking_enabled = False
            self.current_feedback = None
            
            # Export session data automatically
            try:
                export_path = self.baduanjin_tracker.export_session_data()
                summary["session_export_path"] = export_path
            except Exception as export_error:
                print(f"⚠️ Error exporting session data: {export_error}")
                summary["export_error"] = str(export_error)
            
            print("🏁 Exercise tracking disabled")
            return summary
        except Exception as e:
            print(f"❌ Error disabling tracking: {e}")
            return {"success": False, "error": str(e)}
    
    def _stream_loop(self):
        """Enhanced stream loop with Baduanjin exercise tracking integrated"""
        fps_counter = 0
        fps_start_time = time.time()
        frame_count = 0
        
        print("🎥 Enhanced stream loop started with exercise tracking!")
        
        try:
            while self.is_running:
                try:
                    frame_count += 1
                    
                    # Capture frame (from your existing system)
                    if not hasattr(self, 'picam2') or self.picam2 is None:
                        print("❌ picam2 is None in stream loop")
                        break
                    
                    try:
                        frame = self.picam2.capture_array()
                    except Exception as capture_error:
                        print(f"❌ Frame capture error: {capture_error}")
                        time.sleep(0.1)
                        continue
                    
                    # Convert to BGR for OpenCV
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Process pose (from your existing system)
                    try:
                        pose_data = self.process_frame(frame_bgr)
                        self.pose_data = pose_data
                    except Exception as pose_error:
                        print(f"❌ Pose processing error: {pose_error}")
                        pose_data = []
                        self.pose_data = []
                    
                    # 🚀 NEW: Real-time exercise tracking
                    if self.tracking_enabled and pose_data and BADUANJIN_TRACKER_AVAILABLE:
                        try:
                            feedback = self.baduanjin_tracker.process_real_time_pose(pose_data)
                            if feedback:
                                self.current_feedback = feedback
                                self.feedback_buffer.append(feedback)
                                
                                # Keep buffer manageable
                                if len(self.feedback_buffer) > 50:
                                    self.feedback_buffer = self.feedback_buffer[-25:]
                                
                                # Save real-time data for frontend
                                self._save_real_time_feedback(feedback)
                                
                                # Log significant feedback occasionally
                                if frame_count % 60 == 0:  # Every 60 frames
                                    print(f"🎯 Exercise: {feedback.exercise_name} | "
                                          f"Phase: {feedback.current_phase} | "
                                          f"Score: {feedback.form_score:.1f} | "
                                          f"Progress: {feedback.completion_percentage:.1f}%")
                        
                        except Exception as tracking_error:
                            print(f"❌ Exercise tracking error: {tracking_error}")
                    
                    # Create annotated frame (from your existing system + exercise overlay)
                    annotated_frame = frame_bgr.copy()
                    try:
                        # Add pose skeleton (your existing code)
                        for person_data in pose_data:
                            keypoints = np.array(person_data['keypoints'])
                            confidences = np.array(person_data['confidences'])
                            annotated_frame = self.draw_pose(annotated_frame, keypoints, confidences)
                    except Exception as draw_error:
                        print(f"❌ Draw pose error: {draw_error}")
                    
                    # Add text overlays (your existing code + exercise info)
                    try:
                        cv2.putText(annotated_frame, 'Baduanjin Live Analysis', (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        cv2.putText(annotated_frame, f'FPS: {self.session_stats.get("current_fps", 0)}', (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(annotated_frame, f'Persons: {len(pose_data)}', (10, 85), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        # Recording indicator
                        if self.is_recording:
                            cv2.putText(annotated_frame, '🔴 REC', (10, 110), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            
                            # DUAL RECORDING: Save both versions (your existing code)
                            if self.video_writer_original and self.video_writer_original.isOpened():
                                self.video_writer_original.write(frame_bgr)  # Original (clean)
                            
                            if self.video_writer_annotated and self.video_writer_annotated.isOpened():
                                self.video_writer_annotated.write(annotated_frame)  # Annotated
                        
                        # 🚀 NEW: Exercise tracking indicator and overlay
                        if self.tracking_enabled:
                            cv2.putText(annotated_frame, '🎯 TRACKING', (10, 135), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            # Add detailed exercise overlay
                            annotated_frame = self._add_exercise_overlay(annotated_frame)
                                    
                    except Exception as overlay_error:
                        print(f"❌ Overlay error: {overlay_error}")
                    
                    # Calculate FPS (your existing code)
                    fps_counter += 1
                    if fps_counter % 30 == 0:
                        elapsed = time.time() - fps_start_time
                        current_fps = 30 / elapsed if elapsed > 0 else 0
                        fps_start_time = time.time()
                        self.session_stats['current_fps'] = round(current_fps, 1)
                    
                    # Update stats
                    self.session_stats['total_frames'] = self.session_stats.get('total_frames', 0) + 1
                    self.session_stats['persons_detected'] = len(pose_data)
                    
                    # Store current frame (annotated version for display)
                    self.current_frame = annotated_frame.copy()
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as loop_error:
                    print(f"❌ Stream loop iteration error: {loop_error}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.1)
                    
                    if not self.is_running:
                        break
        
        except Exception as fatal_error:
            print(f"❌ Fatal stream loop error: {fatal_error}")
            import traceback
            traceback.print_exc()
        
        print("🏁 Enhanced stream loop ended")
    
    def _add_exercise_overlay(self, frame):
        """Add comprehensive exercise feedback overlay to video frame"""
        if not self.tracking_enabled or not self.current_feedback:
            return frame
        
        try:
            feedback = self.current_feedback
            
            # Create semi-transparent background for better readability
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 160), (550, 350), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            y_offset = 180
            
            # Exercise name
            cv2.putText(frame, f"Exercise: {feedback.exercise_name[:40]}", (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y_offset += 25
            
            # Current phase
            cv2.putText(frame, f"Phase: {feedback.current_phase}", (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
            
            # Progress bar
            progress_width = int(300 * feedback.completion_percentage / 100)
            cv2.rectangle(frame, (15, y_offset), (315, y_offset + 12), (100, 100, 100), -1)
            if progress_width > 0:
                cv2.rectangle(frame, (15, y_offset), (15 + progress_width, y_offset + 12), (0, 255, 0), -1)
            cv2.putText(frame, f"{feedback.completion_percentage:.1f}%", (325, y_offset + 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 30
            
            # Form score with color coding
            score_color = (0, 255, 0) if feedback.form_score > 80 else (0, 255, 255) if feedback.form_score > 60 else (0, 100, 255)
            cv2.putText(frame, f"Form Score: {feedback.form_score:.1f}/100", (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2)
            y_offset += 30
            
            # Feedback messages (top 2)
            for i, msg in enumerate(feedback.feedback_messages[:2]):
                if len(msg) > 50:
                    msg = msg[:47] + "..."
                cv2.putText(frame, f"• {msg}", (15, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                y_offset += 18
            
            # Corrections (top 2)
            for i, correction in enumerate(feedback.corrections[:2]):
                if len(correction) > 50:
                    correction = correction[:47] + "..."
                cv2.putText(frame, f"⚠ {correction}", (15, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 150, 255), 1)
                y_offset += 18
            
            # Pose quality indicators (compact)
            if feedback.pose_quality:
                y_offset += 5
                quality_items = list(feedback.pose_quality.items())[:3]  # Show top 3
                for quality_name, quality_score in quality_items:
                    color = (0, 255, 0) if quality_score > 80 else (0, 255, 255) if quality_score > 60 else (0, 100, 255)
                    display_name = quality_name.replace("_", " ").title()[:12]
                    cv2.putText(frame, f"{display_name}: {quality_score:.0f}", (15, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
                    y_offset += 15
        
        except Exception as e:
            print(f"❌ Error adding exercise overlay: {e}")
        
        return frame
    
    def _save_real_time_feedback(self, feedback: ExerciseFeedback):
        """Save real-time feedback to JSON file for frontend consumption"""
        try:
            from dataclasses import asdict
            feedback_data = {
                "feedback": asdict(feedback),
                "session_stats": self.baduanjin_tracker.get_session_statistics() if self.baduanjin_tracker else {},
                "timestamp": datetime.now().isoformat(),
                "tracking_enabled": self.tracking_enabled,
                "streaming_info": {
                    "is_running": self.is_running,
                    "is_recording": self.is_recording,
                    "persons_detected": self.session_stats.get('persons_detected', 0),
                    "current_fps": self.session_stats.get('current_fps', 0)
                }
            }
            
            with open(self.real_time_data_file, 'w', encoding='utf-8') as f:
                json.dump(feedback_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"❌ Error saving real-time feedback: {e}")
    
    # API endpoint methods for frontend integration
    def get_exercise_list(self) -> Dict:
        """Get list of available Baduanjin exercises"""
        if not BADUANJIN_TRACKER_AVAILABLE or not self.baduanjin_tracker:
            return {"success": False, "error": "Exercise tracker not available"}
        
        exercises = []
        for ex_id, ex_data in self.baduanjin_tracker.exercises.items():
            exercises.append({
                "id": ex_id,
                "name": ex_data["name"],
                "description": ex_data["description"],
                "phases": list(ex_data["key_poses"].keys()),
                "common_mistakes": ex_data["common_mistakes"]
            })
        
        return {
            "success": True,
            "exercises": exercises,
            "total_exercises": len(exercises)
        }
    
    def get_real_time_feedback(self) -> Dict:
        """Get current real-time feedback data"""
        try:
            if self.real_time_data_file.exists():
                with open(self.real_time_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "feedback": None,
                    "session_stats": None,
                    "tracking_enabled": self.tracking_enabled,
                    "message": "No feedback data available"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tracking_enabled": self.tracking_enabled
            }
    
    def get_session_summary(self) -> Dict:
        """Get comprehensive session summary"""
        try:
            if not BADUANJIN_TRACKER_AVAILABLE or not self.baduanjin_tracker:
                return {"success": False, "error": "Exercise tracker not available"}
            
            summary = {
                "session_statistics": self.baduanjin_tracker.get_session_statistics(),
                "recent_feedback": self.feedback_buffer[-10:] if self.feedback_buffer else [],
                "tracking_enabled": self.tracking_enabled,
                "current_exercise": None,
                "video_session_stats": self.session_stats
            }
            
            if self.tracking_enabled and self.baduanjin_tracker.current_exercise:
                exercise_info = self.baduanjin_tracker.exercises[self.baduanjin_tracker.current_exercise]
                summary["current_exercise"] = {
                    "id": self.baduanjin_tracker.current_exercise,
                    "name": exercise_info["name"],
                    "phase": self.baduanjin_tracker.current_phase
                }
            
            return {"success": True, "summary": summary}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def export_session_data(self) -> Dict:
        """Export complete session data including exercise tracking"""
        try:
            if not BADUANJIN_TRACKER_AVAILABLE or not self.baduanjin_tracker:
                return {"success": False, "error": "Exercise tracker not available"}
            
            # Export Baduanjin tracking data
            tracking_file = self.baduanjin_tracker.export_session_data()
            
            # Create combined export
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_file = Path(f"baduanjin_complete_session_{timestamp}.json")
            
            combined_data = {
                "session_info": {
                    "start_time": self.baduanjin_tracker.session_start.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - self.baduanjin_tracker.session_start).total_seconds()
                },
                "video_session_stats": self.session_stats,
                "exercise_tracking_data": self.baduanjin_tracker.get_session_statistics(),
                "real_time_feedback_history": self.feedback_buffer,
                "tracking_file_path": tracking_file,
                "recordings_list": self.get_recordings_list(),
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "combined_export": str(combined_file),
                "tracking_export": tracking_file,
                "message": "Complete session data exported"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_recording(self):
        """Enhanced start recording with exercise tracking info"""
        # Call your existing start_recording method
        result = super().start_recording()
        
        # Add exercise tracking info if active
        if result["success"] and self.tracking_enabled and BADUANJIN_TRACKER_AVAILABLE:
            if self.baduanjin_tracker.current_exercise:
                exercise_info = self.baduanjin_tracker.exercises[self.baduanjin_tracker.current_exercise]
                result["exercise_tracking"] = {
                    "active": True,
                    "exercise_id": self.baduanjin_tracker.current_exercise,
                    "exercise_name": exercise_info["name"],
                    "current_phase": self.baduanjin_tracker.current_phase,
                    "form_score": self.current_feedback.form_score if self.current_feedback else None
                }
            else:
                result["exercise_tracking"] = {"active": False}
        
        return result
    
    def stop_recording(self):
        """Enhanced stop recording with exercise tracking data export"""
        # Call your existing stop_recording method
        result = super().stop_recording()
        
        # Add exercise tracking export if active
        if result["success"] and self.tracking_enabled and BADUANJIN_TRACKER_AVAILABLE:
            try:
                # Export exercise session data alongside video
                session_data = self.baduanjin_tracker.get_session_statistics()
                result["exercise_session_data"] = session_data
                
                # Save exercise data to accompany the video files
                if self.current_recording:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    exercise_data_file = self.recordings_dir / f"baduanjin_exercise_data_{timestamp}.json"
                    
                    exercise_export = {
                        "recording_files": result.get("recording_info", {}),
                        "exercise_session": session_data,
                        "feedback_history": self.feedback_buffer[-20:],  # Last 20 feedback entries
                        "export_timestamp": datetime.now().isoformat()
                    }
                    
                    with open(exercise_data_file, 'w', encoding='utf-8') as f:
                        json.dump(exercise_export, f, indent=2, ensure_ascii=False)
                    
                    result["exercise_data_file"] = str(exercise_data_file)
                    print(f"📊 Exercise data saved: {exercise_data_file}")
                
            except Exception as export_error:
                print(f"⚠️ Error exporting exercise data with recording: {export_error}")
                result["exercise_export_error"] = str(export_error)
        
        return result
    
    def stop_stream(self):
        """Enhanced stop stream with automatic exercise tracking cleanup"""
        # Auto-stop exercise tracking if enabled
        if self.tracking_enabled:
            try:
                self.disable_exercise_tracking()
                print("🎯 Auto-stopped exercise tracking when stream ended")
            except Exception as tracking_error:
                print(f"⚠️ Error auto-stopping tracking: {tracking_error}")
        
        # Call your existing stop_stream method
        return super().stop_stream()

# Factory function for creating enhanced analyzer
def create_enhanced_analyzer():
    """Create enhanced analyzer with Baduanjin tracking"""
    return EnhancedBaduanjinAnalyzer()

if __name__ == "__main__":
    # Example usage
    print("🚀 Testing Enhanced Baduanjin Analyzer...")
    
    analyzer = EnhancedBaduanjinAnalyzer()
    
    if analyzer.baduanjin_tracker:
        print("✅ Enhanced analyzer created with exercise tracking")
        
        # Test exercise listing
        exercises = analyzer.get_exercise_list()
        if exercises["success"]:
            print(f"📋 Available exercises: {exercises['total_exercises']}")
            for exercise in exercises["exercises"][:3]:  # Show first 3
                print(f"  {exercise['id']}. {exercise['name']}")
        
        print("🎯 Enhanced analyzer ready for integration!")
    else:
        print("⚠️ Enhanced analyzer created without exercise tracking")
        print("💡 Ensure baduanjin_tracker.py is available for full functionality")
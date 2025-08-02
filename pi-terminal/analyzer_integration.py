"""
analyzer_integration.py - Integration layer for Baduanjin tracking with existing analyzer
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Import your existing analyzer
from analyzer import BaduanjinWebAnalyzer

# Import the new tracker
from baduanjin_tracker import BaduanjinTracker, ExerciseFeedback

class EnhancedBaduanjinAnalyzer(BaduanjinWebAnalyzer):
    """Enhanced analyzer with real-time Baduanjin exercise tracking"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize Baduanjin tracker
        self.baduanjin_tracker = BaduanjinTracker(output_dir="baduanjin_data")
        
        # Real-time feedback state
        self.tracking_enabled = False
        self.current_feedback = None
        self.feedback_buffer = []
        
        # API endpoints for frontend
        self.real_time_data_file = Path("real_time_feedback.json")
        
        print("✅ Enhanced Baduanjin Analyzer initialized with exercise tracking")
    
    def enable_exercise_tracking(self, exercise_id: int) -> Dict:
        """Enable real-time exercise tracking for specific Baduanjin exercise"""
        try:
            result = self.baduanjin_tracker.start_exercise(exercise_id)
            if result["success"]:
                self.tracking_enabled = True
                print(f"🎯 Exercise tracking enabled: {result['exercise_name']}")
            return result
        except Exception as e:
            print(f"❌ Error enabling tracking: {e}")
            return {"success": False, "error": str(e)}
    
    def disable_exercise_tracking(self) -> Dict:
        """Disable exercise tracking and get summary"""
        try:
            if self.tracking_enabled:
                summary = self.baduanjin_tracker.end_exercise()
                self.tracking_enabled = False
                self.current_feedback = None
                print("🏁 Exercise tracking disabled")
                return summary
            else:
                return {"success": False, "message": "No active tracking"}
        except Exception as e:
            print(f"❌ Error disabling tracking: {e}")
            return {"success": False, "error": str(e)}
    
    def _stream_loop(self):
        """Enhanced stream loop with Baduanjin exercise tracking"""
        fps_counter = 0
        fps_start_time = time.time()
        frame_count = 0
        
        print("🎥 Enhanced stream loop started with exercise tracking!")
        
        try:
            while self.is_running:
                try:
                    frame_count += 1
                    
                    # Capture frame (from original analyzer)
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
                    import cv2
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Process pose (from original analyzer)
                    try:
                        pose_data = self.process_frame(frame_bgr)
                        self.pose_data = pose_data
                    except Exception as pose_error:
                        print(f"❌ Pose processing error: {pose_error}")
                        pose_data = []
                        self.pose_data = []
                    
                    # 🚀 NEW: Real-time exercise tracking
                    if self.tracking_enabled and pose_data:
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
                                
                                # Log significant feedback
                                if frame_count % 30 == 0:  # Every 30 frames
                                    print(f"🤖 Exercise feedback: {feedback.exercise_name} | "
                                          f"Phase: {feedback.current_phase} | "
                                          f"Score: {feedback.form_score:.1f} | "
                                          f"Progress: {feedback.completion_percentage:.1f}%")
                        
                        except Exception as tracking_error:
                            print(f"❌ Exercise tracking error: {tracking_error}")
                    
                    # Create annotated frame (from original analyzer)
                    annotated_frame = frame_bgr.copy()
                    try:
                        import numpy as np
                        for person_data in pose_data:
                            keypoints = np.array(person_data['keypoints'])
                            confidences = np.array(person_data['confidences'])
                            annotated_frame = self.draw_pose(annotated_frame, keypoints, confidences)
                    except Exception as draw_error:
                        print(f"❌ Draw pose error: {draw_error}")
                    
                    # 🚀 NEW: Add exercise feedback overlay
                    annotated_frame = self._add_exercise_overlay(annotated_frame)
                    
                    # Add text overlays (from original analyzer)
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
                            
                            # DUAL RECORDING: Save both versions
                            if self.video_writer_original and self.video_writer_original.isOpened():
                                self.video_writer_original.write(frame_bgr)  # Original (clean)
                            
                            if self.video_writer_annotated and self.video_writer_annotated.isOpened():
                                self.video_writer_annotated.write(annotated_frame)  # Annotated
                        
                        # 🚀 NEW: Exercise tracking indicator
                        if self.tracking_enabled:
                            cv2.putText(annotated_frame, '🎯 TRACKING', (10, 135), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                                    
                    except Exception as overlay_error:
                        print(f"❌ Overlay error: {overlay_error}")
                    
                    # Calculate FPS (from original analyzer)
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
        """Add exercise feedback overlay to video frame"""
        if not self.tracking_enabled or not self.current_feedback:
            return frame
        
        import cv2
        
        try:
            feedback = self.current_feedback
            
            # Background for feedback
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 160), (500, 320), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # Exercise info
            y_offset = 180
            cv2.putText(frame, f"Exercise: {feedback.exercise_name}", (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            y_offset += 25
            cv2.putText(frame, f"Phase: {feedback.current_phase}", (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            y_offset += 25
            # Progress bar
            progress_width = int(300 * feedback.completion_percentage / 100)
            cv2.rectangle(frame, (15, y_offset), (315, y_offset + 10), (100, 100, 100), -1)
            cv2.rectangle(frame, (15, y_offset), (15 + progress_width, y_offset + 10), (0, 255, 0), -1)
            cv2.putText(frame, f"{feedback.completion_percentage:.1f}%", (325, y_offset + 8), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            y_offset += 25
            # Form score
            score_color = (0, 255, 0) if feedback.form_score > 80 else (0, 255, 255) if feedback.form_score > 60 else (0, 0, 255)
            cv2.putText(frame, f"Form Score: {feedback.form_score:.1f}", (15, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2)
            
            # Feedback messages
            y_offset += 25
            for i, msg in enumerate(feedback.feedback_messages[:2]):  # Show top 2 messages
                cv2.putText(frame, f"• {msg}", (15, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                y_offset += 20
            
            # Corrections
            for i, correction in enumerate(feedback.corrections[:2]):  # Show top 2 corrections
                cv2.putText(frame, f"⚠ {correction}", (15, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 255), 1)
                y_offset += 20
        
        except Exception as e:
            print(f"❌ Error adding exercise overlay: {e}")
        
        return frame
    
    def _save_real_time_feedback(self, feedback: ExerciseFeedback):
        """Save real-time feedback to JSON file for frontend consumption"""
        try:
            from dataclasses import asdict
            feedback_data = {
                "feedback": asdict(feedback),
                "session_stats": self.baduanjin_tracker.get_session_statistics(),
                "timestamp": datetime.now().isoformat(),
                "tracking_enabled": self.tracking_enabled
            }
            
            with open(self.real_time_data_file, 'w', encoding='utf-8') as f:
                json.dump(feedback_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"❌ Error saving real-time feedback: {e}")
    
    # API endpoint methods for frontend integration
    def get_exercise_list(self) -> Dict:
        """Get list of available Baduanjin exercises"""
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
            summary = {
                "session_statistics": self.baduanjin_tracker.get_session_statistics(),
                "recent_feedback": self.feedback_buffer[-10:] if self.feedback_buffer else [],
                "tracking_enabled": self.tracking_enabled,
                "current_exercise": None
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
        
    def stop_recording(self):
        """Enhanced stop recording with automatic exercise data export"""
        # Call your existing stop_recording method
        result = super().stop_recording()
        
        # 🚀 NEW: Auto-export exercise data when recording stops
        if result["success"] and self.tracking_enabled and BADUANJIN_TRACKER_AVAILABLE:
            try:
                # Export exercise session data alongside video
                session_data = self.baduanjin_tracker.get_session_statistics()
                result["exercise_session_data"] = session_data
                
                # Save exercise data to baduanjin_data folder
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                exercise_data_file = Config.BADUANJIN_DATA_DIR / f"recording_session_{timestamp}.json"
                
                exercise_export = {
                    "recording_info": result.get("recording_info", {}),
                    "exercise_session": session_data,
                    "feedback_history": self.feedback_buffer[-50:] if self.feedback_buffer else [],
                    "export_timestamp": datetime.now().isoformat(),
                    "recording_files": result.get("recording_info", {}).get("files", {}),
                    "auto_exported_on_recording_stop": True
                }
                
                with open(exercise_data_file, 'w', encoding='utf-8') as f:
                    json.dump(exercise_export, f, indent=2, ensure_ascii=False)
                
                result["exercise_data_file"] = str(exercise_data_file)
                print(f"📊 Exercise data auto-saved to baduanjin_data: {exercise_data_file}")
                
            except Exception as export_error:
                print(f"⚠️ Error auto-exporting exercise data: {export_error}")
                result["exercise_export_error"] = str(export_error)
        
        return result

# Factory function for creating enhanced analyzer
def create_enhanced_analyzer():
    """Create enhanced analyzer with Baduanjin tracking"""
    return EnhancedBaduanjinAnalyzer()

if __name__ == "__main__":
    # Example usage
    analyzer = EnhancedBaduanjinAnalyzer()
    
    # Start streaming
    if analyzer.start_stream():
        print("✅ Stream started")
        
        # Enable exercise tracking
        result = analyzer.enable_exercise_tracking(1)  # Holding up the Sky
        if result["success"]:
            print(f"✅ Tracking enabled for: {result['exercise_name']}")
            
            # Simulate running for a while
            time.sleep(5)
            
            # Get real-time feedback
            feedback_data = analyzer.get_real_time_feedback()
            print("Feedback data:", json.dumps(feedback_data, indent=2))
            
            # Disable tracking
            summary = analyzer.disable_exercise_tracking()
            print("Exercise summary:", summary)
        
        # Export session data
        export_result = analyzer.export_session_data()
        print("Export result:", export_result)
        
        # Stop streaming
        analyzer.stop_stream()
        print("✅ Stream stopped")


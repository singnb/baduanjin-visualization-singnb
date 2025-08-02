"""
baduanjin_tracker.py - Real-time Baduanjin Exercise Tracking and Feedback
"""

import numpy as np
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class PoseKeypoints:
    """Standard YOLO pose keypoints structure"""
    nose: Tuple[float, float] = (0, 0)           # 0
    left_eye: Tuple[float, float] = (0, 0)       # 1
    right_eye: Tuple[float, float] = (0, 0)      # 2
    left_ear: Tuple[float, float] = (0, 0)       # 3
    right_ear: Tuple[float, float] = (0, 0)      # 4
    left_shoulder: Tuple[float, float] = (0, 0)  # 5
    right_shoulder: Tuple[float, float] = (0, 0) # 6
    left_elbow: Tuple[float, float] = (0, 0)     # 7
    right_elbow: Tuple[float, float] = (0, 0)    # 8
    left_wrist: Tuple[float, float] = (0, 0)     # 9
    right_wrist: Tuple[float, float] = (0, 0)    # 10
    left_hip: Tuple[float, float] = (0, 0)       # 11
    right_hip: Tuple[float, float] = (0, 0)      # 12
    left_knee: Tuple[float, float] = (0, 0)      # 13
    right_knee: Tuple[float, float] = (0, 0)     # 14
    left_ankle: Tuple[float, float] = (0, 0)     # 15
    right_ankle: Tuple[float, float] = (0, 0)    # 16

@dataclass
class ExerciseFeedback:
    """Real-time exercise feedback structure"""
    exercise_id: int
    exercise_name: str
    current_phase: str
    completion_percentage: float
    form_score: float  # 0-100
    feedback_messages: List[str]
    corrections: List[str]
    pose_quality: Dict[str, float]
    timestamp: str

@dataclass
class SessionStats:
    """Session-level statistics"""
    total_exercises_attempted: int
    exercises_completed: int
    average_form_score: float
    session_duration: float
    movement_consistency: float
    recommendations: List[str]

class BaduanjinTracker:
    """Real-time Baduanjin exercise tracker with pose analysis"""
    
    def __init__(self, output_dir: str = "baduanjin_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Exercise definitions
        self.exercises = self._define_baduanjin_exercises()
        
        # Tracking state
        self.current_exercise = None
        self.current_phase = "ready"
        self.exercise_start_time = None
        self.pose_history = []
        self.feedback_history = []
        self.session_start = datetime.now()
        
        # Analysis parameters
        self.confidence_threshold = 0.5
        self.pose_hold_duration = 2.0  # seconds to hold pose
        self.transition_tolerance = 0.3
        
        # Session statistics
        self.session_stats = {
            "exercises_attempted": 0,
            "exercises_completed": 0,
            "total_form_scores": [],
            "movement_quality_scores": [],
            "common_mistakes": {},
            "session_start": self.session_start.isoformat()
        }
        
        print("✅ Baduanjin Tracker initialized")
    
    def _define_baduanjin_exercises(self) -> Dict[int, Dict]:
        """Define the 8 Baduanjin exercises with key poses and analysis criteria"""
        return {
            1: {
                "name": "Holding up the Sky (两手托天理三焦)",
                "description": "Raise both hands above head, palms up",
                "key_poses": {
                    "start": {
                        "arms_position": "down",
                        "shoulder_alignment": "level",
                        "spine": "straight"
                    },
                    "lift": {
                        "arms_position": "rising",
                        "wrist_alignment": "parallel",
                        "breathing": "inhale"
                    },
                    "hold": {
                        "arms_position": "overhead",
                        "palms": "up",
                        "shoulders": "relaxed",
                        "duration": 3.0
                    },
                    "lower": {
                        "arms_position": "lowering",
                        "control": "smooth",
                        "breathing": "exhale"
                    }
                },
                "common_mistakes": [
                    "shoulders_raised",
                    "arms_not_straight",
                    "uneven_arm_height",
                    "rushing_movement"
                ]
            },
            
            2: {
                "name": "Drawing the Bow (左右开弓似射雕)",
                "description": "Simulate drawing a bow alternating left and right",
                "key_poses": {
                    "start": {
                        "arms_position": "crossed_chest",
                        "feet": "shoulder_width"
                    },
                    "draw_left": {
                        "left_arm": "extended",
                        "right_arm": "pulled_back",
                        "torso": "stable",
                        "eyes": "following_arrow"
                    },
                    "draw_right": {
                        "right_arm": "extended", 
                        "left_arm": "pulled_back",
                        "symmetry": "maintained"
                    }
                },
                "common_mistakes": [
                    "arms_not_level",
                    "torso_rotation",
                    "feet_position_wrong",
                    "lack_of_focus"
                ]
            },
            
            3: {
                "name": "Single Arm Raise (调理脾胃单举手)",
                "description": "Alternately raise single arms overhead",
                "key_poses": {
                    "start": {
                        "arms": "at_sides",
                        "posture": "upright"
                    },
                    "left_raise": {
                        "left_arm": "overhead",
                        "right_arm": "down_pressed",
                        "balance": "maintained"
                    },
                    "right_raise": {
                        "right_arm": "overhead",
                        "left_arm": "down_pressed",
                        "coordination": "smooth"
                    }
                },
                "common_mistakes": [
                    "both_arms_moving",
                    "leaning_sideways",
                    "arm_not_straight",
                    "rushing_transitions"
                ]
            },
            
            4: {
                "name": "Look Back (五劳七伤往后瞧)",
                "description": "Turn head left and right while keeping body stable",
                "key_poses": {
                    "start": {
                        "head": "forward",
                        "neck": "straight",
                        "shoulders": "relaxed"
                    },
                    "look_left": {
                        "head": "turned_left",
                        "eyes": "far_gaze",
                        "shoulders": "stable"
                    },
                    "look_right": {
                        "head": "turned_right",
                        "neck_rotation": "controlled",
                        "body": "stationary"
                    }
                },
                "common_mistakes": [
                    "shoulder_movement",
                    "excessive_rotation",
                    "neck_strain",
                    "losing_balance"
                ]
            },
            
            5: {
                "name": "Sway Head and Tail (摇头摆尾去心火)",
                "description": "Swaying movements to release tension",
                "key_poses": {
                    "start": {
                        "stance": "wide",
                        "hands": "on_thighs"
                    },
                    "sway_left": {
                        "torso": "leaning_left",
                        "head": "tilted",
                        "flow": "continuous"
                    },
                    "sway_right": {
                        "torso": "leaning_right",
                        "movement": "fluid",
                        "breathing": "natural"
                    }
                },
                "common_mistakes": [
                    "stiff_movement",
                    "feet_lifting",
                    "excessive_force",
                    "irregular_rhythm"
                ]
            },
            
            6: {
                "name": "Reach Down (两手攀足固肾腰)",
                "description": "Bend forward and reach toward feet",
                "key_poses": {
                    "start": {
                        "posture": "upright",
                        "arms": "at_sides"
                    },
                    "forward_bend": {
                        "spine": "curved",
                        "hands": "reaching_down",
                        "knees": "slightly_bent"
                    },
                    "touch_feet": {
                        "hands": "near_feet",
                        "flexibility": "within_limits",
                        "breathing": "controlled"
                    },
                    "return": {
                        "rising": "slowly",
                        "spine": "vertebra_by_vertebra"
                    }
                },
                "common_mistakes": [
                    "forcing_stretch",
                    "knees_locked",
                    "holding_breath",
                    "rising_too_fast"
                ]
            },
            
            7: {
                "name": "Clench Fists (攒拳怒目增气力)",
                "description": "Punch forward with focused intent",
                "key_poses": {
                    "start": {
                        "stance": "horse_stance",
                        "fists": "at_waist"
                    },
                    "punch_left": {
                        "left_fist": "extended",
                        "right_fist": "at_waist",
                        "power": "controlled",
                        "eyes": "focused"
                    },
                    "punch_right": {
                        "right_fist": "extended",
                        "rotation": "proper",
                        "stance": "stable"
                    }
                },
                "common_mistakes": [
                    "weak_stance",
                    "no_fist_rotation",
                    "upper_body_lean",
                    "lack_of_focus"
                ]
            },
            
            8: {
                "name": "Heel Raises (背后七颠百病消)",
                "description": "Rise on toes and gently drop on heels",
                "key_poses": {
                    "start": {
                        "feet": "parallel",
                        "weight": "evenly_distributed"
                    },
                    "toe_raise": {
                        "heels": "lifted",
                        "balance": "maintained",
                        "body": "straight"
                    },
                    "heel_drop": {
                        "landing": "gentle",
                        "vibration": "through_spine",
                        "control": "maintained"
                    }
                },
                "common_mistakes": [
                    "hard_landing",
                    "losing_balance",
                    "feet_apart",
                    "excessive_height"
                ]
            }
        }
    
    def extract_pose_keypoints(self, yolo_keypoints: List[List[float]], 
                             confidences: List[float]) -> Optional[PoseKeypoints]:
        """Convert YOLO keypoints to structured format"""
        if len(yolo_keypoints) < 17 or len(confidences) < 17:
            return None
        
        # Check if enough keypoints have good confidence
        good_keypoints = sum(1 for conf in confidences if conf > self.confidence_threshold)
        if good_keypoints < 8:  # Need at least 8 good keypoints
            return None
        
        try:
            return PoseKeypoints(
                nose=(yolo_keypoints[0][0], yolo_keypoints[0][1]),
                left_eye=(yolo_keypoints[1][0], yolo_keypoints[1][1]),
                right_eye=(yolo_keypoints[2][0], yolo_keypoints[2][1]),
                left_ear=(yolo_keypoints[3][0], yolo_keypoints[3][1]),
                right_ear=(yolo_keypoints[4][0], yolo_keypoints[4][1]),
                left_shoulder=(yolo_keypoints[5][0], yolo_keypoints[5][1]),
                right_shoulder=(yolo_keypoints[6][0], yolo_keypoints[6][1]),
                left_elbow=(yolo_keypoints[7][0], yolo_keypoints[7][1]),
                right_elbow=(yolo_keypoints[8][0], yolo_keypoints[8][1]),
                left_wrist=(yolo_keypoints[9][0], yolo_keypoints[9][1]),
                right_wrist=(yolo_keypoints[10][0], yolo_keypoints[10][1]),
                left_hip=(yolo_keypoints[11][0], yolo_keypoints[11][1]),
                right_hip=(yolo_keypoints[12][0], yolo_keypoints[12][1]),
                left_knee=(yolo_keypoints[13][0], yolo_keypoints[13][1]),
                right_knee=(yolo_keypoints[14][0], yolo_keypoints[14][1]),
                left_ankle=(yolo_keypoints[15][0], yolo_keypoints[15][1]),
                right_ankle=(yolo_keypoints[16][0], yolo_keypoints[16][1])
            )
        except Exception as e:
            print(f"❌ Error extracting keypoints: {e}")
            return None
    
    def analyze_pose_for_exercise(self, pose: PoseKeypoints, exercise_id: int, 
                                phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze pose quality for specific Baduanjin exercise"""
        if exercise_id not in self.exercises:
            return 0.0, [], ["Unknown exercise"]
        
        exercise = self.exercises[exercise_id]
        feedback_messages = []
        corrections = []
        
        # Exercise-specific analysis
        if exercise_id == 1:  # Holding up the Sky
            score, msgs, corr = self._analyze_holding_sky(pose, phase)
        elif exercise_id == 2:  # Drawing the Bow
            score, msgs, corr = self._analyze_drawing_bow(pose, phase)
        elif exercise_id == 3:  # Single Arm Raise
            score, msgs, corr = self._analyze_single_arm_raise(pose, phase)
        elif exercise_id == 4:  # Look Back
            score, msgs, corr = self._analyze_look_back(pose, phase)
        elif exercise_id == 5:  # Sway Head and Tail
            score, msgs, corr = self._analyze_sway_movement(pose, phase)
        elif exercise_id == 6:  # Reach Down
            score, msgs, corr = self._analyze_reach_down(pose, phase)
        elif exercise_id == 7:  # Clench Fists
            score, msgs, corr = self._analyze_clench_fists(pose, phase)
        elif exercise_id == 8:  # Heel Raises
            score, msgs, corr = self._analyze_heel_raises(pose, phase)
        else:
            return 50.0, ["Exercise not implemented"], []
        
        return score, msgs, corr
    
    def _analyze_holding_sky(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Holding up the Sky' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        # Check arm elevation
        left_arm_height = pose.left_shoulder[1] - pose.left_wrist[1]
        right_arm_height = pose.right_shoulder[1] - pose.right_wrist[1]
        
        if phase == "hold":
            # Arms should be overhead
            if left_arm_height < 100 or right_arm_height < 100:
                score -= 20
                corrections.append("Raise arms higher overhead")
            
            # Check arm symmetry
            height_diff = abs(left_arm_height - right_arm_height)
            if height_diff > 50:
                score -= 15
                corrections.append("Keep arms at equal height")
            
            # Check shoulder alignment
            shoulder_diff = abs(pose.left_shoulder[1] - pose.right_shoulder[1])
            if shoulder_diff > 20:
                score -= 10
                corrections.append("Keep shoulders level")
            
            messages.append("Hold this position with palms facing up")
        
        elif phase == "lift" or phase == "lower":
            messages.append(f"Smooth {phase} movement - breathe naturally")
        
        return max(score, 0), messages, corrections
    
    def _analyze_drawing_bow(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Drawing the Bow' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        if "draw" in phase:
            # Check arm extension
            if "left" in phase:
                # Left arm should be extended, right arm pulled back
                left_extension = abs(pose.left_wrist[0] - pose.left_shoulder[0])
                if left_extension < 80:
                    score -= 20
                    corrections.append("Extend left arm further")
                messages.append("Draw the bow with your left arm")
            
            elif "right" in phase:
                right_extension = abs(pose.right_wrist[0] - pose.right_shoulder[0])
                if right_extension < 80:
                    score -= 20
                    corrections.append("Extend right arm further")
                messages.append("Draw the bow with your right arm")
            
            # Check torso stability
            hip_center = (pose.left_hip[0] + pose.right_hip[0]) / 2
            shoulder_center = (pose.left_shoulder[0] + pose.right_shoulder[0]) / 2
            if abs(hip_center - shoulder_center) > 30:
                score -= 15
                corrections.append("Keep torso straight and stable")
        
        return max(score, 0), messages, corrections
    
    def _analyze_single_arm_raise(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Single Arm Raise' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        if "raise" in phase:
            if "left" in phase:
                # Left arm up, right arm down
                left_height = pose.left_shoulder[1] - pose.left_wrist[1]
                right_height = pose.right_shoulder[1] - pose.right_wrist[1]
                
                if left_height < 100:
                    score -= 25
                    corrections.append("Raise left arm higher")
                if right_height > -20:  # Right arm should be down
                    score -= 20
                    corrections.append("Press right arm down firmly")
                
                messages.append("Left arm up, right arm pressed down")
            
            elif "right" in phase:
                # Similar logic for right arm
                right_height = pose.right_shoulder[1] - pose.right_wrist[1]
                left_height = pose.left_shoulder[1] - pose.left_wrist[1]
                
                if right_height < 100:
                    score -= 25
                    corrections.append("Raise right arm higher")
                if left_height > -20:
                    score -= 20
                    corrections.append("Press left arm down firmly")
                
                messages.append("Right arm up, left arm pressed down")
        
        return max(score, 0), messages, corrections
    
    def _analyze_look_back(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Look Back' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        # Check shoulder stability
        shoulder_diff = abs(pose.left_shoulder[1] - pose.right_shoulder[1])
        if shoulder_diff > 15:
            score -= 20
            corrections.append("Keep shoulders level while turning head")
        
        if "look" in phase:
            direction = "left" if "left" in phase else "right"
            messages.append(f"Look far to the {direction}, keep shoulders still")
        
        return max(score, 0), messages, corrections
    
    def _analyze_sway_movement(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Sway Head and Tail' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        if "sway" in phase:
            messages.append("Move fluidly like water, release tension")
            # Check for stiffness by comparing recent poses
            if len(self.pose_history) > 5:
                # Simple stiffness check - if positions haven't changed much
                recent_poses = self.pose_history[-5:]
                position_variance = self._calculate_position_variance(recent_poses)
                if position_variance < 10:
                    score -= 15
                    corrections.append("Move more fluidly, avoid stiffness")
        
        return max(score, 0), messages, corrections
    
    def _analyze_reach_down(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Reach Down' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        if phase == "forward_bend":
            # Check forward bend depth
            hip_to_wrist = pose.left_hip[1] - pose.left_wrist[1]
            if hip_to_wrist < 50:
                messages.append("Bend only to your comfortable limit")
            else:
                score -= 10
                corrections.append("Don't force the stretch")
            
            messages.append("Reach down gently, keep knees soft")
        
        elif phase == "return":
            messages.append("Rise slowly, vertebra by vertebra")
        
        return max(score, 0), messages, corrections
    
    def _analyze_clench_fists(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Clench Fists' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        if "punch" in phase:
            # Check stance stability
            hip_width = abs(pose.left_hip[0] - pose.right_hip[0])
            if hip_width < 60:
                score -= 20
                corrections.append("Widen your stance for better stability")
            
            direction = "left" if "left" in phase else "right"
            messages.append(f"Punch {direction} with power and focus")
        
        return max(score, 0), messages, corrections
    
    def _analyze_heel_raises(self, pose: PoseKeypoints, phase: str) -> Tuple[float, List[str], List[str]]:
        """Analyze 'Heel Raises' exercise"""
        score = 100.0
        messages = []
        corrections = []
        
        if phase == "toe_raise":
            # Check balance by foot position
            foot_distance = abs(pose.left_ankle[0] - pose.right_ankle[0])
            if foot_distance > 100:
                score -= 15
                corrections.append("Keep feet closer together")
            
            messages.append("Rise gently on toes, maintain balance")
        
        elif phase == "heel_drop":
            messages.append("Drop gently, feel the vibration through spine")
        
        return max(score, 0), messages, corrections
    
    def _calculate_position_variance(self, poses: List[Dict]) -> float:
        """Calculate variance in poses for fluidity analysis"""
        if len(poses) < 2:
            return 0
        
        # Simple variance calculation based on key joint positions
        variances = []
        for i in range(len(poses)-1):
            pose1 = poses[i]
            pose2 = poses[i+1]
            
            # Calculate movement between frames
            movement = 0
            for joint in ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']:
                if joint in pose1 and joint in pose2:
                    dx = pose1[joint][0] - pose2[joint][0]
                    dy = pose1[joint][1] - pose2[joint][1]
                    movement += (dx*dx + dy*dy)**0.5
            
            variances.append(movement)
        
        return sum(variances) / len(variances) if variances else 0
    
    def start_exercise(self, exercise_id: int) -> Dict:
        """Start tracking a specific Baduanjin exercise"""
        if exercise_id not in self.exercises:
            return {"success": False, "error": "Invalid exercise ID"}
        
        self.current_exercise = exercise_id
        self.current_phase = "start"
        self.exercise_start_time = time.time()
        self.pose_history = []
        
        self.session_stats["exercises_attempted"] += 1
        
        exercise_info = self.exercises[exercise_id]
        
        print(f"🎯 Starting Exercise {exercise_id}: {exercise_info['name']}")
        
        return {
            "success": True,
            "exercise_id": exercise_id,
            "exercise_name": exercise_info["name"],
            "description": exercise_info["description"],
            "phases": list(exercise_info["key_poses"].keys()),
            "common_mistakes": exercise_info["common_mistakes"]
        }
    
    def process_real_time_pose(self, yolo_pose_data: List[Dict]) -> Optional[ExerciseFeedback]:
        """Process real-time pose data and provide feedback"""
        if not self.current_exercise or not yolo_pose_data:
            return None
        
        # Use first person detected
        person_data = yolo_pose_data[0]
        pose = self.extract_pose_keypoints(
            person_data['keypoints'], 
            person_data['confidences']
        )
        
        if not pose:
            return ExerciseFeedback(
                exercise_id=self.current_exercise,
                exercise_name=self.exercises[self.current_exercise]["name"],
                current_phase=self.current_phase,
                completion_percentage=0.0,
                form_score=0.0,
                feedback_messages=["Pose not clearly detected"],
                corrections=["Position yourself in clear view of camera"],
                pose_quality={},
                timestamp=datetime.now().isoformat()
            )
        
        # Analyze pose for current exercise and phase
        form_score, feedback_msgs, corrections = self.analyze_pose_for_exercise(
            pose, self.current_exercise, self.current_phase
        )
        
        # Update phase progression (simplified state machine)
        completion_percentage = self._calculate_completion_percentage()
        
        # Store pose history for analysis
        pose_dict = asdict(pose)
        pose_dict['timestamp'] = time.time()
        pose_dict['phase'] = self.current_phase
        self.pose_history.append(pose_dict)
        
        # Keep history manageable
        if len(self.pose_history) > 100:
            self.pose_history = self.pose_history[-50:]
        
        # Calculate pose quality metrics
        pose_quality = self._calculate_pose_quality_metrics(pose)
        
        # Create feedback object
        feedback = ExerciseFeedback(
            exercise_id=self.current_exercise,
            exercise_name=self.exercises[self.current_exercise]["name"],
            current_phase=self.current_phase,
            completion_percentage=completion_percentage,
            form_score=form_score,
            feedback_messages=feedback_msgs,
            corrections=corrections,
            pose_quality=pose_quality,
            timestamp=datetime.now().isoformat()
        )
        
        # Store in feedback history
        self.feedback_history.append(asdict(feedback))
        
        # Update session stats
        self.session_stats["total_form_scores"].append(form_score)
        
        return feedback
    
    def _calculate_completion_percentage(self) -> float:
        """Calculate exercise completion percentage"""
        if not self.exercise_start_time:
            return 0.0
        
        elapsed = time.time() - self.exercise_start_time
        # Each exercise phase roughly 3-5 seconds, total ~20 seconds
        return min(100.0, (elapsed / 20.0) * 100)
    
    def _calculate_pose_quality_metrics(self, pose: PoseKeypoints) -> Dict[str, float]:
        """Calculate detailed pose quality metrics"""
        metrics = {}
        
        # Shoulder alignment
        shoulder_diff = abs(pose.left_shoulder[1] - pose.right_shoulder[1])
        metrics["shoulder_alignment"] = max(0, 100 - shoulder_diff * 2)
        
        # Hip alignment
        hip_diff = abs(pose.left_hip[1] - pose.right_hip[1])
        metrics["hip_alignment"] = max(0, 100 - hip_diff * 2)
        
        # Spine straightness (shoulder-hip alignment)
        left_spine = abs(pose.left_shoulder[0] - pose.left_hip[0])
        right_spine = abs(pose.right_shoulder[0] - pose.right_hip[0])
        spine_alignment = abs(left_spine - right_spine)
        metrics["spine_alignment"] = max(0, 100 - spine_alignment)
        
        # Overall stability (how centered the pose is)
        center_x = (pose.left_shoulder[0] + pose.right_shoulder[0]) / 2
        hip_center_x = (pose.left_hip[0] + pose.right_hip[0]) / 2
        stability = abs(center_x - hip_center_x)
        metrics["stability"] = max(0, 100 - stability * 2)
        
        return metrics
    
    def end_exercise(self) -> Dict:
        """End current exercise and return session summary"""
        if not self.current_exercise:
            return {"success": False, "error": "No active exercise"}
        
        exercise_id = self.current_exercise
        exercise_name = self.exercises[exercise_id]["name"]
        
        # Calculate final scores
        if self.feedback_history:
            avg_form_score = sum(f["form_score"] for f in self.feedback_history[-10:]) / min(10, len(self.feedback_history))
            self.session_stats["exercises_completed"] += 1
        else:
            avg_form_score = 0
        
        # Generate exercise summary
        summary = {
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "final_form_score": round(avg_form_score, 1),
            "duration": time.time() - self.exercise_start_time if self.exercise_start_time else 0,
            "total_feedback_points": len(self.feedback_history),
            "completion_status": "completed" if avg_form_score > 70 else "needs_improvement"
        }
        
        # Reset tracking state
        self.current_exercise = None
        self.current_phase = "ready"
        self.exercise_start_time = None
        
        print(f"✅ Exercise completed: {exercise_name} (Score: {avg_form_score:.1f})")
        
        return {"success": True, "summary": summary}
    
    def get_session_statistics(self) -> Dict:
        """Get comprehensive session statistics"""
        current_time = datetime.now()
        session_duration = (current_time - self.session_start).total_seconds()
        
        avg_form_score = 0
        if self.session_stats["total_form_scores"]:
            avg_form_score = sum(self.session_stats["total_form_scores"]) / len(self.session_stats["total_form_scores"])
        
        stats = SessionStats(
            total_exercises_attempted=self.session_stats["exercises_attempted"],
            exercises_completed=self.session_stats["exercises_completed"],
            average_form_score=round(avg_form_score, 1),
            session_duration=round(session_duration, 1),
            movement_consistency=self._calculate_movement_consistency(),
            recommendations=self._generate_recommendations()
        )
        
        return asdict(stats)
    
    def _calculate_movement_consistency(self) -> float:
        """Calculate movement consistency score"""
        if len(self.session_stats["total_form_scores"]) < 5:
            return 0.0
        
        scores = self.session_stats["total_form_scores"]
        variance = sum((score - sum(scores)/len(scores))**2 for score in scores) / len(scores)
        consistency = max(0, 100 - variance)  # Lower variance = higher consistency
        
        return round(consistency, 1)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if self.session_stats["total_form_scores"]:
            avg_score = sum(self.session_stats["total_form_scores"]) / len(self.session_stats["total_form_scores"])
            
            if avg_score < 60:
                recommendations.append("Focus on basic posture and alignment")
                recommendations.append("Practice slower movements for better control")
            elif avg_score < 80:
                recommendations.append("Work on consistency between repetitions")
                recommendations.append("Pay attention to breathing coordination")
            else:
                recommendations.append("Excellent form! Try increasing hold duration")
                recommendations.append("Focus on the mind-body connection")
        
        if self.session_stats["exercises_attempted"] < 3:
            recommendations.append("Try completing more exercises for a full session")
        
        return recommendations
    
    def export_session_data(self, filename: Optional[str] = None) -> str:
        """Export session data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"baduanjin_session_{timestamp}.json"
        
        export_data = {
            "session_info": {
                "start_time": self.session_start.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": (datetime.now() - self.session_start).total_seconds()
            },
            "session_statistics": self.get_session_statistics(),
            "exercise_history": self.feedback_history,
            "pose_history": self.pose_history[-50:],  # Last 50 poses
            "export_timestamp": datetime.now().isoformat()
        }
        
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Session data exported to: {output_path}")
        return str(output_path)

# Integration helper function for analyzer.py
def create_baduanjin_tracker():
    """Factory function to create tracker instance"""
    return BaduanjinTracker()

if __name__ == "__main__":
    # Example usage
    tracker = BaduanjinTracker()
    
    # Simulate starting an exercise
    result = tracker.start_exercise(1)  # Holding up the Sky
    print("Start result:", result)
    
    # Simulate pose data (replace with real YOLO data)
    sample_pose_data = [{
        'keypoints': [[320, 240], [315, 225], [325, 225], [310, 220], [330, 220],
                     [300, 280], [340, 280], [280, 320], [360, 320], [260, 360], 
                     [380, 360], [300, 400], [340, 400], [295, 480], [345, 480],
                     [290, 560], [350, 560]],
        'confidences': [0.9] * 17,
        'person_id': 0
    }]
    
    # Process real-time feedback
    feedback = tracker.process_real_time_pose(sample_pose_data)
    if feedback:
        print("Feedback:", asdict(feedback))
    
    # End exercise
    summary = tracker.end_exercise()
    print("Summary:", summary)
    
    # Export session data
    export_path = tracker.export_session_data()
    print(f"Data exported to: {export_path}")
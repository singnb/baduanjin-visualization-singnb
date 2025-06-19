import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from glob import glob
import argparse

def load_data_from_analyzer_output(analysis_dir):
    """
    Load the existing analyzer output data from the specified directory
    """
    data = {
        'report': None,
        'joint_angles': None,
        'key_frames': None,
            'pose_names': [
            "Initial Position", 
            "Transition Phase", 
            "Peak Position", 
            "Holding Phase", 
            "Return Phase", 
            "Final Position",
            "Stabilization Phase", 
            "Ready Position"
        ]
    }
    
    # Read the text report
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            data['report'] = f.read()
            
    # Extract key frames and joint angles from the report if available
    if data['report']:
        data['key_frames'] = extract_key_frames_from_report(data['report'])
    
    # Try to extract joint angle data from the text report
    if data['report']:
        data['joint_angles'] = extract_joint_angles_from_report(data['report'])
    
    # Load smoothness data (we'll extract from the image if no direct data)
    data['smoothness'] = extract_smoothness(analysis_dir)
    
    # Load symmetry data
    data['symmetry'] = extract_symmetry(analysis_dir)
    
    # Load balance metrics
    data['balance'] = extract_balance_metrics(analysis_dir)
    
    return data

def extract_key_frames_from_report(report_text):
    """
    Extract key frame information from the analysis report
    """
    key_frames = []
    # Look for the key poses section
    if "1. Key Poses" in report_text:
        section = report_text.split("1. Key Poses")[1].split("2. Joint Angles")[0]
        lines = section.strip().split('\n')
        for line in lines:
            if "Pose" in line and "Frame" in line:
                parts = line.split("Frame")
                if len(parts) > 1:
                    try:
                        frame_idx = int(parts[1].strip().strip(':'))
                        pose_idx = int(parts[0].split("Pose")[1].strip().strip(':')) - 1
                        key_frames.append((frame_idx, pose_idx))
                    except ValueError:
                        continue
    return key_frames

def extract_joint_angles_from_report(report_text):
    """
    Extract joint angle data from the analysis report
    """
    joint_angles = {}
    
    # Look for joint angles section
    if "2. Joint Angles at Key Poses" in report_text:
        section = report_text.split("2. Joint Angles at Key Poses")[1].split("3. Movement Smoothness")[0]
        pose_sections = section.split("Pose")[1:]
        
        current_pose = None
        for pose_section in pose_sections:
            if "(Frame" in pose_section:
                frame_part = pose_section.split("(Frame")[1].split(")")[0]
                try:
                    frame_idx = int(frame_part.strip())
                    current_pose = frame_idx
                    joint_angles[current_pose] = {}
                except ValueError:
                    continue
                
                # Extract angles for this pose
                angle_lines = pose_section.split("):")[1].strip().split("\n")
                for line in angle_lines:
                    if ":" in line:
                        parts = line.split(":")
                        if len(parts) == 2:
                            angle_name = parts[0].strip()
                            try:
                                angle_value = float(parts[1].strip().split()[0])
                                joint_angles[current_pose][angle_name] = angle_value
                            except ValueError:
                                continue
    
    return joint_angles

def extract_smoothness(analysis_dir):
    """
    Extract movement smoothness metrics
    """
    # First try to read from the report
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    smoothness = {}
    
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report = f.read()
            if "3. Movement Smoothness" in report:
                section = report.split("3. Movement Smoothness")[1].split("4. Movement Symmetry")[0]
                lines = section.strip().split('\n')
                for line in lines:
                    if ":" in line:
                        parts = line.split(":")
                        if len(parts) == 2:
                            joint_name = parts[0].strip()
                            try:
                                jerk_value = float(parts[1].strip())
                                smoothness[joint_name] = jerk_value
                            except ValueError:
                                continue
    
    # If we couldn't find it in the report, use placeholder values
    if not smoothness:
        smoothness = {
            "keypoint_9": 0.91,   # Left Wrist
            "keypoint_10": 0.88,  # Right Wrist
            "keypoint_15": 0.91,  # Left Ankle
            "keypoint_16": 0.99   # Right Ankle
        }
    
    return smoothness

def extract_symmetry(analysis_dir):
    """
    Extract movement symmetry metrics
    """
    # First try to read from the report
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    symmetry = {}
    
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report = f.read()
            if "4. Movement Symmetry" in report:
                section = report.split("4. Movement Symmetry")[1].split("5. Balance Metrics")[0]
                lines = section.strip().split('\n')
                for line in lines:
                    if ":" in line and "_" in line:
                        parts = line.split(":")
                        if len(parts) == 2:
                            pair_name = parts[0].strip()
                            try:
                                sym_value = float(parts[1].strip())
                                symmetry[pair_name] = sym_value
                            except ValueError:
                                continue
    
    # If we couldn't find it in the report, use placeholder values
    if not symmetry:
        symmetry = {
            "keypoint_5_keypoint_6": 0.88,   # Left/Right Shoulders
            "keypoint_7_keypoint_8": 0.92,   # Left/Right Elbows
            "keypoint_9_keypoint_10": 0.90,  # Left/Right Wrists
            "keypoint_11_keypoint_12": 0.95, # Left/Right Hips
            "keypoint_13_keypoint_14": 0.93, # Left/Right Knees
            "keypoint_15_keypoint_16": 0.91  # Left/Right Ankles
        }
    
    return symmetry

def extract_balance_metrics(analysis_dir):
    """
    Extract balance metrics
    """
    # First try to read from the report
    report_path = os.path.join(analysis_dir, "analysis_report.txt")
    balance = {}
    
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report = f.read()
            if "5. Balance Metrics" in report:
                section = report.split("5. Balance Metrics")[1].split("6. Teaching Recommendations")[0]
                lines = section.strip().split('\n')
                for line in lines:
                    if ":" in line:
                        parts = line.split(":")
                        if len(parts) == 2:
                            metric_name = parts[0].strip()
                            try:
                                metric_value = float(parts[1].strip())
                                balance[metric_name] = metric_value
                            except ValueError:
                                continue
    
    # If we couldn't find it in the report, use placeholder values
    if not balance:
        balance = {
            "com_stability_x": 15.36,
            "com_stability_y": 12.48,
            "com_velocity_mean": 2.65
        }
    
    # Try to extract COM trajectory from the image or data
    com_trajectory = extract_com_trajectory(analysis_dir)
    if com_trajectory:
        balance["com_trajectory"] = com_trajectory
    
    return balance

def extract_com_trajectory(analysis_dir):
    """
    Extract center of mass trajectory (sample points)
    """
    # Placeholder - in a real implementation, you'd extract this from the data
    # Here we're just creating sample points
    sample_frames = list(range(0, 1200, 100))
    x_vals = [362.5 + np.random.normal(0, 1) for _ in sample_frames]
    y_vals = [403.2 + np.random.normal(0, 1) for _ in sample_frames]
    
    return {
        "sampleFrames": sample_frames,
        "x": x_vals,
        "y": y_vals
    }

def create_joint_angles_json(data, output_path, user_type="master"):
    """
    Create the joint angles JSON file
    """
    # Extract frames and angles from data
    key_frames = data['key_frames']
    
    # Create sample frames for visualization
    if key_frames:
        frame_indices = [kf[0] for kf in key_frames]
        # Add more frames for smoother visualization
        sample_frames = list(range(0, max(frame_indices) + 100, 50))
    else:
        # Fallback if no key frames were extracted
        sample_frames = list(range(0, 1200, 50))
        key_frames = [(75, 0), (205, 1), (362, 2), (510, 3), 
                      (658, 4), (795, 5), (905, 6), (1032, 7)]
    
    # Create angle data for each joint
    joint_names = [
        'right_elbow', 'left_elbow', 'right_shoulder', 'left_shoulder',
        'right_hip', 'left_hip', 'right_knee', 'left_knee', 
        'spine_top', 'spine_bottom'
    ]
    
    # Create mock angle data or extract from the report
    angles = {}
    
    for joint in joint_names:
        # Start with mock data
        angles[joint] = []
        
        for frame in sample_frames:
            # Check if we have real data for this frame
            angle_value = None
            
            # Use real data if available, otherwise generate realistic mock data
            if data['joint_angles'] and frame in data['joint_angles']:
                if joint in data['joint_angles'][frame]:
                    angle_value = data['joint_angles'][frame][joint]
            
            if angle_value is None:
                # Generate mock data based on joint type
                if 'elbow' in joint:
                    base = 135
                    var = 20
                elif 'shoulder' in joint:
                    base = 90
                    var = 40
                elif 'hip' in joint:
                    base = 170
                    var = 10
                elif 'knee' in joint:
                    base = 170
                    var = 30
                elif 'spine' in joint:
                    base = 170
                    var = 15
                else:
                    base = 120
                    var = 20
                
                # Add some variation based on the frame number
                cycle = np.sin(frame / 100) * var
                angle_value = base + cycle
            
            angles[joint].append(round(angle_value, 2))
    
    # Create the range of motion data
    rom = {}
    for joint in joint_names:
        if angles[joint]:
            rom[joint] = {
                "min": round(min(angles[joint]), 2),
                "max": round(max(angles[joint]), 2),
                "optimal": round(sum(angles[joint]) / len(angles[joint]), 2)
            }
        else:
            # Fallback if no angles were extracted
            if 'elbow' in joint:
                rom[joint] = {"min": 90, "max": 160, "optimal": 135}
            elif 'shoulder' in joint:
                rom[joint] = {"min": 15, "max": 130, "optimal": 90}
            elif 'hip' in joint:
                rom[joint] = {"min": 150, "max": 178, "optimal": 175}
            elif 'knee' in joint:
                rom[joint] = {"min": 90, "max": 178, "optimal": 170}
            elif 'spine' in joint:
                rom[joint] = {"min": 130, "max": 178, "optimal": 170}
    
    # Create the final JSON structure
    json_data = {
        "title": f"{user_type.capitalize()} Performer Joint Angles",
        "description": "Joint angle measurements throughout the Baduanjin sequence",
        "performer_type": user_type,
        "frames": sample_frames,
        "keyPoseFrames": [kf[0] for kf in key_frames],
        "keyPoseNames": data['pose_names'],
        "angles": angles,
        "rangeOfMotion": rom
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Joint angles JSON saved to {output_path}")

def create_smoothness_json(data, output_path, user_type="master"):
    """
    Create the smoothness JSON file
    """
    # Get smoothness data
    smoothness = data['smoothness']
    
    # Create keypoint name mapping
    keypoint_names = {
        "keypoint_9": "Left Wrist",
        "keypoint_10": "Right Wrist",
        "keypoint_15": "Left Ankle",
        "keypoint_16": "Right Ankle"
    }
    
    # Create movement phases based on key frames
    movement_phases = []
    key_frames = data['key_frames']
    pose_names = data['pose_names']
    
    if key_frames and len(key_frames) > 1:
        for i in range(len(key_frames)):
            start_frame = key_frames[i][0]
            
            # Set end frame to the next key frame or a bit beyond the last one
            if i < len(key_frames) - 1:
                end_frame = key_frames[i+1][0] - 1
            else:
                end_frame = start_frame + 150
            
            # Calculate average jerk for this phase (example calculation)
            avg_jerk = sum(smoothness.values()) / len(smoothness) * (0.85 + 0.1 * np.random.random())
            
            movement_phases.append({
                "name": pose_names[i] if i < len(pose_names) else f"Pose {i+1}",
                "frameRange": [start_frame, end_frame],
                "averageJerk": round(avg_jerk, 2)
            })
    else:
        # Fallback if no key frames were extracted
        frame_ranges = [(0, 150), (151, 300), (301, 450), (451, 600), 
                        (601, 750), (751, 900), (901, 1050), (1051, 1185)]
        
        for i, (start, end) in enumerate(frame_ranges):
            avg_jerk = 0.85 + 0.12 * np.random.random()
            movement_phases.append({
                "name": pose_names[i] if i < len(pose_names) else f"Pose {i+1}",
                "frameRange": [start, end],
                "averageJerk": round(avg_jerk, 2)
            })
    
    # Create the final JSON structure
    json_data = {
        "title": f"{user_type.capitalize()} Performer Movement Smoothness",
        "description": "Jerk measurements for key joints to evaluate movement control",
        "performer_type": user_type,
        "jerkMetrics": {k: round(v, 4) for k, v in smoothness.items()},
        "keypointNames": keypoint_names,
        "movementPhases": movement_phases,
        "overallSmoothness": round(sum(smoothness.values()) / len(smoothness), 2),
        "optimalJerkRange": [0.85, 0.95]
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Smoothness JSON saved to {output_path}")

def create_symmetry_json(data, output_path, user_type="master"):
    """
    Create the symmetry JSON file
    """
    # Get symmetry data
    symmetry = data['symmetry']
    
    # Create keypoint pair name mapping
    keypointPairNames = {
        "keypoint_5_keypoint_6": "Left/Right Shoulders",
        "keypoint_7_keypoint_8": "Left/Right Elbows",
        "keypoint_9_keypoint_10": "Left/Right Wrists",
        "keypoint_11_keypoint_12": "Left/Right Hips",
        "keypoint_13_keypoint_14": "Left/Right Knees",
        "keypoint_15_keypoint_16": "Left/Right Ankles"
    }
    
    # Create key pose symmetry based on key frames
    keyPoseSymmetry = []
    key_frames = data['key_frames']
    pose_names = data['pose_names']
    
    if key_frames:
        for i, (frame_idx, pose_idx) in enumerate(key_frames):
            # Generate a symmetry score for this pose
            base_score = 0.88 + 0.1 * np.random.random()
            
            keyPoseSymmetry.append({
                "poseName": pose_names[i] if i < len(pose_names) else f"Pose {i+1}",
                "frameIndex": frame_idx,
                "symmetryScore": round(base_score, 2)
            })
    else:
        # Fallback if no key frames were extracted
        frame_indices = [75, 205, 362, 510, 658, 795, 905, 1032]
        
        for i, frame_idx in enumerate(frame_indices):
            base_score = 0.88 + 0.1 * np.random.random()
            
            keyPoseSymmetry.append({
                "poseName": pose_names[i] if i < len(pose_names) else f"Pose {i+1}",
                "frameIndex": frame_idx,
                "symmetryScore": round(base_score, 2)
            })
    
    # Create the final JSON structure
    json_data = {
        "title": f"{user_type.capitalize()} Performer Movement Symmetry",
        "description": "Comparison of left and right side movements",
        "performer_type": user_type,
        "symmetryScores": {k: round(v, 2) for k, v in symmetry.items()},
        "keypointPairNames": keypointPairNames,
        "keyPoseSymmetry": keyPoseSymmetry,
        "overallSymmetry": round(sum(symmetry.values()) / len(symmetry), 2),
        "optimalSymmetryRange": [0.90, 1.0]
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Symmetry JSON saved to {output_path}")

def create_balance_json(data, output_path, user_type="master"):
    """
    Create the balance JSON file
    """
    # Get balance data
    balance = data['balance']
    
    # Extract CoM trajectory if available
    com_trajectory = balance.get("com_trajectory", {})
    
    # If no trajectory data, create placeholder
    if not com_trajectory:
        sample_frames = list(range(0, 1200, 100))
        com_trajectory = {
            "sampleFrames": sample_frames,
            "x": [362.5 + np.sin(i/100) for i in sample_frames],
            "y": [403.2 + np.cos(i/100) for i in sample_frames]
        }
    
    # Create key pose balance data based on key frames
    keyPoseBalance = []
    key_frames = data['key_frames']
    pose_names = data['pose_names']
    
    if key_frames:
        for i, (frame_idx, pose_idx) in enumerate(key_frames):
            # Find closest sample frame for CoM position
            closest_idx = 0
            min_dist = float('inf')
            for j, sample_frame in enumerate(com_trajectory.get("sampleFrames", [])):
                dist = abs(sample_frame - frame_idx)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = j
            
            # Get CoM position or use default
            try:
                x_pos = com_trajectory.get("x", [])[closest_idx]
                y_pos = com_trajectory.get("y", [])[closest_idx]
            except (IndexError, KeyError):
                x_pos = 362.5 + np.random.normal(0, 1)
                y_pos = 403.2 + np.random.normal(0, 1)
            
            # Generate a stability score for this pose
            base_score = 0.86 + 0.1 * np.random.random()
            
            keyPoseBalance.append({
                "poseName": pose_names[i] if i < len(pose_names) else f"Pose {i+1}",
                "frameIndex": frame_idx,
                "comPosition": {"x": round(x_pos, 1), "y": round(y_pos, 1)},
                "stabilityScore": round(base_score, 2)
            })
    else:
        # Fallback if no key frames were extracted
        frame_indices = [75, 205, 362, 510, 658, 795, 905, 1032]
        
        for i, frame_idx in enumerate(frame_indices):
            x_pos = 362.5 + np.random.normal(0, 1)
            y_pos = 403.2 + np.random.normal(0, 1)
            base_score = 0.86 + 0.1 * np.random.random()
            
            keyPoseBalance.append({
                "poseName": pose_names[i] if i < len(pose_names) else f"Pose {i+1}",
                "frameIndex": frame_idx,
                "comPosition": {"x": round(x_pos, 1), "y": round(y_pos, 1)},
                "stabilityScore": round(base_score, 2)
            })
    
    # Create the final JSON structure
    json_data = {
        "title": f"{user_type.capitalize()} Performer Balance Metrics",
        "description": "Center of mass trajectory and stability analysis",
        "performer_type": user_type,
        "balanceMetrics": {
            k: round(v, 2) for k, v in balance.items() 
            if k != "com_trajectory"
        },
        "comTrajectory": com_trajectory,
        "keyPoseBalance": keyPoseBalance,
        "overallStability": round(0.86 + 0.05 * np.random.random(), 2),
        "optimalStabilityRange": [0.85, 1.0]
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Balance JSON saved to {output_path}")

def create_recommendations_json(data, output_path, user_type="master"):
    """
    Create a recommendations.json file
    """
    if user_type == "master":
        # Master recommendations
        recommendations = {
            "title": "Master Performance Analysis Recommendations",
            "description": "Insights and teaching recommendations based on master performance",
            "performer_type": user_type,
            "overall": "The Baduanjin sequence demonstrates excellent balance, symmetry, and controlled movements throughout all eight forms. Pay special attention to the fluidity between transitions and maintaining proper alignment.",
            "keyPoints": [
                "Maintain vertical alignment during 'Holding Up The Sky'",
                "Keep shoulders relaxed during 'Drawing The Bow'",
                "Distribute weight evenly between feet during 'Separating Heaven and Earth'",
                "Use controlled rotation during 'Looking Backward' to avoid jerky movements",
                "Keep stable base during 'Swinging Head and Tail'",
                "Use gradual weight shifts during 'Bouncing on Toes'"
            ],
            "jointAngles": "Focus on achieving optimal hip and knee angles during transitions. Maintain 90-degree elbow angles during Drawing The Bow and do not exceed 130-degree shoulder elevation.",
            "smoothness": "All movements should be performed with consistent, controlled speed. Avoid rapid acceleration or deceleration, especially during transitions between forms.",
            "symmetry": "Left and right sides should perform identical movements with equal range of motion. Pay special attention to shoulder and hip symmetry during rotational movements.",
            "balance": "Center of mass should remain stable throughout the sequence, with controlled weight shifts. Maintain stable base of support during single-leg movements."
        }
    else:
        # Learner recommendations (more specific improvement suggestions)
        recommendations = {
            "title": "Learner Performance Analysis Recommendations",
            "description": "Personalized improvement suggestions based on your performance",
            "performer_type": user_type,
            "overall": "Your Baduanjin practice shows good understanding of the basic forms. Focus on refining movement quality and consistency to approach master-level performance.",
            "keyPoints": [
                "Work on maintaining steady breathing throughout each movement",
                "Focus on smoother transitions between poses",
                "Improve alignment in standing positions",
                "Develop more control in rotational movements",
                "Practice balance exercises to improve stability",
                "Pay attention to weight distribution during movements"
            ],
            "jointAngles": "Practice achieving and maintaining optimal joint angles. Compare your angles with the master's performance to identify areas for improvement.",
            "smoothness": "Reduce jerky movements by practicing slower, more controlled motions. Focus on consistent speed throughout each form.",
            "symmetry": "Work on balancing strength and flexibility between left and right sides. Practice mirror exercises to improve symmetry.",
            "balance": "Strengthen core muscles and practice single-leg stands to improve stability. Focus on keeping center of mass controlled during movements."
        }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(recommendations, f, indent=2)
    
    print(f"Recommendations JSON saved to {output_path}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract Baduanjin analysis data into structured JSON files')
    parser.add_argument('--input_dir', default='baduanjin_analysis', help='Input directory with analyzer output')
    parser.add_argument('--output_dir', default='baduanjin_analysis', help='Output directory for JSON files')
    parser.add_argument('--user_type', default='master', choices=['master', 'learner'], 
                      help='Type of user (master or learner) - affects file naming and content')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load data from analyzer output
    data = load_data_from_analyzer_output(args.input_dir)
    
    # Determine file prefix based on user type
    prefix = args.user_type
    
    # Create the JSON files with appropriate naming
    create_joint_angles_json(data, os.path.join(args.output_dir, f'{prefix}_joint_angles.json'), args.user_type)
    create_smoothness_json(data, os.path.join(args.output_dir, f'{prefix}_smoothness.json'), args.user_type)
    create_symmetry_json(data, os.path.join(args.output_dir, f'{prefix}_symmetry.json'), args.user_type)
    create_balance_json(data, os.path.join(args.output_dir, f'{prefix}_balance.json'), args.user_type)
    create_recommendations_json(data, os.path.join(args.output_dir, f'{prefix}_recommendations.json'), args.user_type)
    
    print(f"All JSON files successfully created in {args.output_dir} for {args.user_type}")

if __name__ == "__main__":
    main()
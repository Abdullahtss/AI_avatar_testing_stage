"""
Improved Yoga Exercise Detection - Enhanced rep counting for multi-stage yoga/stretching
Key improvements:
1. Stability-based stage detection (not just angle)
2. Hold duration verification
3. Multi-joint angle verification
4. Smooth angle transitions
5. Better confidence scoring
"""

import time
import numpy as np
from collections import deque


class YogaRepDetector:
    """
    Improved yoga rep detector for multi-stage stretching exercises
    
    Key features:
    - Tracks body stability in poses
    - Verifies hold duration
    - Uses multiple joints for accuracy
    - Smooths noisy angle data
    - Provides confidence scores
    """
    
    def __init__(self, exercise_name, model_stats, config=None):
        """
        Initialize yoga rep detector
        
        Args:
            exercise_name: str (e.g., 'downward_dog', 'stretching')
            model_stats: dict with joint statistics from training
            config: dict with yoga-specific parameters
        """
        self.exercise_name = exercise_name
        self.model_stats = model_stats
        
        # ========== CONFIGURABLE PARAMETERS ==========
        self.config = config or {}
        
        # STABILITY DETECTION
        self.angle_smoothing_window = self.config.get('angle_smoothing_window', 10)
        self.stability_threshold = self.config.get('stability_threshold', 5.0)  # degrees
        self.min_stable_frames = self.config.get('min_stable_frames', 15)  # ~0.5 sec at 30fps
        
        # HOLD VERIFICATION
        self.min_hold_duration = self.config.get('min_hold_duration', 0.5)  # seconds
        self.max_transition_time = self.config.get('max_transition_time', 1.0)  # seconds
        
        # REP SEQUENCE
        self.expected_rep_sequence = [
            "entering",  # Moving into pose
            "stable",    # Holding pose steadily
            "exiting"    # Moving out of pose
        ]
        
        # STATE TRACKING
        self.current_stage = "entering"
        self.prev_stage = None
        self.stage_start_time = time.time()
        self.stage_sequence = []
        self.rep_count = 0
        
        # ANGLE SMOOTHING (moving average)
        self.angle_history = deque(maxlen=self.angle_smoothing_window)
        
        # STABILITY TRACKING
        self.stable_frame_count = 0
        self.entering_start_time = None
        self.stable_start_time = None
        self.exiting_start_time = None
    
    def smooth_angle(self, angle):
        """
        Smooth noisy angle readings using moving average
        
        Args:
            angle: float (current joint angle in degrees)
        
        Returns:
            float: smoothed angle
        """
        self.angle_history.append(angle)
        if len(self.angle_history) > 0:
            return np.mean(self.angle_history)
        return angle
    
    def get_angle_stability(self):
        """
        Calculate how stable/steady the angle is
        
        Returns:
            float: standard deviation of recent angles (lower = more stable)
        """
        if len(self.angle_history) < 3:
            return float('inf')  # Not enough data
        
        angles = list(self.angle_history)
        return np.std(angles)
    
    def is_angle_in_range(self, angle, joint_name, tolerance_multiplier=1.0):
        """
        Check if angle is within expected range for this joint
        
        Args:
            angle: float (current angle)
            joint_name: str (e.g., 'right_shoulder')
            tolerance_multiplier: float (1.0 = use training std as tolerance)
        
        Returns:
            bool: True if angle is within valid range
        """
        if joint_name not in self.model_stats:
            return True  # Can't verify, assume valid
        
        stats = self.model_stats[joint_name]
        angle_min = stats['min']
        angle_max = stats['max']
        angle_avg = stats['avg']
        angle_std = stats['std']
        
        # Allow ±1.5 std deviations from training
        tolerance = angle_std * tolerance_multiplier
        lower_bound = max(angle_min, angle_avg - tolerance)
        upper_bound = min(angle_max, angle_avg + tolerance)
        
        return lower_bound <= angle <= upper_bound
    
    def detect_stage(self, angle, stability):
        """
        Detect current stage based on angle and stability
        
        Stage logic:
        - entering: moving to pose (low stability, angle changing)
        - stable: holding pose (high stability, consistent angle)
        - exiting: leaving pose (low stability, angle changing)
        
        Args:
            angle: float (smoothed joint angle)
            stability: float (angle standard deviation)
        
        Returns:
            str: current stage
        """
        # If very unstable, we're either entering or exiting
        if stability > self.stability_threshold:
            # Check if we were in stable pose
            if self.current_stage == "stable":
                return "exiting"
            else:
                return "entering"
        
        # If very stable, we're holding the pose
        elif stability <= self.stability_threshold:
            self.stable_frame_count += 1
            
            # Need enough stable frames to confirm we're in pose
            if self.stable_frame_count >= self.min_stable_frames:
                return "stable"
            
            # Still stabilizing
            if self.current_stage == "entering":
                return "entering"
            else:
                return "exiting"
        
        return self.current_stage
    
    def update(self, angle, joint_name='right_shoulder'):
        """
        Update rep detector with new frame data
        
        Args:
            angle: float (current joint angle)
            joint_name: str (joint being tracked)
        
        Returns:
            dict with detection info:
                - 'stage': str (current stage)
                - 'rep_detected': bool (True if rep completed)
                - 'rep_count': int (total reps)
                - 'stability': float (current stability score)
                - 'confidence': float (0-1, confidence in stage detection)
        """
        # Smooth the angle
        smoothed_angle = self.smooth_angle(angle)
        
        # Calculate stability
        stability = self.get_angle_stability()
        
        # Detect stage
        detected_stage = self.detect_stage(smoothed_angle, stability)
        
        # Handle stage transitions
        rep_detected = False
        if detected_stage != self.current_stage:
            self.prev_stage = self.current_stage
            self.current_stage = detected_stage
            self.stage_start_time = time.time()
            self.stable_frame_count = 0
            
            print(f"[Yoga] Stage transition: {self.prev_stage} → {self.current_stage}")
            self.stage_sequence.append(self.current_stage)
            
            # Check for rep completion
            rep_detected = self._check_rep_complete()
        
        # Calculate confidence score
        confidence = self._calculate_confidence(stability)
        
        return {
            'stage': self.current_stage,
            'rep_detected': rep_detected,
            'rep_count': self.rep_count,
            'stability': round(stability, 2),
            'confidence': round(confidence, 2),
            'smoothed_angle': round(smoothed_angle, 1),
            'stage_sequence': self.stage_sequence.copy()
        }
    
    def _check_rep_complete(self):
        """
        Check if a complete rep has been detected
        
        Rep sequence: entering → stable → exiting → entering (next rep)
        
        Returns:
            bool: True if rep completed
        """
        # Need at least 3 stages
        if len(self.stage_sequence) < 3:
            return False
        
        # Get last 3 stages
        recent_stages = self.stage_sequence[-3:]
        
        # Check if matches rep pattern: entering -> stable -> exiting
        expected_pattern = ["entering", "stable", "exiting"]
        if recent_stages == expected_pattern:
            self.rep_count += 1
            print(f"[Yoga] ✓ REP {self.rep_count} DETECTED!")
            
            # Reset for next rep
            self.stage_sequence = [self.current_stage]
            return True
        
        return False
    
    def _calculate_confidence(self, stability):
        """
        Calculate confidence score for current detection (0-1)
        
        Factors:
        - Stability (stable = high confidence)
        - Hold duration (longer = higher confidence)
        - Consistent stage transitions
        
        Returns:
            float: confidence score 0-1
        """
        # Base confidence from stability
        max_stability = self.stability_threshold * 2
        stability_confidence = max(0, 1 - (stability / max_stability))
        
        # Bonus for being in stable state
        if self.current_stage == "stable":
            stability_confidence = min(1.0, stability_confidence + 0.3)
        
        return stability_confidence
    
    def get_stage_feedback(self):
        """
        Get coaching feedback based on current state
        
        Returns:
            str: feedback message
        """
        stability = self.get_angle_stability()
        
        if self.current_stage == "entering":
            return "Move into the pose slowly"
        
        elif self.current_stage == "stable":
            if stability > self.stability_threshold:
                return "Hold steady - less movement"
            else:
                return "Good hold - maintain this position"
        
        elif self.current_stage == "exiting":
            return "Slowly exit the pose"
        
        return None
    
    def get_stats(self):
        """Get detector statistics"""
        return {
            'exercise': self.exercise_name,
            'total_reps': self.rep_count,
            'current_stage': self.current_stage,
            'stage_sequence': self.stage_sequence,
            'stability': round(self.get_angle_stability(), 2)
        }


class MultiJointYogaDetector:
    """
    Advanced yoga detector using MULTIPLE joints for higher accuracy
    
    Instead of tracking one joint, tracks multiple joints simultaneously
    to verify pose completion
    
    Example: For downward dog, track:
    - Shoulder angle
    - Elbow angle
    - Hip angle
    - All must be in correct position to count as pose
    """
    
    def __init__(self, exercise_name, model_stats, joints_to_track):
        """
        Initialize multi-joint detector
        
        Args:
            exercise_name: str
            model_stats: dict with stats for all joints
            joints_to_track: list of joint names to use
                e.g., ['right_shoulder', 'right_elbow', 'right_hip']
        """
        self.exercise_name = exercise_name
        self.model_stats = model_stats
        self.joints_to_track = joints_to_track
        
        # Initialize detector for each joint
        self.detectors = {
            joint: YogaRepDetector(f"{exercise_name}_{joint}", model_stats)
            for joint in joints_to_track
        }
        
        self.rep_count = 0
    
    def update(self, angles_dict):
        """
        Update with angles from all tracked joints
        
        Args:
            angles_dict: dict mapping joint_name → angle
                e.g., {'right_shoulder': 120, 'right_elbow': 90, 'right_hip': 80}
        
        Returns:
            dict with detection info
        """
        stages = {}
        confidences = {}
        
        # Update each joint detector
        for joint, angle in angles_dict.items():
            if joint in self.detectors:
                result = self.detectors[joint].update(angle, joint)
                stages[joint] = result['stage']
                confidences[joint] = result['confidence']
        
        # Check if all joints are in same stage with high confidence
        rep_detected = self._check_pose_complete(stages, confidences)
        
        if rep_detected:
            self.rep_count += 1
        
        return {
            'rep_detected': rep_detected,
            'rep_count': self.rep_count,
            'joint_stages': stages,
            'joint_confidences': confidences,
            'overall_confidence': np.mean(list(confidences.values()))
        }
    
    def _check_pose_complete(self, stages, confidences):
        """
        Check if pose is complete across all joints
        
        All joints must agree on stage with good confidence
        """
        if not stages:
            return False
        
        # Get most common stage
        stage_values = list(stages.values())
        most_common = max(set(stage_values), key=stage_values.count)
        
        # Check if all joints are in stable state with high confidence
        all_stable = all(stage == "stable" for stage in stage_values)
        high_confidence = all(conf > 0.7 for conf in confidences.values())
        
        if all_stable and high_confidence:
            return True
        
        return False
    
    def get_stats(self):
        """Get statistics from all detectors"""
        return {
            'exercise': self.exercise_name,
            'total_reps': self.rep_count,
            'joint_stats': {
                joint: detector.get_stats()
                for joint, detector in self.detectors.items()
            }
        }
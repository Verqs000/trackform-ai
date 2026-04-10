"""
Pose Extractor - Production Ready
Uses MediaPipe Pose Landmarker (0.10.33+)
Supports: sprint, hurdles, shot_put, discus, javelin
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions


class PoseExtractor:
    """Pose Extractor using MediaPipe Pose Landmarker."""

    def __init__(self, model_path: str = "models/pose_landmarker.task"):
        self.landmarker = None
        self._initialize(model_path)

    def _initialize(self, model_path: str):
        """Initialize the MediaPipe Pose Landmarker."""
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Pose model not found at: {model_path}. "
                "Download pose_landmarker.task and place it in the models/ folder."
            )

        base_options = BaseOptions(model_asset_path=str(model_path))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.6,
            min_pose_presence_confidence=0.6,
            min_tracking_confidence=0.6,
            output_segmentation_masks=False
        )

        self.landmarker = vision.PoseLandmarker.create_from_options(options)
        print("✅ PoseExtractor initialized successfully")

        self.key_points = {
            'nose': 0,
            'left_shoulder': 11,  'right_shoulder': 12,
            'left_elbow': 13,     'right_elbow': 14,
            'left_wrist': 15,     'right_wrist': 16,
            'left_hip': 23,       'right_hip': 24,
            'left_knee': 25,      'right_knee': 26,
            'left_ankle': 27,     'right_ankle': 28,
            'left_heel': 29,      'right_heel': 30,
            'left_foot_index': 31, 'right_foot_index': 32,
        }

    def extract_from_video(
        self,
        video_path: str,
        event: str = "sprint",
        sample_every: int = 2,
        show_progress: bool = True
    ) -> Tuple[List[Dict], float]:
        """
        Extract poses from video.
        Returns: (list_of_pose_data, fps)
        """
        if self.landmarker is None:
            raise RuntimeError("Landmarker not initialized. Check that pose_landmarker.task exists.")

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps          = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps < 1:
            fps = 30.0

        print(f"📹 Processing: {video_path.name} | {total_frames} frames @ {fps:.1f} FPS | Event: {event}")

        poses         = []
        frame_num     = 0
        processed_count = 0

        progress_bar = None
        if show_progress:
            try:
                import streamlit as st
                progress_bar = st.progress(0)
            except Exception:
                pass

        while True:
            success, image = cap.read()
            if not success:
                break

            frame_num += 1
            if frame_num % sample_every != 0:
                continue

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

            timestamp_ms = int((frame_num / fps) * 1000)

            try:
                results = self.landmarker.detect_for_video(mp_image, timestamp_ms)
            except Exception as e:
                print(f"⚠️ Frame {frame_num} detection error: {e}")
                continue

            if results.pose_landmarks:
                pose_data = self._extract_landmarks(
                    results.pose_landmarks[0], frame_num, fps, event
                )
                poses.append(pose_data)
                processed_count += 1

            if progress_bar and frame_num % 10 == 0:
                progress = min(int((frame_num / total_frames) * 100), 100)
                progress_bar.progress(progress)

            if processed_count % 50 == 0 and processed_count > 0:
                print(f"   → Extracted {processed_count} poses...")

        cap.release()

        if progress_bar:
            progress_bar.progress(100)

        print(f"✅ Pose extraction complete: {len(poses)} poses from {frame_num} frames")

        if len(poses) == 0:
            raise ValueError(
                "No poses detected in video. Make sure the athlete is clearly "
                "visible and the video is not too dark or blurry."
            )

        return poses, float(fps)

    def _extract_landmarks(
        self,
        landmarks,
        frame_num: int,
        fps: float,
        event: str = "sprint"
    ) -> Dict:
        """Extract relevant keypoints from MediaPipe landmarks."""
        data = {
            'frame': frame_num,
            'time':  round(frame_num / fps, 3),
            'event': event,
            'points': {}
        }

        for name, idx in self.key_points.items():
            if idx < len(landmarks):
                lm = landmarks[idx]
                data['points'][name] = {
                    'x':        round(float(lm.x), 4),
                    'y':        round(float(lm.y), 4),
                    'z':        round(float(lm.z), 4),
                    'visible':  float(lm.visibility) > 0.5,
                    'presence': float(lm.presence) > 0.5
                }

        data['angles'] = self._compute_angles(data['points'], event)
        return data

    def _compute_angles(self, points: Dict, event: str) -> Dict:
        """Compute biomechanical angles relevant to the event."""
        angles = {}

        def angle_between(a, b, c) -> Optional[float]:
            try:
                if not all(k in points for k in [a, b, c]):
                    return None
                if not all(points[k].get('visible', False) for k in [a, b, c]):
                    return None
                pa = np.array([points[a]['x'], points[a]['y']])
                pb = np.array([points[b]['x'], points[b]['y']])
                pc = np.array([points[c]['x'], points[c]['y']])
                v1 = pa - pb
                v2 = pc - pb
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
                return round(float(np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))), 2)
            except Exception:
                return None

        # Universal angles
        angles['left_knee_angle']   = angle_between('left_hip',      'left_knee',   'left_ankle')
        angles['right_knee_angle']  = angle_between('right_hip',     'right_knee',  'right_ankle')
        angles['left_elbow_angle']  = angle_between('left_shoulder',  'left_elbow',  'left_wrist')
        angles['right_elbow_angle'] = angle_between('right_shoulder', 'right_elbow', 'right_wrist')
        angles['left_hip_angle']    = angle_between('left_shoulder',  'left_hip',    'left_knee')
        angles['right_hip_angle']   = angle_between('right_shoulder', 'right_hip',   'right_knee')

        if event == 'hurdles':
            angles['lead_leg_angle']   = angle_between('right_hip',  'right_knee', 'right_ankle')
            angles['trail_leg_angle']  = angle_between('left_hip',   'left_knee',  'left_ankle')
            angles['torso_lean']       = angle_between('nose',        'left_shoulder', 'left_hip')
            angles['left_ankle_flex']  = angle_between('left_knee',  'left_ankle',  'left_foot_index')
            angles['right_ankle_flex'] = angle_between('right_knee', 'right_ankle', 'right_foot_index')

        elif event == 'sprint':
            angles['trunk_angle'] = angle_between('left_shoulder', 'left_hip', 'left_knee')

        elif event in ['shot_put', 'discus', 'javelin']:
            angles['throwing_arm_angle']     = angle_between('right_shoulder', 'right_elbow', 'right_wrist')
            angles['shoulder_hip_rotation']  = angle_between('left_shoulder',  'right_shoulder', 'right_hip')

        return {k: v for k, v in angles.items() if v is not None}

    def save_poses(self, poses: List[Dict], output_path: str):
        """Save extracted poses to JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump({
                'metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'total_poses':  len(poses),
                    'event':        poses[0].get('event', 'unknown') if poses else 'unknown'
                },
                'poses': poses
            }, f, indent=2)

        print(f"💾 Saved poses to: {output_path}")


if __name__ == "__main__":
    extractor = PoseExtractor()
    print("✅ PoseExtractor initialized successfully")
    print("Tracking keypoints:", list(extractor.key_points.keys()))
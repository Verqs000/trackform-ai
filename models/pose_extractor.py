"""
Pose Extractor - Production Ready
Uses MediaPipe Pose Landmarker (0.10.33+)
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions


class PoseExtractor:
    """Singleton-style Pose Extractor with MediaPipe Pose Landmarker."""

    _instance = None
    _landmarker = None

    def __new__(cls, model_path: str = "models/pose_landmarker.task"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(model_path)
        return cls._instance

    def _initialize(self, model_path: str):
        """Initialize the MediaPipe Pose Landmarker."""
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Pose model not found at: {model_path}. "
                                  "Download pose_landmarker.task and place it correctly.")

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
        
        self.key_points = {
            'nose': 0,
            'left_shoulder': 11, 'right_shoulder': 12,
            'left_elbow': 13, 'right_elbow': 14,
            'left_wrist': 15, 'right_wrist': 16,
            'left_hip': 23, 'right_hip': 24,
            'left_knee': 25, 'right_knee': 26,
            'left_ankle': 27, 'right_ankle': 28,
            'left_heel': 29, 'right_heel': 30,
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
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if fps < 1:
            fps = 30.0  # fallback

        print(f"📹 Processing: {video_path.name} | {total_frames} frames @ {fps:.1f} FPS")

        poses = []
        frame_num = 0
        processed_count = 0

        progress_bar = None
        if show_progress:
            progress_bar = st.progress(0) if 'st' in globals() else None

        while True:
            success, image = cap.read()
            if not success:
                break

            frame_num += 1
            if frame_num % sample_every != 0:
                continue

            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

            timestamp_ms = int((frame_num / fps) * 1000)
            results = self.landmarker.detect_for_video(mp_image, timestamp_ms)

            if results.pose_landmarks:
                pose_data = self._extract_landmarks(results.pose_landmarks[0], frame_num, fps)
                poses.append(pose_data)
                processed_count += 1

            # Update progress
            if progress_bar and frame_num % 10 == 0:
                progress = min(int((frame_num / total_frames) * 100), 100)
                progress_bar.progress(progress)

            if processed_count % 50 == 0 and processed_count > 0:
                print(f"   → Extracted {processed_count} poses...")

        cap.release()
        
        if progress_bar:
            progress_bar.progress(100)

        print(f"✅ Pose extraction complete: {len(poses)} poses extracted")

        return poses, float(fps)

    def _extract_landmarks(self, landmarks, frame_num: int, fps: float) -> Dict:
        """Extract relevant keypoints from MediaPipe landmarks."""
        data = {
            'frame': frame_num,
            'time': round(frame_num / fps, 3),
            'points': {}
        }

        for name, idx in self.key_points.items():
            if idx < len(landmarks):
                lm = landmarks[idx]
                data['points'][name] = {
                    'x': round(float(lm.x), 4),
                    'y': round(float(lm.y), 4),
                    'z': round(float(lm.z), 4),
                    'visible': float(lm.visibility) > 0.5,
                    'presence': float(lm.presence) > 0.5
                }
        
        return data

    def save_poses(self, poses: List[Dict], output_path: str):
        """Save extracted poses to JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                'metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'total_poses': len(poses)
                },
                'poses': poses
            }, f, indent=2)
        
        print(f"💾 Saved poses to: {output_path}")


# For testing
if __name__ == "__main__":
    extractor = PoseExtractor()
    print("✅ PoseExtractor initialized successfully")
    print("Tracking keypoints:", list(extractor.key_points.keys()))
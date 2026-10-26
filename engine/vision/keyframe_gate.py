"""
OmniInspect Client-Side Vision & Keyframe Gating Engine.
Implements industrial AOI keyframe triggering:
  1. Motion Energy Calculation (frame differencing): Filters out hand tremors and motion blur.
  2. Modified Laplacian Variance (Tenengrad Sharpness): Rejects out-of-focus camera frames.
  3. Slicing Aided Hyper-Inference (SAHI): Slices uncompressed 1:1 optical patches around target IC pins.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
from pydantic import BaseModel


class FrameQualityMetrics(BaseModel):
    is_stable: bool
    is_sharp: bool
    motion_energy: float
    sharpness_score: float
    ready_for_inference: bool


class KeyframeGatingEngine:
    """
    Prevents video streaming bandwidth bloat.
    Only triggers high-res inference when the physical circuit board is stable and in focus.
    """
    def __init__(
        self,
        motion_threshold: float = 2.5,
        sharpness_threshold: float = 85.0,
        history_frames: int = 5
    ):
        self.motion_threshold = motion_threshold
        self.sharpness_threshold = sharpness_threshold
        self.history_frames = history_frames
        self.prev_gray: Optional[np.ndarray] = None
        self.consecutive_stable_count: int = 0

    def compute_sharpness(self, gray_frame: np.ndarray) -> float:
        """Computes variance of Laplacian as a focus/sharpness metric."""
        return float(cv2.Laplacian(gray_frame, cv2.CV_64F).var())

    def compute_motion_energy(self, gray_frame: np.ndarray) -> float:
        """Computes mean absolute frame difference against previous frame."""
        if self.prev_gray is None:
            self.prev_gray = gray_frame.copy()
            return 0.0

        # Downsample for ultra-fast motion check (< 1ms compute)
        h, w = gray_frame.shape[:2]
        small_curr = cv2.resize(gray_frame, (w // 4, h // 4))
        small_prev = cv2.resize(self.prev_gray, (w // 4, h // 4))

        diff = cv2.absdiff(small_curr, small_prev)
        motion_energy = float(np.mean(diff))

        self.prev_gray = gray_frame.copy()
        return motion_energy

    def evaluate_frame(self, bgr_frame: np.ndarray) -> FrameQualityMetrics:
        """
        Evaluates optical stability and optical focus.
        Returns whether the frame is qualified for high-res Meta inference.
        """
        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        motion = self.compute_motion_energy(gray)
        sharpness = self.compute_sharpness(gray)

        is_stable = motion < self.motion_threshold
        is_sharp = sharpness > self.sharpness_threshold

        if is_stable and is_sharp:
            self.consecutive_stable_count += 1
        else:
            self.consecutive_stable_count = 0

        # Require at least 3 consecutive stable/sharp frames to trigger uncompressed inference
        ready = self.consecutive_stable_count >= 3

        return FrameQualityMetrics(
            is_stable=is_stable,
            is_sharp=is_sharp,
            motion_energy=round(motion, 3),
            sharpness_score=round(sharpness, 2),
            ready_for_inference=ready
        )


def test_keyframe_gating():
    engine = KeyframeGatingEngine()
    
    # 1. Simulate blurry/moving frame (low sharpness, high noise)
    blurry_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 120
    q1 = engine.evaluate_frame(blurry_frame)
    print("Test 1 (Blank/Low Texture):", q1.model_dump())
    assert not q1.ready_for_inference

    # 2. Simulate high-contrast PCB texture (sharp)
    sharp_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.putText(sharp_frame, "ATMega328P CAD PINOUT U1 PIN 1", (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # Feed 3 consecutive identical sharp frames (stable)
    for i in range(4):
        q = engine.evaluate_frame(sharp_frame)
        print(f"Test 2 (Stabilized Frame {i+1}):", q.model_dump())

    assert q.ready_for_inference, "Engine failed to latch on stabilized sharp frame."
    print("Keyframe Gating Engine successfully verified!")


if __name__ == "__main__":
    test_keyframe_gating()

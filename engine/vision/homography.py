"""
OmniInspect Spatial Homography & RoI Slicing Engine.
Maps 2D optical camera pixel coordinates (u, v) into CAD metric coordinates (x_mm, y_mm),
and extracts 1:1 uncompressed native-resolution patches for high-density IC pin inspection.
"""

import numpy as np
import cv2
from typing import Tuple, List, Optional, Dict
from pydantic import BaseModel


class Point2D(BaseModel):
    x: float
    y: float


class MetricHomographyEngine:
    """
    Computes and manages the planar projective transformation matrix H between
    the camera coordinate frame and the CAD board coordinate frame:
        [x_cad, y_cad, 1]^T ~ H * [u_pixel, v_pixel, 1]^T
    """
    def __init__(self, board_width_mm: float, board_height_mm: float):
        self.board_width_mm = board_width_mm
        self.board_height_mm = board_height_mm
        self.H_cam_to_cad: Optional[np.ndarray] = None
        self.H_cad_to_cam: Optional[np.ndarray] = None

    def calibrate_from_corners(
        self,
        pixel_corners: List[Tuple[float, float]],
        cad_corners: Optional[List[Tuple[float, float]]] = None
    ) -> bool:
        """
        Calibrates homography using 4 ordered corner coordinates:
        [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
        """
        if len(pixel_corners) != 4:
            raise ValueError("Exactly 4 corner points required for homography calibration.")

        if cad_corners is None:
            # Default to board perimeter in metric millimeters
            cad_corners = [
                (0.0, 0.0),                               # Top-Left
                (self.board_width_mm, 0.0),               # Top-Right
                (self.board_width_mm, self.board_height_mm), # Bottom-Right
                (0.0, self.board_height_mm)               # Bottom-Left
            ]

        src_pts = np.array(pixel_corners, dtype=np.float32)
        dst_pts = np.array(cad_corners, dtype=np.float32)

        # Compute Homography
        H, status = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is None:
            return False

        self.H_cam_to_cad = H
        self.H_cad_to_cam = np.linalg.inv(H)
        return True

    def pixel_to_cad(self, u: float, v: float) -> Tuple[float, float]:
        """Maps a camera pixel (u, v) to metric CAD coordinates (x_mm, y_mm)."""
        if self.H_cam_to_cad is None:
            raise RuntimeError("Engine not calibrated. Call calibrate_from_corners first.")

        pt = np.array([u, v, 1.0], dtype=np.float32).reshape(3, 1)
        res = self.H_cam_to_cad @ pt
        res /= res[2, 0]
        return float(res[0, 0]), float(res[1, 0])

    def cad_to_pixel(self, x_mm: float, y_mm: float) -> Tuple[int, int]:
        """Maps CAD board coordinates (x_mm, y_mm) to camera pixel coordinates (u, v)."""
        if self.H_cad_to_cam is None:
            raise RuntimeError("Engine not calibrated. Call calibrate_from_corners first.")

        pt = np.array([x_mm, y_mm, 1.0], dtype=np.float32).reshape(3, 1)
        res = self.H_cad_to_cam @ pt
        res /= res[2, 0]
        return int(round(res[0, 0])), int(round(res[1, 0]))

    def extract_component_roi(
        self,
        image: np.ndarray,
        center_mm: Tuple[float, float],
        box_size_mm: Tuple[float, float] = (10.0, 10.0)
    ) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Extracts an uncompressed, 1:1 optical patch centered around a target component.
        Preserves sub-millimeter detail for 0.5mm solder bridges without downsampling blur.
        """
        cx_mm, cy_mm = center_mm
        w_mm, h_mm = box_size_mm

        # Determine bounding corners in CAD space
        p_tl_mm = (cx_mm - w_mm / 2.0, cy_mm - h_mm / 2.0)
        p_br_mm = (cx_mm + w_mm / 2.0, cy_mm + h_mm / 2.0)

        # Map to pixel space
        u_min, v_min = self.cad_to_pixel(p_tl_mm[0], p_tl_mm[1])
        u_max, v_max = self.cad_to_pixel(p_br_mm[0], p_br_mm[1])

        # Clamp to image bounds
        img_h, img_w = image.shape[:2]
        u1 = max(0, min(u_min, u_max))
        u2 = min(img_w, max(u_min, u_max))
        v1 = max(0, min(v_min, v_max))
        v2 = min(img_h, max(v_min, v_max))

        roi_crop = image[v1:v2, u1:u2]
        bbox_dict = {"u1": u1, "v1": v1, "u2": u2, "v2": v2}
        return roi_crop, bbox_dict


def test_homography_pipeline():
    # Board dimensions: 68.6mm x 53.4mm (Arduino Uno)
    engine = MetricHomographyEngine(board_width_mm=68.6, board_height_mm=53.4)

    # Simulated camera viewing the board at 1920x1080 with minor perspective tilt
    cam_corners = [
        (350.0, 180.0),   # TL
        (1520.0, 210.0),  # TR
        (1480.0, 890.0),  # BR
        (380.0, 860.0)    # BL
    ]

    success = engine.calibrate_from_corners(cam_corners)
    assert success, "Homography calibration failed"

    # Test coordinate mapping
    test_u, test_v = 350.0, 180.0
    cad_x, cad_y = engine.pixel_to_cad(test_u, test_v)
    print(f"Cam Pixel ({test_u}, {test_v}) -> CAD mm ({cad_x:.2f}, {cad_y:.2f})")
    assert abs(cad_x) < 0.1 and abs(cad_y) < 0.1, "Top-left mapping error exceeds threshold"

    # Test center mapping
    center_u, center_v = engine.cad_to_pixel(34.3, 26.7)
    print(f"CAD Center (34.3mm, 26.7mm) -> Cam Pixel ({center_u}, {center_v})")
    print("Metric Homography Engine successfully verified!")


if __name__ == "__main__":
    test_homography_pipeline()

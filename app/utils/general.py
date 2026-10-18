"""
RoadVision AI - Shared General Utilities
Provides path validations, image checks, and severity categorization.
"""

from pathlib import Path
from typing import Tuple
from app.core.config import settings


def validate_image_path(path: Path) -> bool:
    """Checks if an image file exists and has a supported extension."""
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return path.is_file() and path.suffix.lower() in valid_exts


def validate_video_path(path: Path) -> bool:
    """Checks if a video file exists and has a supported extension."""
    valid_exts = {".mp4", ".avi", ".mov", ".mkv"}
    return path.is_file() and path.suffix.lower() in valid_exts


def validate_weights_path(path: Path) -> bool:
    """Checks if a model weights file exists and has a supported extension."""
    valid_exts = {".pt", ".onnx", ".torchscript", ".engine"}
    return path.is_file() and path.suffix.lower() in valid_exts


def classify_severity(width: int, height: int, frame_w: int, frame_h: int) -> Tuple[str, Tuple[int, int, int]]:
    """
    Categorizes pothole hazard into Critical, Moderate, or Minor based on pixel area.
    Returns:
        (severity_label, (B, G, R) color tuple)
    """
    area = width * height
    frame_area = max(1, frame_w * frame_h)
    ratio = area / frame_area

    if area > settings.SEVERITY_CRITICAL_AREA or ratio > 0.05 or height > 120:
        return "Critical", (50, 50, 235)    # Red (BGR)
    elif area > settings.SEVERITY_MODERATE_AREA or ratio > 0.018 or height > 65:
        return "Moderate", (30, 165, 245)   # Amber Orange (BGR)
    else:
        return "Minor", (230, 215, 20)      # Electric Cyan (BGR)

"""
RoadVision AI - Centralized Application Configuration
Provides centralized, type-safe settings and path resolution with environment variable support.
"""

import os
from pathlib import Path
from typing import Tuple


class Settings:
    # -------------------------------------------------------------------------
    # Filesystem & Paths
    # -------------------------------------------------------------------------
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    APP_DIR: Path = PROJECT_ROOT / "app"
    WEIGHTS_DIR: Path = PROJECT_ROOT / "weights"
    DATA_DIR: Path = PROJECT_ROOT / "data"
    VIDEOS_DIR: Path = DATA_DIR / "videos"
    SNAPSHOTS_DIR: Path = DATA_DIR / "snapshots"
    RUNS_DIR: Path = PROJECT_ROOT / "runs"

    # Default model files
    POTHOLE_WEIGHTS_PATH: Path = WEIGHTS_DIR / "pothole_best.pt"
    COCO_FALLBACK_WEIGHTS_PATH: Path = PROJECT_ROOT / "yolov5s.pt"

    # Default sample test assets
    SAMPLE_IMAGE_PATH: Path = PROJECT_ROOT / "yolov5" / "data" / "images" / "img.jpg"
    SAMPLE_VIDEO_PATH: Path = VIDEOS_DIR / "road_test.mp4"

    def __init__(self):
        # Allow dynamic environment variable overrides per instance
        self.CONF_THRESHOLD: float = float(os.getenv("CONF_THRESHOLD", "0.25"))
        self.IOU_THRESHOLD: float = float(os.getenv("IOU_THRESHOLD", "0.45"))
        self.IMG_SIZE: Tuple[int, int] = (640, 640)
        self.DEVICE: str = os.getenv("DEVICE", "cpu")

        self.TRACKER_MAX_DISTANCE: float = float(os.getenv("TRACKER_MAX_DISTANCE", "85.0"))
        self.TRACKER_MAX_MISSING_FRAMES: int = int(os.getenv("TRACKER_MAX_MISSING_FRAMES", "18"))

        self.SEVERITY_CRITICAL_AREA: int = 24000
        self.SEVERITY_MODERATE_AREA: int = 7000

        self.SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
        self.SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
        self.DEFAULT_PHONE_STREAM_URL: str = os.getenv("DEFAULT_PHONE_STREAM_URL", "http://127.0.0.1:8080/video")

        # Google Maps / Clair API
        self.GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "clair_7nUY5MStJwiTqRzcCrzyBf1xehkXsQzu2")
        self.CLAIR_MAPS_API_URL: str = os.getenv("CLAIR_MAPS_API_URL", "https://api.clair.im/v1/google-maps/search")

    def ensure_directories(self) -> None:
        """Ensure runtime data directories exist."""
        self.WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        self.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self.RUNS_DIR.mkdir(parents=True, exist_ok=True)

    def get_model_weights_path(self) -> Path:
        """Returns the best available model weights path."""
        # Check custom pothole weights first
        if self.POTHOLE_WEIGHTS_PATH.exists():
            return self.POTHOLE_WEIGHTS_PATH
        # Fall back to COCO YOLOv5s
        if self.COCO_FALLBACK_WEIGHTS_PATH.exists():
            return self.COCO_FALLBACK_WEIGHTS_PATH
        return self.POTHOLE_WEIGHTS_PATH


# Global settings singleton
settings = Settings()
settings.ensure_directories()

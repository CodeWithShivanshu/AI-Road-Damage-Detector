"""
RoadVision AI - Video Source Manager
Threaded frame capture manager supporting test video, webcam, and smartphone camera feeds.
"""

import time
import threading
from pathlib import Path
from typing import Optional, Union
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("camera")


class CameraManager:
    """Provides non-blocking threaded frame capture for video files and live streams."""

    def __init__(self, default_source: str = "test_video", custom_target: Optional[str] = None):
        self.source_type = default_source
        self.source_path: str = ""
        self.cap: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        self.current_frame: Optional[np.ndarray] = None
        self.frame_ready = threading.Event()
        self.is_connected = False
        self.status_message = "Initializing camera..."

        self.set_source(default_source, custom_target)

    def set_source(self, source_type: str, custom_target: Optional[Union[str, int]] = None) -> bool:
        """Dynamically switches active video stream source."""
        logger.info(f"Switching video source to: {source_type} (target: {custom_target})")

        # Stop existing capture worker
        with self.lock:
            self.running = False

        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.5)

        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

            self.source_type = source_type
            if source_type == "test_video":
                target = str(custom_target) if custom_target else str(settings.SAMPLE_VIDEO_PATH)
                self.source_path = target
                self.cap = cv2.VideoCapture(target)
            elif source_type == "webcam":
                idx = int(custom_target) if custom_target and str(custom_target).isdigit() else 0
                self.source_path = f"Webcam Device #{idx}"
                self.cap = cv2.VideoCapture(idx)
            elif source_type in ["usb_phone", "ip_camera"]:
                url = str(custom_target) if custom_target else settings.DEFAULT_PHONE_STREAM_URL
                self.source_path = url
                self.cap = cv2.VideoCapture(url)
            elif source_type == "custom_file":
                self.source_path = str(custom_target) if custom_target else ""
                self.cap = cv2.VideoCapture(self.source_path)
            else:
                logger.error(f"Unknown source type requested: {source_type}")
                return False

            if self.cap and self.cap.isOpened():
                self.is_connected = True
                self.status_message = f"Connected to {source_type} ({self.source_path})"
                logger.info(self.status_message)
            else:
                self.is_connected = False
                self.status_message = f"Failed to open source {source_type}: {self.source_path}"
                logger.warning(self.status_message)

            self.running = True
            self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.worker_thread.start()

        return self.is_connected

    def _capture_loop(self) -> None:
        """Background thread reading frames to avoid buffer lag."""
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.1)
                continue

            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.current_frame = frame
                    self.is_connected = True
                self.frame_ready.set()

                # Pace video files at ~30 FPS
                if self.source_type in ["test_video", "custom_file"]:
                    time.sleep(0.033)
            else:
                # Seamless loop for recorded video files
                if self.source_type in ["test_video", "custom_file"]:
                    with self.lock:
                        if self.cap:
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.02)
                else:
                    with self.lock:
                        self.is_connected = False
                    time.sleep(0.4)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Returns a copy of the latest captured frame."""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def release(self) -> None:
        """Stops worker and releases underlying camera resource."""
        with self.lock:
            self.running = False
            if self.cap:
                self.cap.release()
                self.cap = None
        logger.info("CameraManager released.")

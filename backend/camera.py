import cv2
import time
import subprocess
import threading
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent


class CameraManager:
    """Threaded Video Stream Manager supporting test video, local webcam, and USB/Android phone feeds."""
    def __init__(self, default_source: str = "test_video"):
        self.source_type = default_source
        self.source_path = ""
        self.cap: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.current_frame = None
        self.frame_ready = threading.Event()
        self.is_connected = False
        self.status_message = "Initializing..."

        # Determine default test video path
        self.default_test_video = str(ROOT / "data" / "videos" / "road_test.mp4")

        # Start with default source
        self.set_source(default_source)

    def set_source(self, source_type: str, custom_target: Optional[str] = None):
        with self.lock:
            self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)

        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

            self.source_type = source_type
            if source_type == "test_video":
                self.source_path = custom_target or self.default_test_video
                self.cap = cv2.VideoCapture(self.source_path)
            elif source_type == "webcam":
                cam_idx = int(custom_target) if custom_target and custom_target.isdigit() else 0
                self.source_path = f"Webcam {cam_idx}"
                self.cap = cv2.VideoCapture(cam_idx)
            elif source_type == "usb_phone" or source_type == "ip_camera":
                # Default to localhost:8080 (standard for ADB USB port forwarding) or custom phone IP
                url = custom_target or "http://127.0.0.1:8080/video"
                self.source_path = url
                self.cap = cv2.VideoCapture(url)
            elif source_type == "custom_file":
                self.source_path = custom_target or ""
                self.cap = cv2.VideoCapture(self.source_path)

            if self.cap and self.cap.isOpened():
                self.is_connected = True
                self.status_message = f"Connected to {self.source_type} ({self.source_path})"
            else:
                self.is_connected = False
                self.status_message = f"Failed to open source {self.source_type}"

            self.running = True
            self.thread = threading.Thread(target=self._capture_worker, daemon=True)
            self.thread.start()

    def _capture_worker(self):
        """Continuous frame reader thread to prevent network latency and buffer lag."""
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
                # Rate-limit test video playback to ~30 FPS
                if self.source_type in ["test_video", "custom_file"]:
                    time.sleep(0.033)
            else:
                # Loop video files seamlessly when they hit end
                if self.source_type in ["test_video", "custom_file"]:
                    with self.lock:
                        if self.cap:
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.02)
                else:
                    with self.lock:
                        self.is_connected = False
                    time.sleep(0.5)

    def get_latest_frame(self) -> Optional[any]:
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def release(self):
        with self.lock:
            self.running = False
            if self.cap:
                self.cap.release()
                self.cap = None


def forward_adb_usb_port(local_port: int = 8080, phone_port: int = 8080) -> Tuple[bool, str]:
    """Automates 'adb forward tcp:8080 tcp:8080' so phone stream passes over physical USB cable."""
    adb_paths = [
        "adb",
        str(ROOT / "bin" / "platform-tools" / "adb"),
        str(ROOT / "bin" / "adb"),
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb"
    ]

    adb_bin = None
    for p in adb_paths:
        try:
            res = subprocess.run([p, "version"], capture_output=True, timeout=2)
            if res.returncode == 0:
                adb_bin = p
                break
        except Exception:
            continue

    if not adb_bin:
        return False, "ADB not found. Connect Android phone over Wi-Fi IP or install ADB."

    try:
        devices_out = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=3)
        if "device" not in devices_out.stdout.strip():
            return False, "No Android device detected. Enable USB Debugging on phone and reconnect."

        fwd_res = subprocess.run([adb_bin, "forward", f"tcp:{local_port}", f"tcp:{phone_port}"],
                                 capture_output=True, text=True, timeout=3)
        if fwd_res.returncode == 0:
            return True, f"USB tunnel active! Forwarded localhost:{local_port} -> Phone:{phone_port}"
        return False, fwd_res.stderr.strip() or "Failed to forward ADB port"
    except Exception as e:
        return False, str(e)

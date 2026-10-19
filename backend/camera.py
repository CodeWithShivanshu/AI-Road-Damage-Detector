import cv2
import time
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent


def find_adb_binary() -> Optional[str]:
    """Locates the ADB executable on the host machine across common locations."""
    candidates = [
        shutil.which("adb"),
        str(ROOT / "bin" / "adb"),
        str(ROOT / "bin" / "platform-tools" / "adb"),
        str(Path.home() / "Desktop" / "platform-tools" / "adb"),
        str(Path.home() / "platform-tools" / "adb"),
        str(Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb"),
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
        "/usr/bin/adb"
    ]
    for p in candidates:
        if not p:
            continue
        try:
            res = subprocess.run([p, "version"], capture_output=True, timeout=2)
            if res.returncode == 0:
                return p
        except Exception:
            continue
    return None


def get_adb_devices(adb_bin: str) -> List[Dict[str, str]]:
    """Returns a list of connected Android devices and their status."""
    devices = []
    try:
        out = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=3)
        lines = [line.strip() for line in out.stdout.strip().splitlines() if line.strip()]
        for line in lines[1:]:  # Skip "List of devices attached"
            parts = line.split()
            if len(parts) >= 2:
                devices.append({
                    "id": parts[0],
                    "state": parts[1]  # 'device', 'unauthorized', 'offline'
                })
    except Exception:
        pass
    return devices


def get_device_details(adb_bin: str, device_id: str) -> Dict[str, str]:
    """Retrieves manufacturer and model info for an authorized Android device."""
    info = {"model": "Android Device", "manufacturer": "Android"}
    try:
        res_mfg = subprocess.run([adb_bin, "-s", device_id, "shell", "getprop", "ro.product.manufacturer"],
                                 capture_output=True, text=True, timeout=2)
        if res_mfg.returncode == 0 and res_mfg.stdout.strip():
            info["manufacturer"] = res_mfg.stdout.strip().capitalize()

        res_model = subprocess.run([adb_bin, "-s", device_id, "shell", "getprop", "ro.product.model"],
                                   capture_output=True, text=True, timeout=2)
        if res_model.returncode == 0 and res_model.stdout.strip():
            info["model"] = res_model.stdout.strip()
    except Exception:
        pass
    return info


def check_installed_camera_apps(adb_bin: str, device_id: str) -> Dict[str, bool]:
    """Checks if common streaming camera apps (IP Webcam, DroidCam) are installed on the device."""
    apps = {"ip_webcam": False, "droidcam": False}
    try:
        res = subprocess.run([adb_bin, "-s", device_id, "shell", "pm", "list", "packages"],
                             capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            packages = res.stdout
            apps["ip_webcam"] = "com.pas.webcam" in packages
            apps["droidcam"] = "dev47apps.droidcam" in packages or "com.dev47apps.droidcamx" in packages
    except Exception:
        pass
    return apps


def forward_adb_usb_port(local_port: int = 8080, phone_port: int = 8080) -> Tuple[bool, str]:
    """
    Sets up ADB USB port forwarding for phone camera streaming over a physical USB cable.
    Forwards both port 8080 (IP Webcam) and port 4747 (DroidCam) for maximum compatibility.
    """
    adb_bin = find_adb_binary()
    if not adb_bin:
        return False, "ADB not found. Please install Android Platform Tools or connect phone over Wi-Fi."

    devices = get_adb_devices(adb_bin)
    if not devices:
        return False, "No Android phone detected over USB. Ensure USB cable is plugged in and USB Debugging is ON in Developer Options."

    primary = devices[0]
    dev_id = primary["id"]
    state = primary["state"]

    if state == "unauthorized":
        return False, f"Device {dev_id} is unauthorized. Please unlock your phone and tap 'Allow USB Debugging' on the screen."
    if state == "offline":
        return False, f"Device {dev_id} is offline. Please unplug and reconnect the USB cable."

    # Forward port 8080 (IP Webcam default)
    fwd_8080 = subprocess.run([adb_bin, "-s", dev_id, "forward", "tcp:8080", "tcp:8080"],
                              capture_output=True, text=True, timeout=3)
    # Forward port 4747 (DroidCam default)
    fwd_4747 = subprocess.run([adb_bin, "-s", dev_id, "forward", "tcp:4747", "tcp:4747"],
                              capture_output=True, text=True, timeout=3)

    details = get_device_details(adb_bin, dev_id)
    device_name = f"{details['manufacturer']} {details['model']}".strip()

    if fwd_8080.returncode == 0 or fwd_4747.returncode == 0:
        return True, f"USB tunnel active for {device_name} ({dev_id})! Forwarded ports 8080 & 4747."
    return False, fwd_8080.stderr.strip() or "Failed to forward ADB port."


def get_adb_status() -> Dict[str, Any]:
    """Returns comprehensive diagnostic info on ADB, connected phone, and ports for the frontend."""
    adb_bin = find_adb_binary()
    if not adb_bin:
        return {
            "adb_available": False,
            "device_connected": False,
            "message": "ADB binary not found on host."
        }

    devices = get_adb_devices(adb_bin)
    if not devices:
        return {
            "adb_available": True,
            "adb_path": adb_bin,
            "device_connected": False,
            "message": "ADB ready. No phone detected over USB."
        }

    primary = devices[0]
    dev_id = primary["id"]
    state = primary["state"]
    details = get_device_details(adb_bin, dev_id) if state == "device" else {}
    apps = check_installed_camera_apps(adb_bin, dev_id) if state == "device" else {"ip_webcam": False, "droidcam": False}

    return {
        "adb_available": True,
        "adb_path": adb_bin,
        "device_connected": True,
        "device_id": dev_id,
        "device_state": state,
        "manufacturer": details.get("manufacturer", "Unknown"),
        "model": details.get("model", "Android Device"),
        "camera_apps": apps,
        "message": f"Connected to {details.get('manufacturer', '')} {details.get('model', dev_id)} ({state})"
    }


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
            self.is_connected = False
            self.current_frame = None
            self.frame_ready.clear()

            if source_type == "test_video":
                self.source_path = custom_target or self.default_test_video
                self.cap = cv2.VideoCapture(self.source_path)
                if self.cap and self.cap.isOpened():
                    self.is_connected = True
                    self.status_message = f"Connected to {self.source_type} ({self.source_path})"
                else:
                    self.status_message = f"Failed to open video {self.source_path}"

            elif source_type == "webcam":
                cam_idx = int(custom_target) if custom_target and str(custom_target).isdigit() else 0
                self.source_path = f"Webcam {cam_idx}"
                self.cap = cv2.VideoCapture(cam_idx)
                if self.cap and self.cap.isOpened():
                    self.is_connected = True
                    self.status_message = f"Connected to {self.source_path}"
                else:
                    self.status_message = f"Failed to open webcam {cam_idx}"

            elif source_type in ["usb_phone", "ip_camera"]:
                target_url = (custom_target or "").strip()
                if not target_url or target_url == "auto":
                    target_url = "http://127.0.0.1:8080/video"
                self.source_path = target_url
                self.status_message = f"Connecting to phone stream at {self.source_path}..."

            elif source_type == "custom_file":
                self.source_path = custom_target or ""
                self.cap = cv2.VideoCapture(self.source_path)
                if self.cap and self.cap.isOpened():
                    self.is_connected = True
                    self.status_message = f"Connected to custom file ({self.source_path})"
                else:
                    self.status_message = f"Failed to open {self.source_path}"

            self.running = True
            self.thread = threading.Thread(target=self._capture_worker, daemon=True)
            self.thread.start()

    def _capture_worker(self):
        """Continuous frame reader thread with automatic reconnection and stream recovery."""
        last_reconnect_attempt = 0.0

        while self.running:
            # Handle phone / IP camera connecting & reconnecting
            if self.source_type in ["usb_phone", "ip_camera"]:
                if not self.cap or not self.cap.isOpened():
                    now = time.time()
                    if now - last_reconnect_attempt < 1.5:
                        time.sleep(0.1)
                        continue

                    last_reconnect_attempt = now
                    # Candidate URLs to try for USB phone
                    candidates = [self.source_path]
                    if "127.0.0.1:8080" in self.source_path:
                        candidates.extend([
                            "http://127.0.0.1:8080/videofeed",
                            "http://127.0.0.1:8080/mjpegfeed",
                            "http://127.0.0.1:4747/video",
                            "http://127.0.0.1:4747/mjpegfeed"
                        ])
                    elif "127.0.0.1:4747" in self.source_path:
                        candidates.extend([
                            "http://127.0.0.1:4747/mjpegfeed",
                            "http://127.0.0.1:8080/video"
                        ])

                    connected = False
                    for cand in candidates:
                        if not self.running:
                            break
                        try:
                            cap = cv2.VideoCapture(cand)
                            if cap.isOpened():
                                ret, test_frame = cap.read()
                                if ret and test_frame is not None:
                                    with self.lock:
                                        if self.cap:
                                            self.cap.release()
                                        self.cap = cap
                                        self.source_path = cand
                                        self.current_frame = test_frame
                                        self.is_connected = True
                                        self.status_message = f"Connected to Phone Camera ({cand})"
                                    self.frame_ready.set()
                                    connected = True
                                    break
                                else:
                                    cap.release()
                            else:
                                cap.release()
                        except Exception:
                            pass

                    if not connected:
                        with self.lock:
                            self.is_connected = False
                            self.status_message = f"Waiting for phone stream at {self.source_path}... (Tap 'Start Server' in IP Webcam / DroidCam)"
                        time.sleep(0.5)
                        continue

            if not self.cap or not self.cap.isOpened():
                time.sleep(0.1)
                continue

            try:
                ret, frame = self.cap.read()
            except Exception:
                ret, frame = False, None

            if ret and frame is not None:
                with self.lock:
                    self.current_frame = frame
                    self.is_connected = True
                self.frame_ready.set()

                # Rate-limit test video playback to ~30 FPS
                if self.source_type in ["test_video", "custom_file"]:
                    time.sleep(0.033)
            else:
                if self.source_type in ["test_video", "custom_file"]:
                    with self.lock:
                        if self.cap:
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.02)
                else:
                    # Stream dropped or server restarted on phone
                    with self.lock:
                        self.is_connected = False
                        self.status_message = "Phone video stream paused or interrupted. Reconnecting..."
                        if self.cap:
                            self.cap.release()
                            self.cap = None
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

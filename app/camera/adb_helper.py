"""
RoadVision AI - Android ADB Port Forwarding Helper
Automates port forwarding over physical USB cable so smartphone video feeds route over USB.
"""

import subprocess
from typing import Tuple
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("camera.adb")


def forward_adb_usb_port(local_port: int = 8080, phone_port: int = 8080) -> Tuple[bool, str]:
    """
    Executes 'adb forward tcp:8080 tcp:8080' to tunnel Android IP Webcam over USB cable.
    """
    adb_candidates = [
        "adb",
        str(settings.PROJECT_ROOT / "bin" / "platform-tools" / "adb"),
        str(settings.PROJECT_ROOT / "bin" / "adb"),
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb"
    ]

    adb_bin = None
    for candidate in adb_candidates:
        try:
            res = subprocess.run([candidate, "version"], capture_output=True, timeout=2)
            if res.returncode == 0:
                adb_bin = candidate
                break
        except Exception:
            continue

    if not adb_bin:
        msg = "ADB binary not found in PATH or project bin/."
        logger.warning(msg)
        return False, msg

    try:
        devices_res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=3)
        if "device" not in devices_res.stdout.strip():
            msg = "No Android device detected. Connect phone via USB and enable USB Debugging."
            logger.warning(msg)
            return False, msg

        fwd_res = subprocess.run([adb_bin, "forward", f"tcp:{local_port}", f"tcp:{phone_port}"],
                                 capture_output=True, text=True, timeout=3)
        if fwd_res.returncode == 0:
            msg = f"ADB USB Forwarding Active: localhost:{local_port} -> Phone:{phone_port}"
            logger.info(msg)
            return True, msg
        
        err_msg = fwd_res.stderr.strip() or "Failed to forward ADB port."
        logger.error(err_msg)
        return False, err_msg

    except Exception as e:
        logger.error(f"ADB execution error: {e}")
        return False, str(e)

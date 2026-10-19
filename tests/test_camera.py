import pytest
from backend.camera import find_adb_binary, get_adb_status, forward_adb_usb_port, CameraManager

def test_find_adb_binary():
    adb = find_adb_binary()
    assert adb is not None, "ADB binary should be located"

def test_get_adb_status():
    status = get_adb_status()
    assert isinstance(status, dict)
    assert "adb_available" in status
    assert status["adb_available"] is True
    assert "device_connected" in status

def test_forward_adb_usb_port():
    success, msg = forward_adb_usb_port()
    assert isinstance(success, bool)
    assert isinstance(msg, str)
    assert len(msg) > 0

def test_camera_manager_initialization():
    cam = CameraManager(default_source="test_video")
    assert cam.source_type == "test_video"
    cam.release()

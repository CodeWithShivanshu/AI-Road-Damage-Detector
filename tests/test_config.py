import os
from pathlib import Path
from app.core.config import Settings


def test_settings_initialization():
    settings = Settings()
    assert settings.PROJECT_ROOT.exists(), "Project root directory should exist"
    assert isinstance(settings.CONF_THRESHOLD, float)
    assert 0.0 < settings.CONF_THRESHOLD < 1.0
    assert isinstance(settings.IOU_THRESHOLD, float)
    assert settings.IMG_SIZE == (640, 640)


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("CONF_THRESHOLD", "0.42")
    monkeypatch.setenv("DEVICE", "cpu")
    settings = Settings()
    assert settings.CONF_THRESHOLD == 0.42
    assert settings.DEVICE == "cpu"


def test_ensure_directories():
    settings = Settings()
    settings.ensure_directories()
    assert settings.DATA_DIR.exists()
    assert settings.WEIGHTS_DIR.exists()
    assert settings.SNAPSHOTS_DIR.exists()

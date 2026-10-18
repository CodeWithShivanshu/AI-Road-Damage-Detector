from pathlib import Path
from app.core.config import settings
from app.utils.general import validate_image_path, validate_weights_path


def test_core_directories_exist():
    assert (settings.PROJECT_ROOT / "yolov5").exists(), "yolov5 folder must exist"
    assert (settings.PROJECT_ROOT / "models").exists(), "models core folder must exist"
    assert (settings.PROJECT_ROOT / "utils").exists(), "utils core folder must exist"


def test_sample_image_exists():
    img_path = settings.SAMPLE_IMAGE_PATH
    assert img_path.exists(), f"Sample image should exist at {img_path}"
    assert validate_image_path(img_path) is True


def test_weights_path_resolution():
    weights_path = settings.get_model_weights_path()
    assert weights_path.exists(), f"Model weights should exist at {weights_path}"
    assert validate_weights_path(weights_path) is True

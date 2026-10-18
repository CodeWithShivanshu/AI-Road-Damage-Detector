import cv2
import numpy as np
from app.core.config import settings
from app.inference.detector import InferenceEngine
from app.utils.tracking import PotholeTracker


def test_pothole_tracker_deduplication():
    tracker = PotholeTracker(max_distance=50.0)

    # Frame 1: Detection at (100, 100)
    det_f1 = [{"bbox": [90, 90, 110, 110], "conf": 0.85, "severity": "Moderate"}]
    res_f1 = tracker.update(det_f1)
    assert len(res_f1) == 1
    assert res_f1[0]["is_new"] is True
    assert tracker.total_unique_count == 1

    # Frame 2: Same pothole slightly shifted at (102, 104)
    det_f2 = [{"bbox": [92, 94, 112, 114], "conf": 0.88, "severity": "Moderate"}]
    res_f2 = tracker.update(det_f2)
    assert len(res_f2) == 1
    assert res_f2[0]["is_new"] is False
    assert tracker.total_unique_count == 1, "Should not increment count for existing tracked hazard"


def test_inference_engine_prediction():
    engine = InferenceEngine()
    sample_img = settings.SAMPLE_IMAGE_PATH
    assert sample_img.exists()

    detections = engine.predict_image(sample_img, conf_thres=0.25)
    assert isinstance(detections, list)

    # If detections are found, check schema
    if len(detections) > 0:
        det = detections[0]
        assert "bbox" in det
        assert len(det["bbox"]) == 4
        assert "conf" in det
        assert "label" in det
        assert "severity" in det
        assert det["severity"] in ["Critical", "Moderate", "Minor"]

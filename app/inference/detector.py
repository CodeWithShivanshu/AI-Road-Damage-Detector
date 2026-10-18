"""
RoadVision AI - Neural Inference Engine
Encapsulates YOLOv5 model loading, image inference, and real-time frame processing.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import cv2
import numpy as np
import torch

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.general import classify_severity
from app.utils.tracking import PotholeTracker
from app.inference.postprocess import draw_detection_box, draw_hud_overlay

# Ensure project root is in sys.path for YOLOv5 internal imports
ROOT = settings.PROJECT_ROOT
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# PyTorch 2.6+ unpickler patch for YOLOv5 checkpoints
_orig_torch_load = torch.load
torch.load = lambda *args, **kwargs: _orig_torch_load(*args, **{**kwargs, 'weights_only': False}) if 'weights_only' not in kwargs else _orig_torch_load(*args, **kwargs)

from models.common import DetectMultiBackend
from utils.general import non_max_suppression, scale_coords, check_img_size
from utils.datasets import letterbox
from utils.torch_utils import select_device, time_sync

logger = get_logger("inference")


class InferenceEngine:
    """Wrapper around YOLOv5 DetectMultiBackend providing structured prediction interfaces."""

    def __init__(self, weights_path: Optional[Union[str, Path]] = None, device: Optional[str] = None):
        self.weights_path = Path(weights_path) if weights_path else settings.get_model_weights_path()
        self.device_str = device or settings.DEVICE
        self.device = select_device(self.device_str)

        logger.info(f"Loading YOLOv5 model weights from: {self.weights_path} on device: {self.device}")

        # Load backend model
        self.model = DetectMultiBackend(str(self.weights_path), device=self.device, dnn=False)
        self.stride = self.model.stride
        self.names = self.model.names
        self.imgsz = check_img_size(settings.IMG_SIZE, s=self.stride)

        # Warmup model execution
        self.model.warmup(imgsz=(1, 3, *self.imgsz))
        logger.info(f"Model successfully loaded. Active classes: {self.names}")

        self.tracker = PotholeTracker()
        self.fps_filter: List[float] = []

    def predict_image(self, image_or_path: Union[str, Path, np.ndarray], conf_thres: Optional[float] = None,
                      iou_thres: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Runs inference on a single static image.
        Returns a structured list of detected bounding boxes, confidences, labels, and severities.
        """
        conf_thres = conf_thres if conf_thres is not None else settings.CONF_THRESHOLD
        iou_thres = iou_thres if iou_thres is not None else settings.IOU_THRESHOLD

        if isinstance(image_or_path, (str, Path)):
            img_path = Path(image_or_path)
            if not img_path.exists():
                raise FileNotFoundError(f"Input image file not found: {img_path}")
            frame = cv2.imread(str(img_path))
            if frame is None:
                raise ValueError(f"Failed to read image at: {img_path}")
        else:
            frame = image_or_path.copy()

        h0, w0 = frame.shape[:2]

        # 1. Letterbox resize
        im = letterbox(frame, self.imgsz, stride=self.stride, auto=True)[0]
        im = im.transpose((2, 0, 1))[::-1]  # BGR to RGB
        im = np.ascontiguousarray(im)
        im = torch.from_numpy(im).to(self.device).float() / 255.0
        if len(im.shape) == 3:
            im = im[None]

        # 2. Inference
        pred = self.model(im)

        # 3. NMS
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes=None, agnostic=False, max_det=100)

        results = []
        for det in pred:
            if len(det):
                det[:, :4] = scale_coords(im.shape[2:], det[:, :4], frame.shape).round()
                for *xyxy, conf, cls in reversed(det):
                    x1, y1, x2, y2 = map(int, xyxy)
                    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
                    cls_id = int(cls)
                    label = self.names[cls_id] if cls_id < len(self.names) else f"class_{cls_id}"
                    severity, color = classify_severity(bw, bh, w0, h0)

                    results.append({
                        "bbox": [x1, y1, x2, y2],
                        "conf": float(conf),
                        "class_id": cls_id,
                        "label": label,
                        "severity": severity,
                        "color": color
                    })

        return results

    def process_frame(self, frame: np.ndarray, conf_thres: Optional[float] = None,
                      iou_thres: Optional[float] = None, track: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Runs real-time inference on a video frame, tracks hazards, and overlays HUD annotations.
        """
        t_start = time_sync()
        conf_thres = conf_thres if conf_thres is not None else settings.CONF_THRESHOLD
        iou_thres = iou_thres if iou_thres is not None else settings.IOU_THRESHOLD

        t_infer_start = time_sync()
        detections = self.predict_image(frame, conf_thres=conf_thres, iou_thres=iou_thres)
        t_infer = (time_sync() - t_infer_start) * 1000.0

        if track:
            detections = self.tracker.update(detections, frame)

        # Draw bounding boxes and corner accents
        annotated_frame = frame.copy()
        for det in detections:
            draw_detection_box(annotated_frame, det)

        # Compute smoothed FPS
        t_total = time_sync() - t_start
        fps = 1.0 / max(0.001, t_total)
        self.fps_filter.append(fps)
        if len(self.fps_filter) > 15:
            self.fps_filter.pop(0)
        smooth_fps = sum(self.fps_filter) / len(self.fps_filter)

        # Draw HUD banner
        draw_hud_overlay(annotated_frame, smooth_fps, t_infer)

        telemetry = {
            "fps": round(smooth_fps, 1),
            "inference_ms": round(t_infer, 1),
            "current_frame_detections": len(detections),
            "total_potholes": self.tracker.total_unique_count,
            "critical_count": self.tracker.critical_count,
            "moderate_count": self.tracker.moderate_count,
            "minor_count": self.tracker.minor_count,
            "road_score": self.tracker.get_road_quality_score(),
            "detections": [{
                "track_id": d.get("track_id", 0),
                "severity": d["severity"],
                "conf": round(d["conf"], 2),
                "bbox": d["bbox"]
            } for d in detections]
        }

        return annotated_frame, telemetry

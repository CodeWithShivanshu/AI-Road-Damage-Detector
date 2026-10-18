import time
import cv2
import torch
import numpy as np

# PyTorch 2.6+ compatibility patch for YOLOv5 model unpickler
_orig_torch_load = torch.load
torch.load = lambda *args, **kwargs: _orig_torch_load(*args, **{**kwargs, 'weights_only': False}) if 'weights_only' not in kwargs else _orig_torch_load(*args, **kwargs)
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# YOLOv5 core imports
import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from models.common import DetectMultiBackend
from utils.general import non_max_suppression, scale_coords, check_img_size
from utils.datasets import letterbox
from utils.torch_utils import select_device, time_sync

from backend.database import record_detection

SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class PotholeTracker:
    """Tracks unique potholes across video frames to prevent duplicate counts."""
    def __init__(self, max_distance: float = 85.0, max_frames_missing: int = 18):
        self.max_distance = max_distance
        self.max_frames_missing = max_frames_missing
        self.tracked_objects: Dict[int, Dict[str, Any]] = {}
        self.next_id = 1
        self.total_unique_count = 0
        self.critical_count = 0
        self.moderate_count = 0
        self.minor_count = 0

    def reset(self):
        self.tracked_objects.clear()
        self.next_id = 1
        self.total_unique_count = 0
        self.critical_count = 0
        self.moderate_count = 0
        self.minor_count = 0

    def update(self, current_detections: List[Dict[str, Any]], frame: np.ndarray, inspection_id: int) -> List[Dict[str, Any]]:
        updated_detections = []
        matched_track_ids = set()

        for det in current_detections:
            x1, y1, x2, y2 = det["bbox"]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            severity = det["severity"]
            conf = det["conf"]

            best_match_id = None
            min_dist = float("inf")

            for track_id, track in self.tracked_objects.items():
                if track_id in matched_track_ids:
                    continue
                tcx, tcy = track["center"]
                dist = np.hypot(cx - tcx, cy - tcy)
                if dist < self.max_distance and dist < min_dist:
                    min_dist = dist
                    best_match_id = track_id

            if best_match_id is not None:
                # Existing pothole matched
                self.tracked_objects[best_match_id]["center"] = (cx, cy)
                self.tracked_objects[best_match_id]["bbox"] = (x1, y1, x2, y2)
                self.tracked_objects[best_match_id]["missing"] = 0
                matched_track_ids.add(best_match_id)
                det["track_id"] = best_match_id
                det["is_new"] = False
            else:
                # Brand new pothole detected!
                new_id = self.next_id
                self.next_id += 1
                self.total_unique_count += 1
                matched_track_ids.add(new_id)

                if severity == "Critical":
                    self.critical_count += 1
                elif severity == "Moderate":
                    self.moderate_count += 1
                else:
                    self.minor_count += 1

                # Save snapshot crop
                h, w, _ = frame.shape
                pad = 20
                cy1, cy2 = max(0, y1 - pad), min(h, y2 + pad)
                cx1, cx2 = max(0, x1 - pad), min(w, x2 + pad)
                crop = frame[cy1:cy2, cx1:cx2]

                snapshot_rel_path = ""
                if crop.size > 0:
                    snap_name = f"pothole_{new_id}_{int(time.time())}.jpg"
                    snap_file = SNAPSHOTS_DIR / snap_name
                    cv2.imwrite(str(snap_file), crop)
                    snapshot_rel_path = f"/snapshots/{snap_name}"

                # Save in database
                record_detection(
                    inspection_id=inspection_id,
                    confidence=float(conf),
                    severity=severity,
                    bbox=[x1, y1, x2, y2],
                    snapshot_path=snapshot_rel_path
                )

                self.tracked_objects[new_id] = {
                    "center": (cx, cy),
                    "bbox": (x1, y1, x2, y2),
                    "missing": 0,
                    "severity": severity,
                    "conf": conf,
                    "snapshot": snapshot_rel_path
                }
                det["track_id"] = new_id
                det["is_new"] = True

            updated_detections.append(det)

        # Increment missing count for unmatched tracks
        stale_ids = []
        for track_id, track in self.tracked_objects.items():
            if track_id not in matched_track_ids:
                track["missing"] += 1
                if track["missing"] > self.max_frames_missing:
                    stale_ids.append(track_id)

        for sid in stale_ids:
            del self.tracked_objects[sid]

        return updated_detections


class InferenceEngine:
    def __init__(self, weights_path: Optional[str] = None):
        self.root = ROOT
        # Default priority: custom trained pothole weights -> yolov5s.pt
        pothole_weights = self.root / "weights" / "pothole_best.pt"
        coco_weights = self.root / "yolov5s.pt"

        if weights_path and Path(weights_path).exists():
            selected_weights = Path(weights_path)
        elif pothole_weights.exists():
            selected_weights = pothole_weights
        else:
            selected_weights = coco_weights

        self.weights_path = selected_weights
        self.device = select_device("cpu")
        print(f"[InferenceEngine] Loading model weights from: {self.weights_path}")

        # Initialize model
        self.model = DetectMultiBackend(str(self.weights_path), device=self.device, dnn=False)
        self.stride, self.names, self.pt = self.model.stride, self.model.names, self.model.pt
        self.imgsz = check_img_size((640, 640), s=self.stride)

        # Warmup
        self.model.warmup(imgsz=(1, 3, *self.imgsz))
        print(f"[InferenceEngine] Model initialized successfully with classes: {self.names}")

        self.tracker = PotholeTracker()
        self.last_fps = 0.0
        self.fps_filter = []

    def classify_severity(self, width: int, height: int, frame_w: int, frame_h: int) -> Tuple[str, Tuple[int, int, int]]:
        area = width * height
        frame_area = frame_w * frame_h
        ratio = area / max(1, frame_area)

        # Area and aspect thresholding
        if area > 24000 or ratio > 0.05 or height > 120:
            return "Critical", (50, 50, 235)    # Red (BGR)
        elif area > 7000 or ratio > 0.018 or height > 65:
            return "Moderate", (30, 165, 245)   # Amber Orange (BGR)
        else:
            return "Minor", (230, 215, 20)      # Electric Cyan (BGR)

    def process_frame(self, frame: np.ndarray, conf_thres: float = 0.25, iou_thres: float = 0.45,
                      inspection_id: int = 1) -> Tuple[np.ndarray, Dict[str, Any]]:
        t_start = time_sync()
        h0, w0 = frame.shape[:2]

        # 1. Letterbox resizing
        im = letterbox(frame, self.imgsz, stride=self.stride, auto=True)[0]
        im = im.transpose((2, 0, 1))[::-1]  # BGR to RGB, to 3xHxW
        im = np.ascontiguousarray(im)

        im = torch.from_numpy(im).to(self.device).float()
        im /= 255.0  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim

        # 2. Inference
        t_infer_start = time_sync()
        pred = self.model(im)
        t_infer = (time_sync() - t_infer_start) * 1000.0

        # 3. NMS
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes=None, agnostic=False, max_det=100)

        # 4. Extract detections
        raw_detections = []
        for det in pred:
            if len(det):
                det[:, :4] = scale_coords(im.shape[2:], det[:, :4], frame.shape).round()
                for *xyxy, conf, cls in reversed(det):
                    x1, y1, x2, y2 = map(int, xyxy)
                    bw = max(1, x2 - x1)
                    bh = max(1, y2 - y1)
                    cls_id = int(cls)
                    label = self.names[cls_id] if cls_id < len(self.names) else f"class_{cls_id}"

                    severity, color = self.classify_severity(bw, bh, w0, h0)
                    raw_detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "conf": float(conf),
                        "label": label,
                        "severity": severity,
                        "color": color
                    })

        # 5. Object Tracking (deduplication)
        tracked_detections = self.tracker.update(raw_detections, frame, inspection_id)

        # 6. Annotate frame
        annotated_frame = frame.copy()
        for det in tracked_detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["conf"]
            label = det["label"]
            severity = det["severity"]
            color = det["color"]
            track_id = det.get("track_id", 0)

            # Draw sleek bounding box with corner highlights
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
            c_len = min(20, max(8, int((x2 - x1) * 0.2)))
            # Corner accents
            cv2.line(annotated_frame, (x1, y1), (x1 + c_len, y1), (255, 255, 255), 3, cv2.LINE_AA)
            cv2.line(annotated_frame, (x1, y1), (x1, y1 + c_len), (255, 255, 255), 3, cv2.LINE_AA)
            cv2.line(annotated_frame, (x2, y2), (x2 - c_len, y2), (255, 255, 255), 3, cv2.LINE_AA)
            cv2.line(annotated_frame, (x2, y2), (x2, y2 - c_len), (255, 255, 255), 3, cv2.LINE_AA)

            # Tag pill
            tag_text = f"#{track_id} {label.upper()} {int(conf * 100)}% [{severity}]"
            (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated_frame, (x1, max(0, y1 - 22)), (x1 + tw + 10, y1), color, -1)
            cv2.putText(annotated_frame, tag_text, (x1 + 5, max(14, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Calculate FPS
        t_total = time_sync() - t_start
        fps = 1.0 / max(0.001, t_total)
        self.fps_filter.append(fps)
        if len(self.fps_filter) > 15:
            self.fps_filter.pop(0)
        smooth_fps = sum(self.fps_filter) / len(self.fps_filter)

        # Road Quality Index calculation
        # Starts at 100%, drops with severity
        crit = self.tracker.critical_count
        mod = self.tracker.moderate_count
        minor = self.tracker.minor_count
        deduction = (crit * 6.0) + (mod * 2.5) + (minor * 0.8)
        road_score = max(10.0, round(100.0 - deduction, 1))

        # Top-left HUD overlay
        hud_bg = (15, 23, 42)
        cv2.rectangle(annotated_frame, (10, 10), (280, 75), hud_bg, -1)
        cv2.rectangle(annotated_frame, (10, 10), (280, 75), (51, 65, 85), 1)

        # Status indicator
        cv2.circle(annotated_frame, (25, 30), 6, (0, 230, 118), -1)  # Emerald green
        cv2.putText(annotated_frame, "ROADVISION AI ACTIVE", (40, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (241, 245, 249), 1, cv2.LINE_AA)

        fps_text = f"FPS: {smooth_fps:.1f}  |  Latency: {t_infer:.1f}ms"
        cv2.putText(annotated_frame, fps_text, (20, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (148, 163, 184), 1, cv2.LINE_AA)

        telemetry = {
            "fps": round(smooth_fps, 1),
            "inference_ms": round(t_infer, 1),
            "current_frame_detections": len(tracked_detections),
            "total_potholes": self.tracker.total_unique_count,
            "critical_count": self.tracker.critical_count,
            "moderate_count": self.tracker.moderate_count,
            "minor_count": self.tracker.minor_count,
            "road_score": road_score,
            "detections": [{
                "track_id": d.get("track_id", 0),
                "severity": d["severity"],
                "conf": round(d["conf"], 2),
                "bbox": d["bbox"]
            } for d in tracked_detections]
        }

        return annotated_frame, telemetry

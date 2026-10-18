"""
RoadVision AI - Pothole Tracking & Hazard Deduplication
Tracks detections across consecutive video frames to prevent duplicate counts.
"""

import time
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("tracker")


class PotholeTracker:
    """Maintains active tracks of potholes using centroid Euclidean distance."""
    def __init__(self, max_distance: Optional[float] = None, max_frames_missing: Optional[int] = None):
        self.max_distance = max_distance or settings.TRACKER_MAX_DISTANCE
        self.max_frames_missing = max_frames_missing or settings.TRACKER_MAX_MISSING_FRAMES
        self.tracked_objects: Dict[int, Dict[str, Any]] = {}
        self.next_id = 1

        self.total_unique_count = 0
        self.critical_count = 0
        self.moderate_count = 0
        self.minor_count = 0

    def reset(self) -> None:
        """Resets all tracking counters and history."""
        self.tracked_objects.clear()
        self.next_id = 1
        self.total_unique_count = 0
        self.critical_count = 0
        self.moderate_count = 0
        self.minor_count = 0
        logger.info("PotholeTracker state reset.")

    def update(self, detections: List[Dict[str, Any]], frame: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
        """
        Updates tracked objects with new frame detections.
        Matches existing tracks or creates new unique pothole entries.
        """
        updated_detections = []
        matched_track_ids = set()

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            severity = det.get("severity", "Minor")
            conf = det.get("conf", 0.0)

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
                # Existing pothole track updated
                self.tracked_objects[best_match_id]["center"] = (cx, cy)
                self.tracked_objects[best_match_id]["bbox"] = (x1, y1, x2, y2)
                self.tracked_objects[best_match_id]["missing"] = 0
                matched_track_ids.add(best_match_id)
                det["track_id"] = best_match_id
                det["is_new"] = False
            else:
                # New unique hazard detected
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

                # Save snapshot crop if frame is available
                snapshot_rel_path = ""
                if frame is not None and frame.size > 0:
                    h, w, _ = frame.shape
                    pad = 20
                    cy1, cy2 = max(0, y1 - pad), min(h, y2 + pad)
                    cx1, cx2 = max(0, x1 - pad), min(w, x2 + pad)
                    crop = frame[cy1:cy2, cx1:cx2]

                    if crop.size > 0:
                        snap_name = f"pothole_{new_id}_{int(time.time())}.jpg"
                        snap_file = settings.SNAPSHOTS_DIR / snap_name
                        cv2.imwrite(str(snap_file), crop)
                        snapshot_rel_path = f"/snapshots/{snap_name}"

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

        # Drop tracks that haven't been seen for too many frames
        stale_ids = []
        for track_id, track in self.tracked_objects.items():
            if track_id not in matched_track_ids:
                track["missing"] += 1
                if track["missing"] > self.max_frames_missing:
                    stale_ids.append(track_id)

        for sid in stale_ids:
            del self.tracked_objects[sid]

        return updated_detections

    def get_road_quality_score(self) -> float:
        """Calculates dynamic Road Quality Index (100% is perfect, drops with hazards)."""
        deduction = (self.critical_count * 6.0) + (self.moderate_count * 2.5) + (self.minor_count * 0.8)
        return max(10.0, round(100.0 - deduction, 1))

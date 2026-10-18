"""
RoadVision AI - Drawing & Postprocessing Utilities
Provides bounding box styling, HUD rendering, and corner accent overlays.
"""

import cv2
import numpy as np
from typing import Dict, Any, List


def draw_detection_box(frame: np.ndarray, det: Dict[str, Any]) -> None:
    """Draws a modern bounding box with corner accents and tag pill on the frame."""
    x1, y1, x2, y2 = det["bbox"]
    conf = det["conf"]
    label = det["label"]
    severity = det.get("severity", "Minor")
    color = det.get("color", (0, 255, 0))
    track_id = det.get("track_id", 0)

    # 1. Main bounding rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

    # 2. Corner accent markers
    c_len = min(20, max(8, int((x2 - x1) * 0.2)))
    cv2.line(frame, (x1, y1), (x1 + c_len, y1), (255, 255, 255), 3, cv2.LINE_AA)
    cv2.line(frame, (x1, y1), (x1, y1 + c_len), (255, 255, 255), 3, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2 - c_len, y2), (255, 255, 255), 3, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2, y2 - c_len), (255, 255, 255), 3, cv2.LINE_AA)

    # 3. Tag pill header
    tag_text = f"#{track_id} {label.upper()} {int(conf * 100)}% [{severity}]"
    (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    tag_y = max(0, y1 - 22)
    cv2.rectangle(frame, (x1, tag_y), (x1 + tw + 10, y1), color, -1)
    cv2.putText(frame, tag_text, (x1 + 5, max(14, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)


def draw_hud_overlay(frame: np.ndarray, fps: float, latency_ms: float) -> None:
    """Renders top-left HUD telemetry banner."""
    hud_bg = (15, 23, 42)
    cv2.rectangle(frame, (10, 10), (280, 75), hud_bg, -1)
    cv2.rectangle(frame, (10, 10), (280, 75), (51, 65, 85), 1)

    # Emerald pulsating indicator
    cv2.circle(frame, (25, 30), 6, (0, 230, 118), -1)
    cv2.putText(frame, "ROADVISION AI ACTIVE", (40, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (241, 245, 249), 1, cv2.LINE_AA)

    fps_text = f"FPS: {fps:.1f}  |  Latency: {latency_ms:.1f}ms"
    cv2.putText(frame, fps_text, (20, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (148, 163, 184), 1, cv2.LINE_AA)

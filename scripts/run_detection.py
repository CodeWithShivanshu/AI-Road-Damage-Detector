#!/usr/bin/env python3
"""
RoadVision AI - CLI Inference Runner
Runs pothole detection on images, videos, or cameras using the modular application framework.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from app.core.config import settings
from app.core.logging import get_logger
from app.inference.detector import InferenceEngine

logger = get_logger("cli")


def parse_args():
    parser = argparse.ArgumentParser(description="RoadVision AI - Pothole Detection CLI")
    parser.add_argument("--weights", type=str, default=str(settings.get_model_weights_path()),
                        help="Path to model weights (.pt)")
    parser.add_argument("--source", type=str, default=str(settings.SAMPLE_IMAGE_PATH),
                        help="Path to image, video file, or camera index (e.g. 0)")
    parser.add_argument("--conf", type=float, default=settings.CONF_THRESHOLD,
                        help="Confidence threshold (0.0 to 1.0)")
    parser.add_argument("--save", action="store_true", default=True,
                        help="Save output visualization")
    parser.add_argument("--output-dir", type=str, default=str(settings.RUNS_DIR / "cli_detect"),
                        help="Directory to save predictions")
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info(f"Initializing InferenceEngine with weights: {args.weights}")
    engine = InferenceEngine(weights_path=args.weights)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source = args.source
    if source.isdigit():
        source = int(source)

    # 1. Image inference
    if isinstance(source, str) and Path(source).is_file() and Path(source).suffix.lower() in [".jpg", ".jpeg", ".png"]:
        logger.info(f"Running detection on image: {source}")
        frame = cv2.imread(source)
        if frame is None:
            logger.error(f"Failed to read image at: {source}")
            sys.exit(1)

        annotated_frame, telemetry = engine.process_frame(frame, conf_thres=args.conf, track=False)
        potholes = telemetry["detections"]
        logger.info(f"Detections found: {len(potholes)}")
        for i, p in enumerate(potholes, 1):
            logger.info(f"  • Pothole #{i}: Severity={p['severity']}, Confidence={p['conf']*100:.1f}%, BBox={p['bbox']}")

        if args.save:
            save_path = out_dir / Path(source).name
            cv2.imwrite(str(save_path), annotated_frame)
            logger.info(f"Result saved to: {save_path}")

    # 2. Video / Camera inference
    else:
        logger.info(f"Opening video/stream source: {source}")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"Cannot open video source: {source}")
            sys.exit(1)

        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            annotated_frame, telemetry = engine.process_frame(frame, conf_thres=args.conf, track=True)
            frame_count += 1

            if frame_count % 30 == 0:
                logger.info(f"Processed frame #{frame_count} | FPS: {telemetry['fps']} | Total Unique Potholes: {telemetry['total_potholes']}")

        cap.release()
        logger.info(f"Finished processing {frame_count} frames. Total unique potholes: {engine.tracker.total_unique_count}")


if __name__ == "__main__":
    main()

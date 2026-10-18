# RoadVision AI - System Architecture & Technical Design

## 1. Overview
RoadVision AI is a modular, high-performance edge road damage detection platform. It decouples the core computer vision inference layer (built on Ultralytics YOLOv5) from high-level application logic (camera capture, tracking, centralized configuration, and web streaming).

---

## 2. Layered Architecture

```mermaid
graph TD
    subgraph Data Ingest Layer
        V1[Test Video Asset] --> CM[app.camera.CameraManager]
        V2[Local Webcam Device] --> CM
        V3[Android USB Camera Stream] --> CM
    end

    subgraph Core & Utility Layer
        CFG[app.core.config.Settings] --> IE[app.inference.InferenceEngine]
        CFG --> CM
        LOG[app.core.logging] --> IE
        LOG --> CM
    end

    subgraph AI Inference Layer
        CM -->|Raw BGR Frame| IE
        IE -->|DetectMultiBackend| YOLO[YOLOv5 Model: weights/pothole_best.pt]
        YOLO -->|Tensor Outputs| NMS[Non-Maximum Suppression]
        NMS -->|Bounding Boxes| PT[app.utils.tracking.PotholeTracker]
        PT -->|Unique Hazard ID & Severity| POST[app.inference.postprocess]
    end

    subgraph Presentation & API Layer
        POST -->|Annotated Frame + Telemetry| APP[FastAPI Service / Dashboard]
        POST -->|CLI Output| CLI[scripts/run_detection.py]
    end
```

---

## 3. Module Responsibilities

### `app/core/`
- **`config.py`**: Centralized, type-safe settings (`Settings` singleton) managing model paths, confidence thresholds, image sizes, and environment variable overrides (`CONF_THRESHOLD`, `DEVICE`, etc.).
- **`logging.py`**: Standardized logging with timestamps and log levels.

### `app/inference/`
- **`detector.py`**: `InferenceEngine` encapsulates model loading, letterboxing, warmup, batch formatting, and hardware execution (CPU/MPS/CUDA).
- **`postprocess.py`**: Handles bounding box rendering, corner accent markers, tag pills, and HUD telemetry overlays.

### `app/camera/`
- **`manager.py`**: `CameraManager` manages non-blocking threaded frame capture across video files, local webcams, and network/USB RTSP/HTTP streams.
- **`adb_helper.py`**: Manages USB port tunneling (`adb forward tcp:8080 tcp:8080`) to stream video over physical USB cable.

### `app/utils/`
- **`tracking.py`**: `PotholeTracker` tracks centroid trajectories across frames to ensure unique potholes are only counted once.
- **`general.py`**: Path validation, image integrity checks, and hazard severity classification (Critical, Moderate, Minor).

### `yolov5/`, `models/`, `utils/`
- Original, preserved YOLOv5 v6.1 implementation supporting legacy scripts (`train.py`, `val.py`, `detect.py`, `export.py`).

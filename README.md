
## 🏗️ Refactored Project Structure

```text
realv/
├── app/                            # Modular application layer
│   ├── core/                       # Centralized configuration and logging
│   │   ├── config.py               # Path resolutions & environment variables
│   │   └── logging.py              # Standardized structured logger
│   ├── inference/                  # Clean computer vision inference interface
│   │   ├── detector.py             # InferenceEngine wrapping YOLOv5
│   │   └── postprocess.py          # Bounding boxes, corner accents, and HUD overlays
│   ├── camera/                     # Video capture & camera interfaces
│   │   ├── manager.py              # Threaded CameraManager (Video/Webcam/USB)
│   │   └── adb_helper.py           # Android USB ADB port forwarder
│   └── utils/                      # Shared utilities
│       ├── general.py              # Path validators & severity categorizer
│       └── tracking.py             # PotholeTracker (cross-frame deduplication)
│
├── scripts/                        # Maintenance & execution scripts
│   └── run_detection.py            # Modular CLI inference script
│
├── tests/                          # Automated test suite (pytest)
│   ├── test_config.py              # Configuration & env var tests
│   ├── test_paths.py               # File presence & path validation tests
│   └── test_inference.py           # Model inference & tracking tests
│
├── docs/                           # Architecture & user guides
│   ├── architecture.md             # System design & data flow
│   └── usage_guide.md              # Detailed execution documentation
│
├── weights/                        # Model checkpoints directory
│   └── pothole_best.pt             # Trained YOLOv5 Pothole model weights
│
├── yolov5/                         # Original YOLOv5 configurations & assets
│   ├── data/                       # Dataset configs and sample images
│   ├── hyperparameters/            # Hyperparameter configs (hyp.yaml, opt.yaml)
│   └── models/                     # Model architecture YAMLs (yolov5l.yaml)
│
├── detect.py                       # Original YOLOv5 detection entry point (preserved)
├── train.py                        # Original YOLOv5 training script (preserved)
├── val.py                          # Original YOLOv5 validation script (preserved)
├── export.py                       # Original YOLOv5 export script (preserved)
├── run.py                          # Web dashboard launcher
├── requirements.txt                # Unified Python dependencies
├── .env.example                    # Template environment variables
└── .gitignore                      # Git exclusion rules
```

---


## 📊 Dataset & Original Training Results

In this Project I have used custom labelled dataset with some images from google to make the learning process more complex.

### Training Dataset Sample
<table border="0">
<tr>
    <td><img src="./yolov5/data/images/training data.jpg" width="100%" /></td>
    <td><img src="./yolov5/data/images/training data2.jpg" width="100%" /></td>
</tr>
</table>

### Training Results
<p align="left"><img width="800" src="./yolov5/data/results/results.png" align="center"></p>

---

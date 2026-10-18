# RoadVision AI - Usage & Execution Guide

This guide details all execution modes for the RoadVision AI platform.

---

## 1. Setup & Environment
Ensure you have activated the Python virtual environment:

```bash
cd /Users/souravkumar/Desktop/realv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Running Automated Tests
Run the automated test suite verifying configuration loading, path validation, and model inference interfaces:

```bash
pytest tests/ -v
```

---

## 3. Running Inference

### Mode A: Modular CLI Runner (Recommended for Scripts)
Using the clean application interface:

```bash
# On default sample image
python scripts/run_detection.py

# On custom image or video
python scripts/run_detection.py --source yolov5/data/images/img1.jpg --conf 0.30

# On test video footage
python scripts/run_detection.py --source data/videos/road_test.mp4
```

### Mode B: Legacy YOLOv5 Detection Script (Preserved)
The original Ultralytics YOLOv5 detection entry point remains fully functional:

```bash
python detect.py --weights weights/pothole_best.pt --source yolov5/data/images/img.jpg
```

---

## 4. Running the Web Platform & Live Dashboard

Launch the FastAPI streaming backend and web dashboard (served with zero-auth direct access):

```bash
python run.py
```
Open **`http://localhost:8000`** in any web browser.

---

## 5. Training and Validation Entry Points (Preserved)

### Validation
To evaluate model accuracy on a dataset:
```bash
python val.py --data yolov5/data/pothole_detector.yaml --weights weights/pothole_best.pt --img 640
```

### Training
To train or fine-tune weights on custom data:
```bash
python train.py --img 640 --batch 16 --epochs 50 --data yolov5/data/pothole_detector.yaml --weights yolov5s.pt
```

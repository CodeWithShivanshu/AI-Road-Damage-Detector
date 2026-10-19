import os
import cv2
import time
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.engine import InferenceEngine
from backend.camera import CameraManager, forward_adb_usb_port, get_adb_status
from backend.location import gps_tracker
from backend.database import (
    create_inspection_session,
    end_inspection_session,
    get_recent_detections,
    get_all_inspections,
    get_map_route_detections
)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
DATA_DIR = ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RoadVision AI - Autonomous Road Damage Detection")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
engine: Optional[InferenceEngine] = None
camera: Optional[CameraManager] = None
current_inspection_id: int = 1
active_conf_threshold: float = 0.25
latest_telemetry = {
    "fps": 0.0,
    "inference_ms": 0.0,
    "current_frame_detections": 0,
    "total_potholes": 0,
    "critical_count": 0,
    "moderate_count": 0,
    "minor_count": 0,
    "road_score": 100.0,
    "detections": []
}


@app.on_event("startup")
def startup_event():
    global engine, camera, current_inspection_id
    print("[Server] Initializing RoadVision AI Engine...")
    engine = InferenceEngine()
    camera = CameraManager(default_source="test_video")
    current_inspection_id = create_inspection_session(source_type="test_video")
    print(f"[Server] Ready! Initial session #{current_inspection_id} created.")


class SourceChangeRequest(BaseModel):
    source_type: str  # 'test_video', 'webcam', 'usb_phone', 'custom_file'
    target: Optional[str] = None


class SettingsRequest(BaseModel):
    conf_threshold: Optional[float] = None


class DeviceLocationUpdate(BaseModel):
    lat: float
    lng: float
    heading: Optional[float] = None
    speed: Optional[float] = None


class SetAnchorRequest(BaseModel):
    lat: float
    lng: float
    location_name: Optional[str] = ""


@app.get("/api/status")
def get_status():
    global camera, engine, active_conf_threshold
    return {
        "status": "online",
        "model_loaded": engine.weights_path.name if engine else "None",
        "classes": engine.names if engine else [],
        "source_type": camera.source_type if camera else "None",
        "source_path": camera.source_path if camera else "None",
        "is_camera_connected": camera.is_connected if camera else False,
        "conf_threshold": active_conf_threshold,
        "active_session_id": current_inspection_id
    }


@app.get("/api/telemetry")
def get_telemetry():
    global latest_telemetry
    return latest_telemetry


def generate_frames():
    """Generates continuous MJPEG stream with detection annotations and telemetry update."""
    global camera, engine, latest_telemetry, active_conf_threshold, current_inspection_id
    while True:
        if not camera or not engine:
            time.sleep(0.05)
            continue

        raw_frame = camera.get_latest_frame()
        if raw_frame is None:
            time.sleep(0.04)
            continue

        # Run AI detection and overlay HUD
        annotated_frame, telemetry = engine.process_frame(
            raw_frame,
            conf_thres=active_conf_threshold,
            inspection_id=current_inspection_id
        )
        latest_telemetry = telemetry

        # Encode frame as JPEG
        ret, buffer = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")


@app.get("/api/stream")
def video_stream():
    """Live Video Stream with bounding boxes and HUD."""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/api/source/change")
def change_source(req: SourceChangeRequest):
    global camera, engine, current_inspection_id
    if not camera:
        raise HTTPException(status_code=500, detail="Camera manager uninitialized")

    # End previous session
    if engine:
        end_inspection_session(current_inspection_id, {
            "total_potholes": engine.tracker.total_unique_count,
            "critical_count": engine.tracker.critical_count,
            "moderate_count": engine.tracker.moderate_count,
            "minor_count": engine.tracker.minor_count,
            "road_score": latest_telemetry.get("road_score", 100.0)
        })
        engine.tracker.reset()

    # Start new session
    current_inspection_id = create_inspection_session(source_type=req.source_type)
    camera.set_source(req.source_type, req.target)

    return {
        "status": "success",
        "source_type": camera.source_type,
        "source_path": camera.source_path,
        "new_session_id": current_inspection_id
    }


@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    global active_conf_threshold
    if req.conf_threshold is not None:
        active_conf_threshold = max(0.05, min(0.95, req.conf_threshold))
    return {"status": "success", "conf_threshold": active_conf_threshold}


@app.post("/api/session/reset")
def reset_session():
    global engine, current_inspection_id, camera
    if engine:
        end_inspection_session(current_inspection_id, {
            "total_potholes": engine.tracker.total_unique_count,
            "critical_count": engine.tracker.critical_count,
            "moderate_count": engine.tracker.moderate_count,
            "minor_count": engine.tracker.minor_count,
            "road_score": latest_telemetry.get("road_score", 100.0)
        })
        engine.tracker.reset()

    source = camera.source_type if camera else "Manual Reset"
    current_inspection_id = create_inspection_session(source_type=source)
    return {"status": "success", "new_session_id": current_inspection_id}


@app.post("/api/adb/connect")
def connect_adb(local_port: int = 8080, phone_port: int = 8080):
    success, message = forward_adb_usb_port(local_port=local_port, phone_port=phone_port)
    return {"success": success, "message": message}


@app.get("/api/adb/status")
def get_adb_info():
    return get_adb_status()


@app.get("/api/detections/recent")
def get_detections():
    return get_recent_detections(limit=30)


@app.get("/api/inspections/history")
def get_inspections():
    return get_all_inspections(limit=15)


@app.get("/api/location/current")
def get_current_location():
    return gps_tracker.get_current_location()


@app.post("/api/location/update")
def update_location(req: DeviceLocationUpdate):
    return gps_tracker.update_device_location(req.lat, req.lng, req.heading, req.speed)


@app.post("/api/location/set_anchor")
def set_location_anchor(req: SetAnchorRequest):
    return gps_tracker.set_anchor(req.lat, req.lng, req.location_name or "")


@app.get("/api/location/search")
def search_location(q: str):
    results = gps_tracker.search_places(q)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/map/data")
def get_map_data(session_only: bool = False):
    global current_inspection_id
    markers = get_map_route_detections(inspection_id=current_inspection_id)
    if not markers and not session_only:
        markers = get_map_route_detections(inspection_id=None)

    cur_loc = gps_tracker.get_current_location()
    route = gps_tracker.get_route_points()

    return {
        "current_location": cur_loc,
        "route": route,
        "markers": markers,
        "total_markers": len(markers),
        "active_session_id": current_inspection_id
    }


@app.post("/api/upload_video")
async def upload_custom_video(file: UploadFile = File(...)):
    global camera
    target_path = UPLOADS_DIR / f"upload_{int(time.time())}_{file.filename}"
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if camera:
        camera.set_source("custom_file", str(target_path))

    return {"status": "success", "file_path": str(target_path)}


# Mount static snapshots folder
app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")

# Mount frontend static assets
if (FRONTEND_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


@app.get("/")
def serve_dashboard():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "RoadVision AI Backend Running. Dashboard file missing."})

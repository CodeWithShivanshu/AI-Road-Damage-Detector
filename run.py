#!/usr/bin/env python3
"""
RoadVision AI - Main Platform Launcher
Launches the full-stack road damage detection web dashboard & inference backend.
"""

import os
import sys
from pathlib import Path

# Add project root to Python module path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Automatically switch to project .venv if not running inside it
venv_python = ROOT / ".venv" / "bin" / "python"
if venv_python.exists():
    real_venv_prefix = str((ROOT / ".venv").resolve())
    current_prefix = str(Path(sys.prefix).resolve())
    if current_prefix != real_venv_prefix and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)

import uvicorn

if __name__ == "__main__":
    print("\n" + "="*65)
    print(" 🚀 ROADVISION AI - AUTONOMOUS ROAD DAMAGE DETECTION PLATFORM")
    print("="*65)
    print(" • Model:      YOLOv5 Pothole Detector (weights/pothole_best.pt)")
    print(" • Dashboard:  http://localhost:8000")
    print(" • Direct UI:  Zero login required (direct dashboard landing)")
    print(" • Video Feed: Test Video / Webcam / USB Android Phone")
    print("="*65 + "\n")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

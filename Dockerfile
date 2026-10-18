# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install required system packages for OpenCV, Git, curl, and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install setuptools<70 (provides pkg_resources needed by YOLOv5 v6.1)
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir "setuptools<70"

# Pre-download Arial font to avoid HTTP 308 redirect error during font setup
RUN mkdir -p /root/.config/Ultralytics && \
    curl -sSL -o /root/.config/Ultralytics/Arial.ttf https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.ttf

# Install lightweight CPU-only PyTorch (~150MB instead of 5GB of CUDA libraries)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy and install remaining dependencies (excluding torch and ffmpeg so it stays lightweight)
COPY requirements.txt .
RUN grep -Ev "^ffmpeg|^torch|^torchvision" requirements.txt > /tmp/req.txt && \
    pip install --no-cache-dir -r /tmp/req.txt && \
    rm /tmp/req.txt

# Ensure setuptools<70 remains active
RUN pip install --no-cache-dir "setuptools<70"

# Copy project files (includes local models, utils, export.py, configs)
COPY . /app

# Ensure output directories exist
RUN mkdir -p /app/runs/detect /app/weights

# Default execution: run detection on sample image
CMD ["python", "detect.py", "--weights", "yolov5s.pt", "--source", "yolov5/data/images/img.jpg", "--project", "runs/detect", "--name", "exp"]

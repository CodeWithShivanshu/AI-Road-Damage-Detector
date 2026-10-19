# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Prevent interactive prompts during package installation and unbuffer python output
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install required system packages for OpenCV, Git, ffmpeg, ADB, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    adb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip, wheel, and pin setuptools (required by YOLOv5 v6.1 pkg_resources)
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir "setuptools<70"

# Pre-download Arial font to avoid HTTP 308 redirect error during font setup in YOLOv5
RUN mkdir -p /root/.config/Ultralytics && \
    curl -sSL -o /root/.config/Ultralytics/Arial.ttf https://github.com/ultralytics/assets/releases/download/v0.0.0/Arial.ttf

# Install lightweight CPU-only PyTorch and torchvision (~150MB instead of multi-gigabyte CUDA)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining python dependencies
COPY requirements.txt .
RUN grep -Ev "^ffmpeg|^torch|^torchvision" requirements.txt > /tmp/req.txt && \
    pip install --no-cache-dir -r /tmp/req.txt && \
    pip install --no-cache-dir "setuptools<70" && \
    rm /tmp/req.txt

# Copy project files into container
COPY . /app

# Ensure output and data storage directories exist
RUN mkdir -p /app/data/uploads /app/data/snapshots /app/runs /app/weights

# Expose port 8000 for FastAPI / RoadVision AI dashboard
EXPOSE 8000

# Health check to ensure the application is live and serving telemetry
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/telemetry || exit 1

# Launch the RoadVision AI web platform and inference server
CMD ["python", "run.py"]

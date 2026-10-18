/**
 * ROADVISION AI - DASHBOARD LOGIC & TELEMETRY CLIENT
 */

const API = {
  STATUS: '/api/status',
  TELEMETRY: '/api/telemetry',
  CHANGE_SOURCE: '/api/source/change',
  SETTINGS: '/api/settings',
  RESET: '/api/session/reset',
  RECENT_DETECTIONS: '/api/detections/recent',
  ADB_CONNECT: '/api/adb/connect',
  UPLOAD_VIDEO: '/api/upload_video'
};

// DOM Elements
const elTotalPotholes = document.getElementById('stat-total-potholes');
const elFps = document.getElementById('stat-fps');
const elLatency = document.getElementById('stat-latency');
const elRoadScore = document.getElementById('stat-road-score');
const elCurrentDetections = document.getElementById('stat-current-detections');

const elCountCritical = document.getElementById('count-critical');
const elCountModerate = document.getElementById('count-moderate');
const elCountMinor = document.getElementById('count-minor');

const elFeedList = document.getElementById('detections-feed-list');
const elActiveModel = document.getElementById('active-model-name');
const elActiveSource = document.getElementById('active-source-name');

const elSliderConf = document.getElementById('conf-slider');
const elConfValue = document.getElementById('conf-value-display');

const elBtnReset = document.getElementById('btn-reset-session');
const elBtnExport = document.getElementById('btn-export-csv');

const elModalUsb = document.getElementById('usb-camera-modal');
const elBtnCloseModal = document.getElementById('btn-close-modal');
const elBtnAdbConnect = document.getElementById('btn-adb-connect');
const elAdbStatusText = document.getElementById('adb-status-text');
const elInputPhoneUrl = document.getElementById('input-phone-url');
const elBtnApplyPhoneStream = document.getElementById('btn-apply-phone-stream');

const elFileInput = document.getElementById('custom-video-input');
const elBtnUpload = document.getElementById('btn-upload-video');

let knownDetections = new Set();

// ============================================================================
// TELEMETRY POLLING
// ============================================================================
async function updateTelemetry() {
  try {
    const res = await fetch(API.TELEMETRY);
    if (!res.ok) return;
    const data = await res.json();

    if (elTotalPotholes) elTotalPotholes.textContent = data.total_potholes;
    if (elFps) elFps.textContent = `${data.fps}`;
    if (elLatency) elLatency.textContent = `${data.inference_ms}ms`;
    if (elRoadScore) elRoadScore.textContent = `${data.road_score}%`;
    if (elCurrentDetections) elCurrentDetections.textContent = data.current_frame_detections;

    if (elCountCritical) elCountCritical.textContent = data.critical_count;
    if (elCountModerate) elCountModerate.textContent = data.moderate_count;
    if (elCountMinor) elCountMinor.textContent = data.minor_count;

    // Update road score color dynamically
    if (elRoadScore) {
      if (data.road_score > 80) {
        elRoadScore.style.color = '#10b981'; // Green
      } else if (data.road_score > 60) {
        elRoadScore.style.color = '#f59e0b'; // Amber
      } else {
        elRoadScore.style.color = '#ef4444'; // Red
      }
    }
  } catch (err) {
    console.debug('Telemetry poll error:', err);
  }
}

// ============================================================================
// SYSTEM STATUS POLLING
// ============================================================================
async function updateStatus() {
  try {
    const res = await fetch(API.STATUS);
    if (!res.ok) return;
    const data = await res.json();

    if (elActiveModel) elActiveModel.textContent = data.model_loaded;
    if (elActiveSource) elActiveSource.textContent = data.source_type.replace('_', ' ').toUpperCase();
  } catch (err) {
    console.debug('Status poll error:', err);
  }
}

// ============================================================================
// RECENT DETECTIONS FEED
// ============================================================================
async function updateDetectionsFeed() {
  try {
    const res = await fetch(API.RECENT_DETECTIONS);
    if (!res.ok) return;
    const detections = await res.json();

    if (!elFeedList) return;

    if (detections.length === 0) {
      elFeedList.innerHTML = `
        <div style="text-align: center; padding: 32px 16px; color: var(--text-muted); font-size: 0.85rem;">
          No potholes detected yet in this inspection session.
        </div>`;
      return;
    }

    let html = '';
    detections.forEach(det => {
      const sevClass = det.severity.toLowerCase();
      const snapImg = det.snapshot_path 
        ? `<img src="${det.snapshot_path}" alt="Pothole crop" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'54\\' height=\\'54\\' fill=\\'%231e293b\\'><rect width=\\'54\\' height=\\'54\\'/></svg>'">` 
        : `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;font-size:10px;">CROP</div>`;

      html += `
        <div class="feed-item" id="det-item-${det.id}">
          <div class="feed-thumb">
            ${snapImg}
          </div>
          <div class="feed-info">
            <div class="feed-item-header">
              <span class="feed-tag">Pothole #${det.id}</span>
              <span class="badge-severity ${sevClass}">${det.severity}</span>
            </div>
            <div class="feed-item-meta">
              <span>Confidence: ${Math.round(det.confidence * 100)}%</span>
              <span>•</span>
              <span>${det.timestamp.split(' ')[1] || det.timestamp}</span>
            </div>
          </div>
        </div>
      `;
    });

    elFeedList.innerHTML = html;
  } catch (err) {
    console.debug('Detections poll error:', err);
  }
}

// ============================================================================
// SOURCE SWITCHING
// ============================================================================
async function switchSource(sourceType, target = null) {
  try {
    const res = await fetch(API.CHANGE_SOURCE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: sourceType, target: target })
    });
    const data = await res.json();
    if (data.status === 'success') {
      document.querySelectorAll('.btn-source').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById(`btn-src-${sourceType}`);
      if (activeBtn) activeBtn.classList.add('active');

      // Refresh stream image src to prevent freezing
      const streamImg = document.getElementById('live-stream-img');
      if (streamImg) {
        streamImg.src = '/api/stream?t=' + Date.now();
      }
      updateStatus();
    }
  } catch (err) {
    console.error('Error switching source:', err);
  }
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  // Source selector buttons
  const btnSrcTest = document.getElementById('btn-src-test_video');
  const btnSrcWebcam = document.getElementById('btn-src-webcam');
  const btnSrcUsb = document.getElementById('btn-src-usb_phone');

  if (btnSrcTest) btnSrcTest.addEventListener('click', () => switchSource('test_video'));
  if (btnSrcWebcam) btnSrcWebcam.addEventListener('click', () => switchSource('webcam', '0'));
  
  if (btnSrcUsb) {
    btnSrcUsb.addEventListener('click', () => {
      if (elModalUsb) elModalUsb.classList.add('show');
    });
  }

  if (elBtnCloseModal && elModalUsb) {
    elBtnCloseModal.addEventListener('click', () => {
      elModalUsb.classList.remove('show');
    });
  }

  // ADB Auto-Connect
  if (elBtnAdbConnect) {
    elBtnAdbConnect.addEventListener('click', async () => {
      if (elAdbStatusText) elAdbStatusText.textContent = 'Executing ADB port forwarding...';
      try {
        const res = await fetch(API.ADB_CONNECT, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          if (elAdbStatusText) {
            elAdbStatusText.style.color = '#10b981';
            elAdbStatusText.textContent = `✓ ${data.message}`;
          }
          // Automatically switch to USB stream
          switchSource('usb_phone', 'http://127.0.0.1:8080/video');
          setTimeout(() => elModalUsb.classList.remove('show'), 1200);
        } else {
          if (elAdbStatusText) {
            elAdbStatusText.style.color = '#f59e0b';
            elAdbStatusText.textContent = `Notice: ${data.message}`;
          }
        }
      } catch (err) {
        if (elAdbStatusText) elAdbStatusText.textContent = 'Error connecting to ADB.';
      }
    });
  }

  // Apply Phone IP Stream URL
  if (elBtnApplyPhoneStream && elInputPhoneUrl) {
    elBtnApplyPhoneStream.addEventListener('click', () => {
      const url = elInputPhoneUrl.value.trim() || 'http://127.0.0.1:8080/video';
      switchSource('usb_phone', url);
      if (elModalUsb) elModalUsb.classList.remove('show');
    });
  }

  // Upload Custom Dashcam Video
  if (elBtnUpload && elFileInput) {
    elBtnUpload.addEventListener('click', () => elFileInput.click());
    elFileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      try {
        elBtnUpload.textContent = 'Uploading...';
        const res = await fetch(API.UPLOAD_VIDEO, {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.status === 'success') {
          elBtnUpload.textContent = 'Upload Video';
          const streamImg = document.getElementById('live-stream-img');
          if (streamImg) streamImg.src = '/api/stream?t=' + Date.now();
          updateStatus();
        }
      } catch (err) {
        alert('Upload failed: ' + err.message);
        elBtnUpload.textContent = 'Upload Video';
      }
    });
  }

  // Confidence Threshold Slider
  if (elSliderConf && elConfValue) {
    elSliderConf.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      elConfValue.textContent = `${Math.round(val * 100)}%`;
    });

    elSliderConf.addEventListener('change', async (e) => {
      const val = parseFloat(e.target.value);
      try {
        await fetch(API.SETTINGS, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ conf_threshold: val })
        });
      } catch (err) {
        console.error('Settings update error:', err);
      }
    });
  }

  // Reset Session
  if (elBtnReset) {
    elBtnReset.addEventListener('click', async () => {
      if (confirm('Reset current inspection counters and start a new session?')) {
        await fetch(API.RESET, { method: 'POST' });
        updateTelemetry();
        updateDetectionsFeed();
      }
    });
  }

  // Export CSV
  if (elBtnExport) {
    elBtnExport.addEventListener('click', async () => {
      try {
        const res = await fetch(API.RECENT_DETECTIONS);
        const data = await res.json();
        if (data.length === 0) {
          alert('No detections logged to export.');
          return;
        }

        let csv = 'Detection_ID,Timestamp,Severity,Confidence,BBox_X1,BBox_Y1,BBox_X2,BBox_Y2,Snapshot\n';
        data.forEach(d => {
          const b = d.bbox || [0, 0, 0, 0];
          csv += `${d.id},"${d.timestamp}",${d.severity},${d.confidence},${b[0]},${b[1]},${b[2]},${b[3]},"${d.snapshot_path}"\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `roadvision_inspection_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        console.error('Export error:', err);
      }
    });
  }

  // Start background update loops
  updateStatus();
  updateTelemetry();
  updateDetectionsFeed();

  setInterval(updateTelemetry, 350);
  setInterval(updateDetectionsFeed, 1800);
});

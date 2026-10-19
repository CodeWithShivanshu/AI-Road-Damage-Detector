/**
 * ROADVISION AI - DASHBOARD LOGIC, TELEMETRY & INTERACTIVE ROUTE MAP
 * High-performance dark UI with OpenStreetMap Cyber-Dark, Esri Satellite,
 * Clair Google Maps search integration, and real-time pothole photo telemetry.
 */

const API = {
  STATUS: '/api/status',
  TELEMETRY: '/api/telemetry',
  CHANGE_SOURCE: '/api/source/change',
  SETTINGS: '/api/settings',
  RESET: '/api/session/reset',
  RECENT_DETECTIONS: '/api/detections/recent',
  ADB_CONNECT: '/api/adb/connect',
  ADB_STATUS: '/api/adb/status',
  UPLOAD_VIDEO: '/api/upload_video',
  MAP_DATA: '/api/map/data',
  LOCATION_SEARCH: '/api/location/search',
  SET_ANCHOR: '/api/location/set_anchor',
  UPDATE_LOCATION: '/api/location/update'
};

// DOM Elements: Header & Top Telemetry
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

// Camera & USB Modal Elements
const elModalUsb = document.getElementById('usb-camera-modal');
const elBtnCloseModal = document.getElementById('btn-close-modal');
const elBtnAdbConnect = document.getElementById('btn-adb-connect');
const elAdbStatusText = document.getElementById('adb-status-text');
const elInputPhoneUrl = document.getElementById('input-phone-url');
const elBtnApplyPhoneStream = document.getElementById('btn-apply-phone-stream');

const elFileInput = document.getElementById('custom-video-input');
const elBtnUpload = document.getElementById('btn-upload-video');

// View Switcher Elements
const btnTabVision = document.getElementById('tab-btn-vision');
const btnTabMap = document.getElementById('tab-btn-map');
const btnTabSplit = document.getElementById('tab-btn-split');

// Map Toolbar & Ribbon Elements
const elMapSearchInput = document.getElementById('map-search-input');
const elBtnMapSearch = document.getElementById('btn-map-search');
const elSearchResultsDropdown = document.getElementById('search-results-dropdown');
const elBtnDeviceGps = document.getElementById('btn-device-gps');
const elRouteDistancePill = document.getElementById('route-distance-pill');
const elGpsStatusPill = document.getElementById('gps-status-pill');
const elRouteStartName = document.getElementById('route-start-name');
const elRouteCurrentCoords = document.getElementById('route-current-coords');
const elRouteTotalHazards = document.getElementById('route-total-hazards');
const elBtnCenterMap = document.getElementById('btn-center-map');
const elBtnFitHazards = document.getElementById('btn-fit-hazards');
const elBtnClearRoute = document.getElementById('btn-clear-route');

// Lightbox Modal Elements
const elLightboxModal = document.getElementById('photo-lightbox-modal');
const elLightboxImg = document.getElementById('lightbox-img');
const elLightboxCaption = document.getElementById('lightbox-caption');
const elLightboxTitle = document.getElementById('lightbox-title');
const elBtnCloseLightbox = document.getElementById('btn-close-lightbox');

// Map State
let leafletMap = null;
let routePolyline = null;
let vehicleMarker = null;
let markerLayers = new Map(); // id -> L.Marker
let currentViewMode = 'vision'; // 'vision' | 'map' | 'split'
let deviceGpsWatchId = null;
let isUserPanned = false;
let activeSeverityFilter = 'all'; // 'all' | 'Critical' | 'Moderate' | 'Minor'
let cachedDetections = [];

// Free, reliable tile providers without API keys or watermarks
const tileLayers = {
  dark: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    className: 'cyber-dark-tiles',
    attribution: '&copy; OpenStreetMap contributors'
  }),
  satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: '&copy; Esri &mdash; Earthstar Geographics'
  }),
  streets: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: '&copy; Esri &mdash; StreetMap Community'
  })
};
let activeLayerName = 'dark';

// ============================================================================
// 1. TELEMETRY POLLING
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

    // Update filter counts
    const filterAll = document.getElementById('filter-count-all');
    const filterCrit = document.getElementById('filter-count-crit');
    const filterMod = document.getElementById('filter-count-mod');
    const filterMin = document.getElementById('filter-count-min');
    if (filterAll) filterAll.textContent = data.total_potholes;
    if (filterCrit) filterCrit.textContent = data.critical_count;
    if (filterMod) filterMod.textContent = data.moderate_count;
    if (filterMin) filterMin.textContent = data.minor_count;

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
// 2. SYSTEM STATUS POLLING
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
// 3. RECENT DETECTIONS FEED
// ============================================================================
async function updateDetectionsFeed() {
  try {
    const res = await fetch(API.RECENT_DETECTIONS);
    if (!res.ok) return;
    cachedDetections = await res.json();

    renderDetectionsFeed();
  } catch (err) {
    console.debug('Detections poll error:', err);
  }
}

function renderDetectionsFeed() {
  if (!elFeedList) return;

  const filtered = activeSeverityFilter === 'all'
    ? cachedDetections
    : cachedDetections.filter(d => (d.severity || '').toLowerCase() === activeSeverityFilter.toLowerCase());

  if (filtered.length === 0) {
    elFeedList.innerHTML = `
      <div style="text-align: center; padding: 36px 16px; color: var(--text-muted); font-size: 0.85rem;">
        ${activeSeverityFilter === 'all' ? 'No potholes detected yet in this inspection session.' : `No ${activeSeverityFilter} potholes found.`}
      </div>`;
    return;
  }

  let html = '';
  filtered.forEach(det => {
    const sevClass = (det.severity || 'Minor').toLowerCase();
    const snapImg = det.snapshot_path 
      ? `<img src="${det.snapshot_path}" alt="Pothole crop" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'54\\' height=\\'54\\' fill=\\'%231e293b\\'><rect width=\\'54\\' height=\\'54\\'/></svg>'">` 
      : `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;font-size:10px;">CROP</div>`;

    html += `
      <div class="feed-item" id="det-item-${det.id}" onclick="focusOnHazard(${det.id}, ${det.lat || 0}, ${det.lng || 0})">
        <div class="feed-thumb" title="Click to focus map and view snapshot">
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
          ${det.lat && det.lng ? `
            <div style="font-size: 0.72rem; color: var(--accent-cyan); font-family: var(--font-mono); margin-top: 2px;">
              📍 ${det.lat.toFixed(4)}, ${det.lng.toFixed(4)} <span style="color:var(--text-muted);">(click to focus)</span>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  });

  elFeedList.innerHTML = html;
}

window.focusOnHazard = function(hazardId, lat, lng) {
  if (!leafletMap || !lat || !lng) return;
  isUserPanned = true;
  leafletMap.flyTo([lat, lng], 17, { animate: true, duration: 0.8 });
  const marker = markerLayers.get(hazardId);
  if (marker) {
    marker.openPopup();
  }
  document.querySelectorAll('.feed-item').forEach(el => el.classList.remove('selected'));
  const itemEl = document.getElementById(`det-item-${hazardId}`);
  if (itemEl) itemEl.classList.add('selected');
};

// ============================================================================
// 4. INTERACTIVE ROUTE & DAMAGE MAP (LEAFLET + CLAIR GOOGLE MAPS)
// ============================================================================
function initDamageMap() {
  const mapElement = document.getElementById('damageMap');
  if (!mapElement || leafletMap) return;

  // Initialize Leaflet map
  leafletMap = L.map('damageMap', {
    zoomControl: true,
    attributionControl: false
  }).setView([28.6139, 77.2090], 16);

  // Set default tile layer (Cyber Dark Mode OSM - free, fast, no watermark)
  tileLayers.dark.addTo(leafletMap);

  // Layer Switcher Buttons
  document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const layerKey = btn.getAttribute('data-layer');
      switchMapLayer(layerKey);
    });
  });

  // Route Polyline ("Kaha se Kaha tak" path)
  routePolyline = L.polyline([], {
    color: '#06b6d4',
    weight: 4.5,
    opacity: 0.85,
    lineJoin: 'round',
    dashArray: null
  }).addTo(leafletMap);

  // Vehicle Pulsing Indicator Marker
  const vehicleIcon = L.divIcon({
    className: 'custom-vehicle-div-icon',
    html: `
      <div class="vehicle-marker-icon">
        <div class="vehicle-pulse-ring"></div>
        <div class="vehicle-dot"></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });

  vehicleMarker = L.marker([28.6139, 77.2090], {
    icon: vehicleIcon,
    zIndexOffset: 1000
  }).addTo(leafletMap);

  leafletMap.on('dragstart', () => {
    isUserPanned = true;
  });
}

function switchMapLayer(layerName) {
  if (!leafletMap || !tileLayers[layerName]) return;
  Object.values(tileLayers).forEach(layer => {
    if (leafletMap.hasLayer(layer)) {
      leafletMap.removeLayer(layer);
    }
  });
  tileLayers[layerName].addTo(leafletMap);
  tileLayers[layerName].bringToBack();
  activeLayerName = layerName;

  document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-layer') === layerName);
  });
}

function calculatePathDistanceKm(coords) {
  if (coords.length < 2) return 0.0;
  let totalMeters = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const lat1 = coords[i][0] * Math.PI / 180;
    const lat2 = coords[i+1][0] * Math.PI / 180;
    const dLat = (coords[i+1][0] - coords[i][0]) * Math.PI / 180;
    const dLon = (coords[i+1][1] - coords[i][1]) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    totalMeters += 6371000 * c;
  }
  return totalMeters / 1000.0;
}

function fitAllHazards() {
  if (!leafletMap) return;
  const allPoints = [];
  if (vehicleMarker) allPoints.push(vehicleMarker.getLatLng());
  markerLayers.forEach(marker => allPoints.push(marker.getLatLng()));
  if (allPoints.length > 0) {
    const bounds = L.latLngBounds(allPoints);
    leafletMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 17 });
    isUserPanned = true;
  }
}

async function updateMapTelemetry() {
  if (!leafletMap) return;

  try {
    const res = await fetch(API.MAP_DATA);
    if (!res.ok) return;
    const data = await res.json();

    const cur = data.current_location;
    if (cur && cur.lat && cur.lng) {
      // Update vehicle marker
      vehicleMarker.setLatLng([cur.lat, cur.lng]);

      // If user hasn't manually panned away, smoothly follow vehicle
      if (!isUserPanned) {
        leafletMap.panTo([cur.lat, cur.lng], { animate: true, duration: 0.5 });
      }

      // Update current coordinates banner
      if (elRouteCurrentCoords) {
        elRouteCurrentCoords.textContent = `${cur.lat.toFixed(4)}° N, ${cur.lng.toFixed(4)}° E`;
      }
      if (elRouteStartName && cur.location_name) {
        elRouteStartName.textContent = cur.location_name;
      }
      if (elGpsStatusPill) {
        if (cur.is_live_device) {
          elGpsStatusPill.textContent = '📡 GPS: LIVE DEVICE';
          elGpsStatusPill.className = 'hud-pill success';
        } else {
          elGpsStatusPill.textContent = `📡 GPS: SIMULATED (${cur.speed_kmh} KM/H)`;
          elGpsStatusPill.className = 'hud-pill';
        }
      }
    }

    // Update Route Polyline
    if (data.route && data.route.length > 0) {
      const latlngs = data.route.map(pt => [pt.lat, pt.lng]);
      routePolyline.setLatLngs(latlngs);

      const distanceKm = calculatePathDistanceKm(latlngs);
      if (elRouteDistancePill) {
        elRouteDistancePill.textContent = `${distanceKm.toFixed(2)} KM TRAVELED`;
      }
    }

    // Update Damage Detected Markers along Route
    if (data.markers && Array.isArray(data.markers)) {
      if (elRouteTotalHazards) {
        elRouteTotalHazards.textContent = `${data.markers.length} Hazards Detected`;
      }

      data.markers.forEach(m => {
        if (markerLayers.has(m.id)) return; // already rendered

        const sev = m.severity || 'Moderate';
        let pinColor = '#f59e0b';
        if (sev === 'Critical') pinColor = '#ef4444';
        if (sev === 'Minor') pinColor = '#06b6d4';

        const customPinIcon = L.divIcon({
          className: 'custom-hazard-pin',
          html: `
            <div class="hazard-marker-wrapper" id="map-pin-${m.id}">
              ${sev === 'Critical' ? '<div class="hazard-pulse-ring critical"></div>' : ''}
              <svg class="hazard-marker-pin" viewBox="0 0 28 36" fill="none">
                <path d="M14 0C6.268 0 0 6.268 0 14c0 10.5 14 22 14 22s14-11.5 14-22c0-7.732-6.268-14-14-14z" fill="${pinColor}" stroke="#ffffff" stroke-width="1.5"/>
                <circle cx="14" cy="13" r="5" fill="#0b1220"/>
                <circle cx="14" cy="13" r="2.5" fill="#ffffff"/>
              </svg>
            </div>
          `,
          iconSize: [28, 36],
          iconAnchor: [14, 36],
          popupAnchor: [0, -36]
        });

        const marker = L.marker([m.lat, m.lng], { icon: customPinIcon }).addTo(leafletMap);

        // Build interactive popup with live photo snapshot
        const snapHtml = m.snapshot_path ? `
          <div class="popup-snapshot-container" onclick="openLightbox('${m.snapshot_path}', 'Hazard #${m.id} - ${sev} (${Math.round(m.confidence * 100)}%)')">
            <img src="${m.snapshot_path}" class="popup-snapshot-img" alt="Damage Snapshot">
          </div>
        ` : '';

        const popupHtml = `
          <div class="map-hazard-popup">
            <div class="popup-header">
              <span class="popup-title">Pothole #${m.id}</span>
              <span class="badge-severity ${sev.toLowerCase()}">${sev}</span>
            </div>
            ${snapHtml}
            <div class="popup-meta">
              <div><strong>GPS:</strong> ${m.lat.toFixed(5)}°, ${m.lng.toFixed(5)}°</div>
              <div><strong>Confidence:</strong> ${Math.round(m.confidence * 100)}%</div>
              <div><strong>Recorded:</strong> ${m.timestamp}</div>
            </div>
            <button class="btn-popup-zoom" onclick="openLightbox('${m.snapshot_path}', 'Hazard #${m.id} - ${sev} [${m.lat.toFixed(4)}, ${m.lng.toFixed(4)}]')">
              🔍 View Full Photo Snapshot
            </button>
          </div>
        `;

        marker.bindPopup(popupHtml);
        markerLayers.set(m.id, marker);
      });
    }

  } catch (err) {
    console.debug('Map telemetry poll error:', err);
  }
}

// ============================================================================
// 5. GOOGLE MAPS CLAIR SEARCH & CITY PRESETS
// ============================================================================
async function performLocationSearch(query) {
  if (!query || !query.trim()) return;
  const q = query.trim();

  if (elSearchResultsDropdown) {
    elSearchResultsDropdown.innerHTML = `<div style="padding: 12px; color: var(--text-muted); font-size: 0.8rem;">Searching Google Maps via Clair API...</div>`;
    elSearchResultsDropdown.classList.remove('hidden');
  }

  try {
    const res = await fetch(`${API.LOCATION_SEARCH}?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const results = data.results || [];

    if (results.length === 0) {
      if (elSearchResultsDropdown) {
        elSearchResultsDropdown.innerHTML = `<div style="padding: 12px; color: var(--text-muted); font-size: 0.8rem;">No coordinates found for "${q}".</div>`;
      }
      return;
    }

    let html = '';
    results.slice(0, 5).forEach((item, idx) => {
      html += `
        <div class="search-item" data-idx="${idx}">
          <div class="search-item-title">${item.title}</div>
          <div class="search-item-address">${item.address || ''}</div>
        </div>
      `;
    });

    if (elSearchResultsDropdown) {
      elSearchResultsDropdown.innerHTML = html;
      elSearchResultsDropdown.querySelectorAll('.search-item').forEach(itemEl => {
        itemEl.addEventListener('click', () => {
          const idx = parseInt(itemEl.getAttribute('data-idx'));
          selectLocationResult(results[idx]);
        });
      });
    }

    // Auto-apply top result
    selectLocationResult(results[0]);

  } catch (err) {
    console.error('Location search error:', err);
    if (elSearchResultsDropdown) {
      elSearchResultsDropdown.innerHTML = `<div style="padding: 12px; color: var(--accent-crimson); font-size: 0.8rem;">Search failed: ${err.message}</div>`;
    }
  }
}

async function selectLocationResult(item) {
  if (!item || item.latitude == null || item.longitude == null) return;

  if (elSearchResultsDropdown) {
    elSearchResultsDropdown.classList.add('hidden');
  }

  const lat = item.latitude;
  const lng = item.longitude;
  const title = item.title || item.address;

  try {
    await fetch(API.SET_ANCHOR, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: lat,
        lng: lng,
        location_name: title
      })
    });

    if (elRouteStartName) elRouteStartName.textContent = title;
    if (elRouteCurrentCoords) elRouteCurrentCoords.textContent = `${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`;

    markerLayers.forEach(m => leafletMap.removeLayer(m));
    markerLayers.clear();
    if (routePolyline) routePolyline.setLatLngs([[lat, lng]]);

    if (leafletMap) {
      leafletMap.setView([lat, lng], 16);
      isUserPanned = false;
    }
  } catch (err) {
    console.error('Error setting anchor:', err);
  }
}

// ============================================================================
// 6. DEVICE / SMARTPHONE LIVE GPS TRACKING
// ============================================================================
function toggleDeviceGps() {
  if (deviceGpsWatchId !== null) {
    navigator.geolocation.clearWatch(deviceGpsWatchId);
    deviceGpsWatchId = null;
    if (elBtnDeviceGps) {
      elBtnDeviceGps.textContent = '📱 My Live GPS';
      elBtnDeviceGps.classList.remove('active');
    }
    if (elGpsStatusPill) {
      elGpsStatusPill.textContent = '📡 GPS: SIMULATED';
    }
    return;
  }

  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser.');
    return;
  }

  deviceGpsWatchId = navigator.geolocation.watchPosition(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      const heading = pos.coords.heading;
      const speed = pos.coords.speed;

      try {
        await fetch(API.UPDATE_LOCATION, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lat: lat,
            lng: lng,
            heading: heading,
            speed: speed
          })
        });

        if (elGpsStatusPill) {
          elGpsStatusPill.textContent = '📡 GPS: LIVE DEVICE';
          elGpsStatusPill.className = 'hud-pill success';
        }
      } catch (err) {
        console.debug('Device GPS stream error:', err);
      }
    },
    (err) => {
      console.warn('Geolocation error:', err);
      alert('Could not access device GPS: ' + err.message);
      deviceGpsWatchId = null;
    },
    { enableHighAccuracy: true, maximumAge: 1000 }
  );

  if (elBtnDeviceGps) {
    elBtnDeviceGps.textContent = '🟢 GPS Streaming';
    elBtnDeviceGps.classList.add('active');
  }
}

// ============================================================================
// 7. VIEW MODE SWITCHER
// ============================================================================
function switchViewMode(mode) {
  currentViewMode = mode;
  document.body.classList.remove('view-map', 'view-split');

  if (btnTabVision) btnTabVision.classList.remove('active');
  if (btnTabMap) btnTabMap.classList.remove('active');
  if (btnTabSplit) btnTabSplit.classList.remove('active');

  if (mode === 'map') {
    document.body.classList.add('view-map');
    if (btnTabMap) btnTabMap.classList.add('active');
  } else if (mode === 'split') {
    document.body.classList.add('view-split');
    if (btnTabSplit) btnTabSplit.classList.add('active');
  } else {
    // vision
    if (btnTabVision) btnTabVision.classList.add('active');
  }

  // Refresh Leaflet size
  setTimeout(() => {
    if (leafletMap) {
      leafletMap.invalidateSize();
    }
  }, 100);
}

// ============================================================================
// 8. PHOTO LIGHTBOX MODAL
// ============================================================================
window.openLightbox = function(imageSrc, caption) {
  if (!imageSrc || !elLightboxModal) return;
  if (elLightboxImg) elLightboxImg.src = imageSrc;
  if (elLightboxCaption) elLightboxCaption.textContent = caption || 'Road Damage Snapshot';
  if (elLightboxTitle) elLightboxTitle.textContent = caption ? caption.split('[')[0] : 'Hazard Photo Snapshot';
  elLightboxModal.classList.add('show');
};

// ============================================================================
// 9. SOURCE SWITCHING & CAMERA SELECTION
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
// 10. INITIALIZATION & EVENT LISTENERS
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Leaflet Map
  initDamageMap();

  // View Navigation Tabs
  if (btnTabVision) btnTabVision.addEventListener('click', () => switchViewMode('vision'));
  if (btnTabMap) btnTabMap.addEventListener('click', () => switchViewMode('map'));
  if (btnTabSplit) btnTabSplit.addEventListener('click', () => switchViewMode('split'));

  // Severity Card Filter Clicking
  const sevPillCrit = document.querySelector('.severity-pill-card.critical');
  const sevPillMod = document.querySelector('.severity-pill-card.moderate');
  const sevPillMin = document.querySelector('.severity-pill-card.minor');

  function setFilter(sev) {
    activeSeverityFilter = (activeSeverityFilter === sev) ? 'all' : sev;
    document.querySelectorAll('.filter-chip').forEach(c => {
      c.classList.toggle('active', c.getAttribute('data-filter') === activeSeverityFilter);
    });
    document.querySelectorAll('.severity-pill-card').forEach(p => p.classList.remove('active-filter'));
    if (activeSeverityFilter !== 'all') {
      const activePill = document.querySelector(`.severity-pill-card.${activeSeverityFilter.toLowerCase()}`);
      if (activePill) activePill.classList.add('active-filter');
    }
    renderDetectionsFeed();
  }

  if (sevPillCrit) sevPillCrit.addEventListener('click', () => setFilter('Critical'));
  if (sevPillMod) sevPillMod.addEventListener('click', () => setFilter('Moderate'));
  if (sevPillMin) sevPillMin.addEventListener('click', () => setFilter('Minor'));

  // Feed Filter Chips
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const filter = chip.getAttribute('data-filter');
      setFilter(filter);
    });
  });

  // Source selector buttons
  const btnSrcTest = document.getElementById('btn-src-test_video');
  const btnSrcWebcam = document.getElementById('btn-src-webcam');
  const btnSrcUsb = document.getElementById('btn-src-usb_phone');

  if (btnSrcTest) btnSrcTest.addEventListener('click', () => switchSource('test_video'));
  if (btnSrcWebcam) btnSrcWebcam.addEventListener('click', () => switchSource('webcam', '0'));
  if (btnSrcUsb) {
    btnSrcUsb.addEventListener('click', () => {
      if (elModalUsb) {
        elModalUsb.classList.add('show');
        checkAdbDeviceStatus();
      }
    });
  }

  if (elBtnCloseModal && elModalUsb) {
    elBtnCloseModal.addEventListener('click', () => {
      elModalUsb.classList.remove('show');
    });
  }

  // Lightbox Close
  if (elBtnCloseLightbox && elLightboxModal) {
    elBtnCloseLightbox.addEventListener('click', () => {
      elLightboxModal.classList.remove('show');
    });
  }
  if (elLightboxModal) {
    elLightboxModal.addEventListener('click', (e) => {
      if (e.target === elLightboxModal) elLightboxModal.classList.remove('show');
    });
  }

  // Google Maps Search Button & Enter Key
  if (elBtnMapSearch && elMapSearchInput) {
    elBtnMapSearch.addEventListener('click', () => {
      performLocationSearch(elMapSearchInput.value);
    });
    elMapSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        performLocationSearch(elMapSearchInput.value);
      }
    });
  }

  // City Preset Chips
  document.querySelectorAll('.chip-preset[data-query]').forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.getAttribute('data-query');
      if (elMapSearchInput) elMapSearchInput.value = q;
      performLocationSearch(q);
    });
  });

  // Device Live GPS Button
  if (elBtnDeviceGps) {
    elBtnDeviceGps.addEventListener('click', toggleDeviceGps);
  }

  // Center Map Button (Follow Vehicle)
  if (elBtnCenterMap) {
    elBtnCenterMap.addEventListener('click', () => {
      isUserPanned = false;
      if (vehicleMarker && leafletMap) {
        leafletMap.setView(vehicleMarker.getLatLng(), 16);
      }
    });
  }

  // Fit All Hazards in View
  if (elBtnFitHazards) {
    elBtnFitHazards.addEventListener('click', fitAllHazards);
  }

  // Clear / Reset Route Button
  if (elBtnClearRoute) {
    elBtnClearRoute.addEventListener('click', async () => {
      if (confirm('Clear current inspection route and reset path tracking?')) {
        await fetch(API.RESET, { method: 'POST' });
        markerLayers.forEach(m => leafletMap.removeLayer(m));
        markerLayers.clear();
        if (routePolyline) routePolyline.setLatLngs([]);
        isUserPanned = false;
        updateMapTelemetry();
        updateDetectionsFeed();
      }
    });
  }

  // Close search dropdown on click outside
  document.addEventListener('click', (e) => {
    if (elSearchResultsDropdown && !e.target.closest('.search-input-wrapper')) {
      elSearchResultsDropdown.classList.add('hidden');
    }
  });

  // Live ADB Device Diagnostic Check
  async function checkAdbDeviceStatus() {
    const badge = document.getElementById('adb-live-badge');
    const icon = document.getElementById('adb-badge-icon');
    const title = document.getElementById('adb-badge-title');
    const desc = document.getElementById('adb-badge-desc');
    if (!badge || !title) return;

    title.textContent = 'Scanning USB connection...';
    if (desc) desc.textContent = 'Querying Android Debug Bridge...';

    try {
      const res = await fetch(API.ADB_STATUS);
      const data = await res.json();

      if (data.device_connected && data.device_state === 'device') {
        badge.style.background = 'rgba(16, 185, 129, 0.12)';
        badge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        if (icon) icon.textContent = '🟢';
        title.textContent = `Phone Detected: ${data.manufacturer} ${data.model}`;
        let detail = `USB Debugging Active (Device: ${data.device_id}).`;
        if (!data.camera_apps?.ip_webcam && !data.camera_apps?.droidcam) {
          detail += ` ⚠️ Please install IP Webcam or DroidCam on your phone.`;
        } else {
          detail += ` ✓ Ready to stream! Tap 'Start Server' on phone.`;
        }
        if (desc) desc.textContent = detail;
      } else if (data.device_connected && data.device_state === 'unauthorized') {
        badge.style.background = 'rgba(245, 158, 11, 0.15)';
        badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        if (icon) icon.textContent = '🟡';
        title.textContent = `Device Found (${data.device_id}) - Unauthorized`;
        if (desc) desc.textContent = "Please unlock your phone and tap 'Allow USB Debugging' on screen.";
      } else if (data.adb_available) {
        badge.style.background = 'rgba(239, 68, 68, 0.12)';
        badge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        if (icon) icon.textContent = '🔴';
        title.textContent = 'No Phone Detected over USB';
        if (desc) desc.textContent = 'Connect phone via USB and ensure USB Debugging is ON in Developer Options.';
      } else {
        badge.style.background = 'rgba(239, 68, 68, 0.12)';
        badge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        if (icon) icon.textContent = '⚠️';
        title.textContent = 'ADB Not Found';
        if (desc) desc.textContent = data.message || 'Android platform-tools not found on host.';
      }
    } catch (err) {
      if (title) title.textContent = 'Unable to check ADB status';
      if (desc) desc.textContent = 'Server response error: ' + err.message;
    }
  }

  const btnRefreshAdb = document.getElementById('btn-refresh-adb');
  if (btnRefreshAdb) {
    btnRefreshAdb.addEventListener('click', checkAdbDeviceStatus);
  }

  // ADB Auto-Connect
  if (elBtnAdbConnect) {
    elBtnAdbConnect.addEventListener('click', async () => {
      if (elAdbStatusText) {
        elAdbStatusText.style.color = '#38bdf8';
        elAdbStatusText.textContent = 'Forwarding USB ports (8080 & 4747)...';
      }
      try {
        const res = await fetch(API.ADB_CONNECT, { method: 'POST' });
        const data = await res.json();
        const targetUrl = (elInputPhoneUrl ? elInputPhoneUrl.value.trim() : '') || 'http://127.0.0.1:8080/video';

        if (data.success) {
          if (elAdbStatusText) {
            elAdbStatusText.style.color = '#10b981';
            elAdbStatusText.textContent = `✓ ${data.message}`;
          }
          switchSource('usb_phone', targetUrl);
          setTimeout(() => {
            if (elModalUsb) elModalUsb.classList.remove('show');
          }, 1400);
        } else {
          if (elAdbStatusText) {
            elAdbStatusText.style.color = '#f59e0b';
            elAdbStatusText.textContent = `Notice: ${data.message}`;
          }
          // Switch anyway so auto-reconnector can pick up stream when ready
          switchSource('usb_phone', targetUrl);
        }
      } catch (err) {
        if (elAdbStatusText) {
          elAdbStatusText.style.color = '#ef4444';
          elAdbStatusText.textContent = 'Error connecting to ADB: ' + err.message;
        }
      }
    });
  }

  // Apply Direct Phone Stream URL
  if (elBtnApplyPhoneStream && elInputPhoneUrl) {
    elBtnApplyPhoneStream.addEventListener('click', () => {
      const url = elInputPhoneUrl.value.trim() || 'http://127.0.0.1:8080/video';
      switchSource('usb_phone', url);
      if (elModalUsb) elModalUsb.classList.remove('show');
    });
  }

  // Upload Custom Video
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
        markerLayers.forEach(m => leafletMap.removeLayer(m));
        markerLayers.clear();
        if (routePolyline) routePolyline.setLatLngs([]);
        isUserPanned = false;
        updateTelemetry();
        updateDetectionsFeed();
        updateMapTelemetry();
      }
    });
  }

  // Export CSV (Including Lat/Lng coordinates and snapshots)
  if (elBtnExport) {
    elBtnExport.addEventListener('click', async () => {
      try {
        const res = await fetch(API.RECENT_DETECTIONS);
        const data = await res.json();
        if (data.length === 0) {
          alert('No detections logged to export.');
          return;
        }

        let csv = 'Detection_ID,Timestamp,Severity,Confidence,Latitude,Longitude,BBox_X1,BBox_Y1,BBox_X2,BBox_Y2,Snapshot\n';
        data.forEach(d => {
          const b = d.bbox || [0, 0, 0, 0];
          const lat = d.lat != null ? d.lat : '';
          const lng = d.lng != null ? d.lng : '';
          csv += `${d.id},"${d.timestamp}",${d.severity},${d.confidence},${lat},${lng},${b[0]},${b[1]},${b[2]},${b[3]},"${d.snapshot_path}"\n`;
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
  updateMapTelemetry();

  setInterval(updateTelemetry, 400);
  setInterval(updateDetectionsFeed, 1800);
  setInterval(updateMapTelemetry, 1500);
});

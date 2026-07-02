// ==========================================================
//  1. MAP INITIALIZATION & BASEMAP
//  Center Bago City: [10.5389, 122.8375]
//  Basemap: CartoDB Positron (clean, minimalist light style)
// ==========================================================
const map = L.map('map', {
  center: [10.5389, 122.8375],
  zoom: 12,
  zoomControl: true,
  attributionControl: true
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  subdomains: 'abcd',
  maxZoom: 19
}).addTo(map);

// ==========================================================
//  2. SPATIAL GEOMETRY REFERENCES & STATE
//  Asynchronous layer storage variables.
// ==========================================================
let cityLayer, barangayLayer;
let cityData, barangaysData;
const labelLayer = L.layerGroup();
const illuminatedLayerGroup = L.layerGroup().addTo(map);
let userMarker = null;

const locateBtn = document.getElementById('locateBtn');

// PULSE Dashboard State & Tab References
const tabGis = document.getElementById('tabGis');
const tabPulse = document.getElementById('tabPulse');
const contentGis = document.getElementById('contentGis');
const contentPulse = document.getElementById('contentPulse');

const barangayRiskScores = {};
const barangayLayersByName = {};
const activeFootprints = {};
const activeHotspots = {};

let simIntervalId = null;
let simSpeed = 3000; // default 3s interval

// ==========================================================
//  3. ASYNC DATA FETCH LOADING
//  Concurrent load for bago-city and barangays.
// ==========================================================
Promise.all([
  fetch('data/bago-city.geojson').then(res => {
    if (!res.ok) throw new Error('Bago City boundary limit file (data/bago-city.geojson) could not be fetched.');
    return res.json();
  }),
  fetch('data/barangays.geojson').then(res => {
    if (!res.ok) throw new Error('Barangay boundaries file (data/barangays.geojson) could not be fetched.');
    return res.json();
  })
])
.then(([cityRes, barangayRes]) => {
  // Save global dataset references for Turf PIP calculations
  cityData = cityRes;
  barangaysData = barangayRes;

  // Restore button action state
  locateBtn.disabled = false;
  locateBtn.textContent = "📍 Pinpoint & Illuminate My Location";

  // Render base layers (Official LGU Light Style Spec)
  // City Limit: Heavy black dashed/dotted line, transparent fill
  cityLayer = L.geoJSON(cityData, {
    interactive: false,
    style: {
      color: '#000000',
      weight: 3,
      opacity: 0.85,
      fillColor: 'transparent',
      fillOpacity: 0,
      dashArray: '6, 4'
    }
  }).addTo(map);

  // Barangay Boundaries: Very thin, subtle muted gray lines, transparent fill
  barangayLayer = L.geoJSON(barangaysData, {
    style: {
      color: '#a0a0a0',
      weight: 1,
      opacity: 0.75,
      fillColor: 'transparent',
      fillOpacity: 0
    }
  }).addTo(map);

  // Puroks Layer removed

  // Fit boundaries initially
  map.fitBounds(cityLayer.getBounds().pad(0.05));

  // Map individual layers by name for direct visual updates
  barangayLayer.eachLayer(layer => {
    if (layer.feature && layer.feature.properties && layer.feature.properties.name) {
      barangayLayersByName[layer.feature.properties.name] = layer;
    }
  });

  // Initialize Risk Scores to low baselines (0.05 - 0.30)
  barangaysData.features.forEach(feature => {
    const name = feature.properties.name;
    barangayRiskScores[name] = 0.05 + Math.random() * 0.25;
  });

  // Attach standard interactive popups and hover styles
  bindBaseLayerPopups();

  // Render initial PULSE Outbreak list items in the sidebar
  renderSidebarList();

  // Apply visual styling (elevating critical areas initially if any)
  for (const name in barangayRiskScores) {
    updateBarangayVisuals(name);
  }
  updateGlobalStats();

  // Initialize control buttons and tab triggers
  initPulseDashboard();

  // Create text-only label layers at Turf centroids
  addLabels(cityData);
  addLabels(barangaysData);
  labelLayer.addTo(map);
})
.catch(err => {
  console.error(err);
  locateBtn.textContent = "⚠️ GIS Data Load Failed";
  const detailsContainer = document.getElementById('locationDetails');
  detailsContainer.innerHTML = `
    <div class="location-error-warning">
      <div class="warning-title">⚠️ File Loading Error</div>
      <p>Failed to load boundary datasets asynchronously.</p>
      <p style="font-size: 11px; margin-top: 6px; opacity: 0.85; line-height: 1.4;">
        <b>Reason:</b> ${err.message}<br><br>
        Note: If opening files directly via the <code>file://</code> protocol, browsers block local requests. Please serve this project via a local HTTP server.
      </p>
    </div>
  `;
  detailsContainer.style.display = 'block';
});

// ==========================================================
//  4. BASE LAYER INTERACTION & POPUPS
// ==========================================================
function bindBaseLayerPopups() {
  // cityLayer is non-interactive to allow clicking through directly to Barangays.
  // Barangay popups are bound dynamically in updateBarangayVisuals() to represent live risk scores

  // Hover highlighting styles
  const hoverHighlightStyle = {
    weight: 3.5,
    fillColor: '#000000',
    fillOpacity: 0.02
  };

  const hoverHandler = (layer, baseStyle, isBarangay = false) => {
    layer.on('mouseover', function () {
      if (isBarangay) {
        const name = this.feature.properties.name;
        // If the barangay is levitating (critical risk), skip the default flat hover style
        if (barangayRiskScores[name] >= 0.8) return;
      }
      this.setStyle(hoverHighlightStyle);
      this.bringToFront();
      
      // Keep pulsing hotspots and footprints layering correctly
      if (isBarangay) {
        const name = this.feature.properties.name;
        if (activeHotspots[name]) activeHotspots[name].bringToFront();
      }
    });
    layer.on('mouseout', function () {
      if (isBarangay) {
        const name = this.feature.properties.name;
        // If critical, do not restore normal styles
        if (barangayRiskScores[name] >= 0.8) return;
        
        // Restore warning or stable styles correctly
        const score = barangayRiskScores[name];
        if (score >= 0.5) {
          this.setStyle({
            color: '#fbbf24',
            weight: 1.5,
            opacity: 0.85,
            fillColor: '#fbbf24',
            fillOpacity: 0.06
          });
          return;
        }
      }
      this.setStyle(baseStyle);
    });
  };

  // cityLayer is non-interactive, so hover handling is only applied to barangayLayer
  barangayLayer.eachLayer(layer => hoverHandler(layer, { color: '#a0a0a0', weight: 1, opacity: 0.75, fillColor: 'transparent', fillOpacity: 0 }, true));
}

// ==========================================================
//  5. TURF.JS LABEL CENTROID PLACEMENTS
// ==========================================================
function addLabels(geojsonData) {
  geojsonData.features.forEach(function (feature) {
    if (!feature.properties || !feature.properties.name) return;

    // Use Turf to compute the precise centroid coordinates of the boundary polygon
    const centroid = turf.centroid(feature);
    const latLng = [centroid.geometry.coordinates[1], centroid.geometry.coordinates[0]];

    // Create a text-only, pinless label marker
    const label = L.marker(latLng, {
      icon: L.divIcon({
        className: 'area-label',
        html: '<span class="label-text">' + feature.properties.name + '</span>',
        iconSize: null,
        iconAnchor: [0, 0]
      }),
      interactive: false
    });

    labelLayer.addLayer(label);
  });
}

// ==========================================================
//  6. GEOLOCATION AND TURF DYNAMIC BOUNDARY ILLUMINATION
// ==========================================================
locateBtn.addEventListener('click', function () {
  const btn = this;
  const detailsContainer = document.getElementById('locationDetails');

  btn.disabled = true;
  btn.textContent = "⏳ Acquiring High-Accuracy GPS Position...";

  detailsContainer.innerHTML = '';
  detailsContainer.style.display = 'none';

  // Clear previous boundary highlights
  illuminatedLayerGroup.clearLayers();

  const geoOptions = {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 0
  };

  if (!navigator.geolocation) {
    showLocationError("Geolocation is not supported by your browser.");
    resetButtonState();
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function (position) {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      const accuracy = position.coords.accuracy;

      // Process geographic location calculation
      processUserLocation(lat, lng, accuracy);
    },
    function (error) {
      let errorMsg = "Unable to retrieve your location.";
      switch (error.code) {
        case error.PERMISSION_DENIED:
          errorMsg = "Location permission denied. Please allow access to your location.";
          break;
        case error.POSITION_UNAVAILABLE:
          errorMsg = "Location information is unavailable.";
          break;
        case error.TIMEOUT:
          errorMsg = "The request to get your location timed out.";
          break;
      }
      showLocationError(errorMsg);
      resetButtonState();
    },
    geoOptions
  );

  function showLocationError(msg) {
    detailsContainer.innerHTML = `
      <div class="location-error-warning">
        <div class="warning-title">⚠️ GPS Error</div>
        <p>${msg}</p>
      </div>
    `;
    detailsContainer.style.display = 'block';
  }

  function resetButtonState() {
    btn.disabled = false;
    btn.textContent = "📍 Pinpoint & Illuminate My Location";
  }

  function processUserLocation(lat, lng, accuracy) {
    // Generate a point feature in standard GeoJSON [longitude, latitude] order
    const userPoint = turf.point([lng, lat]);

    // Check city limit point containment
    let insideCity = false;
    let matchedCityFeature = null;

    cityData.features.forEach(feature => {
      if (turf.booleanPointInPolygon(userPoint, feature)) {
        insideCity = true;
        matchedCityFeature = feature;
      }
    });

    // Fallback: outside mapped limits
    if (!insideCity) {
      // Zoom out to show full city bounds
      map.fitBounds(cityLayer.getBounds().pad(0.05), { animate: true });

      // Add a distinct warning marker on map
      updateLocationMarker(lat, lng, `
        <div style="font-family: 'Inter', sans-serif; font-size: 12px; color: #f0f0f5;">
          <div style="font-weight: 700; color: #ef4444;">⚠️ Out of Bounds</div>
          <div><b>Coords:</b> ${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
          <div style="font-size: 11px; opacity: 0.85; margin-top: 4px;">You are outside mapped LGU boundaries.</div>
        </div>
      `);

      // Alert within sidebar
      detailsContainer.innerHTML = `
        <div class="location-error-warning">
          <div class="warning-title">⚠️ Outside LGU Boundaries</div>
          <p>You are outside mapped LGU boundaries.</p>
          <div class="warning-coords font-mono">Coords: ${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
        </div>
      `;
      detailsContainer.style.display = 'block';
      resetButtonState();
      return;
    }

    // Inside bounds: zoom map closely
    map.setView([lat, lng], 16, { animate: true });

    // Place location marker pin
    updateLocationMarker(lat, lng, `
      <div style="font-family: 'Inter', sans-serif; font-size: 12px; color: #f0f0f5; line-height: 1.45;">
        <div style="font-weight: 700; color: #00b4ff; margin-bottom: 2px;">📍 Position Pinpointed</div>
        <div><b>Coords:</b> ${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
        <div><b>Accuracy:</b> ±${accuracy.toFixed(1)} meters</div>
      </div>
    `);

    // Dynamic highlights (Temporary boundary lighting overlay layers)
    // 1. City limit: Solid red glow outline (non-interactive)
    L.geoJSON(matchedCityFeature, {
      interactive: false,
      style: {
        color: '#ff1a1a',
        weight: 4.5,
        opacity: 0.95,
        fillColor: '#ff1a1a',
        fillOpacity: 0.04
      }
    }).addTo(illuminatedLayerGroup);

    // 2. Matching Barangay: Bright neon orange stroke
    let matchedBarangay = null;
    barangaysData.features.forEach(feature => {
      if (turf.booleanPointInPolygon(userPoint, feature)) {
        matchedBarangay = feature;
      }
    });

    if (matchedBarangay) {
      L.geoJSON(matchedBarangay, {
        style: {
          color: '#ff6600',
          weight: 4,
          opacity: 0.95,
          fillColor: '#ff6600',
          fillOpacity: 0.08
        }
      }).addTo(illuminatedLayerGroup);
    }

    // Update active readout panels
    const brgName = matchedBarangay ? matchedBarangay.properties.name : 'Unmapped Barangay';

    detailsContainer.innerHTML = `
      <div class="location-details-container illuminated">
        <div class="status-title">✨ Boundaries Illuminated</div>
        <div class="location-detail-row">
          <span class="location-detail-label">City</span>
          <span class="location-detail-val">Bago City</span>
        </div>
        <div class="location-detail-row">
          <span class="location-detail-label">Barangay</span>
          <span class="location-detail-val">${brgName}</span>
        </div>
        <div class="location-detail-row">
          <span class="location-detail-label">Coordinates</span>
          <span class="location-detail-val font-mono" style="font-size: 11px;">${lat.toFixed(5)}, ${lng.toFixed(5)}</span>
        </div>
      </div>
    `;
    detailsContainer.style.display = 'block';
    resetButtonState();
  }

  function updateLocationMarker(lat, lng, popupContent) {
    if (userMarker) {
      userMarker.setLatLng([lat, lng]);
    } else {
      userMarker = L.marker([lat, lng]).addTo(map);
    }
    userMarker.bindPopup(popupContent).openPopup();
  }
});

// ==========================================================
//  7. SIDEBAR TOGGLE WIRING
// ==========================================================
document.getElementById('toggleCity').addEventListener('change', function () {
  if (this.checked) {
    map.addLayer(cityLayer);
  } else {
    map.removeLayer(cityLayer);
  }
});

document.getElementById('toggleBarangay').addEventListener('change', function () {
  if (this.checked) {
    map.addLayer(barangayLayer);
  } else {
    map.removeLayer(barangayLayer);
  }
});

// Toggle puroks removed

document.getElementById('toggleLabels').addEventListener('change', function () {
  if (this.checked) {
    map.addLayer(labelLayer);
  } else {
    map.removeLayer(labelLayer);
  }
});

// ==========================================================
//  8. MOBILE SIDEBAR DRAWER TOGGLE
// ==========================================================
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');

sidebarToggle.addEventListener('click', function () {
  sidebar.classList.toggle('open');
  this.textContent = sidebar.classList.contains('open') ? '✕' : '☰';
});

map.on('click', function () {
  if (window.innerWidth <= 540 && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    sidebarToggle.textContent = '☰';
  }
});

// ==========================================================
//  9. PULSE OUTBREAK SURVEILLANCE & LEVITATION ENGINE
// ==========================================================

// Render scrollable risk profiles inside the sidebar
function renderSidebarList() {
  const container = document.getElementById('pulseBarangayList');
  if (!container) return;

  container.innerHTML = '';
  
  // Sort alphabetically so the list order is stable and predictable for manual tuning
  const sortedNames = Object.keys(barangayRiskScores).sort();

  sortedNames.forEach(name => {
    const score = barangayRiskScores[name];
    const safeName = name.toLowerCase().replace(/[^a-z0-9]/g, '-');
    const badgeClass = score >= 0.8 ? 'critical' : (score >= 0.5 ? 'warning' : 'stable');
    const badgeText = score >= 0.8 ? 'Critical' : (score >= 0.5 ? 'Warning' : 'Stable');

    const item = document.createElement('div');
    item.className = 'pulse-item';
    item.id = `item-${safeName}`;
    item.setAttribute('data-name', name);

    item.innerHTML = `
      <div class="pulse-item-header">
        <span class="pulse-item-name">${name}</span>
        <span class="pulse-item-badge ${badgeClass}" id="badge-${safeName}">${badgeText}</span>
      </div>
      <div class="pulse-item-bar-container">
        <div class="pulse-item-bar ${badgeClass}" id="bar-${safeName}" style="width: ${score * 100}%"></div>
      </div>
      <div class="pulse-item-details" id="details-${safeName}">
        <div class="pulse-slider-row">
          <div class="pulse-slider-label">
            <span>Manual Risk Adjustment:</span>
            <span class="pulse-slider-val ${badgeClass}" id="sliderVal-${safeName}">${score.toFixed(2)}</span>
          </div>
          <input type="range" class="pulse-item-slider ${badgeClass}" id="slider-${safeName}" min="0" max="1" step="0.01" value="${score.toFixed(2)}" />
        </div>
      </div>
    `;

    // Click expands item, zooms to Barangay polygon, and displays Leaflet popup
    item.addEventListener('click', function(e) {
      // If we clicked the range slider, do not toggle expand state
      if (e.target.tagName === 'INPUT' || e.target.classList.contains('pulse-slider-row')) {
        return;
      }

      const wasExpanded = this.classList.contains('expanded');
      
      // Close other expanded elements
      document.querySelectorAll('.pulse-item').forEach(el => {
        el.classList.remove('expanded');
        el.classList.remove('active');
      });

      if (!wasExpanded) {
        this.classList.add('expanded');
        this.classList.add('active');

        // Focus map onto Barangay geometry
        const layer = barangayLayersByName[name];
        if (layer) {
          const bounds = layer.getBounds();
          map.fitBounds(bounds, { maxZoom: 15, animate: true, padding: [20, 20] });
          setTimeout(() => layer.openPopup(), 400);
        }
      }
    });

    // Slider adjustment controls manual scores
    const slider = item.querySelector(`#slider-${safeName}`);
    slider.addEventListener('input', function(e) {
      const val = parseFloat(this.value);
      barangayRiskScores[name] = val;
      
      // Update local item components directly for immediate response
      const valLabel = item.querySelector(`#sliderVal-${safeName}`);
      valLabel.textContent = val.toFixed(2);
      valLabel.className = `pulse-slider-val ${val >= 0.8 ? 'critical' : (val >= 0.5 ? 'warning' : 'stable')}`;
      
      this.className = `pulse-item-slider ${val >= 0.8 ? 'critical' : (val >= 0.5 ? 'warning' : 'stable')}`;
      
      updateBarangayVisuals(name);
      updateSidebarItem(name);
      updateGlobalStats();
      toggleCriticalLegendSwatch();
    });

    container.appendChild(item);
  });
}

// Update a single item's visual indicators inside the list (used during simulation)
function updateSidebarItem(name) {
  const safeName = name.toLowerCase().replace(/[^a-z0-9]/g, '-');
  const item = document.getElementById(`item-${safeName}`);
  if (!item) return;

  const score = barangayRiskScores[name];
  const badgeClass = score >= 0.8 ? 'critical' : (score >= 0.5 ? 'warning' : 'stable');
  const badgeText = score >= 0.8 ? 'Critical' : (score >= 0.5 ? 'Warning' : 'Stable');

  // Update Badge
  const badge = item.querySelector(`#badge-${safeName}`);
  if (badge) {
    badge.textContent = badgeText;
    badge.className = `pulse-item-badge ${badgeClass}`;
  }

  // Update Progress Bar
  const bar = item.querySelector(`#bar-${safeName}`);
  if (bar) {
    bar.className = `pulse-item-bar ${badgeClass}`;
    bar.style.width = `${score * 100}%`;
  }

  // Update Slider and Slider numerical indicator
  const slider = item.querySelector(`#slider-${safeName}`);
  if (slider && document.activeElement !== slider) {
    slider.value = score.toFixed(2);
    slider.className = `pulse-item-slider ${badgeClass}`;
  }

  const sliderVal = item.querySelector(`#sliderVal-${safeName}`);
  if (sliderVal) {
    sliderVal.textContent = score.toFixed(2);
    sliderVal.className = `pulse-slider-val ${badgeClass}`;
  }
}

// Recalculates stats grids and updates headers
function updateGlobalStats() {
  let criticalCount = 0;
  let warningCount = 0;
  let stableCount = 0;

  for (const name in barangayRiskScores) {
    const score = barangayRiskScores[name];
    if (score >= 0.8) {
      criticalCount++;
    } else if (score >= 0.5) {
      warningCount++;
    } else {
      stableCount++;
    }
  }

  // Inject counts into UI
  const critEl = document.getElementById('pulseCritCount');
  const warnEl = document.getElementById('pulseWarnCount');
  const stabEl = document.getElementById('pulseStableCount');

  if (critEl) critEl.textContent = criticalCount;
  if (warnEl) warnEl.textContent = warningCount;
  if (stabEl) stabEl.textContent = stableCount;

  // Update Status Indicator Badge
  const indicator = document.getElementById('pulseStatusIndicator');
  if (indicator) {
    const label = indicator.querySelector('.status-indicator-text');
    if (criticalCount > 0) {
      indicator.className = 'pulse-indicator-badge critical';
      if (label) label.textContent = 'Outbreak Detected';
    } else if (warningCount > 0) {
      indicator.className = 'pulse-indicator-badge warning';
      if (label) label.textContent = 'Elevated Risk';
    } else {
      indicator.className = 'pulse-indicator-badge stable';
      if (label) label.textContent = 'Stable';
    }
  }
}

// Toggle legend visual helper dynamically
function toggleCriticalLegendSwatch() {
  const swatchItem = document.getElementById('legendCriticalItem');
  if (!swatchItem) return;

  const hasCritical = Object.values(barangayRiskScores).some(score => score >= 0.8);
  swatchItem.style.display = hasCritical ? 'flex' : 'none';
}

// Trigger visuals and SVG class offsets on critical risk score thresholds
function updateBarangayVisuals(name) {
  const layer = barangayLayersByName[name];
  if (!layer) return;

  const score = barangayRiskScores[name];
  const isCritical = score >= 0.8;
  const isWarning = score >= 0.5 && score < 0.8;

  // Determine standard Leaflet styling options
  let style;
  if (isCritical) {
    style = {
      color: '#ff2a5f',
      weight: 2.5,
      opacity: 0.9,
      fillColor: '#ff2a5f',
      fillOpacity: 0.15
    };
  } else if (isWarning) {
    style = {
      color: '#fbbf24',
      weight: 1.5,
      opacity: 0.85,
      fillColor: '#fbbf24',
      fillOpacity: 0.06
    };
  } else {
    // Stable Default Style
    style = {
      color: '#a0a0a0',
      weight: 1,
      opacity: 0.75,
      fillColor: 'transparent',
      fillOpacity: 0
    };
  }

  // Apply styling to Leaflet vector layer
  layer.setStyle(style);

  // Directly adjust SVG element class name for translation & drop-shadow styles
  if (layer._path) {
    if (isCritical) {
      layer._path.classList.add('levitating-polygon');
      layer.bringToFront();
    } else {
      layer._path.classList.remove('levitating-polygon');
    }
  }

  // Manage Ground Footprint layer underneath
  if (isCritical) {
    if (!activeFootprints[name]) {
      const footprintStyle = {
        color: '#11111b',
        weight: 1.5,
        opacity: 0.6,
        dashArray: '3, 6',
        fillColor: '#000000',
        fillOpacity: 0.12,
        interactive: false
      };
      // Place a static shadow footprint on the ground map
      const footprint = L.geoJSON(layer.feature, { style: footprintStyle }).addTo(map);
      activeFootprints[name] = footprint;
    }
  } else {
    if (activeFootprints[name]) {
      map.removeLayer(activeFootprints[name]);
      delete activeFootprints[name];
    }
  }

  // Manage Centroid Pulsing Hotspot Marker
  if (isCritical) {
    if (!activeHotspots[name]) {
      const centroid = turf.centroid(layer.feature);
      const latLng = [centroid.geometry.coordinates[1], centroid.geometry.coordinates[0]];
      
      const hotspotIcon = L.divIcon({
        className: 'pulsing-hotspot-container',
        html: `
          <div class="pulsing-hotspot" title="${name} Outbreak Hotspot">
            <div class="pulsing-hotspot-inner"></div>
            <div class="pulsing-hotspot-ring"></div>
          </div>
        `,
        iconSize: [14, 14],
        iconAnchor: [7, 7]
      });

      const hotspot = L.marker(latLng, { icon: hotspotIcon, interactive: false }).addTo(map);
      activeHotspots[name] = hotspot;
    }
  } else {
    if (activeHotspots[name]) {
      map.removeLayer(activeHotspots[name]);
      delete activeHotspots[name];
    }
  }

  // Bind custom popup details
  const badgeClass = isCritical ? 'critical' : (isWarning ? 'warning' : 'stable');
  const badgeText = isCritical ? 'Critical Outbreak' : (isWarning ? 'Warning' : 'Stable');

  layer.bindPopup(`
    <div>
      <span class="popup-type barangay ${badgeClass}">${badgeText}</span>
      <div class="popup-title">${name}</div>
      <div class="popup-desc" style="margin-top: 4px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 2px; font-size: 12px;">
          <span>Risk Score:</span>
          <strong class="font-mono ${badgeClass}" style="color: ${isCritical ? '#ff2a5f' : (isWarning ? '#fbbf24' : '#34d399')}">${score.toFixed(3)}</strong>
        </div>
        <div style="font-size: 11.5px; opacity: 0.85; margin-top: 6px; line-height: 1.4;">
          ${isCritical 
            ? '⚠️ Zone has elevated and detached due to critical risk factors. Immediate containment required.' 
            : (isWarning ? '⚠️ Alert: Risk score elevated. Outbreak vector suspected.' : 'Region is currently stable. Normal baseline monitored.')}
        </div>
      </div>
    </div>
  `);

  if (layer.isPopupOpen()) {
    layer.setPopupContent(layer.getPopup());
  }
}

// Run simulation step (uses random walk algorithm for natural variance)
function runSimulationStep() {
  for (const name in barangayRiskScores) {
    const current = barangayRiskScores[name];
    
    // Generate random shift: slightly biased downwards (-0.05 to +0.04) so outbreaks remain anomalies
    const delta = (Math.random() - 0.55) * 0.12;
    const nextVal = Math.max(0.01, Math.min(1.0, current + delta));

    barangayRiskScores[name] = nextVal;
    
    updateBarangayVisuals(name);
    updateSidebarItem(name);
  }
  updateGlobalStats();
  toggleCriticalLegendSwatch();
}

// Dashboard Buttons Wiring & Tab Switching
function initPulseDashboard() {
  // Tab Event Listeners
  tabGis.addEventListener('click', () => {
    tabGis.classList.add('active');
    tabGis.setAttribute('aria-selected', 'true');
    tabPulse.classList.remove('active');
    tabPulse.setAttribute('aria-selected', 'false');
    
    contentGis.style.display = 'block';
    contentGis.classList.add('active');
    contentPulse.style.display = 'none';
    contentPulse.classList.remove('active');
  });

  tabPulse.addEventListener('click', () => {
    tabPulse.classList.add('active');
    tabPulse.setAttribute('aria-selected', 'true');
    tabGis.classList.remove('active');
    tabGis.setAttribute('aria-selected', 'false');
    
    contentPulse.style.display = 'block';
    contentPulse.classList.add('active');
    contentGis.style.display = 'none';
    contentGis.classList.remove('active');
    
    toggleCriticalLegendSwatch();
  });

  // Play / Pause Simulation
  const playBtn = document.getElementById('simPlayBtn');
  if (playBtn) {
    playBtn.addEventListener('click', function() {
      if (simIntervalId) {
        // Pause
        clearInterval(simIntervalId);
        simIntervalId = null;
        this.innerHTML = '<span class="btn-icon">▶</span> Run Real-time Simulation';
        this.className = 'sim-btn play-btn';
      } else {
        // Run
        simIntervalId = setInterval(runSimulationStep, simSpeed);
        this.innerHTML = '<span class="btn-icon">⏸</span> Pause Simulation';
        this.className = 'sim-btn pause-btn';
      }
    });
  }

  // Speed Control Slider
  const speedRange = document.getElementById('simSpeedRange');
  const speedVal = document.getElementById('simSpeedVal');
  if (speedRange && speedVal) {
    speedRange.addEventListener('input', function() {
      const seconds = this.value;
      speedVal.textContent = `${seconds}s`;
      simSpeed = seconds * 1000;

      // Reset interval if running
      if (simIntervalId) {
        clearInterval(simIntervalId);
        simIntervalId = setInterval(runSimulationStep, simSpeed);
      }
    });
  }

  // Spike Outbreaks Trigger
  const triggerBtn = document.getElementById('simTriggerBtn');
  if (triggerBtn) {
    triggerBtn.addEventListener('click', function() {
      // Pick 1-3 random stable barangays and push them to critical risk
      const names = Object.keys(barangayRiskScores);
      const stableNames = names.filter(n => barangayRiskScores[n] < 0.5);
      
      if (stableNames.length === 0) return;

      const numOutbreaks = Math.min(stableNames.length, Math.floor(Math.random() * 3) + 1);
      
      // Shuffle stableNames
      for (let i = stableNames.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [stableNames[i], stableNames[j]] = [stableNames[j], stableNames[i]];
      }

      const selected = stableNames.slice(0, numOutbreaks);
      selected.forEach(name => {
        // Assign a critical score between 0.82 and 0.98
        barangayRiskScores[name] = 0.82 + Math.random() * 0.16;
        updateBarangayVisuals(name);
        updateSidebarItem(name);
      });

      updateGlobalStats();
      toggleCriticalLegendSwatch();

      // Pan map to show the first spiked outbreak
      const firstLayer = barangayLayersByName[selected[0]];
      if (firstLayer) {
        map.fitBounds(firstLayer.getBounds(), { maxZoom: 14, animate: true });
        setTimeout(() => firstLayer.openPopup(), 400);
      }
    });
  }

  // Reset Dashboard Trigger
  const resetBtn = document.getElementById('simResetBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', function() {
      // Reset all scores to stable baseline
      for (const name in barangayRiskScores) {
        barangayRiskScores[name] = 0.05 + Math.random() * 0.25;
        updateBarangayVisuals(name);
        updateSidebarItem(name);
      }
      updateGlobalStats();
      toggleCriticalLegendSwatch();
    });
  }
}

// Failsafe listener: Leaflet re-creates / alters SVG path layers on zoom or pan actions,
// which can strip CSS styling classes. We hook into moveend and zoomend to ensure
// the levitation classes are re-applied.
map.on('moveend zoomend', function() {
  for (const name in barangayRiskScores) {
    if (barangayRiskScores[name] >= 0.8) {
      const layer = barangayLayersByName[name];
      if (layer && layer._path) {
        layer._path.classList.add('levitating-polygon');
      }
    }
  }
});

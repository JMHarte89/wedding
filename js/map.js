/**
 * Wedding map — Leaflet-based map with layer toggles and quick navigation.
 * Loads places from data-places-url on the container element.
 * Add ?debug=1 to the page URL to show a diagnostics panel above the map.
 */
(function () {
  'use strict';

  const KENDAL_CENTRE = [54.3269, -2.7476];
  const DEFAULT_ZOOM = 13;
  const FOCUS_ZOOM = 15;

  window.__WEDDING_MAP_JS_LOADED__ = '20260219d';
  if (typeof console !== 'undefined' && console.log) {
    console.log('map.js loaded', window.__WEDDING_MAP_JS_LOADED__, typeof location !== 'undefined' ? location.href : '');
  }

  var debugMode = typeof window !== 'undefined' && window.location && window.location.search.indexOf('debug=1') !== -1;
  var debugBannerEl = null;
  var firstRuntimeErrorShown = false;

  function ensureDebugBanner() {
    if (!debugMode || debugBannerEl) return;
    var body = document.body;
    if (!body) {
      document.addEventListener('DOMContentLoaded', ensureDebugBanner);
      return;
    }
    var banner = document.createElement('div');
    banner.id = 'map-debug-banner';
    banner.className = 'map-debug-banner';
    banner.setAttribute('aria-live', 'polite');
    banner.textContent = 'Map debug active — build 20260219d';
    body.insertBefore(banner, body.firstChild);
    debugBannerEl = banner;
  }

  if (debugMode) {
    ensureDebugBanner();
    window.addEventListener('error', function (e) {
      if (firstRuntimeErrorShown || !debugBannerEl) return;
      firstRuntimeErrorShown = true;
      debugBannerEl.textContent = debugBannerEl.textContent + '\nRuntime error: ' + (e.message || String(e));
    });
    window.addEventListener('unhandledrejection', function (e) {
      if (firstRuntimeErrorShown || !debugBannerEl) return;
      firstRuntimeErrorShown = true;
      var msg = (e.reason && (e.reason.message || e.reason)) || 'Unhandled promise rejection';
      debugBannerEl.textContent = debugBannerEl.textContent + '\nRuntime error: ' + String(msg).slice(0, 200);
    });
  }

  function isDebug() {
    return typeof window !== 'undefined' && window.location && window.location.search.indexOf('debug=1') !== -1;
  }

  function haversine(lat1, lng1, lat2, lng2) {
    var R = 3958.8; // miles
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLng = (lng2 - lng1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  var MAP_ERROR_MSG = 'Map failed to load. Please refresh, or use \'View full screen map\'.';

  function updateDebugPanelStage(container, stage) {
    if (!isDebug() || !container || !container.parentNode) return;
    var pre = container.parentNode.querySelector('.map-debug-panel pre');
    if (!pre) return;
    var lines = pre.textContent.split('\n');
    var found = false;
    for (var i = 0; i < lines.length; i += 1) {
      if (lines[i].indexOf('Stage:') === 0) {
        lines[i] = 'Stage: ' + stage;
        found = true;
        break;
      }
    }
    if (!found) lines.push('Stage: ' + stage);
    pre.textContent = lines.join('\n');
  }

  function showMapError(container, err, stageOrInfo) {
    if (!container) return;
    console.error('map.js: Failed to load map:', err);
    var msg = MAP_ERROR_MSG;
    var stageStr = typeof stageOrInfo === 'string' ? stageOrInfo : (stageOrInfo && stageOrInfo.stage);
    var info = typeof stageOrInfo === 'object' && stageOrInfo ? stageOrInfo : {};
    if (isDebug()) {
      msg += '\nStage: ' + (stageStr || info.stage || '—');
      msg += '\nDebug error: ' + (err != null ? String(err) : '—');
      if (err && err.stack) {
        var firstLine = err.stack.split('\n')[0];
        if (firstLine) msg += '\n' + firstLine.trim();
      }
      if (info.status !== undefined || info.contentType) {
        msg += '\n[Debug: ' + (info.status !== undefined ? 'status ' + info.status : '') + (info.contentType ? '; content-type ' + info.contentType : '') + ']';
      }
    }
    container.textContent = msg;
    container.classList.add('map-load-error');
  }

  function renderDebugPanel(container, data) {
    if (!isDebug() || !container || !container.parentNode) return;
    var wrap = document.createElement('div');
    wrap.className = 'map-debug-panel';
    wrap.setAttribute('aria-live', 'polite');
    var lines = [
      'Leaflet loaded? ' + (typeof L !== 'undefined' ? 'yes' : 'no'),
      'places.json URL: ' + (container.getAttribute('data-places-url') || '—'),
      'Fetch: ' + (data.fetchStatus !== undefined ? data.fetchStatus : '—'),
      'Content-Type: ' + (data.contentType !== undefined ? data.contentType : '—'),
      'JSON parse: ' + (data.jsonOk === true ? 'ok' : data.jsonOk === false ? 'failed' : '—'),
      'Places loaded: ' + (typeof data.placeCount === 'number' ? data.placeCount : '—'),
      'Stage: start'
    ];
    wrap.innerHTML = '<pre>' + lines.map(function (s) { return escapeHtml(s); }).join('\n') + '</pre>';
    container.parentNode.insertBefore(wrap, container);
  }

  function initMap() {
    var stage = 'start';
    function setStage(s) {
      stage = s;
      updateDebugPanelStage(container, stage);
    }

    var container = document.getElementById('wedding-map');
    if (!container) return;
    setStage('container found');

    if (typeof L === 'undefined') {
      showMapError(container, new Error('Leaflet (L) is not defined. Check that Leaflet JS loads before map.js.'), stage);
      return;
    }
    setStage('leaflet ok');

    var placesUrl = container.getAttribute('data-places-url');
    if (!placesUrl) {
      showMapError(container, new Error('No data-places-url on map container'), stage);
      return;
    }

    if (isDebug()) {
      renderDebugPanel(container, {
        fetchStatus: 'pending',
        contentType: '—',
        jsonOk: '—',
        placeCount: '—'
      });
    }

    fetch(placesUrl)
      .then(function (r) {
        setStage('fetch ok');
        var ct = (r.headers.get('content-type') || '').toLowerCase();
        var debugInfo = { stage: 'fetch ok', status: r.status, contentType: (r.headers.get('content-type') || '—') };
        if (ct.indexOf('text/html') !== -1) {
          var e = new Error('Server returned HTML instead of JSON (often a 404 page). Check the places URL.');
          e.debugInfo = debugInfo;
          throw e;
        }
        if (!r.ok) {
          var e2 = new Error('Fetch failed: ' + r.status + ' ' + r.statusText);
          e2.debugInfo = debugInfo;
          throw e2;
        }
        return r.json().then(
          function (data) { return { response: r, data: data, contentType: ct }; },
          function (parseErr) {
            parseErr.debugInfo = debugInfo;
            throw parseErr;
          }
        );
      })
      .then(function (result) {
        var data = result.data;
        setStage('fetch ok');
        if (!data || !Array.isArray(data.places)) {
          var invalidErr = new Error('Invalid places data');
          invalidErr.debugInfo = { stage: 'json ok' };
          throw invalidErr;
        }
        setStage('json ok');
        if (isDebug()) {
          var panel = container.parentNode.querySelector('.map-debug-panel');
          if (panel) {
            var pre = panel.querySelector('pre');
            pre.textContent = [
              'Leaflet loaded? yes',
              'places.json URL: ' + placesUrl,
              'Fetch: ' + result.response.status + ' ' + result.response.statusText,
              'Content-Type: ' + result.contentType,
              'JSON parse: ok',
              'Places loaded: ' + data.places.length,
              'Tile errors: 0',
              'Stage: ' + stage
            ].join('\n');
          }
        }
        setStage('renderMap start');
        try {
          renderMap(container, data, setStage);
          setStage('done');
        } catch (err) {
          updateDebugPanelStage(container, stage);
          showMapError(container, err, stage);
          return;
        }
        bindQuickNav(data);
      })
      .catch(function (err) {
        var info = err && err.debugInfo ? { stage: err.debugInfo.stage || 'fetch failed', status: err.debugInfo.status, contentType: err.debugInfo.contentType } : 'fetch failed';
        showMapError(container, err, info);
      });
  }

  function bindQuickNav(data) {
    var markersByKey = window._weddingMapMarkersByKey || {};
    var map = window._weddingMap;
    if (!map) return;

    var buttons = document.querySelectorAll('[data-map-focus]');
    buttons.forEach(function (btn) {
      var key = btn.getAttribute('data-map-focus');
      var info = markersByKey[key];
      if (!info) {
        btn.disabled = true;
        return;
      }
      btn.addEventListener('click', function () {
        map.setView([info.lat, info.lng], FOCUS_ZOOM);
        if (info.marker && info.marker.openPopup) {
          info.marker.openPopup();
        }
      });
    });
  }

  function renderMap(container, data, setStage) {
    var layers = data.layers || [];
    var places = data.places || [];
    var layerMap = {};
    var markersByKey = {};
    var venueCoords = null;
    if (typeof setStage !== 'function') setStage = function () {};

    places.forEach(function (p) {
      if (p.key === 'venue') {
        var vLat = Number(p.lat);
        var vLng = Number(p.lng);
        if (Number.isFinite(vLat) && Number.isFinite(vLng)) venueCoords = [vLat, vLng];
      }
    });

    if (container.offsetHeight === 0) {
      container.style.height = window.matchMedia('(max-width: 480px)').matches ? '360px' : '420px';
    }

    var map = L.map(container).setView(KENDAL_CENTRE, DEFAULT_ZOOM);
    window._weddingMap = map;
    setStage('map created');

    var tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    setStage('tile layer added');

    if (isDebug()) {
      var tileErrorCount = 0;
      var debugPre = container.parentNode && container.parentNode.querySelector('.map-debug-panel pre');
      tileLayer.on('tileerror', function () {
        tileErrorCount += 1;
        if (debugPre) {
          var lines = debugPre.textContent.split('\n');
          for (var i = 0; i < lines.length; i += 1) {
            if (lines[i].indexOf('Tile errors:') === 0) {
              lines[i] = 'Tile errors: ' + tileErrorCount;
              break;
            }
          }
          debugPre.textContent = lines.join('\n');
        }
      });
    }

    setTimeout(function () { map.invalidateSize(); }, 250);
    setTimeout(function () { map.invalidateSize(); }, 1000);
    window.addEventListener('load', function () { map.invalidateSize(); });
    window.addEventListener('resize', function () { map.invalidateSize(); });

    if (isDebug()) {
      var debugPreEl = container.parentNode && container.parentNode.querySelector('.map-debug-panel pre');
      if (debugPreEl) {
        var w = container.offsetWidth;
        var h = container.offsetHeight;
        var leafletPresent = map.getContainer() ? 'yes' : 'no';
        var cs = getComputedStyle(container);
        var compHeight = cs.height;
        var compMinHeight = cs.minHeight;
        var compDisplay = cs.display;
        debugPreEl.textContent = debugPreEl.textContent + '\nMap container size: ' + w + 'x' + h + '\nLeaflet container present: ' + leafletPresent + '\nMap computed height: ' + compHeight + ' (min-height: ' + compMinHeight + ')\nMap computed display: ' + compDisplay;
        setTimeout(function () {
          var w1 = container.offsetWidth;
          var h1 = container.offsetHeight;
          var cs1 = getComputedStyle(container);
          var lines = debugPreEl.textContent.split('\n');
          for (var i = 0; i < lines.length; i += 1) {
            if (lines[i].indexOf('Map container size:') === 0) {
              lines[i] = 'Map container size: ' + w1 + 'x' + h1;
            } else if (lines[i].indexOf('Map computed height:') === 0) {
              lines[i] = 'Map computed height: ' + cs1.height + ' (min-height: ' + cs1.minHeight + ')';
            } else if (lines[i].indexOf('Map computed display:') === 0) {
              lines[i] = 'Map computed display: ' + cs1.display;
            }
          }
          debugPreEl.textContent = lines.join('\n');
        }, 1000);
      }
    }

    var validLayerIds = new Set();
    layers.forEach(function (layer) {
      var group = L.layerGroup();
      layerMap[layer.id] = { group: group, label: layer.label, emoji: layer.emoji || '' };
      validLayerIds.add(layer.id);
      group.addTo(map);
    });
    var fallbackLayerId = layerMap.hotels ? 'hotels' : (layers[0] && layers[0].id) || 'hotels';
    if (!layerMap[fallbackLayerId]) {
      var otherGroup = L.layerGroup();
      layerMap.other = { group: otherGroup, label: 'Other', emoji: '📍' };
      otherGroup.addTo(map);
      fallbackLayerId = 'other';
    }

    function makePin(variant, label) {
      return L.divIcon({
        className: 'map-pin-icon',
        html: '<div class="map-pin map-pin--' + variant + '">' + escapeHtml(label) + '</div>',
        iconSize: [42, 42],
        iconAnchor: [21, 21],
        popupAnchor: [0, -18]
      });
    }
    function makeBox(variant, label) {
      return L.divIcon({
        className: 'map-box-icon',
        html: '<div class="map-box map-box--' + variant + '">' + escapeHtml(label) + '</div>',
        iconSize: [42, 42],
        iconAnchor: [21, 21],
        popupAnchor: [0, -18]
      });
    }
    var churchIcon = makePin('church', 'C');
    var venueIcon = makePin('venue', 'V');
    var parkingIcon = makeBox('parking', 'P');

    var bounds = [];
    var markersAdded = 0;
    var markersSkipped = 0;
    var markerErrorCount = 0;
    var markerErrors = [];
    var layerFallbacks = 0;

    places.forEach(function (place) {
      var layerId = place.layer;
      if (!layerId || !validLayerIds.has(layerId)) {
        layerId = fallbackLayerId;
        layerFallbacks += 1;
      }
      var layerInfo = layerMap[layerId];
      if (!layerInfo) return;

      var lat = Number(place.lat);
      var lng = Number(place.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        markersSkipped += 1;
        return;
      }

      try {
        var icon;
        var markerOptions = {};
        if (place.key === 'church') {
          icon = churchIcon;
          markerOptions.zIndexOffset = 1000;
          markerOptions.riseOnHover = true;
        } else if (place.key === 'church_parking' || place.key === 'venue_parking' || place.key === 'county_hall') {
          icon = parkingIcon;
          markerOptions.zIndexOffset = 900;
          markerOptions.riseOnHover = true;
        } else if (place.key === 'venue') {
          icon = venueIcon;
          markerOptions.zIndexOffset = 950;
          markerOptions.riseOnHover = true;
        } else {
          var emoji = layerInfo.emoji;
          var iconClass = 'wedding-marker';
          if (place.priority) iconClass += ' wedding-marker-priority';
          var size = place.priority ? 40 : 32;
          icon = L.divIcon({
            className: iconClass,
            html: '<span class="wedding-marker-emoji">' + (emoji || '📍') + '</span>',
            iconSize: [size, size],
            iconAnchor: [size / 2, size]
          });
        }
        markerOptions.icon = icon;
        var popupContent = buildPopupContent(place, venueCoords);
        var marker = L.marker([lat, lng], markerOptions)
          .bindPopup(popupContent)
          .addTo(layerInfo.group);
        bounds.push([lat, lng]);
        markersAdded += 1;
        if (place.key) {
          markersByKey[place.key] = { marker: marker, lat: lat, lng: lng };
        }
      } catch (err) {
        markerErrorCount += 1;
        var reason = (err && err.message) ? err.message : String(err);
        if (markerErrors.length < 3) {
          markerErrors.push({ name: place.name || '—', reason: reason.slice(0, 80) });
        }
      }
    });
    setStage('markers loop complete');

    if (isDebug()) {
      var preEl = container.parentNode && container.parentNode.querySelector('.map-debug-panel pre');
      if (preEl) {
        var extra = [
          'Markers added: ' + markersAdded,
          'Markers skipped: ' + markersSkipped,
          'Marker errors: ' + markerErrorCount
        ];
        if (markerErrors.length > 0) {
          for (var i = 0; i < markerErrors.length; i += 1) {
            extra.push('- ' + (markerErrors[i].name || '—') + ': ' + (markerErrors[i].reason || '—'));
          }
        }
        preEl.textContent = preEl.textContent + '\n' + extra.join('\n');
      }
    }

    window._weddingMapMarkersByKey = markersByKey;

    setStage('fit bounds');
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
    }

    var overlays = {};
    layers.forEach(function (layer) {
      var info = layerMap[layer.id];
      if (info && info.group) {
        overlays[layer.emoji + ' ' + layer.label] = info.group;
      }
    });
    if (layerMap.other && layerMap.other.group) {
      overlays[layerMap.other.emoji + ' ' + layerMap.other.label] = layerMap.other.group;
    }
    L.control.layers(null, overlays, { collapsed: true }).addTo(map);
  }

  function buildPopupContent(place, venueCoords) {
    var parts = ['<strong>' + escapeHtml(place.name) + '</strong>'];
    if (place.note) parts.push('<br>' + escapeHtml(place.note));
    if (place.key === 'venue_parking') {
      parts.push('<div class="popup-muted">Parking is limited.</div>');
    }

    var facts = [];
    if (place.price) facts.push('Price guide: ' + escapeHtml(place.price));
    if (typeof place.stars === 'number') facts.push('Star rating: ' + place.stars + '-star');
    if (typeof place.rooms === 'number') facts.push('Rooms: ' + place.rooms);
    if (typeof place.beds === 'number') facts.push('Beds: ' + place.beds);
    if (typeof place.spaces === 'number') facts.push('Parking spaces: ' + place.spaces);
    if (venueCoords && (place.layer === 'hotels' || place.layer === 'camping')) {
      var mi = haversine(place.lat, place.lng, venueCoords[0], venueCoords[1]);
      var km = mi * 1.60934;
      facts.push('Distance to venue: ' + mi.toFixed(1) + ' mi / ' + km.toFixed(1) + ' km');
    }
    if (place.highlights && place.highlights.length) {
      place.highlights.forEach(function (h) {
        facts.push(escapeHtml(h));
      });
    }
    if (facts.length) {
      parts.push('<ul class="popup-facts">');
      facts.forEach(function (f) {
        parts.push('<li>' + f + '</li>');
      });
      parts.push('</ul>');
    }

    var links = [];
    if (place.url) {
      links.push('<a href="' + escapeHtml(place.url) + '" target="_blank" rel="noopener">Website / book</a>');
    }
    links.push('<a href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(place.lat + ',' + place.lng) + '" target="_blank" rel="noopener">Open in Google Maps</a>');
    if (links.length) {
      parts.push('<p class="popup-links">' + links.join(' · ') + '</p>');
    }

    return parts.join('');
  }

  function escapeHtml(s) {
    if (s == null) return '';
    var div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMap);
  } else {
    initMap();
  }
})();

/**
 * Wedding map — Leaflet-based map with layer toggles and quick navigation.
 * Loads places from data-places-url on the container element.
 * Add ?debug=1 to the page URL to show a diagnostics panel above the map.
 */
(function () {
  'use strict';

  window.__WEDDING_MAP_JS_LOADED__ = '20260219a';
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
    banner.textContent = 'Map debug active — build 20260219a';
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

  function showMapError(container, err, debugInfo) {
    if (!container) return;
    console.error('map.js: Failed to load map:', err);
    var msg = MAP_ERROR_MSG;
    if (isDebug() && debugInfo) {
      msg += ' [Debug: ' + (debugInfo.status !== undefined ? 'status ' + debugInfo.status : '') + (debugInfo.contentType ? '; content-type ' + debugInfo.contentType : '') + ']';
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
      'Places loaded: ' + (typeof data.placeCount === 'number' ? data.placeCount : '—')
    ];
    wrap.innerHTML = '<pre>' + lines.map(function (s) { return escapeHtml(s); }).join('\n') + '</pre>';
    container.parentNode.insertBefore(wrap, container);
  }

  function initMap() {
    var container = document.getElementById('wedding-map');
    if (!container) return;

    if (typeof L === 'undefined') {
      showMapError(container, new Error('Leaflet (L) is not defined. Check that Leaflet JS loads before map.js.'));
      return;
    }

    var placesUrl = container.getAttribute('data-places-url');
    if (!placesUrl) {
      showMapError(container, new Error('No data-places-url on map container'));
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
        var ct = (r.headers.get('content-type') || '').toLowerCase();
        var debugInfo = { status: r.status, contentType: (r.headers.get('content-type') || '—') };
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
        if (!data || !Array.isArray(data.places)) throw new Error('Invalid places data');
        if (isDebug()) {
          var panel = container.parentNode.querySelector('.map-debug-panel');
          if (panel) {
            panel.querySelector('pre').textContent = [
              'Leaflet loaded? yes',
              'places.json URL: ' + placesUrl,
              'Fetch: ' + result.response.status + ' ' + result.response.statusText,
              'Content-Type: ' + result.contentType,
              'JSON parse: ok',
              'Places loaded: ' + data.places.length,
              'Tile errors: 0'
            ].join('\n');
          }
        }
        renderMap(container, data);
        bindQuickNav(data);
      })
      .catch(function (err) {
        showMapError(container, err, isDebug() && err && err.debugInfo ? err.debugInfo : null);
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

  function renderMap(container, data) {
    var layers = data.layers || [];
    var places = data.places || [];
    var layerMap = {};
    var markersByKey = {};
    var venueCoords = null;

    places.forEach(function (p) {
      if (p.key === 'venue') {
        var vLat = Number(p.lat);
        var vLng = Number(p.lng);
        if (Number.isFinite(vLat) && Number.isFinite(vLng)) venueCoords = [vLat, vLng];
      }
    });

    var map = L.map(container).setView(KENDAL_CENTRE, DEFAULT_ZOOM);
    window._weddingMap = map;

    var tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

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
    window.addEventListener('resize', function () { map.invalidateSize(); });

    if (isDebug()) {
      var debugPreEl = container.parentNode && container.parentNode.querySelector('.map-debug-panel pre');
      if (debugPreEl) {
        var w = container.offsetWidth;
        var h = container.offsetHeight;
        var leafletPresent = map.getContainer() ? 'yes' : 'no';
        debugPreEl.textContent = debugPreEl.textContent + '\nMap container size: ' + w + 'x' + h + '\nLeaflet container present: ' + leafletPresent;
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
        var emoji = layerInfo.emoji;
        var iconClass = 'wedding-marker';
        if (place.priority) iconClass += ' wedding-marker-priority';
        var size = place.priority ? 40 : 32;
        var icon = L.divIcon({
          className: iconClass,
          html: '<span class="wedding-marker-emoji">' + (emoji || '📍') + '</span>',
          iconSize: [size, size],
          iconAnchor: [size / 2, size]
        });
        var popupContent = buildPopupContent(place, venueCoords);
        var marker = L.marker([lat, lng], { icon: icon })
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

    var facts = [];
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

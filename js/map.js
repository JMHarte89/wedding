/**
 * Wedding map — Leaflet-based map with layer toggles and quick navigation.
 * Loads places from data-places-url on the container element.
 */
(function () {
  var KENDAL_CENTRE = [54.3269, -2.7476];
  var DEFAULT_ZOOM = 13;
  var FOCUS_ZOOM = 17;

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

  function initMap() {
    var container = document.getElementById('wedding-map');
    if (!container) return;

    var placesUrl = container.getAttribute('data-places-url');
    if (!placesUrl) return;

    fetch(placesUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderMap(container, data);
        bindQuickNav(data);
      })
      .catch(function (err) {
        console.error('map.js: Failed to load places:', err);
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
      if (p.key === 'venue' && typeof p.lat === 'number' && typeof p.lng === 'number') {
        venueCoords = [p.lat, p.lng];
      }
    });

    var map = L.map(container).setView(KENDAL_CENTRE, DEFAULT_ZOOM);
    window._weddingMap = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    layers.forEach(function (layer) {
      var group = L.layerGroup();
      layerMap[layer.id] = { group: group, label: layer.label, emoji: layer.emoji || '' };
      group.addTo(map);
    });

    var bounds = [];
    places.forEach(function (place) {
      var lat = place.lat;
      var lng = place.lng;
      if (typeof lat !== 'number' || typeof lng !== 'number') return;

      var layerInfo = layerMap[place.layer];
      if (!layerInfo) return;

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

      if (place.key) {
        markersByKey[place.key] = { marker: marker, lat: lat, lng: lng };
      }
    });

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

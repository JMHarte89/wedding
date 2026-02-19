/**
 * Wedding map — Leaflet-based map with layer toggles.
 * Loads places from data-places-url on the container element.
 */
(function () {
  var KENDAL_CENTRE = [54.3269, -2.7476];
  var DEFAULT_ZOOM = 13;

  function initMap() {
    var container = document.getElementById('wedding-map');
    if (!container) return;

    var placesUrl = container.getAttribute('data-places-url');
    if (!placesUrl) {
      console.warn('map.js: No data-places-url on #wedding-map');
      return;
    }

    fetch(placesUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderMap(container, data);
      })
      .catch(function (err) {
        console.error('map.js: Failed to load places:', err);
      });
  }

  function renderMap(container, data) {
    var layers = data.layers || [];
    var places = data.places || [];
    var layerMap = {};

    var map = L.map(container).setView(KENDAL_CENTRE, DEFAULT_ZOOM);

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
      if (typeof lat !== 'number' || typeof lng !== 'number') {
        console.warn('map.js: Skipping place (missing lat/lng):', place.name);
        return;
      }

      var layerInfo = layerMap[place.layer];
      if (!layerInfo) return;

      var emoji = layerInfo.emoji;
      var icon = L.divIcon({
        className: 'wedding-marker',
        html: '<span class="wedding-marker-emoji">' + (emoji || '📍') + '</span>',
        iconSize: [32, 32],
        iconAnchor: [16, 32]
      });

      var popupParts = ['<strong>' + escapeHtml(place.name) + '</strong>'];
      if (place.note) popupParts.push('<br>' + escapeHtml(place.note));
      if (place.url) popupParts.push('<br><a href="' + escapeHtml(place.url) + '" target="_blank" rel="noopener">Book / check availability</a>');
      var popupContent = popupParts.join('');

      var marker = L.marker([lat, lng], { icon: icon })
        .bindPopup(popupContent)
        .addTo(layerInfo.group);
      bounds.push([lat, lng]);
    });

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

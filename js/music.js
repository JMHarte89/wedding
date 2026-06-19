(function () {
  'use strict';

  var STORAGE_KEY = 'wedding_playlist';
  var CFG = window.WEDDING_CONFIG || {};
  var TARGET_MINS = Number(CFG.playlistTargetMins) || 300;
  var TARGET_SECS = TARGET_MINS * 60;
  var APPS_SCRIPT_URL = CFG.appsScriptUrl;
  var PLAYLIST_URL = CFG.spotifyPlaylistUrl;
  var APPS_PLACEHOLDER = 'APPS_SCRIPT_URL_PLACEHOLDER';
  var PLAYLIST_PLACEHOLDER = 'SPOTIFY_PLAYLIST_URL_PLACEHOLDER';

  // Module-level token cache (page session). Apps Script also caches server-side.
  var tokenCache = { token: null, expiresAt: 0 };

  // ---------- localStorage state ----------
  function loadPlaylist() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) { return []; }
  }
  function savePlaylist(list) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  }

  // ---------- Formatting ----------
  function fmtClock(totalSecs) {
    var h = Math.floor(totalSecs / 3600);
    var m = Math.floor((totalSecs % 3600) / 60);
    if (h && m) return h + 'h ' + m + 'm';
    if (h) return h + 'h';
    return m + 'm';
  }
  function fmtTrack(ms) {
    var s = Math.round(ms / 1000);
    var m = Math.floor(s / 60);
    var ss = (s % 60).toString();
    if (ss.length < 2) ss = '0' + ss;
    return m + ':' + ss;
  }

  // ---------- Duration clock ----------
  function renderClock() {
    var list = loadPlaylist();
    var totalSecs = list.reduce(function (a, t) { return a + (Number(t.durationSecs) || 0); }, 0);
    var remaining = Math.max(0, TARGET_SECS - totalSecs);
    var pct = (totalSecs / TARGET_SECS) * 100;

    document.getElementById('stat-count').textContent = String(list.length);
    document.getElementById('stat-total').textContent = fmtClock(totalSecs);
    document.getElementById('stat-remaining').textContent =
      totalSecs >= TARGET_SECS ? 'Full set!' : fmtClock(remaining);

    var bar = document.getElementById('progress-bar');
    bar.style.width = Math.min(100, pct) + '%';
    bar.classList.remove('is-warn', 'is-over');
    if (pct > 100) bar.classList.add('is-over');
    else if (pct > 80) bar.classList.add('is-warn');

    document.getElementById('progress-status').textContent =
      Math.round(pct) + '% of the ' + Math.round(TARGET_MINS / 60) + 'h target.';
  }

  // ---------- Spotify token via Apps Script ----------
  function getSpotifyToken() {
    if (tokenCache.token && Date.now() < tokenCache.expiresAt) {
      return Promise.resolve(tokenCache.token);
    }
    if (!APPS_SCRIPT_URL || APPS_SCRIPT_URL === APPS_PLACEHOLDER) {
      return Promise.reject(new Error('Apps Script URL not configured yet.'));
    }
    var sep = APPS_SCRIPT_URL.indexOf('?') === -1 ? '?' : '&';
    var url = APPS_SCRIPT_URL + sep + 'action=token';
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('Token proxy returned ' + r.status);
      return r.json();
    }).then(function (data) {
      if (!data || !data.token) {
        throw new Error((data && data.error) || 'No token returned');
      }
      tokenCache = { token: data.token, expiresAt: Date.now() + 50 * 60 * 1000 };
      return data.token;
    });
  }

  // ---------- Spotify search ----------
  function searchSpotify(query, limit) {
    return getSpotifyToken().then(function (token) {
      var url = 'https://api.spotify.com/v1/search?q=' + encodeURIComponent(query)
        + '&type=track&limit=' + (limit || 10) + '&market=GB';
      return fetch(url, { headers: { Authorization: 'Bearer ' + token } });
    }).then(function (r) {
      if (r.status === 401) {
        tokenCache = { token: null, expiresAt: 0 };
        throw new Error('Spotify token expired — please try again.');
      }
      if (!r.ok) throw new Error('Spotify returned ' + r.status);
      return r.json();
    }).then(function (data) {
      return (data && data.tracks && data.tracks.items) || [];
    });
  }

  // ---------- Render results ----------
  function renderResults(containerId, tracks, statusId) {
    var ul = document.getElementById(containerId);
    ul.innerHTML = '';
    var status = statusId ? document.getElementById(statusId) : null;

    if (!tracks.length) {
      if (status) status.textContent = 'No tracks found. Try a different search.';
      return;
    }
    if (status) status.textContent = '';

    var suggested = new Set(loadPlaylist().map(function (t) { return t.spotifyId; }));

    tracks.forEach(function (track) {
      var li = document.createElement('li');
      li.className = 'music-result';
      li.setAttribute('data-spotify-id', track.id);

      var imgUrl = (track.album && track.album.images && track.album.images[0] && track.album.images[0].url) || '';
      var artist = (track.artists || []).map(function (a) { return a.name; }).join(', ');
      var already = suggested.has(track.id);

      var artHtml = imgUrl
        ? '<img src="' + escapeAttr(imgUrl) + '" alt="" loading="lazy" width="64" height="64">'
        : '';
      li.innerHTML =
        '<div class="music-result__art">' + artHtml + '</div>' +
        '<div class="music-result__meta">' +
          '<p class="music-result__title"></p>' +
          '<p class="music-result__artist"></p>' +
          '<p class="music-result__album"></p>' +
        '</div>' +
        '<div class="music-result__action">' +
          '<span class="music-result__duration"></span>' +
          '<button type="button" class="btn ' + (already ? 'btn-secondary' : 'btn-primary') + '"' +
            (already ? ' disabled' : '') + '>' +
            (already ? 'Suggested' : 'Suggest this song') +
          '</button>' +
        '</div>';

      li.querySelector('.music-result__title').textContent = track.name;
      li.querySelector('.music-result__artist').textContent = artist;
      li.querySelector('.music-result__album').textContent = (track.album && track.album.name) || '';
      li.querySelector('.music-result__duration').textContent = fmtTrack(track.duration_ms);

      var btn = li.querySelector('button');
      btn.addEventListener('click', function () {
        if (btn.disabled) return;
        suggest(track, btn);
      });
      ul.appendChild(li);
    });
  }

  function escapeAttr(s) {
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  }

  // ---------- Suggest a track ----------
  function suggest(track, btn) {
    var list = loadPlaylist();
    if (list.some(function (t) { return t.spotifyId === track.id; })) {
      markButtonSuggested(btn);
      return;
    }
    var entry = {
      spotifyId: track.id,
      trackName: track.name,
      artistName: (track.artists || []).map(function (a) { return a.name; }).join(', '),
      durationSecs: Math.round(track.duration_ms / 1000)
    };
    list.push(entry);
    savePlaylist(list);
    markButtonSuggested(btn);
    syncAllSuggestedButtons();
    renderClock();
    postSongRequest(entry).catch(function (err) {
      // Keep local state even if the proxy fails — guest still sees their suggestion.
      if (window.console) console.warn('song_request POST failed (kept locally):', err);
    });
  }

  function markButtonSuggested(btn) {
    btn.disabled = true;
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-secondary');
    btn.textContent = 'Suggested';
  }

  function syncAllSuggestedButtons() {
    var ids = new Set(loadPlaylist().map(function (t) { return t.spotifyId; }));
    var items = document.querySelectorAll('.music-result');
    items.forEach(function (li) {
      var id = li.getAttribute('data-spotify-id');
      if (id && ids.has(id)) {
        var btn = li.querySelector('button');
        if (btn && !btn.disabled) markButtonSuggested(btn);
      }
    });
  }

  function postSongRequest(entry) {
    if (!APPS_SCRIPT_URL || APPS_SCRIPT_URL === APPS_PLACEHOLDER) {
      return Promise.reject(new Error('Apps Script URL not configured yet.'));
    }
    return fetch(APPS_SCRIPT_URL, {
      method: 'POST',
      // text/plain keeps this a CORS "simple request" (no preflight).
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({
        action: 'song_request',
        guestCode: '',
        guestName: '',
        trackName: entry.trackName,
        artistName: entry.artistName,
        spotifyId: entry.spotifyId,
        durationSecs: entry.durationSecs
      })
    }).then(function (r) {
      if (!r.ok) throw new Error('Apps Script returned ' + r.status);
      return r.json();
    }).then(function (data) {
      if (!data || data.success !== true) {
        throw new Error((data && data.error) || 'Unknown error');
      }
      return data;
    });
  }

  // ---------- Form handlers ----------
  function runSearch(inputId, resultsId, statusId, limit) {
    var input = document.getElementById(inputId);
    var status = document.getElementById(statusId);
    var q = input.value.trim();
    if (!q) return;
    status.textContent = 'Searching…';
    searchSpotify(q, limit).then(function (tracks) {
      renderResults(resultsId, tracks, statusId);
    }).catch(function (err) {
      status.textContent = 'Could not search: ' + err.message;
    });
  }

  // ---------- Init ----------
  document.addEventListener('DOMContentLoaded', function () {
    renderClock();

    document.getElementById('search-form').addEventListener('submit', function (e) {
      e.preventDefault();
      runSearch('search-input', 'search-results', 'search-status', 10);
    });

    document.getElementById('paste-form').addEventListener('submit', function (e) {
      e.preventDefault();
      runSearch('paste-input', 'paste-results', 'paste-status', 3);
    });

    var link = document.getElementById('collab-link');
    if (PLAYLIST_URL && PLAYLIST_URL !== PLAYLIST_PLACEHOLDER) {
      link.href = PLAYLIST_URL;
    } else {
      link.setAttribute('aria-disabled', 'true');
      link.addEventListener('click', function (e) {
        e.preventDefault();
        alert('Playlist URL not set yet. Update WEDDING_CONFIG.spotifyPlaylistUrl in js/config.js.');
      });
    }
  });
})();

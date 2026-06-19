/**
 * Jason & Rebecca — Wedding site Apps Script proxy
 * =================================================
 *
 * Handles two jobs for the static GitHub Pages site:
 *   1. Spotify token exchange (Client Credentials flow). The browser cannot
 *      hold the Spotify client secret. This script does.
 *   2. Form posts (RSVP, song requests, preference updates) appended to a
 *      Google Sheet, with an email notification.
 *
 * -------------------------------------------------------------------------
 * SETUP — do this once before deploying
 * -------------------------------------------------------------------------
 * 1. Go to https://script.google.com and create a new project.
 * 2. Paste this entire file into Code.gs (replacing the default content).
 * 3. Open Project Settings (the cog icon, bottom-left) -> Script Properties
 *    -> Add script property, and create FOUR properties:
 *       CLIENT_ID      = Spotify Developer app Client ID
 *       CLIENT_SECRET  = Spotify Developer app Client Secret
 *       SHEET_ID       = the long ID from your Google Sheet URL
 *                        (between /d/ and /edit)
 *       NOTIFY_EMAIL   = email address that should receive submission
 *                        notifications
 * 4. In that same Google Sheet, the script will auto-create the tabs it
 *    needs on first use: "rsvp", "song_request", "preference_update".
 *    You can create them in advance if you prefer.
 * 5. Click Deploy -> New deployment -> Type: Web app.
 *       Execute as:     Me
 *       Who has access: Anyone
 *    Authorise the script when prompted (it needs Sheets, Mail, and external
 *    URL access). Copy the Web app URL it gives you.
 * 6. Paste that URL into js/config.js as appsScriptUrl.
 *
 * -------------------------------------------------------------------------
 * CORS NOTE
 * -------------------------------------------------------------------------
 * Apps Script web apps do not honour custom response headers — Google strips
 * them at the edge. We sidestep CORS by:
 *   - GET (token):  ContentService JSON. Browsers accept this cross-origin.
 *   - POST (forms): the client sends Content-Type: text/plain;charset=utf-8
 *     with a JSON string in the body. That is a CORS "simple request" so no
 *     preflight fires. This script reads e.postData.contents and parses it.
 * -------------------------------------------------------------------------
 */

var TOKEN_CACHE_KEY = 'spotify_token';
var TOKEN_CACHE_SECS = 3300; // 55 minutes (Spotify tokens last 60)

function props_() {
  return PropertiesService.getScriptProperties();
}

function getSpotifyToken() {
  var cache = CacheService.getScriptCache();
  var cached = cache.get(TOKEN_CACHE_KEY);
  if (cached) {
    return { token: cached };
  }

  var clientId = props_().getProperty('CLIENT_ID');
  var clientSecret = props_().getProperty('CLIENT_SECRET');
  if (!clientId || !clientSecret) {
    throw new Error('Missing CLIENT_ID or CLIENT_SECRET in Script Properties');
  }

  var auth = Utilities.base64Encode(clientId + ':' + clientSecret);
  var response = UrlFetchApp.fetch('https://accounts.spotify.com/api/token', {
    method: 'post',
    headers: { Authorization: 'Basic ' + auth },
    contentType: 'application/x-www-form-urlencoded',
    payload: 'grant_type=client_credentials',
    muteHttpExceptions: true
  });

  var data = JSON.parse(response.getContentText());
  if (!data.access_token) {
    throw new Error('Spotify token error: ' + response.getContentText());
  }
  cache.put(TOKEN_CACHE_KEY, data.access_token, TOKEN_CACHE_SECS);
  return { token: data.access_token };
}

function doGet(e) {
  var action = (e && e.parameter && e.parameter.action) || 'token';
  try {
    if (action === 'token') {
      return jsonOut_(getSpotifyToken());
    }
    return jsonOut_({ error: 'unknown action: ' + action });
  } catch (err) {
    return jsonOut_({ error: String((err && err.message) || err) });
  }
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      throw new Error('Missing request body');
    }
    var body = JSON.parse(e.postData.contents);
    var action = body.action;
    if (!action) {
      throw new Error('Missing action field');
    }
    if (['rsvp', 'song_request', 'preference_update'].indexOf(action) === -1) {
      throw new Error('Unsupported action: ' + action);
    }

    var sheet = openTab_(action);
    var row = buildRow_(action, body, new Date());
    sheet.appendRow(row);
    notify_(action, body);

    return jsonOut_({ success: true });
  } catch (err) {
    return jsonOut_({ success: false, error: String((err && err.message) || err) });
  }
}

function openTab_(name) {
  var sheetId = props_().getProperty('SHEET_ID');
  if (!sheetId) {
    throw new Error('Missing SHEET_ID in Script Properties');
  }
  var ss = SpreadsheetApp.openById(sheetId);
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headerFor_(name));
  } else if (sheet.getLastRow() === 0) {
    sheet.appendRow(headerFor_(name));
  }
  return sheet;
}

function headerFor_(action) {
  if (action === 'rsvp') {
    return ['Timestamp', 'guestCode', 'guestName', 'dietary', 'plusOne', 'evening', 'notes'];
  }
  if (action === 'song_request') {
    return ['Timestamp', 'guestCode', 'guestName', 'trackName', 'artistName', 'spotifyId', 'durationSecs'];
  }
  if (action === 'preference_update') {
    return ['Timestamp', 'guestCode', 'guestName', 'field', 'oldValue', 'newValue'];
  }
  return ['Timestamp', 'raw'];
}

function buildRow_(action, b, now) {
  if (action === 'rsvp') {
    return [now, b.guestCode || '', b.guestName || '', b.dietary || '', !!b.plusOne, !!b.evening, b.notes || ''];
  }
  if (action === 'song_request') {
    return [now, b.guestCode || '', b.guestName || '', b.trackName || '', b.artistName || '', b.spotifyId || '', Number(b.durationSecs) || 0];
  }
  if (action === 'preference_update') {
    return [now, b.guestCode || '', b.guestName || '', b.field || '', b.oldValue || '', b.newValue || ''];
  }
  return [now, JSON.stringify(b)];
}

function notify_(action, b) {
  var to = props_().getProperty('NOTIFY_EMAIL');
  if (!to) return;
  var who = (b.guestName || '(unknown)') + (b.guestCode ? ' [' + b.guestCode + ']' : '');
  var subject = 'Wedding site: ' + action;
  var lines = ['Submission received.', '', 'Guest: ' + who, 'Action: ' + action, ''];
  if (action === 'rsvp') {
    lines.push('Plus one: ' + !!b.plusOne);
    lines.push('Evening:  ' + !!b.evening);
    lines.push('Dietary:  ' + (b.dietary || '-'));
    lines.push('Notes:    ' + (b.notes || '-'));
  } else if (action === 'song_request') {
    lines.push('Track:       ' + (b.trackName || '-') + '  —  ' + (b.artistName || '-'));
    lines.push('Spotify ID:  ' + (b.spotifyId || '-'));
    lines.push('Duration:    ' + (b.durationSecs || '-') + ' s');
  } else if (action === 'preference_update') {
    lines.push('Field:    ' + (b.field || '-'));
    lines.push('Old:      ' + (b.oldValue || '-'));
    lines.push('New:      ' + (b.newValue || '-'));
  }
  MailApp.sendEmail(to, subject, lines.join('\n'));
}

function jsonOut_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

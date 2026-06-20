/*
 * build-guests.js — regenerate data/guests.json from data/guestlist.csv
 *
 * data/guestlist.csv is the SINGLE SOURCE OF TRUTH for the guest list.
 * Edit that file, then run:
 *
 *     node scripts/build-guests.js
 *
 * This reads the CSV, splits the pipe-separated "members" column into an
 * array, turns the TRUE/FALSE day/evening columns into real booleans, and
 * writes data/guests.json (pretty-printed). Do NOT edit guests.json by hand.
 *
 * No npm dependencies — plain Node core only.
 */

'use strict';

var fs = require('fs');
var path = require('path');

var ROOT = path.join(__dirname, '..');
var CSV_PATH = path.join(ROOT, 'data', 'guestlist.csv');
var JSON_PATH = path.join(ROOT, 'data', 'guests.json');

/**
 * Parse CSV text into an array of row-arrays.
 * Correctly handles double-quoted fields that contain commas, newlines,
 * and escaped quotes ("" -> ").
 */
function parseCsv(text) {
  // Strip a UTF-8 BOM if present.
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);

  var rows = [];
  var field = '';
  var row = [];
  var inQuotes = false;
  var i = 0;
  var len = text.length;

  function endField() { row.push(field); field = ''; }
  function endRow() { endField(); rows.push(row); row = []; }

  while (i < len) {
    var ch = text[i];

    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; } // escaped quote
        inQuotes = false; i++; continue;
      }
      field += ch; i++; continue;
    }

    if (ch === '"') { inQuotes = true; i++; continue; }
    if (ch === ',') { endField(); i++; continue; }
    if (ch === '\r') { i++; continue; } // ignore CR; \n drives row breaks
    if (ch === '\n') { endRow(); i++; continue; }
    field += ch; i++;
  }
  // Flush any trailing field/row that wasn't terminated by a newline.
  if (field !== '' || row.length > 0) endRow();

  return rows;
}

function toBool(v) {
  return String(v).trim().toUpperCase() === 'TRUE';
}

function main() {
  var raw = fs.readFileSync(CSV_PATH, 'utf8');
  var rows = parseCsv(raw).filter(function (r) {
    // Drop completely empty rows (e.g. a trailing blank line).
    return r.some(function (c) { return String(c).trim() !== ''; });
  });

  if (rows.length === 0) {
    console.error('No rows found in ' + CSV_PATH);
    process.exit(1);
  }

  var header = rows[0].map(function (h) { return h.trim(); });
  var idx = {};
  header.forEach(function (h, n) { idx[h] = n; });

  var required = ['code', 'greeting', 'members', 'day', 'evening', 'notes'];
  required.forEach(function (col) {
    if (!(col in idx)) {
      console.error('Missing required column: "' + col + '"');
      process.exit(1);
    }
  });

  var guests = [];
  var seen = {}; // lowercased code -> first original code seen
  var duplicates = [];

  for (var r = 1; r < rows.length; r++) {
    var cols = rows[r];
    var code = (cols[idx.code] || '').trim();
    if (!code) continue;

    var lc = code.toLowerCase();
    if (Object.prototype.hasOwnProperty.call(seen, lc)) {
      duplicates.push({ code: code, collidesWith: seen[lc] });
    } else {
      seen[lc] = code;
    }

    var members = (cols[idx.members] || '')
      .split('|')
      .map(function (m) { return m.trim(); })
      .filter(function (m) { return m !== ''; });

    guests.push({
      code: code,
      greeting: (cols[idx.greeting] || '').trim(),
      members: members,
      day: toBool(cols[idx.day]),
      evening: toBool(cols[idx.evening]),
      notes: (cols[idx.notes] || '').trim()
    });
  }

  fs.writeFileSync(JSON_PATH, JSON.stringify(guests, null, 2) + '\n', 'utf8');

  console.log('Wrote ' + guests.length + ' households to ' + path.relative(ROOT, JSON_PATH));

  if (duplicates.length) {
    console.warn('WARNING: ' + duplicates.length + ' duplicate code(s) found (case-insensitive):');
    duplicates.forEach(function (d) {
      console.warn('  "' + d.code + '" collides with "' + d.collidesWith + '"');
    });
    process.exitCode = 1;
  } else {
    console.log('No duplicate codes.');
  }
}

main();

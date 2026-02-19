# Map debug report — Leaflet not loading on travel pages

## Root cause

No single structural bug was found in the repo (paths, IDs, and CSS are correct). The most likely real-world cause of the map not loading and “raw HTML” appearing is:

- **Server returns an HTML page instead of JSON** when requesting `data/places.json` (e.g. GitHub Pages 404 or error page, or a redirect to an HTML document). The response `Content-Type` is then `text/html`. Calling `response.json()` on that can throw or produce invalid data, and the map never initialises. If any HTML is ever shown in the map area, it would be from that kind of response being handled incorrectly.

**Files verified:**

- **Paths:** Repo uses `data/places.json` and `js/map.js` (lowercase). HTML references match:
  - `/travel.html`: `data-places-url="data/places.json"`, `script src="js/map.js"`
  - `/test/travel.html`: `data-places-url="../data/places.json"`, `script src="../js/map.js"`
- **Script order:** Leaflet JS is loaded before `map.js` on both pages.
- **Duplicate IDs:** Only one `id="wedding-map"` per page.
- **CSS:** `.leaflet-map` has non-zero height (420px; 360px on small screens) in `styles.css` with no overriding rule zeroing it.

## Changes made

- **`/js/map.js`**
  - **Content-Type check:** Before calling `response.json()`, the response `Content-Type` header is checked. If it includes `text/html`, the request is treated as an error (typical for 404/error HTML pages). A clear error is thrown and the friendly message is shown.
  - **Error payload:** Fetch failures (non-ok status or HTML response) attach `status` and `contentType` to the error so the debug UI can show them.
  - **Debug mode:** If the page URL contains `?debug=1`, a small diagnostics panel is rendered above the map container showing: Leaflet loaded?, places.json URL, fetch status code + content-type, JSON parse success, and number of places loaded. In normal mode no panel is shown.
  - **Friendly failure message:** On any failure, the map container shows a short message and, in debug mode, appends `[Debug: status …; content-type …]` so you can see why the request failed without relying on the console.

- **`/styles.css`**
  - Added `.map-debug-panel` (and `pre` inside it) so the debug panel is readable and doesn’t break layout.

- **`/MAP_DEBUG_REPORT.md`**
  - This file: root cause, list of changes, and how to verify.

### Additional patch (map initialises but renders blank / tile issues)

- **`/js/map.js`**
  - **HTTPS tile URL:** Tile layer explicitly uses `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (no mixed content). Attribution is set for OpenStreetMap contributors.
  - **DOM-ready init:** Init already runs after DOM is ready: if `document.readyState === 'loading'` we wait for `DOMContentLoaded`, otherwise we run immediately.
  - **Blank map fix:** After creating the map and adding the tile layer we call `setTimeout(function () { map.invalidateSize(); }, 250)` so the map recalculates size once the container has settled. We also add `window.addEventListener('resize', function () { map.invalidateSize(); })` so the map updates on window resize.
  - **Tile error diagnostics (debug mode):** When `?debug=1` is in the URL, the tile layer has a `tileerror` listener. The debug panel shows a line “Tile errors: N” that increments on each tile load failure (e.g. mixed-content blocking or network errors). Confirms whether tiles are being blocked.

## How to verify

### Locally

1. **Normal load**
   - Open `/travel.html` (e.g. `file:///.../travel.html` or via a local server).
   - Map should load if `data/places.json` is served as JSON. If you use `file://`, fetch may be blocked by CORS; use a local server (e.g. `npx serve .` or your editor’s live server).

2. **Debug panel**
   - Open `/travel.html?debug=1` (and optionally `/test/travel.html?debug=1`).
   - A small panel above the map should show: Leaflet loaded?, places URL, Fetch status, Content-Type, JSON parse result, Places loaded count, Tile errors: N (N increments if any tile requests fail).

3. **Simulated HTML response**
   - Temporarily point `data-places-url` at an HTML page (e.g. `travel.html`) and reload. You should see the friendly “Map failed to load…” message and, with `?debug=1`, status and content-type indicating HTML.

### GitHub Pages

- **Root travel:** `https://<user>.github.io/<repo>/travel.html`  
  Uses `data/places.json` and `js/map.js` (relative to repo root). Ensure the repo has `data/places.json` and `js/map.js` in lowercase; GitHub Pages is case-sensitive.
- **Test travel:** `https://<user>.github.io/<repo>/test/travel.html`  
  Uses `../data/places.json` and `../js/map.js`.
- Add `?debug=1` to either URL to see the diagnostics panel and confirm fetch status, content-type, and tile error count if the map still fails.

### Blank map / tiles

- If the map area is present but grey or blank, the `invalidateSize()` delay and resize listener should help after layout settles. Reload and wait a moment, or resize the window.
- With `?debug=1`, check “Tile errors: N”. If N increases, tiles are being blocked (e.g. mixed content or network). Ensure the tile URL is HTTPS (it is in code) and that the page is served over HTTPS on GitHub Pages.

### Case-sensitivity (GitHub Pages)

If the map works locally but not on GitHub Pages, check that paths are exactly:

- `data/places.json` (not `Data/places.json` etc.)
- `js/map.js` (not `JS/map.js` etc.)

To fix case-only renames on Windows, use a two-step rename, e.g.:

```bash
git mv data temp-data && git mv temp-data Data   # only if you had wrong case
```

Then update HTML to use the correct lowercase paths as above.

---

## Build 20260219a

### What changed

- **Cache busting:** Script and data URLs now include a query string so browsers and CDNs don’t serve old copies.
  - **`/travel.html`:** `script src="js/map.js?v=20260219a" defer` and `data-places-url="data/places.json?v=20260219a"`.
  - **`/test/travel.html`:** `script src="../js/map.js?v=20260219a" defer` and `data-places-url="../data/places.json?v=20260219a"`.
  - Leaflet script also has `defer`; order is still Leaflet first, then `map.js`.

- **Proof that map.js runs:** As soon as `map.js` runs it sets `window.__WEDDING_MAP_JS_LOADED__ = "20260219a"` and logs `"map.js loaded"` plus the build and `location.href` to the console. In the console you can also type `window.__WEDDING_MAP_JS_LOADED__` to confirm the script executed.

- **Debug banner (always when `?debug=1`):** If the URL has `debug=1`, a banner is created at the very top of `<body>` **before** any Leaflet or fetch logic. It shows: **"Map debug active — build 20260219a"**. It is created immediately, or on `DOMContentLoaded` if `document.body` is not yet available. This banner appears even when the map div is missing or Leaflet failed to load, so you can tell that `map.js` ran and debug mode is on.

- **First runtime error on-page:** When `debug=1`, global listeners are added for `window` `error` and `unhandledrejection`. The **first** error or unhandled rejection is appended to the debug banner as a new line: **"Runtime error: &lt;message&gt;"**. So you can see the first failure without opening the console.

- Existing behaviour is unchanged: debug panel (fetch status, content-type, places count, tile errors), content-type hardening, and tileerror counter still apply when the map container and Leaflet are present.

### What to check in the browser

1. Open **`travel.html?debug=1`** (or your full URL, e.g. `https://<user>.github.io/<repo>/travel.html?debug=1`).
2. You should **always** see the banner at the top: **"Map debug active — build 20260219a"** if `map.js` has run and the URL has `debug=1`. If you don’t see it, `map.js` did not execute (script path, syntax error before the banner, or caching).
3. In the console, confirm **"map.js loaded"** and `window.__WEDDING_MAP_JS_LOADED__ === "20260219a"`.
4. If something throws or a promise rejects, the **first** error text appears under the banner as **"Runtime error: …"**.
5. Below that, the existing debug panel (above the map) still shows fetch/content-type/places/tile errors when the map container exists and Leaflet is loaded.

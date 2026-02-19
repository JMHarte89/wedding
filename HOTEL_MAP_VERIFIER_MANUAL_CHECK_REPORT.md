# Hotel Map Verifier – Manual check pass

**Date:** 2026-02-19  
**Baseline:** `/data/places.json`  
**Rules:** No file edits; recommend coordinate changes only when difference >150 m; prefer OSM/GetTheData/official sources.

---

## 1. Places in scope (hotels + camping from places.json)

All 26 accommodation/camping places were considered. The subset below was marked “Needs manual check” in the prior audit and was verified in this pass using authoritative coordinate sources where available.

---

## 2. Verification summary

| Place | Address / postcode | Source | Verified lat,lng | Current lat,lng | Δ (approx) | Fix? |
|-------|-------------------|--------|-------------------|------------------|-------------|------|
| Riverside Hotel Kendal | Beezon Road, Kendal LA9 6FS | OSM | 54.330506, -2.741900 | 54.330502, -2.741897 | ~5 m | No |
| Stonecross Manor Hotel | 84 Milnthorpe Road, Kendal LA9 5HP | — | — | 54.313049, -2.752831 | — | Needs manual check (no coord source used) |
| Premier Inn Kendal Central | Maude Street, Kendal LA9 4QG | GetTheData LA9 4QG | 54.330866, -2.747990 | 54.327233, -2.749353 | ~400 m | **Yes** |
| Kendal Hostel | 118–120 Highgate, Kendal LA9 4HE | GetTheData LA9 4HE | 54.325365, -2.748122 | 54.324602, -2.747581 | ~100 m | No |
| Damson Dene Hotel | Crosthwaite, Lyth Valley LA8 8JE | GetTheData LA8 8JE | 54.318397, -2.891213 | 54.31399, -2.88427 | ~700 m | **Yes** |
| Days Inn Kendal (Killington Lake) | Killington Lake / M6 | — | — | 54.240236, -2.771677 | — | Needs manual check (no postcode/coord source used) |
| Linthwaite House | Crook Road, Bowness LA23 3JA | findthatpostcode LA23 3JA | 54.352286, -2.91318 | 54.352286, -2.91318 | 0 m | No |
| Low Wood Bay Resort & Spa | Ambleside Road, Windermere LA23 1LP | Doogal LA23 1LP | 54.410257, -2.947919 | 54.412399, -2.946218 | ~250 m | **Yes** |
| Lakes Hotel & Spa | Lake Road, Bowness LA23 3HH | GetTheData LA23 3HH | 54.361498, -2.920356 | 54.360009, -2.920256 | ~165 m | **Yes** |
| The Belsfield Hotel (Bowness-on-Windermere) | Kendal Road, Bowness LA23 3EL | GeoHack Belsfield Hotel | 54.36177, -2.92101 | 54.3618, -2.9211 | ~15 m | No |
| The Samling Hotel (Windermere/Troutbeck) | Ambleside Road, Windermere LA23 1LR | GeoHack The Samling Hotel | 54.41466, -2.95076 | 54.41465, -2.95084 | ~10 m | No |
| YHA Windermere | Bridge Lane, Troutbeck LA23 1LA | — | — | 54.403862, -2.917495 | — | Needs manual check (LA23 1LA area coords not tied to Bridge Lane) |
| YHA Ambleside | Ambleside | — | — | 54.419161, -2.961748 | — | Needs manual check (no coord source used) |
| Kendal Club Campsite (Caravan and Motorhome Club) | — | — | — | 54.28166, -2.75658 | — | Needs manual check |
| Kendal Camping & Caravanning Club Site | — | — | — | 54.3465, -2.7307 | — | Needs manual check |
| Park Cliffe | — | — | — | 54.312059, -2.937711 | — | Needs manual check |
| Low Wray Campsite | — | — | — | 54.400864, -2.96611 | — | Needs manual check |
| Skelwith Fold Caravan Park | — | — | — | 54.411763, -2.985365 | — | Needs manual check |

---

## 3. Corrections table (full fields)

| name | category | current lat,lng | verified lat,lng | current URL | verified URL | verified address | fix needed | notes | sources |
|------|----------|----------------|------------------|-------------|--------------|------------------|-----------|------|---------|
| Premier Inn Kendal Central | hotel | 54.327233, -2.749353 | 54.330866, -2.747990 | premierinn.com/…/kendal-central.html | same | Maude Street, Kendal LA9 4QG | Yes | Postcode centre ~400 m from current pin | [GetTheData LA9 4QG](https://www.getthedata.com/postcode/LA9-4QG) |
| Damson Dene Hotel | hotel | 54.31399, -2.88427 | 54.318397, -2.891213 | damsondene.co.uk | same | Crosthwaite, LA8 8JE | Yes | Postcode centre ~700 m from current pin; FSA lists Damson Dene at this postcode | [GetTheData LA8 8JE](https://www.getthedata.com/postcode/LA8-8JE) |
| Low Wood Bay Resort & Spa | hotel | 54.412399, -2.946218 | 54.410257, -2.947919 | englishlakes.co.uk/low-wood-bay | same | Ambleside Road, Windermere LA23 1LP | Yes | Postcode centre ~250 m from current pin | Doogal [LA23 1LP](https://www.doogal.co.uk/ShowMap?postcode=LA23+1LP) |
| Lakes Hotel & Spa | hotel | 54.360009, -2.920256 | 54.361498, -2.920356 | lakeshotel.co.uk | same | Bowness-on-Windermere LA23 3HH | Yes | Postcode centre ~165 m from current pin | [GetTheData LA23 3HH](https://www.getthedata.com/postcode/LA23-3HH) |

All other checked places: **No** (within 150 m) or **Needs manual check** (no authoritative coord source used in this pass).

---

## 4. Patch-ready outputs

### A) JSON snippets (for `places.json` only where fix needed)

Apply only if you choose to update `/data/places.json` from this report (no automatic edits were made).

```json
{ "name": "Premier Inn Kendal Central", "lat": 54.330866, "lng": -2.74799, "url": "https://www.premierinn.com/gb/en/hotels/england/cumbria/kendal/kendal-central.html" }
```

```json
{ "name": "Damson Dene Hotel", "lat": 54.318397, "lng": -2.891213, "url": "https://www.damsondene.co.uk/" }
```

```json
{ "name": "Low Wood Bay Resort & Spa", "lat": 54.410257, "lng": -2.947919, "url": "https://englishlakes.co.uk/low-wood-bay/" }
```

```json
{ "name": "Lakes Hotel & Spa", "lat": 54.361498, "lng": -2.920356, "url": "https://www.lakeshotel.co.uk/" }
```

### B) Updated CSV rows only (for `/test/HOTELS.md` CSV block)

Replace only these four rows in the CSV; leave all other rows unchanged.

```csv
Premier Inn Kendal Central,hotel,54.330866,-2.74799,https://www.premierinn.com/gb/en/hotels/england/cumbria/kendal/kendal-central.html,£
Damson Dene Hotel,hotel,54.318397,-2.891213,https://www.damsondene.co.uk/,££
Low Wood Bay Resort & Spa,hotel,54.410257,-2.947919,https://englishlakes.co.uk/low-wood-bay/,£££
Lakes Hotel & Spa,hotel,54.361498,-2.920356,https://www.lakeshotel.co.uk/,£££
```

---

**End of report.** No files were modified by this pass.

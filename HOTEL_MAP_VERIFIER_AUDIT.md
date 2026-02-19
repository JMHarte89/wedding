# Hotel Map Verifier — Audit Report

**Date:** 2026-02-19  
**Scope:** All hotel, hostel, and camping entries in `/data/places.json` and `/test/HOTELS.md` CSV.  
**Rules:** No file edits; UK spelling; patch-ready snippets only for corrections.

---

## 1. Extract + reconcile repo data

### 1.1 Places in `places.json` (layer = hotels or camping)

| # | Name (repo) | Layer |
|---|-------------|--------|
| 1 | Riverside Hotel Kendal | hotels |
| 2 | Castle Green Hotel Kendal | hotels |
| 3 | Stonecross Manor Hotel | hotels |
| 4 | Premier Inn Kendal Central | hotels |
| 5 | Travelodge Kendal Town Centre (Riverside Place) | hotels |
| 6 | Travelodge Kendal (Prizet, LA8 8AA) | hotels |
| 7 | Kendal Hostel | hotels |
| 8 | The Lakeland Kendal Hotel | hotels |
| 9 | Damson Dene Hotel | hotels |
| 10 | The Punch Bowl Inn | hotels |
| 11 | Crooklands Hotel | hotels |
| 12 | Days Inn Kendal (Killington Lake) | hotels |
| 13 | Gilpin Hotel & Lake House | hotels |
| 14 | Linthwaite House | hotels |
| 15 | Low Wood Bay Resort & Spa | hotels |
| 16 | Lakes Hotel & Spa | hotels |
| 17 | The Belsfield Hotel (Bowness-on-Windermere) | hotels |
| 18 | Langdale Chase Hotel (Windermere) | hotels |
| 19 | The Samling Hotel (Windermere/Troutbeck) | hotels |
| 20 | YHA Windermere | hotels |
| 21 | YHA Ambleside | hotels |
| 22 | Kendal Club Campsite (Caravan and Motorhome Club) | camping |
| 23 | Kendal Camping & Caravanning Club Site | camping |
| 24 | Park Cliffe | camping |
| 25 | Low Wray Campsite | camping |
| 26 | Skelwith Fold Caravan Park | camping |

**Key venues (for context only, not audited):** Holy Trinity Kendal Parish Church (ceremony), The Venue (Kendal) (reception).

### 1.2 CSV block in `/test/HOTELS.md`

The CSV has columns: `name,category,lat,lng,url,price`. It contains **26 rows**, one per accommodation/camping place above. All 26 names in the CSV match `places.json` exactly (same naming and order).

### 1.3 Reconciliation

| Check | Result |
|-------|--------|
| **In places.json but missing from CSV** | None. All 26 hotels/camping entries appear in the CSV. |
| **In CSV but missing from places.json** | None. All 26 CSV rows have a matching place in places.json. |
| **Name mismatches (same property, different name)** | None between CSV and places.json. |
| **HOTELS.md prose vs CSV/places.json** | **Out of sync:** Sections 1–5 in HOTELS.md list coords and sometimes names that do not match the CSV/places.json (e.g. Castle Green listed as “Castle Green Hotel” without “Kendal”; The Lakeland Kendal Hotel shown as 54.332862, -2.747721 in prose but 54.33114, -2.74041 in data; Lake District section lists old coords for Gilpin, Belsfield, Langdale Chase, Samling). **Recommendation:** Treat CSV as single source of truth; update prose in HOTELS.md to match CSV (names + coords) in a separate editorial pass. |
| **Missing from HOTELS.md prose list** | **Kendal Club Campsite (Caravan and Motorhome Club)** appears in places.json and CSV but is not listed in the “5. Camping / glamping” prose (only four camping sites are named there). |

---

## 2. Web verification (per place)

Authoritative sources used: GetTheData.com (postcodes), GeoHack/Wikipedia (landmarks), official hotel/chain pages, listing sites (e.g. MapQuest, Visit Lake District). Where no coordinate-bearing source was found, “Needs manual check” is used.

### Priority places (verified first)

- **Travelodge Kendal Town Centre (Riverside Place)**  
  - Identity: Town-centre property, Riverside Place, Lound Road, Kendal, LA9 7FW.  
  - GetTheData LA9 7FW: **54.319839, -2.743610**. Repo: 54.31983, -2.74361. Match.  
  - URL: travelodge.co.uk/hotels/675/Kendal-Town-Centre-hotel — correct property page.  
  - **Verdict:** Correct property; coords and URL correct.

- **Travelodge Kendal (Prizet, LA8 8AA)**  
  - Identity: Out-of-centre property, A591, Prizet, Kendal, LA8 8AA (distinct from Town Centre).  
  - findthatpostcode.uk / ONS: LA8 8AA **54.297604, -2.75948**. Repo: 54.297604, -2.759481. Match.  
  - URL: travelodge.co.uk/hotels/330/Kendal-hotel — correct property page.  
  - **Verdict:** Correct property; coords and URL correct.

- **Langdale Chase Hotel (Windermere)**  
  - Identity: Ambleside Road, Ecclerigg, Windermere, LA23 1LW.  
  - GeoHack (Wikipedia): **54.406, -2.946**. Repo: 54.4069, -2.9464. Within ~100 m.  
  - URL: langdalechase.co.uk — official.  
  - **Verdict:** Correct property; coords and URL correct.

- **Gilpin Hotel & Lake House**  
  - Identity: Crook Road, Windermere, LA23 3NE.  
  - Apple Maps / listing: **54.3554121, -2.8805047**. Repo: 54.35535, -2.88047. Match.  
  - URL: thegilpin.co.uk — official.  
  - **Verdict:** Correct property; coords and URL correct.

- **The Samling Hotel (Windermere/Troutbeck)**  
  - Identity: Ambleside Road, Windermere, LA23 1LR.  
  - No coordinate-bearing authoritative source retrieved in this run. Repo: 54.41465, -2.95084.  
  - URL: thesamlinghotel.co.uk — official.  
  - **Verdict:** Correct property and URL; coords **Needs manual check** (e.g. OSM/Nominatim or LA23 1LR postcode lookup).

### Remaining places (concise)

- **Riverside Hotel Kendal** — riversidekendal.co.uk. Repo 54.330502, -2.741897. No coords source fetched; **Needs manual check** for lat/lng.
- **Castle Green Hotel Kendal** — castlegreenhotel.co.uk. Repo 54.324159, -2.720953. GetTheData LA9 6RG (from prior run) ~54.32385, -2.72100; close. URL correct.
- **Stonecross Manor Hotel** — 84 Milnthorpe Road, Kendal LA9 5HP; everbrightgrouphotels.com/stonecross-manor-leisure. Repo 54.313049, -2.752831. URL correct; coords **Needs manual check** (e.g. LA9 5HP).
- **Premier Inn Kendal Central** — Maude Street, Kendal LA9 4QG; premierinn.com property page. Repo 54.327233, -2.749353. URL correct; coords **Needs manual check** (e.g. LA9 4QG).
- **Kendal Hostel** — 118–120 Highgate, Kendal LA9 4HE (from official site / prior run); kendalhostel.co.uk. Repo 54.324602, -2.747581. URL correct; coords **Needs manual check**.
- **The Lakeland Kendal Hotel** — Station Road, Kendal LA9 6BT (Mapcarta); aghotels.co.uk/the-lakeland-hotel. Repo 54.33114, -2.74041. URL correct; coords align with prior verification.
- **Damson Dene Hotel** — Crosthwaite, Lyth Valley, LA8 8JE; damsondene.co.uk. Repo 54.31399, -2.88427. URL correct; coords **Needs manual check** (e.g. LA8 8JE).
- **The Punch Bowl Inn** — Crosthwaite, Lyth Valley, LA8 8HR; thepunchbowlinn.co.uk. One listing: ~54.3132, -2.8527; repo 54.31358, -2.853586. Close. URL correct.
- **Crooklands Hotel** — Crooklands, LA7 7NW; thecrooklands.com. Doogal LA7 7NW ~54.24678, -2.71568; repo 54.24644, -2.7156. Match. URL correct.
- **Days Inn Kendal (Killington Lake)** — Wyndham property page; motorway stopover. Repo 54.240236, -2.771677. URL correct; coords **Needs manual check**.
- **Linthwaite House** — Crook Road, Bowness-on-Windermere LA23 3JA; linthwaitehouse.co.uk. Repo 54.352286, -2.91318. URL correct; coords **Needs manual check**.
- **Low Wood Bay Resort & Spa** — Ambleside Road, Windermere LA23 1LP; englishlakes.co.uk/low-wood-bay. Repo 54.412399, -2.946218. URL correct; coords **Needs manual check**.
- **Lakes Hotel & Spa** — Lake Road, Bowness-on-Windermere LA23 3HH; lakeshotel.co.uk. Repo 54.360009, -2.920256. URL correct; coords **Needs manual check**.
- **The Belsfield Hotel (Bowness-on-Windermere)** — Kendal Road, Bowness LA23 3EL; lake-district-hotels.co.uk/the-belsfield. Repo 54.3618, -2.9211. URL correct; coords **Needs manual check** (e.g. LA23 3EL).
- **YHA Windermere** — Bridge Lane, Troutbeck, LA23 1LA; yha.org.uk/hostel/yha-windermere. Repo 54.403862, -2.917495. URL correct; coords **Needs manual check**.
- **YHA Ambleside** — yha.org.uk/hostel/yha-ambleside. Repo 54.419161, -2.961748. URL correct; coords **Needs manual check**.
- **Kendal Club Campsite (Caravan and Motorhome Club)** — caravanclub.co.uk club site. Repo 54.28166, -2.75658. URL correct; coords **Needs manual check**.
- **Kendal Camping & Caravanning Club Site** — campingandcaravanningclub.co.uk. Repo 54.3465, -2.7307. URL correct; coords **Needs manual check**.
- **Park Cliffe** — parkcliffe.co.uk. Repo 54.312059, -2.937711. URL correct; coords **Needs manual check**.
- **Low Wray Campsite** — nationaltrust.org.uk/visit/lakes/low-wray-campsite. Repo 54.400864, -2.96611. URL correct; coords **Needs manual check**.
- **Skelwith Fold Caravan Park** — skelwithfold.co.uk. Repo 54.411763, -2.985365. URL correct; coords **Needs manual check**.

---

## 3. Duplicate detection

- **Same/similar name:** No duplicates. “Riverside Hotel Kendal” vs “Castle Green Hotel Kendal” are different properties (different addresses, brands, ownership).
- **Same domain / same property page:** No duplicate entries. Each URL is a single property (chain property pages are distinct: 675 vs 330 for Travelodges).
- **Coords within ~150 m:** No two accommodation entries share the same or near-identical pin. Travelodge Town Centre (LA9 7FW) and Prizet (LA8 8AA) are clearly separated.

**Conclusion:** No duplicates. No merge or rename required.

---

## 4. Corrections pack (audit table)

| Place name (repo) | Category | Current lat,lng | Verified lat,lng | Current URL | Verified URL | Verified address | Fix needed? | Notes | Sources |
|-------------------|----------|-----------------|------------------|-------------|--------------|------------------|-------------|-------|---------|
| Riverside Hotel Kendal | hotel | 54.330502, -2.741897 | — | riversidekendal.co.uk | same | Kendal (riverside) | Needs manual check | Coords not verified this run | Official site; no coord source |
| Castle Green Hotel Kendal | hotel | 54.324159, -2.720953 | ~54.32385, -2.72100 (LA9 6RG) | castlegreenhotel.co.uk | same | Kendal, edge of town (LA9 6RG) | No | Close to LA9 6RG | GetTheData LA9 6RG; castlegreenhotel.co.uk |
| Stonecross Manor Hotel | hotel | 54.313049, -2.752831 | — | everbrightgrouphotels.com/stonecross-manor-leisure | same | 84 Milnthorpe Road, Kendal LA9 5HP | Needs manual check | Coords not verified this run | Everbright; hotelplanner; TripAdvisor |
| Premier Inn Kendal Central | hotel | 54.327233, -2.749353 | — | premierinn.com/…/kendal-central.html | same | Maude Street, Kendal LA9 4QG | Needs manual check | Coords not verified this run | Premier Inn; directory listings |
| Travelodge Kendal Town Centre (Riverside Place) | hotel | 54.31983, -2.74361 | 54.319839, -2.743610 | travelodge.co.uk/hotels/675/… | same | Riverside Place, Lound Road, Kendal LA9 7FW | No | Coords match postcode | GetTheData LA9 7FW; Travelodge 675 |
| Travelodge Kendal (Prizet, LA8 8AA) | hotel | 54.297604, -2.759481 | 54.297604, -2.75948 | travelodge.co.uk/hotels/330/… | same | A591, Prizet, Kendal LA8 8AA | No | Coords match postcode | findthatpostcode LA8 8AA; Travelodge 330 |
| Kendal Hostel | hostel | 54.324602, -2.747581 | — | kendalhostel.co.uk | same | 118–120 Highgate, Kendal LA9 4HE | Needs manual check | Coords not verified this run | kendalhostel.co.uk |
| The Lakeland Kendal Hotel | hotel | 54.33114, -2.74041 | — | aghotels.co.uk/the-lakeland-hotel | same | Station Road, Kendal LA9 6BT | No | Prior run verified; Mapcarta | Mapcarta; aghotels |
| Damson Dene Hotel | hotel | 54.31399, -2.88427 | — | damsondene.co.uk | same | Crosthwaite, Lyth Valley LA8 8JE | Needs manual check | Coords not verified this run | damsondene.co.uk/find-and-contact |
| The Punch Bowl Inn | hotel | 54.31358, -2.853586 | ~54.3132, -2.8527 | thepunchbowlinn.co.uk | same | Crosthwaite, Lyth Valley LA8 8HR | No | Close to listing coords | leadingrestaurants; whatpub; MapQuest |
| Crooklands Hotel | hotel | 54.24644, -2.7156 | 54.24678, -2.71568 (LA7 7NW) | thecrooklands.com | same | Crooklands, LA7 7NW | No | Coords match area | Doogal LA7 7NW; crooklands.com; Wikipedia Crooklands |
| Days Inn Kendal (Killington Lake) | hotel | 54.240236, -2.771677 | — | wyndhamhotels.com/…/days-inn-kendal-killington-lake/overview | same | Killington Lake / M6 area | Needs manual check | Coords not verified this run | Wyndham property page |
| Gilpin Hotel & Lake House | hotel | 54.35535, -2.88047 | 54.35541, -2.88050 | thegilpin.co.uk | same | Crook Road, Windermere LA23 3NE | No | Coords match | Apple Maps; MapQuest; thegilpin.co.uk |
| Linthwaite House | hotel | 54.352286, -2.91318 | — | linthwaitehouse.co.uk | same | Crook Road, Bowness-on-Windermere LA23 3JA | Needs manual check | Coords not verified this run | linthwaitehouse.co.uk; visitlakedistrict |
| Low Wood Bay Resort & Spa | hotel | 54.412399, -2.946218 | — | englishlakes.co.uk/low-wood-bay | same | Ambleside Road, Windermere LA23 1LP | Needs manual check | Coords not verified this run | englishlakes.co.uk; MapQuest |
| Lakes Hotel & Spa | hotel | 54.360009, -2.920256 | — | lakeshotel.co.uk | same | Lake Road, Bowness-on-Windermere LA23 3HH | Needs manual check | Coords not verified this run | lakeshotel.co.uk; booking.com |
| The Belsfield Hotel (Bowness-on-Windermere) | hotel | 54.3618, -2.9211 | — | lake-district-hotels.co.uk/the-belsfield | same | Kendal Road, Bowness LA23 3EL | Needs manual check | Coords not verified this run | britishlistedbuildings; wikiaccommodation |
| Langdale Chase Hotel (Windermere) | hotel | 54.4069, -2.9464 | 54.406, -2.946 | langdalechase.co.uk | same | Ambleside Road, Ecclerigg, Windermere LA23 1LW | No | Within ~100 m of GeoHack | GeoHack/Wikipedia Langdale Chase; langdalechase.co.uk |
| The Samling Hotel (Windermere/Troutbeck) | hotel | 54.41465, -2.95084 | — | thesamlinghotel.co.uk | same | Ambleside Road, Windermere LA23 1LR | Needs manual check | Coords not verified this run | thesamlinghotel.co.uk; MapQuest |
| YHA Windermere | hostel | 54.403862, -2.917495 | — | yha.org.uk/hostel/yha-windermere | same | Bridge Lane, Troutbeck LA23 1LA | Needs manual check | Coords not verified this run | YHA; booking.com |
| YHA Ambleside | hostel | 54.419161, -2.961748 | — | yha.org.uk/hostel/yha-ambleside | same | — | Needs manual check | Coords not verified this run | YHA |
| Kendal Club Campsite (Caravan and Motorhome Club) | camping | 54.28166, -2.75658 | — | caravanclub.co.uk/…/kendal-club-campsite/ | same | — | Needs manual check | Coords not verified this run | Caravan Club |
| Kendal Camping & Caravanning Club Site | camping | 54.3465, -2.7307 | — | campingandcaravanningclub.co.uk/…/kendal/ | same | — | Needs manual check | Coords not verified this run | C&CC |
| Park Cliffe | camping | 54.312059, -2.937711 | — | parkcliffe.co.uk | same | — | Needs manual check | Coords not verified this run | parkcliffe.co.uk |
| Low Wray Campsite | camping | 54.400864, -2.96611 | — | nationaltrust.org.uk/…/low-wray-campsite | same | — | Needs manual check | Coords not verified this run | National Trust |
| Skelwith Fold Caravan Park | camping | 54.411763, -2.985365 | — | skelwithfold.co.uk | same | — | Needs manual check | Coords not verified this run | skelwithfold.co.uk |

---

## 5. Patch-ready outputs

**No changes are required** to `places.json` or to the CSV in `test/HOTELS.md` for the 26 entries audited. All URLs are canonical (official or correct property pages). Verified coordinates either match the repo or are within an acceptable tolerance; the rest are marked “Needs manual check” and no patch is proposed without a verified source.

Therefore:

- **A) JSON snippets:** None (no fixes).
- **B) Updated CSV block:** Not provided; keep the existing CSV as-is.

### Optional follow-up (no patch from this audit)

- **Manual checks:** For every row marked “Needs manual check”, run a postcode/address lookup (e.g. GetTheData, Nominatim, or official site map) and only then update lat/lng if they differ.
- **HOTELS.md prose:** Update sections 1–5 so that names and coords match the CSV (and add **Kendal Club Campsite (Caravan and Motorhome Club)** to the camping list).

---

**End of audit.**

# Changelog

## [Unreleased] Sargassum naming and bounded composite retrieval

### Changed
- Rename user-facing section from `Offshore floating algae` to `Offshore sargassum` in strings, layouts and backend wording.
- Live USF sargassum search requests only `7DAY` products and selects the closest valid composite ending date within a bounded lookback.
- Display exact `period_start` to `period_end` and elapsed age (`ended N days ago`) on the algae/sargassum card and evidence sheet.
- Qualify sargassum detection as rendered-image color matching; do not imply measured biomass, density or beaching severity.
- Update `floating_sargassum_card_poc.py` status strings and source language to `sargassum`.
- Add `SnorkelFormat.periodAge()` and extend backend tests for exact sargassum provenance and qualified wording.

## [Unreleased] UI polish from first-run feedback

### Changed
- Replace the toolbar’s up-arrow refresh icon with a proper `ic_refresh` and `Refresh sources` accessibility label.
- Replace clipped-oval replay banner with a rounded amber banner that reads `Recorded demo · sources have different dates`.
- Format capture/retrieval times to `America/New_York` local time, e.g. `Retrieved Sep 14, 1:10 PM EDT · capture time unverified`.
- Map raw backend statuses to plain-language labels (`Stream active, capture time unverified`, `Earlier view`, etc.).
- Make the evidence sheet a scrollable `NestedScrollView` with a clearer drag handle and padding.
- Show wind and rain as separate, populated sections in the evidence sheet.
- Preserve camera image aspect ratio with `centerInside` so sample-region labels remain readable.

## [Milestone 2] Snorkel Conditions — live source fetch and separation

### Added
- `?mode=live` query parameter on `/api/snorkel-conditions` that runs the live camera, weather and offshore-algae PoCs and keeps `mode=recorded_replay` as the default.
- Live runner in `backend/app/routers/snorkel_conditions.py` that fetches camera health, runs the water-appearance PoC, fetches Open-Meteo weather and does a bounded USF sargassum search.
- `live-check` cache as the live source directory; cached results are retained when a live source fails, never silently replaced with the recorded demo.
- `age_minutes` and `local_conditions_verified` on `CameraHealthObservation`; `framing_verified` on `WaterAppearanceObservation` to gate automated colour claims.
- Human-readable `ageLabel` for camera age (e.g. "22 min old", "7 days old") and a `cameraTime` formatter that separates capture, provider label and retrieval time.
- `/fixtures/live` static mount for live-cache images.
- Updated `backend/tests/test_snorkel_conditions.py` with age/framing provenance and a live-mode reachability test.

### Changed
- `HomeFragment` now loads the recorded replay on open and fetches `?mode=live` on the refresh action.
- Live appearance results are shown for visual review only; colour headline and samples are suppressed until framing is verified.
- `NetworkModule` read timeout raised to 180s to tolerate live PoC runtime.

### Notes
- Live mode attempts to fetch each source independently. Failures are isolated; other cards remain usable.
- USF composite search bounds itself to the latest valid date within the last 5 days and reports the exact composite period.
- Surface motion and C-16 remain experimental/informational.

## [Milestone 1] Snorkel Conditions — recorded replay parity

### Added
- Backend `/api/snorkel-conditions` endpoint that serves a combined, provenance-preserving contract built from the devin-handoff PoC outputs.
- Pydantic models in `backend/app/models/snorkel_conditions.py`: camera health, water appearance, wind/rain, offshore algae, C-16 info, and developer-only surface motion.
- Static fixture mounting at `/fixtures` so the Android client can load the shipped camera, appearance, algae and motion images over HTTP.
- Android `SnorkelConditionsResponse` data model, `SnorkelApiService`, `SnorkelConditionsRepository`, `SnorkelViewModel` and `SnorkelUiState`.
- Camera-first `HomeFragment` with recorded-replay banner, hero camera card, wind, rain, algae and C-16 cards.
- `EvidenceBottomSheet` showing the selected camera’s source times, colour samples, source link and limitations.
- Coil image loading, dark marine colour theme, and updated navigation graph.
- Parity unit tests in `backend/tests/test_snorkel_conditions.py` verifying the contract and fixture image reachability.

### Notes
- This build uses the **recorded replay** from the handoff package; it is intentionally not live and each source keeps its own observed timestamp.
- Surface motion remains developer-only and is not shown on the Home screen.
- No live source adapters, caching, or device-side image processing in this milestone.

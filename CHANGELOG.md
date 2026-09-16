# Changelog

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

# Palm Beach Plume Tracker — UI/UX Design Specification

Version 1.0 • September 11, 2026 • Implementation handoff
Companion to [technical-specification.md](technical-specification.md), v0.2.

## 1. Purpose and authority

Build the coastal Android interface shown in [the visual concept](assets/palm-beach-plume-tracker-concept.png), using the existing Kotlin/XML/Material 3 scaffold. This document defines appearance, interaction, presentation rules and acceptance criteria. It does not authorize a rewrite of the app or a change to scientific calculations.

Priority: technical specification for product scope; actual backend response for displayed values; this document for presentation and behavior; concept image for overall visual direction. Differences between code and the technical document are explicitly recorded in section 12 and require deliberate reconciliation, not silent changes. The numeric fixtures and decorative map geography in the artwork are not authoritative.

The goal is a map that makes the score, current direction, clarity, uncertainty and runoff understandable at a glance, with deeper information one gesture away. Finish the existing device-launch work first; implement this document in the phases in section 13.

## 2. Scope

V1: Home/Map, collapsed conditions teaser, expanded Conditions Details, Settings, saved spots, source availability/freshness, manual refresh and system/light/dark appearance. Retain the current background refresh arrangement while the scaffold is stabilized.

Exclude sargassum until v2, subscriptions, social features, booking, notifications, new forecast timelines and new scientific algorithms. Appearance selection and map-layer controls are design refinements. The concept’s palm decorations, slogans and outer phone frames are presentation artwork and must not appear inside the app.

## 3. Existing implementation baseline

Inspected September 11, 2026. This is a source inspection, not a verified device run.

| Existing piece | Design implementation direction |
| --- | --- |
| Kotlin Fragments, XML, ViewBinding, Material Components 1.12.0 | Keep this stack; Compose migration is unnecessary |
| MapFragment / fragment_map.xml | Retain map lifecycle; replace floating placeholder views with the specified card, map annotations and teaser |
| ConditionsBottomSheet / bottom_sheet_conditions.xml | Restyle existing content; add omitted fields; ultimately integrate persistent collapsed/expanded behavior |
| SettingsFragment / fragment_settings.xml | Extend backend-only form with units, theme, favorites and truthful connection setup |
| ConditionsViewModel and ConditionsUiState | Preserve MVVM; extend state to retain prior data on refresh errors and selected spot |
| Theme.Material3.Light.NoActionBar | Introduce DayNight theme and semantic light/night resources |
| ConditionsResponse.kt | Already includes scene age and plume direction; add backend structure mapping |
| Existing debug screen | Keep developer diagnostics out of the primary navigation |

No production layout, build configuration or runtime code is changed by this documentation handoff.

## 4. Design tokens

Use named resources shared by all screens. Values below are implementation defaults, replacing approximate values in the earlier UI notes. Dynamic wallpaper colors are off by default to preserve the marine identity.

### 4.1 Color

| Semantic role | Light | Dark |
| --- | --- | --- |
| background | #F3F8FA | #031C2A |
| surface | #FFFFFF | #082B3D |
| surfaceContainer | #EAF3F6 | #10384A |
| primary | #006B76 | #74D9E2 |
| onPrimary | #FFFFFF | #00363C |
| primaryContainer | #C8F0F2 | #004F58 |
| onPrimaryContainer | #00363C | #B7F2F5 |
| onSurface | #082B40 | #EEF7FB |
| onSurfaceVariant | #465E6D | #B7CBD5 |
| outline | #687F8C | #819AA8 |
| outlineVariant (decorative divider) | #D7E4EA | #345262 |
| errorContainer | #FFE1DE | #642D2B |
| onErrorContainer | #6B1515 | #FFE0DC |

Status chips use these fixed background/foreground pairs in both themes, so the category remains familiar:
Excellent #CBEBDD / #123F2D; Good #D8EBC6 / #2A421C; Fair #FFE3A0 / #513B00; Marginal #FFD7B5 / #5B2C05; Poor #FFDAD6 / #651C18; Unknown #E2EAF0 / #304653.

Status color belongs in the small chip/accent, not the entire score card. Unknown is neutral, never the same red as Poor. Keep surfaces solid by default; map cards may use 96% opacity only if text contrast still passes over all map areas.

Clarity raster stops: score 100 #168FA8, 75 #49B7BE, 50 #98C4A0, 25 #C9AB68, 0 #89552E. These are continuous visualization colors, not extra scientific categories. Default raster opacity 35%; user layer options allow 0–60%. Missing/cloud-masked pixels are transparent and marked in the legend as no data.

### 4.2 Typography, spacing and shape

Use platform Roboto/sans with tabular numerals where available. Do not add a font dependency solely for this design.

| Role | Size / line height | Weight |
| --- | --- | --- |
| Index number | 44 / 48 sp | 700 |
| Screen title | 22 / 28 sp | 600 |
| Card title | 16 / 24 sp | 600 |
| Primary reading | 20 / 28 sp | 600 |
| Body / input | 16 / 24 sp | 400 |
| Metadata | 13 / 18 sp | 400 |
| Chip / navigation label | 12 / 16 sp | 500 |

Spacing scale: 4, 8, 12, 16, 24, 32 dp. Screen horizontal padding 16 dp; card padding 16 dp; inter-card gap 12 dp; group gap 24 dp. Standard card radius 20 dp; hero 24 dp; sheet top corners 28 dp; inputs 12 dp; filled button 16 dp; chips fully rounded.

Main action height 52 dp; input minimum 56 dp; clickable row minimum 56 dp; all touch targets at least 48 × 48 dp. Icons 24 dp; small metadata icons 18 dp; current arrow 32 dp minimum. Use one consistent outlined Material icon family: map, settings, layers, my_location, refresh, expand_less/more, close, water, rain, info, star, add, visibility.

Elevation: ordinary cards 0 dp plus 1 dp divider; floating hero 3 dp; map action rail 3 dp; sheet 6 dp. Avoid glossy buttons, heavy drop shadows and decorative gradients despite minor generated-image embellishments.

## 5. Home / Map

### 5.1 Layout contract

Reference viewport: 412 × 892 dp including system bars. Fit available space using actual insets; do not hardcode status/navigation bar heights. Portrait first; minimum supported layout width 320 dp.

Order from top: system status bar; 64 dp app bar; map viewport; collapsed sheet; 80 dp two-item bottom navigation; system gesture inset. The map extends beneath the floating sheet, while its camera padding and attribution account for the sheet and navigation.

App bar: wave mark optional, title “Plume Tracker,” subtitle “Palm Beach County.” Settings icon opens the same destination as bottom navigation; retain only if it fits without crowding. Main navigation: Map / Settings. Details is a sheet, not a third tab.

Hero card: 16 dp below app bar and centered within the map’s unobstructed horizontal area. Reserve 72 dp at the trailing edge for the action rail; target hero width 252 dp at 412 dp viewport, minimum 204 dp. Height wraps content, approximately 136 dp at default font size. Show index number with smaller /100, “Snorkel Index,” category chip, divider, accuracy/quality label and separate resolutions.

Required badge copy:
“Nearshore Accuracy · Good”
“Currents 750 m · Clarity 10 m”
If it wraps, give each resolution its own line. Tapping accuracy opens an explanation: “Resolution is source grid spacing, not guaranteed accuracy at your entry point.” Show each source name and grid spacing. No single combined “10 m accuracy” badge.

At narrow widths or font scale above 1.3, move the hero into a full-width content row above the map and move controls to a bottom map rail above the teaser. Preserve at least 160 dp usable map height when possible. If vertical space is insufficient, use a reduced teaser with location and “View conditions”; the full details remain accessible.

### 5.2 Map and data layers

Initial camera: Boynton Inlet, latitude 26.530, longitude -80.052; zoom 14; north up; pitch 0. Retain pan/zoom on refresh and on return from Settings. Recenter returns to the selected spot, not device GPS. Location permission is not required for this action. Retain visible Mapbox attribution and logo using map padding.

Use real map geography; simplify roads and points of interest. Land is pale coastal sand in light mode; dark desaturated land in night mode. Water should remain distinct from land. Keep inlet and selected spot labels legible.

Layer order: base map → clarity raster → supported plume geometry → current arrows → source/spot labels. Do not use the existing screen-centered circle as a real satellite layer.

Current: anchor arrows geographically. A single returned current supports one representative current marker, not a spatial vector field. Multiple arrows require gridded current data. Label “S · 0.43 kn”; details show “175° · toward S.” Rotation must account for camera bearing; either keep map bearing at zero or subtract camera bearing from the arrow screen rotation. Missing direction hides the arrow; available speed can remain as text. Zero speed is a valid reading.

Clarity: require a georeferenced raster/tile contract with scene timestamp and pixel resolution before drawing spatial coverage. If only a scalar score exists, show the clarity reading in a card and layer state “Clarity map unavailable.” Keep the concept heatmap for explicitly labeled demo mode only. Never synthesize coverage from a point reading.

Plume: use plume.direction_deg and speed_mps when available, labeled “Inferred drift” because current code copies the current vector. Source chip maps LakeO → “Lake O influence,” C16_runoff → “C-16 runoff,” tidal_local → “Local / tidal.” Show source classification without claiming confirmed local contamination. One arrow does not establish a plume footprint. Draw a dashed footprint only when backend geometry exists; until then, demo geometry must be labeled “Demo plume area.” Put a C-16 location pin only at a verified source coordinate.

Action rail: Layers, Recenter, Refresh; 48 dp circles separated by 8 dp, 16 dp from trailing edge. Refresh may use a 56 dp FAB if space permits. Accessible labels include the action, not just icon names.

Layers opens a modal list with Current, Water clarity, Plume, Source markers. Defaults on where supported. Unavailable layers remain listed with “No map data available”; do not turn a nonfunctional switch on. Retain preferences. Opacity slider is enabled only for an available clarity raster. Legend is visible only when the corresponding data layer is visible.

### 5.3 Collapsed teaser

Persistent card with drag handle 32 × 4 dp, 8 dp top gap, 16 dp content padding, approximately 196 dp at default text scale. It sits immediately above navigation with no accidental gap.

Header: selected spot, expand chevron, “Last checked · 9:41 AM” (client fetch completion, not sensor observation). A demo screen says “Demo data” prominently. Three equal reading columns:
- Rain: “12 mm · 24h”
- C-16 runoff: “High”
- Lake O: “120 cfs”

Use High consistently; the artwork’s “Elevated” is replaced. Unknown values read “Unavailable.” Lower row “View conditions” is a full-width 48 dp touch target. Teaser header tap, lower row tap or upward swipe expands the same sheet.

## 6. Conditions Details

Final behavior: one persistent BottomSheetBehavior with collapsed and expanded states; keep the existing BottomSheetDialogFragment as an acceptable intermediate implementation while the app is being stabilized. Do not present two sheets at once.

Expanded sheet reaches the top safe inset plus 16 dp, covers bottom navigation, and leaves a small map strip only where space allows. Fixed header with handle, “Conditions Details,” selected spot and 48 dp close target; scrollable middle; fixed Refresh conditions button above gesture inset. Android Back and close collapse to teaser. At content top, downward drag collapses; scrolling content must not accidentally collapse. Preserve sheet state across rotation and background/foreground; navigation to Settings collapses it.

Content order and binding:

| Card | Required content |
| --- | --- |
| Snorkel Index | Score/100, backend label chip, nearshore quality; “Why this score?” expands backend reasons |
| Current | Selected speed unit; direction degrees and compass; source name; resolution; source timestamp if available |
| Water clarity | Score/100 and continuous bar; estimated NTU; source; resolution; last clear scene timestamp and age |
| Runoff | C-16 flow cfs; 24h rain in chosen unit; Low/Moderate/High intensity; timestamp |
| Lake Okeechobee | Lake stage ft; east discharge cfs; influence when present; expandable structures |
| Plume source | Readable source label; confidence percent; Macro/Meso/Micro scale; inferred direction and speed if present |
| Source quality | Nearshore quality, separate resolutions, coverage caveats and per-source availability |

Each card has its own state; never replace the whole sheet when only one feed fails. An empty reasons list displays “No deductions reported,” not N/A and not “Safe to snorkel.”

Lake structures: map backend S80, S351, S352, S354 to S-80, S-351, S-352, S-354, with cfs units. Show S308 separately as “S-308 · additional reading” when present; do not add it to the documented east total. Null structure values read “Unavailable.” Never recompute the aggregate from an incomplete breakdown.

Clarity metadata exact example: “Last clear scene · Sep 10, 9:22 AM EDT.” Cloud cover text, when justified by source metadata/error: “Cloud cover limits new imagery. Showing the last clear scene.” Do not infer clouds just from an old timestamp.

Scale help: “Macro · regional,” “Meso · local area,” “Micro · fine scale.” These are source classification labels, not numerical map accuracy. Null scale reads “Scale unavailable”; do not reconstruct it from confidence.

## 7. Settings

Scrollable form with 64 dp title bar and back action. Use a consistent 16 dp margin and 24 dp group gap. Save button fixed above keyboard/system inset; form scrolls focused field into view. All editable values form a draft until Save.

1. Appearance: System (default), Light, Dark segmented control.
2. Units: Current speed m/s / knots (default knots); Rainfall mm / inches (default mm).
3. Connection: Backend URL, supporting text appropriate to the current environment; Windy API key; Copernicus Data Space email/password; setup status.
4. Favourite spots: Boynton Inlet default, additional saved spots, Add a spot.
5. Save settings.

Backend URL: required, trim whitespace, require valid http/https URL and host. Support current emulator/local development HTTP URLs; do not silently rewrite the scheme. Do not display example server addresses as configured connections. Store a valid setting separately from whether the host responds. On successful local save: “Settings saved”; on subsequent fetch failure: “Saved, but the backend could not be reached” with Retry. On invalid input, focus field and display a specific inline error. Prevent duplicate save submissions.

Credentials: the technical spec requires these fields, but current API exposes no credential update endpoint. Until a secure configuration contract exists, show a “Set up on backend” row and helper text for each provider; do not present an enabled Save flow that falsely claims to configure the server. Demo-only forms can show masked fixture values. When credential support is implemented, mask secrets, use explicit reveal controls, do not prefill a fake masked string as a real password, do not log or export secrets, and distinguish configured/unchanged/replaced states. Never send provider credentials to a newly selected host without an explicit save action and a defined secure configuration contract.

Favorite addition: “Save selected map location” opens name field with selected coordinates; require nonempty name. Save locally. Selecting a favorite updates selected coordinates, camera and fetch target together. Rename and remove via row menu; removal Snackbar offers Undo. Do not include precise reef spots that were not supplied. Locations outside supported data coverage show a coverage message rather than guaranteed readings.

Back with edits: Save / Discard / Keep editing. Save persists valid local preferences; network success is not required for unit/theme settings. Appearance preview may apply while editing but must revert on discard. Unit changes update both map and details through shared formatters.

## 8. State, freshness and error contract

| State | Required presentation |
| --- | --- |
| Initial load | Map shell remains; neutral score placeholder “—”; compact progress; no fabricated layers |
| Valid data | Render each source independently, with timestamps |
| Refresh with existing data | Keep values and camera; animate refresh icon; disable duplicate refresh; “Checking…” |
| Refresh fails with existing data | Retain previous values, label “Showing previous data”; “Couldn’t refresh” and Retry |
| Initial network failure | “Couldn’t load conditions”; Retry and Open Settings; no numeric score |
| Partial response | Valid cards remain; affected field “Unavailable” with concise reason |
| Missing/unknown timestamp | “Update time unavailable”; never assign current time as observation time |
| Stale source | “Older data” chip and actual age; keep it distinct from unavailable |
| Map load failure | “Map unavailable” with Retry; conditions and Settings still usable |
| All useful source inputs absent | Neutral index presentation “Insufficient data,” even if backend still returns a composite; retain backend value only in diagnostics until backend policy is reconciled |
| Unsupported raster/plume geometry | Numeric details remain; layer unavailable message; no invented footprint |

Freshness separates client last-checked time, per-source timestamp and satellite last-clear-scene time. Store instants as provided; format local time with timezone for dated observations. Ages are relative to actual observation where known, not the latest request. For exact fixture screenshots, freeze the demo clock.

Use the technical spec’s >2h stale marker only on timestamps with known semantics, and prefer trustworthy source-specific status. The current /status implementation repeats a shared cache timestamp for every source, so it cannot establish independent sensor freshness. Show it as backend cache status. Satellite scene age must always be visible; an older clear scene is not automatically a network failure. Future or malformed timestamps read “Update time unavailable.”

30-minute cache TTL means Refresh checks the backend but does not guarantee a new observation. Snackbar: “Conditions checked” instead of “Live data updated.” Background work is best effort; do not promise exact 30-minute delivery. Refreshing must remain single-flight per selected location, and late responses from a previous favorite must not overwrite the current favorite.

## 9. Formatting and data integrity

- Bind score, label, reasons, quality and classification from the backend. Do not duplicate scientific formulas in Android.
- Display knots with two decimal places using m/s × 1.943844; m/s with two decimals. Use “kn” consistently, not mixed kt/kn.
- Rain: mm with up to one decimal; inches with two decimals, mm ÷ 25.4. Keep “24h” beside the value.
- Flow: whole cfs with grouping; lake stage: one decimal ft; NTU: one decimal with “estimated.”
- Direction: normalize valid degrees to [0,360), round display to whole degrees, use 8-point compass sectors centered at N/NE/E/SE/S/SW/W/NW. 175° → S. Direction means water moves toward this bearing.
- Confidence: nearest whole percent; do not interpret it as confidence in snorkeling safety.
- Resolution: meters below 1,000; kilometers above, up to one decimal; keep explicit “Current” and “Clarity.” A missing point/tidal grid resolution displays “Point / tidal” only where source semantics establish this, otherwise “Resolution unavailable.”
- UI source aliases: Sentinel2 → Sentinel-2; Sentinel3 → Sentinel-3; NOAA_MODIS → MODIS; NOAA_COOPS → NOAA CO-OPS; preserve NWPS/HYCOM/Windy.
- Null is never zero. Missing clarity must not become 50. Missing confidence is not 0%. Out-of-range or invalid values should be marked unavailable, not quietly made plausible.
- Present API errors as concise human-readable messages. Raw stack traces, endpoint secrets and backend JSON belong only in redacted developer diagnostics.
- API object-null versus field-null behavior must be reconciled: current client requires top-level source objects, while technical prose says failures can be null. Client parsing must not crash on supported partial responses.
- Snorkel Index is suitability information, not a safety guarantee. No “Safe to enter” CTA.

## 10. Motion, accessibility and responsive behavior

Sheet transition target 250 ms; short fades 150 ms; no perpetual particles or decorative motion. Honor reduced-motion settings; refresh progress must have a text equivalent.

At 100% font scale, preserve the concept’s hierarchy; at 130% and 200%, allow rows/cards to grow and scroll. Do not shrink body text to fit. At 320 dp, stack teaser readings if necessary and apply the compact-map alternative in section 5. Landscape/height-constrained mode uses a reduced teaser and full-height scrollable expanded details; do not force the portrait phone-board proportions. For widths ≥600 dp, keep form/detail content within 560 dp and allow the map to use remaining width; a tablet two-pane redesign is outside v1.

Meet at least 4.5:1 contrast for ordinary text, 3:1 for large text and essential nontext controls. Validate implemented colors, including overlays, rather than assuming the token palette guarantees every combination. Provide TalkBack labels for each marker, icon, score and unit. Reading example: “Snorkel Index 75 out of 100, Good.” Sheet expansion moves focus to its title; collapse restores focus to the opener. Exclude decorative map arrows from repeated announcements when an equivalent summary is available. Provide every essential condition in text outside the map.

## 11. Reproducible review fixtures

Provide debug-only Demo mode using the same UI and formatters as live mode. Visibly mark “Demo data” and never silently switch into demo after a network error. No demo credential is a real secret.

Primary fixture should match current backend behavior, not the image’s arbitrary numbers:
- Location 26.530, -80.052; current 0.22 m/s toward 175°, NWPS, 750 m.
- Clarity 72, NTU 4.2, Sentinel2, 10 m, scene 2026-09-10T13:22:00Z.
- C-16 260 cfs; rain 12 mm; intensity high.
- Lake east discharge 120 cfs, stage 14.2 ft, influence low; structures null unless a separate explicit fixture supplies them.
- Current scoring code produces 75 / Good with reason “High C-16 discharge.”
- Current classifier with default thresholds produces C16_runoff and 59% confidence. Classification scale is meso before enrichment; current enrichment drops it, so use null in an as-is API fixture. A target fixture can use meso only after the backend bug is corrected.
- Nearshore quality Good; current-derived plume direction 175° → S, not the picture’s SSE.
- Freeze clock at 2026-09-11T13:41:00Z for board comparison; source timestamps are explicit fixtures, not invented observations.

Additional scenarios: all-null source readings; clarity unavailable only; missing current direction with valid speed; HYCOM 8 km fallback; old satellite scene; failed refresh with prior values; map unavailable; settings invalid URL; changed units; 200% font; unavailable geometry. Include 68 / Good as a label-consistency fixture and 55 / Fair as an amber category fixture. These isolated category fixtures are presentation tests, not derived environmental calculations.

## 12. Reconciliation register

The following findings supersede assumptions in the earlier ui-design-notes.md. They are implementation follow-ups, not changes made by this handoff.

| Item | Evidence in repository | Required treatment |
| --- | --- | --- |
| Image score 68/Fair | services/plume.py labels 60–79 Good | Keep image styling; use backend label and corresponding color |
| Primary artwork values vs scoring | clarity 72/high runoff/low Lake influence gives 75 | Use section 11 fixture for review |
| Confidence 64% in artwork | code uses 0.5 + C-16/3000, unlike technical prose | Show returned 59% under current defaults; resolve science separately |
| Plume direction said to be missing in earlier notes | Present in Python/Kotlin models; copied from current | Use field, label inferred, no frontend invented trajectory |
| Plume scale lost | enrich_plume_with_current reconstructs object without resolution | Backend fix required to preserve scale; UI renders null truthfully |
| Lake breakdown | Python has structures; Kotlin LakeOData omits it | Add client mapping; no new endpoint is needed just for these fields |
| Clarity scene age | Present in both models, not displayed in current sheet | Bind existing field |
| Clarity map | MapFragment colors a screen view and defaults null to 50 | Remove fabricated live coverage; use scalar-only state until raster contract exists |
| Plume area / vector field | No geometry, raster or gridded-vector response contract | Keep demo-only spatial art separate; implement real geometry later |
| Source freshness | status router reuses inlet cache time across sources | Do not label this independent sensor freshness |
| Credentials | Android currently saves URL; no config endpoint in listed routers | Truthful backend-setup state pending secure contract |
| Quality semantics | Code derives label from current resolution and clarity score | Show backend label, separate resolutions; do not call label a measured accuracy |
| All-null inputs can still yield a score | compute_snorkel_index applies limited missing-data penalties | Neutral “Insufficient data” presentation; track backend validity policy separately |
| Favorites and refresh | ViewModel refresh defaults to inlet | Maintain selected coordinate state and request association |
| Null source object | Kotlin source properties non-null | Align supported failure shape before partial-data acceptance |

## 13. Incremental implementation plan for Devin

### Phase 0 — Keep device launch as the current milestone

Finish existing build/install/launch work. Verify map or recoverable map failure, backend connection, details opening and Settings navigation on the target Android device. Keep a working baseline. This document requires no SDK upgrades or architecture migration.

### Phase 1 — Visual foundation with fixtures

Add semantic theme resources and DayNight support. Establish shared reading/status/metadata components and formatters. Implement debug fixtures. Match Home card, app bar, action rail and teaser; add navigation. At this stage static demo map overlays are allowed only with Demo data labeling.

Acceptance: light/dark Home screenshots visually match composition; score/quality remain distinct; no clipping at 360 dp or 130% font.

### Phase 2 — Details and Settings

Restyle the existing details implementation before replacing sheet mechanics. Add scene timestamp, quality explanation, reasons, per-structure client mapping and scroll/pinned-action layout. Implement units/theme/favorites and truthful connection states. Then connect persistent collapsed/expanded behavior.

Acceptance: details reachable by tap and swipe; Back collapses; all form actions work; units agree across screens; null cards render independently.

### Phase 3 — Live data presentation

Replace fixture source with repository data through the existing ViewModel. Retain prior values on refresh errors, handle selected-spot races, map source ages correctly, and fix the documented scale/mapping defects as separate small changes. Draw geographically grounded annotations. Numeric conditions may ship before raster delivery.

Acceptance: no fabricated data, geography or freshness. Unavailable geometry has explicit fallback. No global loading screen on manual refresh.

### Phase 4 — Visual and device acceptance

Compare implementation screenshots side-by-side with the concept at default font scale. Prioritize hierarchy, spacing, card shape, marine palette, sheet behavior and map legibility. Use the written corrections for labels, timestamps and geometry. Validate on a physical device outdoors as well as the emulator; screen readability matters more than matching subtle shadows.

## 14. Acceptance checklist

- [ ] Existing app still builds, installs and launches after each implementation phase.
- [ ] Home shows score, backend label, separate resolutions, direction/speed and three compact indicators.
- [ ] Light and dark modes use semantic resources; system mode follows the device.
- [ ] Actual map shows Boynton Inlet with unobscured attribution and correct layer anchoring.
- [ ] A scalar reading does not render as a measured spatial raster or footprint.
- [ ] 175° arrow points toward S at all supported map bearings.
- [ ] Teaser expands by tap/swipe; expanded details scroll; Back/close collapse; no duplicate sheet.
- [ ] Current/clarity metadata and last-clear-scene age are visible.
- [ ] Lake breakdown maps real structure fields, and nulls are not zero.
- [ ] Plume confidence/scale and inferred nature are explicit.
- [ ] Why this score displays backend reasons.
- [ ] Refresh preserves prior data/camera and cannot launch duplicate in-flight requests.
- [ ] Failed/partial/stale responses remain distinguishable; no null-to-50 clarity fallback.
- [ ] Settings save, validation, discard, keyboard behavior, units and favorite selection work.
- [ ] Provider setup does not claim success without a supported backend configuration flow.
- [ ] 320/360/412 dp widths, landscape and 100/130/200% fonts remain usable.
- [ ] TalkBack, contrast, 48 dp targets and reduced motion are checked.
- [ ] Review screenshots cover light/dark Home, Details, Settings and partial failure.
- [ ] Fixture readings and decorative concept art never appear as live observations.

## 15. Handoff instruction

Implement this specification incrementally after the existing Android launch milestone. Use assets/palm-beach-plume-tracker-concept.png as the visual target and this document for exact behavior and corrections. Preserve Kotlin/XML/MVVM and the current working build. Start with explicitly labeled fixture data, submit screenshots for appearance review, then bind live values. Treat section 12 as a separate integration checklist; do not alter scientific formulas merely to match the image.

## 16. PBC Snorkel Conditions — approved Home and Evidence visual design

This section records the approved design tokens and layout for the camera-first Snorkel Conditions redesign (implemented in the `milestone-1-snorkel-replay` branch). It supersedes any conflicting plume-tracker tokens for the Snorkel Conditions screens.

### 16.1 Color tokens

| Semantic role | Light | Dark |
| --- | --- | --- |
| screen background | #F4F9FB | #041B29 |
| toolbar | #FFFFFF | #06283D |
| main card surface | #FFFFFF | #0B3046 |
| raised card surface | #E4F0F3 | #123E54 |
| subtle card outline | #D7E4EA | #28566C |
| primary text | #0B202B | #F0F8FC |
| secondary text | #5A7480 | #AAC4D3 |
| icons, links, selected controls | #006064 | #64DDED |
| primary | #006064 | #64DDED |
| onPrimary | #FFFFFF | #041B29 |
| primaryContainer | #E0F2F1 | #123E54 |
| onPrimaryContainer | #005B4F | #64DDED |
| onSurface | #0B202B | #F0F8FC |
| onSurfaceVariant | #5A7480 | #AAC4D3 |
| experimental/unclear | #5A7480 | #9DB4C0 |
| amber (status only) | #B07D00 | #FFDA86 |

Amber is reserved for an actual sargassum signal or a warning state; it is not used to brand the sargassum card. Experimental/unknown states are rendered in the neutral on-surface-variant colour.

### 16.2 Layout order — Home

From top to bottom:
1. App bar: wave icon, `PBC Snorkel` title, refresh icon, settings icon.
2. Camera hero card (full width, 280 dp height): coastal image with bottom gradient; overlay shows location, appearance headline, retrieval/capture-time chip, and `See evidence` text link.
3. Conditions panel begins immediately below the hero:
   - Surface flow tile (first), identified as Delray, with a structured direction/evidence label (`Likely`, `Possible`, mixed, no clear motion, or unable), neutral `Experimental` chip, freshness and separate capture/retrieval/analysis times, and a `See evidence` text link. Missing capture time does not suppress motion evidence.
   - Two compact cards side-by-side: Wind and Rain.
   - Offshore sargassum card: status text in amber only when the status is a signal, exact composite period and age, three text links (`Chart`, `Source`, `Legend`).
   - C-16 information row: note + `Open SFWMD information` text link.

No global `Live` banner is shown. Each source keeps its own capture, retrieval or composite timestamp.

### 16.3 Evidence sheet

- Fixed drag handle and header `Camera evidence` with a close icon.
- Location with a wave icon.
- Full-width camera crop with rounded corners (sample-region boxes are not rendered on top; they appear only when framing has been validated and are shown in sample rows).
- `Water appearance` with rows such as `A Nearshore · blue-green`.
- Two timestamp chips: `Retrieved …` and `Capture time unverified` (or similar status).
- `Open camera` text link.
- Sections for `Wind`, `Rain context`, `Surface flow` and `Offshore sargassum`.
- `Limitations` list at the bottom.

### 16.4 Typography and shape

- Screen title: `?attr/textAppearanceTitleLarge`.
- Card headline: `?attr/textAppearanceHeadlineSmall`.
- Body: `?attr/textAppearanceBodyMedium`.
- Metadata/caption: `?attr/textAppearanceBodySmall`.
- 16 dp side margins; 12 dp between cards; card corner radius 20 dp; hero corner radius 24 dp; 48 dp touch targets.


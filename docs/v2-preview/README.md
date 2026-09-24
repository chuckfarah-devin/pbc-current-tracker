# PBC Snorkel V2 map visual preview

All displayed conditions are clearly labeled simulated visual-preview scenarios. No live rating rules or Boynton transport adjustment are implemented.

## Original GUI reference alongside revised Android preview

<table>
<tr><th>Original PBC GUI mockup</th><th>Revised Android V2 map — compact Delray</th></tr>
<tr><td><img src="../assets/palm-beach-plume-tracker-concept.png" width="430" alt="Original PBC GUI mockup"></td><td><img src="delray-final.png" width="300" alt="Final Android V2 sourced-map preview with compact Delray summary"></td></tr>
</table>

## Final bounded-map review

| Delray — compact | Hilton — view-only |
|---|---|
| <img src="delray-final.png" width="280"> | <img src="hilton-final.png" width="280"> |

The navigation recording is [v2-map-navigation.mp4](v2-map-navigation.mp4). It demonstrates north/south panning, zoom controls, camera selection, bounded recentering, and panel expansion.

The offline background uses bundled, simplified Florida Fish and Wildlife Conservation Commission shoreline and Intracoastal Waterway Open Data, clipped with overscan from Miami-Dade through northern Palm Beach County. Camera pins and sourced shapes share the same WGS84 projection, and bounded pan/zoom prevents exposing the extract edges. It requires no network or third-party map tiles. The map displays FWC attribution in-app and is not intended for navigation. Jupiter remains conditional on verification of a useful beach-facing view.

## Accepted visual follow-ups

- Separate or cluster the closely spaced Hilton and Courtyard pins and labels at corridor-wide zoom levels. Both cameras remain individually selectable in the accepted preview.
- Keep marker and place labels clear of the right-side map controls, screen edges, and bottom conditions panel at every supported zoom level.

## Pre-merge acceptance check

- Existing Camera view opens from the Map/Camera switch and continues to render its recorded camera, appearance, motion, wind, and rain evidence.
- Offline Demo can be enabled in Settings and loads bundled recorded data without a backend or internet connection. The Camera view visibly identifies `Demo mode · offline recorded data`.
- With Demo disabled, the Camera view returns to its configured Live data source while the V2 Map remains independently and prominently labeled `DEMO · SIMULATED`. Map scenario values are not presented as live observations.
- Hilton and Courtyard were each selected independently despite their current overlap.
- No live Good/Fair/Poor rules or Boynton adjustment are included.

## Next implementation step

Add location-specific live weather and camera-health data to the map cards. Keep live Good/Fair/Poor rules and the Boynton adjustment deferred until their inputs and rules are reviewed.

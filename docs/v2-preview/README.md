# PBC Snorkel V2 map visual preview

All displayed conditions are clearly labeled simulated visual-preview scenarios. No live rating rules or Boynton transport adjustment are implemented.

## Original GUI reference alongside Android implementation

<table>
<tr><th>Original PBC GUI mockup</th><th>Android V2 map preview — Delray simulated Good</th></tr>
<tr><td><img src="../assets/palm-beach-plume-tracker-concept.png" width="430" alt="Original PBC GUI mockup"></td><td><img src="delray-good.png" width="300" alt="Android V2 map preview with Delray selected and simulated Good scenario"></td></tr>
</table>

## Required scenarios

| Delray — simulated Good | Delray — simulated Fair/Poor | Broward view-only |
|---|---|---|
| <img src="delray-good.png" width="280"> | <img src="delray-fair-poor.png" width="280"> | <img src="broward-view-only.png" width="280"> |

The offline background is intentionally identified as a schematic rather than a conventional tile basemap. Marker positions are projected from the reviewed WGS84 coordinates and require no network or third-party map tiles. Jupiter remains labeled as a beach-facing view that must be verified before live integration.

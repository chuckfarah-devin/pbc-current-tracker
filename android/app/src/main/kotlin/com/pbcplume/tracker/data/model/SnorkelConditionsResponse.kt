package com.pbcplume.tracker.data.model

import com.squareup.moshi.Json

/** Combined conditions contract returned by GET /api/snorkel-conditions.
 *  Each observation keeps its own timestamps, status and limitations. */
data class SnorkelConditionsResponse(
    @Json(name = "generated_at_utc") val generatedAtUtc: String,
    val mode: String,
    @Json(name = "mode_disclaimer") val modeDisclaimer: String,
    @Json(name = "refresh_status") val refreshStatus: String = "idle",
    @Json(name = "refresh_started_at") val refreshStartedAt: String? = null,
    val location: SnorkelLocation,
    val cameras: List<CameraHealthObservation> = emptyList(),
    @Json(name = "water_appearance") val waterAppearance: List<WaterAppearanceObservation> = emptyList(),
    val weather: WeatherObservation?,
    val algae: AlgaeObservation?,
    val c16: C16Info?,
    @Json(name = "surface_motion") val surfaceMotion: SurfaceMotionObservation?,
    val limitations: List<String> = emptyList()
)

data class SnorkelLocation(
    val lat: Double,
    val lon: Double,
    val label: String
)

data class CameraHealthObservation(
    @Json(name = "camera_id") val cameraId: String,
    val location: String,
    val view: String?,
    @Json(name = "page_url") val pageUrl: String?,
    @Json(name = "source_url") val sourceUrl: String?,
    @Json(name = "fetched_at") val fetchedAt: String?,
    @Json(name = "observed_at") val observedAt: String?,
    @Json(name = "observed_at_local") val observedAtLocal: String?,
    val freshness: String?,
    @Json(name = "age_minutes") val ageMinutes: Double?,
    @Json(name = "local_conditions_verified") val localConditionsVerified: Boolean = false,
    val status: String,
    val error: String?,
    @Json(name = "visual_flags") val visualFlags: List<String> = emptyList(),
    @Json(name = "image_url") val imageUrl: String?,
    @Json(name = "image_width") val imageWidth: Int?,
    @Json(name = "image_height") val imageHeight: Int?,
    @Json(name = "mean_brightness") val meanBrightness: Double?,
    val limitations: List<String> = emptyList()
)

data class WaterAppearanceObservation(
    @Json(name = "camera_id") val cameraId: String,
    val location: String,
    val headline: String,
    @Json(name = "source_url") val sourceUrl: String?,
    @Json(name = "image_url") val imageUrl: String?,
    @Json(name = "fetched_at") val fetchedAt: String?,
    @Json(name = "observed_at") val observedAt: String?,
    @Json(name = "observed_at_local") val observedAtLocal: String?,
    val samples: List<WaterColourSample> = emptyList(),
    @Json(name = "framing_verified") val framingVerified: Boolean = false,
    @Json(name = "current_direction") val currentDirection: String?,
    @Json(name = "underwater_visibility") val underwaterVisibility: String?,
    val status: String,
    val limitations: List<String> = emptyList()
)

data class WaterColourSample(
    val region: String,
    val bounds: List<Double>,
    @Json(name = "warm_percent") val warmPercent: Double,
    @Json(name = "blue_green_percent") val blueGreenPercent: Double,
    @Json(name = "other_percent") val otherPercent: Double,
    @Json(name = "mean_rgb") val meanRgb: List<Double>,
    val pixels: Int
)

data class WeatherObservation(
    @Json(name = "reference_time_utc") val referenceTimeUtc: String?,
    @Json(name = "reference_time_local") val referenceTimeLocal: String?,
    val source: String?,
    @Json(name = "recent_24h") val recent24h: RainWindow,
    @Json(name = "forward_24h") val forward24h: RainWindow,
    val wind: WindObservation,
    @Json(name = "daily_outlook") val dailyOutlook: List<RainWindow> = emptyList(),
    val limitations: List<String> = emptyList()
)

data class WindObservation(
    @Json(name = "time_utc") val timeUtc: String?,
    @Json(name = "time_local") val timeLocal: String?,
    @Json(name = "speed_kn") val speedKn: Double?,
    @Json(name = "speed_mph") val speedMph: Double?,
    @Json(name = "gust_kn") val gustKn: Double?,
    @Json(name = "gust_mph") val gustMph: Double?,
    @Json(name = "gust_period") val gustPeriod: String?,
    @Json(name = "from_degrees") val fromDegrees: Double?,
    @Json(name = "from_compass") val fromCompass: String?,
    @Json(name = "toward_degrees") val towardDegrees: Double?,
    @Json(name = "toward_compass") val towardCompass: String?,
    val preferred: Boolean = false,
    @Json(name = "preferred_label") val preferredLabel: String?,
    val status: String
)

data class RainWindow(
    val date: String?,
    val label: String?,
    @Json(name = "start_utc") val startUtc: String?,
    @Json(name = "end_utc") val endUtc: String?,
    val mm: Double?,
    val inches: Double?,
    val category: String?,
    val status: String
)

data class AlgaeObservation(
    @Json(name = "source_filename") val sourceFilename: String?,
    @Json(name = "period_start") val periodStart: String?,
    @Json(name = "period_end") val periodEnd: String?,
    val product: String?,
    val composite: String?,
    @Json(name = "nominal_resolution_m") val nominalResolutionM: Int?,
    @Json(name = "source_url") val sourceUrl: String?,
    @Json(name = "source_image_url") val sourceImageUrl: String?,
    @Json(name = "source_legend_url") val sourceLegendUrl: String?,
    @Json(name = "source_bounds_wsen") val sourceBoundsWsen: List<Double>,
    val regions: List<AlgaeRegion> = emptyList(),
    val limitations: List<String> = emptyList()
)

data class AlgaeRegion(
    val name: String,
    val status: String,
    @Json(name = "image_url") val imageUrl: String?,
    @Json(name = "colored_pixels_pct_of_recognized_water") val coloredPixelsPct: Double?,
    @Json(name = "recognized_water_pixels_pct") val recognizedWaterPixelsPct: Double?,
    @Json(name = "requested_bounds_wsen") val requestedBoundsWsen: List<Double>,
    @Json(name = "crop_ltrb_exclusive") val cropLtrbExclusive: List<Int>,
    val interpretation: String
)

data class C16Info(
    @Json(name = "live_flow") val liveFlow: String?,
    @Json(name = "info_url") val infoUrl: String,
    val notes: String
)

data class SurfaceMotionObservation(
    @Json(name = "developer_only") val developerOnly: Boolean = true,
    val location: String = "Delray Beach",
    @Json(name = "acquisition_id") val acquisitionId: String?,
    @Json(name = "observed_at") val observedAt: String?,
    @Json(name = "retrieved_at") val retrievedAt: String?,
    @Json(name = "analyzed_at") val analyzedAt: String?,
    @Json(name = "fetched_at") val fetchedAt: String?,
    val direction: String = "unknown",
    @Json(name = "evidence_strength") val evidenceStrength: String = "unable",
    val freshness: String = "unknown",
    val reason: String?,
    @Json(name = "orientation_verified") val orientationVerified: Boolean = false,
    @Json(name = "regions_image_url") val regionsImageUrl: String?,
    @Json(name = "clip_url") val clipUrl: String?,
    @Json(name = "user_label") val userLabel: String?,
    @Json(name = "automated_observation") val automatedObservation: String?,
    val interpretation: String,
    val status: String,
    val limitations: List<String> = emptyList()
)

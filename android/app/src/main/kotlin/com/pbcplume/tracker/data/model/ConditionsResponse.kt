package com.pbcplume.tracker.data.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

/** Root response from GET /api/conditions (matches backend v0.2) */
@JsonClass(generateAdapter = true)
data class ConditionsResponse(
    val location: LocationInfo,
    val current: CurrentData,
    val turbidity: TurbidityData,
    val runoff: RunoffData,
    @Json(name = "lake_o") val lakeO: LakeOData,
    val plume: PlumeData,
    @Json(name = "snorkel_index") val snorkelIndex: SnorkelIndex,
    @Json(name = "nearshore_quality") val nearshoreQuality: String?,
    val sargassum: SargassumData? = null   // Phase 4 — always null in v1
)

@JsonClass(generateAdapter = true)
data class LocationInfo(
    val lat: Double,
    val lon: Double
)

@JsonClass(generateAdapter = true)
data class CurrentData(
    @Json(name = "speed_mps") val speedMps: Double?,
    @Json(name = "direction_deg") val directionDeg: Double?,
    val source: String?,
    @Json(name = "resolution_m") val resolutionM: Int?,
    val timestamp: String?,
    val error: String?
)

@JsonClass(generateAdapter = true)
data class TurbidityData(
    val ntu: Double?,
    @Json(name = "clarity_score") val clarityScore: Int?,
    val source: String?,
    @Json(name = "resolution_m") val resolutionM: Int?,
    @Json(name = "last_clear_scene") val lastClearScene: String?,
    val timestamp: String?,
    val error: String?
)

@JsonClass(generateAdapter = true)
data class RunoffData(
    @Json(name = "recent_rain_mm") val recentRainMm: Double?,
    @Json(name = "c16_flow_cfs") val c16FlowCfs: Double?,
    @Json(name = "runoff_intensity") val runoffIntensity: String?,
    val timestamp: String?,
    val error: String?
)

@JsonClass(generateAdapter = true)
data class LakeOData(
    @Json(name = "lake_stage_ft") val lakeStageFt: Double?,
    @Json(name = "east_discharge_cfs_total") val eastDischargeCfsTotal: Double?,
    @Json(name = "lake_o_influence") val lakeOInfluence: String?,
    val timestamp: String?,
    val error: String?
)

@JsonClass(generateAdapter = true)
data class PlumeData(
    @Json(name = "direction_deg") val directionDeg: Double?,
    @Json(name = "speed_mps") val speedMps: Double?,
    val source: String?,
    val confidence: Double?,
    val resolution: String?   // macro / meso / micro
)

@JsonClass(generateAdapter = true)
data class SnorkelIndex(
    val score: Int,
    val label: String,
    val reasons: List<String>
)

// Phase 4 stub — null until Backend Phase 4 ships
@JsonClass(generateAdapter = true)
data class SargassumData(
    @Json(name = "density_class") val densityClass: Int?,
    val presence: Boolean?,
    val confidence: Double?,
    val source: String?,
    @Json(name = "resolution_m") val resolutionM: Int?,
    val error: String?
)

/** Response from GET /api/status */
@JsonClass(generateAdapter = true)
data class StatusResponse(
    val status: String,
    @Json(name = "last_update") val lastUpdate: String,
    val sources: Map<String, SourceStatus>
)

@JsonClass(generateAdapter = true)
data class SourceStatus(
    @Json(name = "last_update") val lastUpdate: String?,
    val status: String,
    val error: String?
)

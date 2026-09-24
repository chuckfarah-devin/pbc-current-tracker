package com.pbcplume.tracker.ui

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

data class BeachLocation(
    val id: String,
    val name: String,
    val municipality: String,
    val lat: Double,
    val lon: Double,
    val cameraUrl: String,
    val cameraIds: Set<String> = emptySet(),
    val viewOnly: Boolean = false,
    val motionSupported: Boolean = false,
)

object BeachLocations {
    val all = listOf(
        BeachLocation("jupiter", "Jupiter Beach", "Jupiter", 26.9400, -80.0700, "https://video-monitoring.com/beachcams/jupiter/", setOf("jupiter")),
        BeachLocation("singer", "Singer Island Beach", "Riviera Beach", 26.7910, -80.0335, "https://www.thesingerresort.com/live-webcam/", setOf("singer"), true),
        BeachLocation("boynton", "Boynton Inlet", "South Lake Worth Inlet", 26.5456, -80.0428, "https://video-monitoring.com/beachcams/boyntoninlet/", setOf("boynton_s4", "boynton_s6", "boynton_s8", "boynton_s10")),
        BeachLocation("delray", "Delray Municipal Beach", "Delray Beach", 26.4616, -80.0585, "https://live1.brownrice.com/embed/delraybeach1", setOf("delray"), motionSupported = true),
        BeachLocation("boca", "South Beach Park", "Boca Raton", 26.3540, -80.0699, "https://video-monitoring.com/beachcams/boca/slideshow.htm?station=Main+Shot", setOf("boca", "boca_south_beach")),
        BeachLocation("ebb", "Ebb Tide Resort", "Pompano Beach", 26.2295, -80.0899, "https://ebbtideresort.com/ebb-tide-resort-live-beach-cam/", setOf("ebb", "ebb_tide"), true),
        BeachLocation("hilton", "Hilton Beach House", "Fort Lauderdale", 26.1329, -80.1049, "https://www.fllbeachcam.com/", setOf("hilton"), true),
        BeachLocation("courtyard", "Courtyard Beach", "Fort Lauderdale", 26.1174, -80.1056, "https://seetheview.com/cam/580/fort-lauderdale-beach-live-cam", setOf("courtyard"), true),
    )

    fun get(id: String) = all.firstOrNull { it.id == id } ?: all.first { it.id == "delray" }
}

data class MapViewport(val scale: Float, val offsetX: Float, val offsetY: Float)

class LocationSelectionViewModel : ViewModel() {
    private val _selectedId = MutableStateFlow("delray")
    val selectedId = _selectedId.asStateFlow()

    val selected get() = BeachLocations.get(_selectedId.value)
    var mapViewport: MapViewport? = null

    fun select(id: String) {
        if (BeachLocations.all.any { it.id == id }) _selectedId.value = id
    }
}

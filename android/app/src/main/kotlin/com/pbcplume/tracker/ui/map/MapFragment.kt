package com.pbcplume.tracker.ui.map

import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.pbcplume.tracker.R
import com.pbcplume.tracker.databinding.FragmentMapBinding

class MapFragment : Fragment() {
    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private data class Location(
        val id: String,
        val name: String,
        val municipality: String,
        val lat: Double,
        val lon: Double,
        val cameraUrl: String,
        val viewOnly: Boolean = false
    )

    private enum class Scenario { GOOD, FAIR, VIEW_ONLY }

    private val locations = listOf(
        Location("jupiter", "Jupiter Beach", "Jupiter · beach-facing view to verify", 26.9400, -80.0700, "https://video-monitoring.com/beachcams/jupiter/"),
        Location("singer", "Singer Island Beach", "Riviera Beach", 26.7910, -80.0335, "https://www.thesingerresort.com/live-webcam/", true),
        Location("boynton", "Boynton Inlet", "South Lake Worth Inlet · inlet context", 26.5456, -80.0428, "https://video-monitoring.com/beachcams/boyntoninlet/"),
        Location("delray", "Delray Municipal Beach", "Delray Beach · default location", 26.4616, -80.0585, "https://live1.brownrice.com/embed/delraybeach1"),
        Location("boca", "South Beach Park", "Boca Raton", 26.3540, -80.0699, "https://video-monitoring.com/beachcams/boca/slideshow.htm?station=Main+Shot"),
        Location("ebb", "Ebb Tide Resort", "Pompano Beach · view-only", 26.2295, -80.0899, "https://ebbtideresort.com/ebb-tide-resort-live-beach-cam/", true),
        Location("hilton", "Hilton Beach House", "Fort Lauderdale · view-only", 26.1329, -80.1049, "https://www.fllbeachcam.com/", true),
        Location("courtyard", "Courtyard Beach", "Fort Lauderdale · view-only", 26.1174, -80.1056, "https://seetheview.com/cam/580/fort-lauderdale-beach-live-cam", true)
    )

    private var selected = locations.first { it.id == "delray" }
    private var scenario = Scenario.GOOD
    private var expanded = true

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, state: Bundle?): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, state: Bundle?) {
        binding.mapPreview.markers = locations.map { MapPreviewView.Marker(it.id, shortLabel(it), it.lat, it.lon) }
        binding.mapPreview.selectedId = selected.id
        binding.mapPreview.onMarkerSelected = { id ->
            selected = locations.first { it.id == id }
            scenario = if (selected.viewOnly) Scenario.VIEW_ONLY else Scenario.GOOD
            syncScenarioToggle()
            render()
        }
        binding.btnCameraMode.setOnClickListener { findNavController().navigate(R.id.action_map_to_home) }
        binding.btnExpand.setOnClickListener { expanded = !expanded; render() }
        binding.btnOpenCamera.setOnClickListener { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(selected.cameraUrl))) }
        binding.scenarioToggle.addOnButtonCheckedListener { _, id, checked ->
            if (!checked) return@addOnButtonCheckedListener
            when (id) {
                R.id.btnGood -> { selected = locations.first { it.id == "delray" }; scenario = Scenario.GOOD }
                R.id.btnFair -> { selected = locations.first { it.id == "delray" }; scenario = Scenario.FAIR }
                R.id.btnBroward -> { selected = locations.first { it.id == "hilton" }; scenario = Scenario.VIEW_ONLY }
            }
            binding.mapPreview.selectedId = selected.id
            render()
        }
        binding.btnGood.isChecked = true
        render()
    }

    private fun render() = with(binding) {
        tvLocation.text = selected.name
        tvMunicipality.text = selected.municipality
        tvScenario.text = when (scenario) {
            Scenario.GOOD -> "SIMULATED GOOD · visual preview only"
            Scenario.FAIR -> "SIMULATED FAIR / POOR · visual preview only"
            Scenario.VIEW_ONLY -> "VIEW-ONLY DEMO · no local analysis"
        }
        when (scenario) {
            Scenario.GOOD -> {
                tvRating.text = "Good"
                tvRating.setTextColor(Color.rgb(20, 80, 55))
                tvRating.setBackgroundResource(R.drawable.bg_rating_good)
                tvWind.text = "W 7 mph"
                tvRain.text = "0.02 in"
                tvMotion.text = "Northward"
                tvAppearance.text = "Water appearance: simulated usable blue-green observation"
                tvSargassum.text = "Sargassum present · demo source date Jul 03, 2026"
                tvReason.text = "Demo rationale: west wind below 10 mph and little recent rain. Evidence strength remains in Details. Not a safety rating."
            }
            Scenario.FAIR -> {
                tvRating.text = "Fair"
                tvRating.setTextColor(Color.rgb(100, 62, 0))
                tvRating.setBackgroundColor(Color.rgb(255, 218, 134))
                tvWind.text = "E 14 mph"
                tvRain.text = "0.74 in"
                tvMotion.text = "Southward"
                tvAppearance.text = "Water appearance: simulated mixed observation"
                tvSargassum.text = "Sargassum present · demo source date Jul 03, 2026"
                tvReason.text = "Demo rationale: recent rain and onshore wind are adverse. Fair/Poor thresholds remain proposals and are not implemented live."
            }
            Scenario.VIEW_ONLY -> {
                tvRating.text = "Not rated"
                tvRating.setTextColor(Color.rgb(70, 90, 100))
                tvRating.setBackgroundColor(Color.rgb(228, 240, 243))
                tvWind.text = "Unavailable"
                tvRain.text = "Unavailable"
                tvMotion.text = "Unavailable"
                tvAppearance.text = "No bundled local imagery · open the provider camera when online"
                tvSargassum.text = "Offshore sargassum · no local demo observation"
                tvReason.text = "This PTZ camera is view-only. Missing analysis remains explicit; no Delray conditions or imagery are substituted."
            }
        }
        groupDetails.visibility = if (expanded) View.VISIBLE else View.GONE
        btnExpand.rotation = if (expanded) 180f else 0f
        mapPreview.selectedId = selected.id
    }

    private fun syncScenarioToggle() {
        when (scenario) {
            Scenario.GOOD -> binding.btnGood.isChecked = true
            Scenario.FAIR -> binding.btnFair.isChecked = true
            Scenario.VIEW_ONLY -> binding.btnBroward.isChecked = true
        }
    }

    private fun shortLabel(location: Location) = when (location.id) {
        "jupiter" -> "Jupiter"
        "singer" -> "Singer"
        "boynton" -> "Boynton"
        "delray" -> "Delray"
        "boca" -> "Boca"
        "ebb" -> "Pompano"
        "hilton" -> "Hilton FLL"
        else -> "Courtyard"
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

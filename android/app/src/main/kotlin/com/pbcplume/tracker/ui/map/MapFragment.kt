package com.pbcplume.tracker.ui.map

import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.PopupMenu
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.pbcplume.tracker.R
import com.pbcplume.tracker.databinding.FragmentMapBinding

class MapFragment : Fragment() {
    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private data class Location(val id: String, val name: String, val municipality: String, val lat: Double, val lon: Double, val cameraUrl: String, val viewOnly: Boolean = false)
    private enum class Scenario { GOOD, FAIR, VIEW_ONLY }

    private val locations = listOf(
        Location("jupiter", "Jupiter Beach", "Jupiter · beach-facing view to verify", 26.9400, -80.0700, "https://video-monitoring.com/beachcams/jupiter/"),
        Location("singer", "Singer Island Beach", "Riviera Beach", 26.7910, -80.0335, "https://www.thesingerresort.com/live-webcam/", true),
        Location("boynton", "Boynton Inlet", "South Lake Worth Inlet · inlet context", 26.5456, -80.0428, "https://video-monitoring.com/beachcams/boyntoninlet/"),
        Location("delray", "Delray Municipal Beach", "Delray Beach · default location", 26.4616, -80.0585, "https://live1.brownrice.com/embed/delraybeach1"),
        Location("boca", "South Beach Park", "Boca Raton", 26.3540, -80.0699, "https://video-monitoring.com/beachcams/boca/slideshow.htm?station=Main+Shot"),
        Location("ebb", "Ebb Tide Resort", "Pompano Beach · view-only camera", 26.2295, -80.0899, "https://ebbtideresort.com/ebb-tide-resort-live-beach-cam/", true),
        Location("hilton", "Hilton Beach House", "Fort Lauderdale · view-only camera", 26.1329, -80.1049, "https://www.fllbeachcam.com/", true),
        Location("courtyard", "Courtyard Beach", "Fort Lauderdale · view-only camera", 26.1174, -80.1056, "https://seetheview.com/cam/580/fort-lauderdale-beach-live-cam", true)
    )

    private var selected = locations.first { it.id == "delray" }
    private var scenario = Scenario.GOOD
    private var expanded = false

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, state: Bundle?): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, state: Bundle?) {
        binding.mapPreview.markers = locations.map { MapPreviewView.Marker(it.id, shortLabel(it), it.municipality, it.lat, it.lon) }
        binding.mapPreview.selectedId = selected.id
        binding.mapPreview.onMarkerSelected = { id -> selectLocation(locations.first { it.id == id }) }
        binding.btnCameraMode.setOnClickListener { findNavController().navigate(R.id.action_map_to_home) }
        binding.btnExpand.setOnClickListener { toggleDetails() }
        binding.btnDetails.setOnClickListener { toggleDetails() }
        binding.btnOpenCamera.setOnClickListener { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(selected.cameraUrl))) }
        binding.btnZoomIn.setOnClickListener { binding.mapPreview.zoomBy(1.35f) }
        binding.btnZoomOut.setOnClickListener { binding.mapPreview.zoomBy(.74f) }
        binding.btnShowAll.setOnClickListener { binding.mapPreview.showAll() }
        binding.btnRecenter.setOnClickListener { binding.mapPreview.centerOn(selected.id) }
        binding.btnScenarioMenu.setOnClickListener { showScenarioMenu(it) }
        binding.mapPreview.post { binding.mapPreview.centerOn(selected.id) }
        render()
    }

    private fun selectLocation(location: Location) {
        selected = location
        scenario = if (location.viewOnly) Scenario.VIEW_ONLY else Scenario.GOOD
        expanded = false
        binding.mapPreview.selectedId = location.id
        binding.mapPreview.post { binding.mapPreview.centerOn(location.id) }
        render()
    }

    private fun toggleDetails() {
        expanded = !expanded
        render()
        binding.mapPreview.post { binding.mapPreview.centerOn(selected.id) }
    }

    private fun showScenarioMenu(anchor: View) {
        PopupMenu(requireContext(), anchor).apply {
            menu.add("Delray · Good demo")
            menu.add("Delray · Fair/Poor demo")
            menu.add("Hilton · View-only demo")
            setOnMenuItemClickListener {
                when (it.title.toString()) {
                    "Delray · Good demo" -> { selected = locations.first { item -> item.id == "delray" }; scenario = Scenario.GOOD }
                    "Delray · Fair/Poor demo" -> { selected = locations.first { item -> item.id == "delray" }; scenario = Scenario.FAIR }
                    else -> { selected = locations.first { item -> item.id == "hilton" }; scenario = Scenario.VIEW_ONLY }
                }
                expanded = false
                binding.mapPreview.selectedId = selected.id
                binding.mapPreview.post { binding.mapPreview.centerOn(selected.id) }
                render()
                true
            }
            show()
        }
    }

    private fun render() = with(binding) {
        tvLocation.text = selected.name
        tvMunicipality.text = selected.municipality
        when (scenario) {
            Scenario.GOOD -> {
                rating("Good", "#BFE8D3", "#145037")
                tvCompactConditions.text = "W 7 mph · Rain 0.02 in · Northward"
                tvCompactEvidence.text = "Blue-green appearance · Offshore sargassum present"
                tvWind.text = "W 7 mph"
                tvRain.text = "0.02 in"
                tvMotion.text = "Northward"
                tvAppearance.text = "Water appearance: simulated usable blue-green observation"
                sargassum(true, "Sargassum present", "Demo composite ended Jul 03, 2026")
                tvReason.text = "Simulated evidence: west wind below 10 mph and little recent rain. Direction evidence strength: likely. Personal preference preview only; not a safety rating."
            }
            Scenario.FAIR -> {
                rating("Fair", "#FFDA86", "#6A4300")
                tvCompactConditions.text = "E 14 mph · Rain 0.74 in · Southward"
                tvCompactEvidence.text = "Mixed appearance · Offshore sargassum present"
                tvWind.text = "E 14 mph"
                tvRain.text = "0.74 in"
                tvMotion.text = "Southward"
                tvAppearance.text = "Water appearance: simulated mixed observation"
                sargassum(true, "Sargassum present", "Demo composite ended Jul 03, 2026")
                tvReason.text = "Simulated evidence: recent rain and onshore wind. Direction evidence strength: possible. Fair/Poor thresholds remain proposals."
            }
            Scenario.VIEW_ONLY -> {
                rating("Not rated", "#E4F0F3", "#405B66")
                tvCompactConditions.text = "SE 9 mph · Rain 0.08 in · Surface unavailable"
                tvCompactEvidence.text = "Camera view-only · analysis unavailable"
                tvWind.text = "SE 9 mph"
                tvRain.text = "0.08 in"
                tvMotion.text = "Unavailable"
                tvAppearance.text = "Camera analysis unavailable · no bundled local imagery"
                sargassum(false, "Offshore sargassum unavailable", "No local demo observation")
                tvReason.text = "Weather is shown independently for this demo. The PTZ camera remains view-only; no Delray imagery or analysis is substituted."
            }
        }
        groupDetails.visibility = if (expanded) View.VISIBLE else View.GONE
        btnExpand.rotation = if (expanded) 180f else 0f
        btnDetails.text = if (expanded) "Hide details" else "Details"
        mapPreview.selectedId = selected.id
    }

    private fun rating(text: String, background: String, foreground: String) {
        binding.tvRating.text = text
        binding.tvRating.setTextColor(Color.parseColor(foreground))
        binding.tvRating.backgroundTintList = ColorStateList.valueOf(Color.parseColor(background))
    }

    private fun sargassum(present: Boolean, headline: String, date: String) {
        val color = Color.parseColor(if (present) "#C62828" else "#607780")
        binding.tvSargassum.text = headline
        binding.tvSargassum.setTextColor(color)
        binding.ivSargassum.imageTintList = ColorStateList.valueOf(color)
        binding.tvSargassumDate.text = date
    }

    private fun shortLabel(location: Location) = when (location.id) {
        "jupiter" -> "Jupiter Beach"
        "singer" -> "Singer Island"
        "boynton" -> "Boynton Inlet"
        "delray" -> "Delray"
        "boca" -> "South Beach Park"
        "ebb" -> "Ebb Tide"
        "hilton" -> "Hilton"
        else -> "Courtyard"
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}

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
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.navigation.fragment.findNavController
import com.pbcplume.tracker.R
import com.pbcplume.tracker.databinding.FragmentMapBinding
import com.pbcplume.tracker.ui.BeachLocation
import com.pbcplume.tracker.ui.BeachLocations
import com.pbcplume.tracker.ui.ConditionsViewModel
import com.pbcplume.tracker.ui.LiveLocationViewModel
import com.pbcplume.tracker.ui.LocationSelectionViewModel
import com.pbcplume.tracker.ui.LocationWeatherState
import com.pbcplume.tracker.ui.SnorkelUiState
import com.pbcplume.tracker.ui.SnorkelViewModel
import kotlinx.coroutines.launch

class MapFragment : Fragment() {
    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private enum class Scenario { GOOD, FAIR, VIEW_ONLY }

    private val locations = BeachLocations.all
    private val locationSelection: LocationSelectionViewModel by activityViewModels()
    private val conditions: SnorkelViewModel by activityViewModels()
    private val liveLocation: LiveLocationViewModel by activityViewModels()
    private var selected = BeachLocations.get("delray")
    private var scenario = Scenario.GOOD
    private var expanded = false
    private var conditionsState: SnorkelUiState = SnorkelUiState.Loading
    private var weatherState = LocationWeatherState("delray", "unavailable")

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, state: Bundle?): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, state: Bundle?) {
        binding.mapPreview.markers = locations.map { MapPreviewView.Marker(it.id, shortLabel(it), it.municipality, it.lat, it.lon) }
        binding.mapPreview.selectedId = selected.id
        binding.mapPreview.onMarkerSelected = { id -> selectLocation(locations.first { it.id == id }) }
        val toggleText = ColorStateList(arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()), intArrayOf(Color.WHITE, Color.parseColor("#005E66")))
        val toggleBackground = ColorStateList(arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()), intArrayOf(Color.parseColor("#006A70"), Color.WHITE))
        binding.btnMapMode.setTextColor(toggleText)
        binding.btnCameraMode.setTextColor(toggleText)
        binding.btnMapMode.backgroundTintList = toggleBackground
        binding.btnCameraMode.backgroundTintList = toggleBackground
        binding.btnCameraMode.setOnClickListener { findNavController().navigate(R.id.action_map_to_home) }
        binding.btnExpand.setOnClickListener { toggleDetails() }
        binding.btnDetails.setOnClickListener { toggleDetails() }
        binding.btnOpenCamera.setOnClickListener { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(selected.cameraUrl))) }
        binding.btnZoomIn.setOnClickListener { binding.mapPreview.zoomBy(1.35f) }
        binding.btnZoomOut.setOnClickListener { binding.mapPreview.zoomBy(.74f) }
        binding.btnShowAll.setOnClickListener { binding.mapPreview.showAll() }
        binding.btnRecenter.setOnClickListener { centerSelected() }
        binding.btnScenarioMenu.setOnClickListener { showScenarioMenu(it) }
        selected = locationSelection.selected
        binding.mapPreview.selectedId = selected.id
        binding.mapPreview.post {
            locationSelection.mapViewport?.let(binding.mapPreview::restoreViewport) ?: centerSelected()
        }
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                conditions.uiState.collect {
                    conditionsState = it
                    render()
                }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                liveLocation.weather.collect {
                    weatherState = it
                    render()
                }
            }
        }
        liveLocation.load(selected)
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                locationSelection.selectedId.collect { id ->
                    if (selected.id != id) {
                        selected = BeachLocations.get(id)
                        scenario = if (selected.viewOnly) Scenario.VIEW_ONLY else Scenario.GOOD
                        binding.mapPreview.selectedId = id
                        liveLocation.load(selected)
                        render()
                        binding.mapPreview.post { centerSelected() }
                    }
                }
            }
        }
        render()
    }

    private fun selectLocation(location: BeachLocation) {
        selected = location
        locationSelection.select(location.id)
        liveLocation.load(location)
        scenario = if (location.viewOnly) Scenario.VIEW_ONLY else Scenario.GOOD
        expanded = false
        binding.mapPreview.selectedId = location.id
        render()
        binding.mapPreview.post { centerSelected() }
    }

    private fun toggleDetails() {
        expanded = !expanded
        render()
        binding.mapPreview.post { centerSelected() }
    }

    private fun centerSelected() {
        binding.mapPreview.centerOn(selected.id, binding.cardConditions.top)
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
                locationSelection.select(selected.id)
                binding.mapPreview.selectedId = selected.id
                render()
                binding.mapPreview.post { centerSelected() }
                true
            }
            show()
        }
    }

    private fun render() = with(binding) {
        val prefs = requireContext().getSharedPreferences(ConditionsViewModel.PREF_FILE, 0)
        val demoMode = prefs.getBoolean(ConditionsViewModel.PREF_DEMO_MODE, ConditionsViewModel.DEFAULT_DEMO_MODE)
        tvLocation.text = selected.name
        tvMunicipality.text = selected.municipality
        tvMapMode.text = if (demoMode) "DEMO · SIMULATED" else "LIVE · NO RATING"
        btnScenarioMenu.visibility = if (demoMode) View.VISIBLE else View.GONE
        if (!demoMode) {
            renderLive()
        } else if (selected.id != "delray") {
            renderDemoLocation()
        } else when (scenario) {
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

    private fun renderDemoLocation() = with(binding) {
        rating("Not rated", "#E4F0F3", "#405B66")
        tvCompactConditions.text = "Recorded local observations unavailable"
        tvCompactEvidence.text = if (selected.viewOnly) "View-only camera · open provider" else "No bundled local imagery"
        tvWind.text = "Unavailable"
        tvRain.text = "Unavailable"
        tvMotion.text = "Unavailable"
        tvAppearance.text = "No imagery or analysis from another location is substituted."
        sargassum(false, "Offshore sargassum context", "Recorded regional composite")
        tvReason.text = "Offline Demo contains no location-specific observation bundle for ${selected.name}."
    }

    private fun renderLive() = with(binding) {
        rating("Not rated", "#E4F0F3", "#405B66")
        val data = (conditionsState as? SnorkelUiState.Success)?.data
        val camera = data?.cameras?.firstOrNull { it.cameraId in selected.cameraIds }
        val localWeather = weatherState.takeIf { it.locationId == selected.id }
        val checking = localWeather?.status == "checking" || conditionsState is SnorkelUiState.Loading || data?.refreshStatus == "running"
        val wind = localWeather?.windMph?.let { speed -> "${compass(localWeather.windFromDegrees)} %.1f mph".format(speed) }
        val rain = localWeather?.rain24hInches?.let { "%.2f in".format(it) }
        val health = when {
            checking -> "Camera checking"
            camera == null && selected.viewOnly -> "View-only · open provider"
            camera == null -> "Camera unavailable"
            camera.status == "cached" || camera.freshness == "stale" -> "Camera cached"
            else -> "Camera ${camera.status.replace('_', ' ')}"
        }
        tvCompactConditions.text = listOfNotNull(wind, rain, health).joinToString(" · ").ifBlank { "Checking location observations…" }
        tvCompactEvidence.text = "Local weather ${localWeather?.status ?: "unavailable"} · $health"
        tvWind.text = wind ?: if (checking) "Checking" else "Unavailable"
        tvRain.text = rain ?: if (checking) "Checking" else "Unavailable"
        tvMotion.text = if (selected.motionSupported && data?.surfaceMotion != null) data.surfaceMotion.direction.replaceFirstChar { it.uppercase() } else "Unavailable"
        tvAppearance.text = when {
            selected.viewOnly -> "In-app imagery unsupported · use Open camera"
            camera != null -> "Camera health: $health"
            else -> "No supported imagery is available for this location"
        }
        val algae = data?.algae
        sargassum(false, "Offshore sargassum context", algae?.periodEnd?.let { "Composite ended $it" } ?: "Unavailable")
        tvReason.text = "Live observations are source-specific. Missing or non-local values remain unavailable; no rating is calculated."
    }

    private fun compass(degrees: Double?): String {
        if (degrees == null) return "—"
        val points = listOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        return points[((degrees + 22.5) / 45.0).toInt() % points.size]
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

    private fun shortLabel(location: BeachLocation) = when (location.id) {
        "jupiter" -> "Jupiter Beach"
        "singer" -> "Singer Island"
        "boynton" -> "Boynton Inlet"
        "delray" -> "Delray"
        "boca" -> "South Beach Park"
        "ebb" -> "Ebb Tide"
        "hilton" -> "Hilton"
        else -> "Courtyard"
    }

    override fun onStop() {
        locationSelection.mapViewport = binding.mapPreview.viewport()
        super.onStop()
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}

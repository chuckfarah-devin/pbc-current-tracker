package com.pbcplume.tracker.ui.home

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.navigation.fragment.findNavController
import coil.load
import com.pbcplume.tracker.R
import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import com.pbcplume.tracker.databinding.FragmentHomeBinding
import com.pbcplume.tracker.ui.BeachLocations
import com.pbcplume.tracker.ui.ConditionsViewModel
import com.pbcplume.tracker.ui.LiveLocationViewModel
import com.pbcplume.tracker.ui.LocationSelectionViewModel
import com.pbcplume.tracker.ui.LocationWeatherState
import com.pbcplume.tracker.ui.SnorkelUiState
import com.pbcplume.tracker.ui.SnorkelViewModel
import com.pbcplume.tracker.util.SnorkelFormat
import kotlinx.coroutines.launch
import timber.log.Timber

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private val viewModel: SnorkelViewModel by activityViewModels()
    private val locationSelection: LocationSelectionViewModel by activityViewModels()
    private val liveLocation: LiveLocationViewModel by activityViewModels()
    private var currentConditions: SnorkelConditionsResponse? = null
    private var weatherState = LocationWeatherState("delray", "unavailable")
    private var selectedCameraId: String? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnRefresh.setOnClickListener {
            viewModel.refresh()
            liveLocation.load(locationSelection.selected, force = true)
        }
        binding.btnMap.setOnClickListener { findNavController().navigate(R.id.action_home_to_map) }
        binding.btnSeeEvidence.setOnClickListener { openEvidenceSheet() }
        binding.btnOpenSfwmd.setOnClickListener { openSfwmd() }
        binding.btnSettings.setOnClickListener { findNavController().navigate(R.id.action_home_to_settings) }

        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state -> render(state) }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                locationSelection.selectedId.collect {
                    liveLocation.load(locationSelection.selected)
                    currentConditions?.let(::bind)
                }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                liveLocation.weather.collect {
                    weatherState = it
                    currentConditions?.let(::bind)
                }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.isRefreshing.collect { refreshing ->
                    binding.progressBar.visibility = if (refreshing) View.VISIBLE else View.GONE
                }
            }
        }
    }

    private fun render(state: SnorkelUiState) {
        when (state) {
            is SnorkelUiState.Loading -> {
                binding.progressBar.visibility = View.VISIBLE
                binding.tvError.visibility = View.GONE
            }
            is SnorkelUiState.Error -> {
                binding.progressBar.visibility = View.GONE
                binding.tvError.visibility = View.VISIBLE
                binding.tvError.text = state.message
                Timber.e("Home error: ${state.message}")
            }
            is SnorkelUiState.Success -> {
                binding.progressBar.visibility = View.GONE
                binding.tvError.visibility = View.GONE
                currentConditions = state.data
                bind(state.data)
            }
        }
    }

    private fun bind(data: SnorkelConditionsResponse) {
        // Demo mode banner
        val prefs = requireContext().getSharedPreferences(ConditionsViewModel.PREF_FILE, 0)
        val demoMode = prefs.getBoolean(ConditionsViewModel.PREF_DEMO_MODE, ConditionsViewModel.DEFAULT_DEMO_MODE)
        binding.tvDemoModeBanner.visibility = if (demoMode) View.VISIBLE else View.GONE

        val selectedLocation = locationSelection.selected
        val appearance = data.waterAppearance.firstOrNull { it.cameraId in selectedLocation.cameraIds }
        val health = data.cameras.firstOrNull { it.cameraId in selectedLocation.cameraIds }

        selectedCameraId = appearance?.cameraId ?: health?.cameraId

        val framingOk = appearance?.framingVerified == true
        val heroImage = if (framingOk) appearance?.imageUrl else health?.imageUrl
        if (heroImage != null) {
            binding.ivCameraHero.load(heroImage) {
                crossfade(true)
                placeholder(R.drawable.ic_launcher_background)
            }
        } else {
            binding.ivCameraHero.setImageResource(R.drawable.ic_launcher_background)
        }
        binding.tvHeroHeadline.text = when {
            framingOk && !appearance?.headline.isNullOrBlank() -> appearance?.headline
            health != null -> getString(R.string.camera_visual_review)
            selectedLocation.viewOnly -> "View-only camera"
            else -> "Imagery unavailable"
        }
        binding.tvHeroCamera.text = selectedLocation.name
        if (appearance == null && health == null) {
            binding.btnSeeEvidence.text = "Open live camera"
            binding.btnSeeEvidence.setOnClickListener { openUrl(selectedLocation.cameraUrl) }
        } else {
            binding.btnSeeEvidence.text = getString(R.string.see_evidence)
            binding.btnSeeEvidence.setOnClickListener { openEvidenceSheet() }
        }

        val observed = SnorkelFormat.time(health?.observedAt ?: appearance?.observedAt)
        val age = health?.ageMinutes
        val provider = health?.observedAtLocal ?: appearance?.observedAtLocal
        val retrieved = SnorkelFormat.time(health?.fetchedAt ?: appearance?.fetchedAt)
        val cameraFreshness = when {
            data.mode == "recorded_replay" -> "Recorded"
            health?.status == "cached" -> "Cached"
            else -> "Updated"
        }
        binding.tvHeroTime.text = "$cameraFreshness · ${SnorkelFormat.cameraTime(observed, age, provider, retrieved)}"

        val localWeather = data.weather.takeIf {
            kotlin.math.abs(data.location.lat - selectedLocation.lat) < .08 &&
                kotlin.math.abs(data.location.lon - selectedLocation.lon) < .08
        }

        val liveWeather = weatherState.takeIf { !demoMode && it.locationId == selectedLocation.id }
        val speed = if (demoMode) localWeather?.wind?.speedMph else liveWeather?.windMph
        val direction = if (demoMode) localWeather?.wind?.fromCompass else compass(liveWeather?.windFromDegrees)
        binding.tvWindHeadline.text = speed?.let { "%.1f mph".format(it) } ?: weatherLabel(liveWeather)
        binding.tvWindGusts.text = direction?.let { "From $it" } ?: getString(R.string.na)
        binding.tvWindLabel.text = if (demoMode) {
            localWeather?.wind?.timeUtc?.let { "Recorded · ${SnorkelFormat.time(it)}" } ?: getString(R.string.na)
        } else {
            "${liveWeather?.status?.replaceFirstChar { it.uppercase() } ?: "Unavailable"} · ${liveWeather?.source ?: "Open-Meteo"}${liveWeather?.observedAt?.let { " · $it" } ?: ""}"
        }

        val recent = if (demoMode) localWeather?.recent24h?.inches ?: localWeather?.recent24h?.mm?.div(25.4) else liveWeather?.rain24hInches
        binding.tvRainRecent.text = recent?.let { "%.2f in".format(it) } ?: weatherLabel(liveWeather)
        binding.tvRainPeriod.text = getString(R.string.rain_previous)
        binding.tvRainForward.text = if (demoMode) "Recorded local window" else "${liveWeather?.status?.replaceFirstChar { it.uppercase() } ?: "Unavailable"} · location-specific"

        // Algae
        fun setLinkButton(btn: android.view.View, url: String?) {
            if (url?.isNotBlank() == true) {
                btn.visibility = View.VISIBLE
                btn.setOnClickListener { openUrl(url) }
            } else {
                btn.visibility = View.GONE
            }
        }

        data.algae?.let { a ->
            val region = a.regions.find { it.name.contains("Boynton", ignoreCase = true) }
                ?: a.regions.firstOrNull()
            val periodAge = SnorkelFormat.periodAge(a.periodEnd)
            binding.tvAlgaeStatus.text = region?.let { SnorkelFormat.shortAlgaeStatus(it.status) }
                ?: getString(R.string.na)
            binding.tvAlgaePeriod.text = buildString {
                append(if (data.mode == "recorded_replay") "Recorded · " else if (a.limitations.any { it.contains("cached", true) }) "Cached · " else "Updated · ")
                append("${a.periodStart} to ${a.periodEnd}")
                if (periodAge != null) append(" · $periodAge")
                append(" · nominal ${a.nominalResolutionM}m composite")
            }
            val chartVisible = !a.sourceImageUrl.isNullOrBlank()
            val sourceVisible = !a.sourceUrl.isNullOrBlank()
            val legendVisible = !a.sourceLegendUrl.isNullOrBlank()
            binding.btnViewUsfChart.visibility = View.VISIBLE
            binding.btnViewUsfChart.setOnClickListener { findNavController().navigate(R.id.action_home_to_sargassum_chart) }
            setLinkButton(binding.btnViewUsfSource, a.sourceUrl)
            setLinkButton(binding.btnViewUsfLegend, a.sourceLegendUrl)
            binding.tvUsfDot1.visibility =
                if (chartVisible && (sourceVisible || legendVisible)) View.VISIBLE else View.GONE
            binding.tvUsfDot2.visibility =
                if (sourceVisible && legendVisible) View.VISIBLE else View.GONE
        } ?: run {
            binding.tvAlgaeStatus.text = getString(R.string.na)
            binding.tvAlgaePeriod.text = getString(R.string.na)
            binding.btnViewUsfChart.visibility = View.GONE
            binding.btnViewUsfSource.visibility = View.GONE
            binding.btnViewUsfLegend.visibility = View.GONE
        }

        // Surface flow (experimental)
        val m = data.surfaceMotion.takeIf { selectedLocation.motionSupported }
        val fallbackCameraUrl = health?.pageUrl ?: appearance?.sourceUrl
        val actionUrl = m?.clipUrl ?: m?.regionsImageUrl ?: fallbackCameraUrl
        val isActionable = !actionUrl.isNullOrBlank()

        val checking = m?.status == "checking" || m?.evidenceStrength == "pending"
        val (headline, support, arrowRes) = when {
            m == null -> Triple(getString(R.string.surface_flow_unavailable), "", null)
            checking -> Triple(getString(R.string.surface_flow_checking), m.interpretation, null)
            m.evidenceStrength == "likely" -> Triple("Likely ${m.direction}", if (data.mode == "recorded_replay") "Recorded reference · not live." else m.automatedObservation ?: "", when (m.direction) {
                "northward" -> R.drawable.ic_direction_n
                "southward" -> R.drawable.ic_direction_s
                else -> R.drawable.ic_direction_none
            })
            m.evidenceStrength == "possible" -> Triple("Possible ${m.direction}", m.automatedObservation ?: "", when (m.direction) {
                "northward" -> R.drawable.ic_direction_n
                "southward" -> R.drawable.ic_direction_s
                else -> R.drawable.ic_direction_none
            })
            m.evidenceStrength == "mixed" -> Triple("Motion detected · direction mixed", m.automatedObservation ?: "", R.drawable.ic_direction_none)
            m.evidenceStrength == "none" -> Triple(getString(R.string.surface_flow_no_clear_motion), m.automatedObservation ?: "", R.drawable.ic_direction_none)
            else -> Triple(getString(R.string.surface_flow_unavailable), m.reason ?: m.interpretation, R.drawable.ic_direction_none)
        }

        binding.tvSurfaceFlowTitle.text = "Surface flow · ${selectedLocation.name}"
        binding.tvSurfaceFlowStatus.text = headline
        binding.tvSurfaceFlowSupport.text = support
        binding.tvSurfaceFlowSupport.visibility =
            if (support.isBlank()) View.GONE else View.VISIBLE
        if (arrowRes != null) {
            binding.ivSurfaceFlowArrow.setImageResource(arrowRes)
            binding.ivSurfaceFlowArrow.visibility = View.VISIBLE
        } else {
            binding.ivSurfaceFlowArrow.visibility = View.GONE
        }

        val flowObserved = SnorkelFormat.time(m?.observedAt)
        val flowRetrieved = SnorkelFormat.time(m?.retrievedAt)
        val flowAnalyzed = SnorkelFormat.time(m?.analyzedAt ?: m?.fetchedAt)
        binding.tvSurfaceFlowTime.text = buildString {
            append((m?.freshness ?: "unknown").replaceFirstChar { it.uppercase() })
            if (flowRetrieved != null) append(" · retrieved $flowRetrieved")
            if (flowObserved != null) append(" · captured $flowObserved") else append(" · capture time unverified")
            if (flowAnalyzed != null) {
                append("\nAnalyzed $flowAnalyzed")
            } else if (checking) {
                append("\nAnalysis in progress…")
            }
        }

        if (isActionable) {
            binding.cardSurfaceFlow.isClickable = true
            binding.cardSurfaceFlow.isFocusable = true
            binding.ivSurfaceFlowChevron.visibility = View.VISIBLE
            binding.cardSurfaceFlow.setOnClickListener { openEvidenceSheet(selectedCameraId) }
            binding.cardSurfaceFlow.contentDescription = getString(R.string.view_surface_flow_evidence)
        } else {
            binding.cardSurfaceFlow.isClickable = false
            binding.cardSurfaceFlow.isFocusable = false
            binding.ivSurfaceFlowChevron.visibility = View.GONE
            binding.cardSurfaceFlow.setOnClickListener(null)
            binding.cardSurfaceFlow.contentDescription = null
        }

        // C-16
        binding.tvC16Notes.text = data.c16?.notes ?: getString(R.string.na)
    }

    private fun compass(degrees: Double?): String? {
        if (degrees == null) return null
        val points = listOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        return points[((degrees + 22.5) / 45.0).toInt() % points.size]
    }

    private fun weatherLabel(weather: LocationWeatherState?) = when (weather?.status) {
        "checking" -> "Checking"
        "cached" -> "Cached"
        else -> getString(R.string.na)
    }

    private fun openEvidenceSheet(cameraId: String? = selectedCameraId) {
        EvidenceBottomSheet.newInstance(cameraId ?: "delray")
            .show(childFragmentManager, EvidenceBottomSheet.TAG)
    }

    private fun openUrl(url: String) {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    private fun openSfwmd() {
        val url = currentConditions?.c16?.infoUrl ?: "https://www.sfwmd.gov/"
        openUrl(url)
    }


    override fun onResume() {
        super.onResume()
        viewModel.load()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

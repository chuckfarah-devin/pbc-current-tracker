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
import com.pbcplume.tracker.ui.ConditionsViewModel
import com.pbcplume.tracker.ui.SnorkelUiState
import com.pbcplume.tracker.ui.SnorkelViewModel
import com.pbcplume.tracker.util.SnorkelFormat
import kotlinx.coroutines.launch
import timber.log.Timber

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private val viewModel: SnorkelViewModel by activityViewModels()
    private var currentConditions: SnorkelConditionsResponse? = null
    private var selectedCameraId: String? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnRefresh.setOnClickListener { viewModel.refresh() }
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

        // Camera hero — default to Delray, otherwise the first available appearance
        val appearance = data.waterAppearance.find { it.cameraId == "delray" }
            ?: data.waterAppearance.firstOrNull()
        val health = data.cameras.find { it.cameraId == appearance?.cameraId }
            ?: data.cameras.firstOrNull()

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
            else -> getString(R.string.na)
        }
        binding.tvHeroCamera.text = appearance?.location
            ?: health?.location
            ?: getString(R.string.na)

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

        // Wind
        data.weather?.wind?.let { w ->
            val speed = w.speedMph ?: w.speedKn?.times(1.150779448)
            val gust = w.gustMph ?: w.gustKn?.times(1.150779448)
            val from = w.fromCompass ?: getString(R.string.na)
            val toward = w.towardCompass ?: getString(R.string.na)
            binding.tvWindHeadline.text = if (speed != null) "%.1f mph".format(speed) else getString(R.string.na)
            binding.tvWindGusts.text = "From $from · toward $toward"
            binding.tvWindLabel.text = buildString {
                if (gust != null) {
                    val period = w.gustPeriod?.let { " · $it" } ?: ""
                    append("Gusts %.1f mph$period".format(gust))
                }
                SnorkelFormat.time(w.timeUtc)?.let {
                    if (isNotEmpty()) append("\n")
                    append("${if (data.mode == "recorded_replay") "Recorded" else "Updated"} · $it")
                }
            }.ifBlank { getString(R.string.na) }
        } ?: run {
            binding.tvWindHeadline.text = getString(R.string.na)
            binding.tvWindGusts.text = getString(R.string.na)
            binding.tvWindLabel.text = getString(R.string.na)
        }

        // Rain
        data.weather?.let { w ->
            val recent = w.recent24h.mm
            val forward = w.forward24h.mm
            binding.tvRainRecent.text = if (recent != null) "%.1f mm".format(recent) else getString(R.string.na)
            binding.tvRainPeriod.text = getString(R.string.rain_previous)
            binding.tvRainForward.text = buildString {
                append(if (forward != null) "${getString(R.string.rain_next)} · %.1f mm".format(forward) else getString(R.string.na))
                val start = SnorkelFormat.time(w.recent24h.startUtc)
                val end = SnorkelFormat.time(w.recent24h.endUtc)
                if (start != null || end != null) append("\n${if (data.mode == "recorded_replay") "Recorded" else "Updated"} · ${start ?: "?"}–${end ?: "?"}")
            }
        } ?: run {
            binding.tvRainRecent.text = getString(R.string.na)
            binding.tvRainPeriod.text = getString(R.string.rain_previous)
            binding.tvRainForward.text = getString(R.string.na)
        }

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
            setLinkButton(binding.btnViewUsfChart, a.sourceImageUrl)
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
        val m = data.surfaceMotion
        val delrayHealth = data.cameras.find { it.cameraId == "delray" }
        val fallbackCameraUrl = delrayHealth?.pageUrl ?: appearance?.sourceUrl
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

        binding.tvSurfaceFlowTitle.text = "Surface flow · ${m?.location ?: "Delray Beach"}"
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
            binding.cardSurfaceFlow.setOnClickListener { openEvidenceSheet("delray") }
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


    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

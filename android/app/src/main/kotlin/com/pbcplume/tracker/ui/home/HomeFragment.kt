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
            framingOk && appearance?.headline != null -> appearance.headline
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
        binding.tvHeroTime.text = SnorkelFormat.cameraTime(observed, age, provider, retrieved)

        // Wind
        data.weather?.wind?.let { w ->
            val speed = w.speedMph ?: w.speedKn?.times(1.150779448)
            val gust = w.gustMph ?: w.gustKn?.times(1.150779448)
            val from = w.fromCompass ?: getString(R.string.na)
            val toward = w.towardCompass ?: getString(R.string.na)
            binding.tvWindHeadline.text = if (speed != null) "%.1f mph".format(speed) else getString(R.string.na)
            binding.tvWindGusts.text = "From $from · toward $toward"
            binding.tvWindLabel.text = if (gust != null) {
                val period = w.gustPeriod?.let { " · $it" } ?: ""
                "Gusts %.1f mph$period".format(gust)
            } else {
                getString(R.string.na)
            }
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
            binding.tvRainForward.text = if (forward != null)
                "${getString(R.string.rain_next)} · %.1f mm".format(forward)
            else
                getString(R.string.na)
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
        data.surfaceMotion?.let { m ->
            val rawDirection = m.userLabel?.removePrefix("Surface flow: ")?.trim() ?: getString(R.string.na)
            val direction = rawDirection.replaceFirstChar { it.uppercase() }
            binding.tvSurfaceFlowStatus.text = direction
            binding.tvSurfaceFlowSupport.text = if (data.mode == "recorded_replay") {
                "Recorded reference · not live."
            } else {
                m.automatedObservation ?: m.interpretation ?: ""
            }
            binding.tvSurfaceFlowSupport.visibility =
                if (binding.tvSurfaceFlowSupport.text.isBlank()) View.GONE else View.VISIBLE
            binding.ivSurfaceFlowArrow.setImageResource(when {
                rawDirection.contains("northward") -> R.drawable.ic_direction_n
                rawDirection.contains("southward") -> R.drawable.ic_direction_s
                else -> R.drawable.ic_direction_none
            })
            binding.ivSurfaceFlowArrow.visibility = View.VISIBLE
            val flowObserved = SnorkelFormat.time(m.observedAt)
            val flowAnalyzed = SnorkelFormat.time(m.fetchedAt)
            binding.tvSurfaceFlowTime.text = buildString {
                if (flowObserved != null) append("Observed $flowObserved")
                if (flowAnalyzed != null) {
                    if (isNotEmpty()) append(" · ")
                    append("analyzed $flowAnalyzed")
                }
                if (isEmpty()) append("Capture time unknown")
            }
            val url = m.clipUrl?.takeIf { it.isNotBlank() } ?: m.regionsImageUrl
            if (url != null) {
                binding.cardSurfaceFlow.setOnClickListener { openSurfaceFlowEvidence(url) }
            } else {
                binding.cardSurfaceFlow.setOnClickListener(null)
            }
        } ?: run {
            binding.tvSurfaceFlowStatus.text = getString(R.string.na)
            binding.tvSurfaceFlowSupport.visibility = View.GONE
            binding.tvSurfaceFlowTime.text = "Capture time unknown"
            binding.ivSurfaceFlowArrow.visibility = View.GONE
            binding.cardSurfaceFlow.setOnClickListener(null)
        }

        // C-16
        binding.tvC16Notes.text = data.c16?.notes ?: getString(R.string.na)
    }

    private fun openEvidenceSheet() {
        val cameraId = selectedCameraId ?: return
        EvidenceBottomSheet.newInstance(cameraId)
            .show(childFragmentManager, EvidenceBottomSheet.TAG)
    }

    private fun openUrl(url: String) {
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    private fun openSfwmd() {
        val url = currentConditions?.c16?.infoUrl ?: "https://www.sfwmd.gov/"
        openUrl(url)
    }

    private fun openSurfaceFlowEvidence(url: String) {
        openUrl(url)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

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
        // Mode banner (recorded or live)
        binding.tvModeBanner.visibility = View.VISIBLE
        binding.tvModeBanner.text = when (data.mode) {
            "live" -> "Live fetch · check each observation time"
            else -> getString(R.string.recorded_replay)
        }

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
            health != null -> "Camera view for visual review · framing not verified"
            else -> getString(R.string.na)
        }
        binding.tvHeroCamera.text = appearance?.let { "${it.location} · ${it.cameraId}" }
            ?: health?.let { "${it.location} · ${it.view ?: it.cameraId}" }
            ?: getString(R.string.na)

        val observed = SnorkelFormat.time(health?.observedAt ?: appearance?.observedAt)
        val age = health?.ageMinutes
        val provider = health?.observedAtLocal ?: appearance?.observedAtLocal
        val retrieved = SnorkelFormat.time(health?.fetchedAt ?: appearance?.fetchedAt)
        binding.tvHeroTime.text = SnorkelFormat.cameraTime(observed, age, provider, retrieved)

        val status = SnorkelFormat.statusLabel(health?.status ?: appearance?.status)
        val ageText = SnorkelFormat.ageLabel(age)
        binding.tvHeroFreshness.text = if (ageText != null) "$status · $ageText" else status

        // Wind
        data.weather?.wind?.let { w ->
            val speed = w.speedMph ?: w.speedKn?.times(1.150779448)
            val gust = w.gustMph ?: w.gustKn?.times(1.150779448)
            val mphText = if (speed != null) "%.1f mph".format(speed) else getString(R.string.na)
            val from = w.fromCompass ?: getString(R.string.na)
            val toward = w.towardCompass?.let { " → $it" } ?: ""
            binding.tvWindHeadline.text = "$mphText from $from$toward"
            binding.tvWindGusts.text = if (gust != null)
                "Gusts %.1f mph · %s".format(gust, w.gustPeriod ?: "")
            else
                getString(R.string.na)
            binding.tvWindLabel.text = w.preferredLabel
                ?: getString(R.string.loading)
        } ?: run {
            binding.tvWindHeadline.text = getString(R.string.na)
            binding.tvWindGusts.text = getString(R.string.na)
            binding.tvWindLabel.text = getString(R.string.na)
        }

        // Rain
        data.weather?.let { w ->
            val recent = w.recent24h.mm
            val forward = w.forward24h.mm
            binding.tvRainRecent.text = if (recent != null)
                "%.1f mm / previous 24 completed hours".format(recent)
            else
                getString(R.string.na)
            binding.tvRainForward.text = if (forward != null)
                "Next 24-hour window: %.1f mm".format(forward)
            else
                getString(R.string.na)
        } ?: run {
            binding.tvRainRecent.text = getString(R.string.na)
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
            binding.tvAlgaeStatus.text = region?.let { SnorkelFormat.statusLabel(it.status) }
                ?: getString(R.string.na)
            binding.tvAlgaePeriod.text = buildString {
                append("${a.periodStart} to ${a.periodEnd}")
                if (periodAge != null) append(" · $periodAge")
                append(" · nominal ${a.nominalResolutionM}m composite")
            }
            setLinkButton(binding.btnViewUsfChart, a.sourceImageUrl)
            setLinkButton(binding.btnViewUsfSource, a.sourceUrl)
            setLinkButton(binding.btnViewUsfLegend, a.sourceLegendUrl)
        } ?: run {
            binding.tvAlgaeStatus.text = getString(R.string.na)
            binding.tvAlgaePeriod.text = getString(R.string.na)
            binding.btnViewUsfChart.visibility = View.GONE
            binding.btnViewUsfSource.visibility = View.GONE
            binding.btnViewUsfLegend.visibility = View.GONE
        }

        // Surface flow (experimental)
        data.surfaceMotion?.let { m ->
            binding.tvSurfaceFlowStatus.text = m.userLabel ?: getString(R.string.na)
            binding.tvSurfaceFlowTime.text = SnorkelFormat.time(m.observedAt)
                ?.let { "Observed $it" }
                ?: getString(R.string.na)
            val url = m.clipUrl?.takeIf { it.isNotBlank() } ?: m.regionsImageUrl
            if (url != null) {
                binding.btnSurfaceFlowEvidence.visibility = View.VISIBLE
                binding.btnSurfaceFlowEvidence.setOnClickListener { openSurfaceFlowEvidence(url) }
            } else {
                binding.btnSurfaceFlowEvidence.visibility = View.GONE
            }
        } ?: run {
            binding.tvSurfaceFlowStatus.text = getString(R.string.na)
            binding.tvSurfaceFlowTime.text = getString(R.string.na)
            binding.btnSurfaceFlowEvidence.visibility = View.GONE
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

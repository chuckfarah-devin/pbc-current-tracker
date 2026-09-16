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
        // Recorded replay banner
        if (data.mode == "recorded_replay") {
            binding.tvModeBanner.visibility = View.VISIBLE
            binding.tvModeBanner.text = getString(R.string.recorded_replay)
        } else {
            binding.tvModeBanner.visibility = View.GONE
        }

        // Camera hero — default to Delray, otherwise the first available appearance
        val appearance = data.waterAppearance.find { it.cameraId == "delray" }
            ?: data.waterAppearance.firstOrNull()
        val health = data.cameras.find { it.cameraId == appearance?.cameraId }
            ?: data.cameras.firstOrNull()

        selectedCameraId = appearance?.cameraId ?: health?.cameraId

        val heroImage = appearance?.imageUrl ?: health?.imageUrl
        if (heroImage != null) {
            binding.ivCameraHero.load(heroImage) {
                crossfade(true)
                placeholder(R.drawable.ic_launcher_background)
            }
        } else {
            binding.ivCameraHero.setImageResource(R.drawable.ic_launcher_background)
        }

        binding.tvHeroHeadline.text = appearance?.headline
            ?: getString(R.string.loading)
        binding.tvHeroCamera.text = appearance?.let { "${it.location} · ${it.cameraId}" }
            ?: health?.let { "${it.location} · ${it.view ?: it.cameraId}" }
            ?: getString(R.string.na)

        val observed = SnorkelFormat.time(appearance?.observedAt ?: health?.observedAt)
        val retrieved = SnorkelFormat.time(appearance?.fetchedAt ?: health?.fetchedAt)
        binding.tvHeroTime.text = when {
            observed != null -> "Observed $observed"
            retrieved != null -> "Retrieved $retrieved · capture time unverified"
            else -> getString(R.string.na)
        }

        binding.tvHeroFreshness.text = SnorkelFormat.statusLabel(health?.status ?: appearance?.status)

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
        data.algae?.let { a ->
            val region = a.regions.find { it.name.contains("Boynton", ignoreCase = true) }
                ?: a.regions.firstOrNull()
            binding.tvAlgaeStatus.text = region?.status ?: a.periodEnd
            binding.tvAlgaePeriod.text = "${a.periodStart} to ${a.periodEnd} · nominal ${a.nominalResolutionM}m composite"
        } ?: run {
            binding.tvAlgaeStatus.text = getString(R.string.na)
            binding.tvAlgaePeriod.text = getString(R.string.na)
        }

        // C-16
        binding.tvC16Notes.text = data.c16?.notes ?: getString(R.string.na)
    }

    private fun openEvidenceSheet() {
        val cameraId = selectedCameraId ?: return
        EvidenceBottomSheet.newInstance(cameraId)
            .show(childFragmentManager, EvidenceBottomSheet.TAG)
    }

    private fun openSfwmd() {
        val url = currentConditions?.c16?.infoUrl ?: "https://www.sfwmd.gov/"
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

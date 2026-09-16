package com.pbcplume.tracker.ui.home

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import coil.load
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.pbcplume.tracker.R
import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import com.pbcplume.tracker.databinding.BottomSheetEvidenceBinding
import com.pbcplume.tracker.ui.SnorkelUiState
import com.pbcplume.tracker.ui.SnorkelViewModel
import com.pbcplume.tracker.util.SnorkelFormat
import kotlinx.coroutines.launch

class EvidenceBottomSheet : BottomSheetDialogFragment() {

    companion object {
        const val TAG = "EvidenceBottomSheet"
        private const val ARG_CAMERA_ID = "camera_id"

        fun newInstance(cameraId: String): EvidenceBottomSheet {
            return EvidenceBottomSheet().apply {
                arguments = Bundle().apply {
                    putString(ARG_CAMERA_ID, cameraId)
                }
            }
        }
    }

    private var _binding: BottomSheetEvidenceBinding? = null
    private val binding get() = _binding!!
    private val viewModel: SnorkelViewModel by activityViewModels()
    private val cameraId: String? by lazy { arguments?.getString(ARG_CAMERA_ID) }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = BottomSheetEvidenceBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    if (state is SnorkelUiState.Success) bind(state.data)
                }
            }
        }
    }

    private fun bind(data: SnorkelConditionsResponse) {
        val appearance = data.waterAppearance.find { it.cameraId == cameraId }
            ?: data.waterAppearance.firstOrNull()
        val health = data.cameras.find { it.cameraId == appearance?.cameraId ?: cameraId }
            ?: data.cameras.firstOrNull()

        val imageUrl = appearance?.imageUrl ?: health?.imageUrl
        if (imageUrl != null) {
            binding.ivEvidenceImage.load(imageUrl) { crossfade(true) }
        } else {
            binding.ivEvidenceImage.setImageResource(R.drawable.ic_launcher_background)
        }

        binding.tvEvidenceHeadline.text = appearance?.headline ?: getString(R.string.na)
        binding.tvEvidenceCamera.text = appearance?.let { "${it.location} · ${it.cameraId}" }
            ?: health?.let { "${it.location} · ${it.view ?: it.cameraId}" }
            ?: getString(R.string.na)

        val observed = SnorkelFormat.time(health?.observedAt ?: appearance?.observedAt)
        val age = health?.ageMinutes
        val provider = health?.observedAtLocal ?: appearance?.observedAtLocal
        val retrieved = SnorkelFormat.time(health?.fetchedAt ?: appearance?.fetchedAt)
        binding.tvEvidenceObserved.text = SnorkelFormat.cameraTime(observed, age, provider, retrieved)

        val status = SnorkelFormat.statusLabel(health?.status ?: appearance?.status)
        val ageText = SnorkelFormat.ageLabel(age)
        binding.tvEvidenceStatus.text = if (ageText != null) "$status · $ageText" else status

        val sourceUrl = health?.pageUrl ?: appearance?.sourceUrl
        binding.btnSourceLink.setOnClickListener {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(sourceUrl ?: "https://www.sfwmd.gov/")))
        }
        binding.btnSourceLink.isEnabled = sourceUrl != null

        binding.containerSamples.removeAllViews()
        when {
            appearance?.framingVerified != true -> {
                val tv = TextView(requireContext())
                tv.text = "Framing not verified · no automated colour claim."
                tv.setPadding(0, 4, 0, 4)
                tv.setTextColor(requireContext().getColor(android.R.color.white))
                binding.containerSamples.addView(tv)
            }
            appearance.samples.isNullOrEmpty() -> {
                val tv = TextView(requireContext())
                tv.text = getString(R.string.na)
                tv.setTextColor(requireContext().getColor(android.R.color.white))
                binding.containerSamples.addView(tv)
            }
            else -> {
                appearance.samples.forEach { s ->
                    val tv = TextView(requireContext())
                    tv.text = (
                        "${s.region}: ${"%.1f".format(s.blueGreenPercent)}% blue-green, " +
                        "${"%.1f".format(s.warmPercent)}% warm, " +
                        "${"%.1f".format(s.otherPercent)}% other " +
                        "· ${s.pixels} pixels"
                        )
                    tv.setPadding(0, 4, 0, 4)
                    tv.setTextColor(requireContext().getColor(android.R.color.white))
                    binding.containerSamples.addView(tv)
                }
            }
        }

        data.weather?.let { w ->
            val speed = w.wind.speedMph ?: w.wind.speedKn?.times(1.150779448)
            val from = w.wind.fromCompass ?: getString(R.string.na)
            val toward = w.wind.towardCompass ?: ""
            val gust = w.wind.gustMph ?: w.wind.gustKn?.times(1.150779448)
            binding.tvEvidenceWind.text = (
                "%.1f mph from $from${if (toward.isNotBlank()) " → $toward" else ""}\n".format(speed) +
                "Gusts %.1f mph".format(gust)
            )
            val recent = w.recent24h.mm
            val forward = w.forward24h.mm
            binding.tvEvidenceRain.text = (
                "Previous 24h: %.1f mm\n".format(recent) +
                "Next 24h: %.1f mm".format(forward)
            )
        } ?: run {
            binding.tvEvidenceWind.text = getString(R.string.na)
            binding.tvEvidenceRain.text = getString(R.string.na)
        }

        data.algae?.let { a ->
            val region = a.regions.find { it.name.contains("Boynton", ignoreCase = true) }
                ?: a.regions.firstOrNull()
            val periodAge = SnorkelFormat.periodAge(a.periodEnd)
            val periodAgeText = periodAge?.let { " · $it" } ?: ""
            binding.tvEvidenceAlgae.text = (
                "${region?.let { SnorkelFormat.statusLabel(it.status) } ?: getString(R.string.na)}\n" +
                "${a.periodStart} to ${a.periodEnd}$periodAgeText · ${a.nominalResolutionM} m composite\n" +
                "Rendered-image color match; not measured biomass or beaching severity.\n" +
                (region?.interpretation ?: "")
            )
        } ?: run {
            binding.tvEvidenceAlgae.text = getString(R.string.na)
        }

        val limitations = mutableListOf<String>()
        limitations.addAll(data.limitations)
        health?.limitations?.let { limitations.addAll(it) }
        appearance?.limitations?.let { limitations.addAll(it) }
        binding.tvEvidenceLimitations.text = if (limitations.isEmpty())
            getString(R.string.na)
        else
            limitations.filter { it.isNotBlank() }.joinToString("\n• ", "• ")
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

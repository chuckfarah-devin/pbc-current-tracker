package com.pbcplume.tracker.ui.sargassum

import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import coil.load
import com.pbcplume.tracker.databinding.FragmentSargassumChartBinding
import com.pbcplume.tracker.ui.ConditionsViewModel
import com.pbcplume.tracker.ui.LocationSelectionViewModel
import com.pbcplume.tracker.ui.SnorkelUiState
import com.pbcplume.tracker.ui.SnorkelViewModel
import kotlinx.coroutines.launch

class SargassumChartFragment : Fragment() {
    private var _binding: FragmentSargassumChartBinding? = null
    private val binding get() = _binding!!
    private val conditions: SnorkelViewModel by activityViewModels()
    private val locationSelection: LocationSelectionViewModel by activityViewModels()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, state: Bundle?): View {
        _binding = FragmentSargassumChartBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, state: Bundle?) {
        val prefs = requireContext().getSharedPreferences(ConditionsViewModel.PREF_FILE, 0)
        val demoMode = prefs.getBoolean(ConditionsViewModel.PREF_DEMO_MODE, ConditionsViewModel.DEFAULT_DEMO_MODE)
        if (demoMode) {
            val chart = requireContext().assets.open("demo/sargassum/full_chart.png").use(BitmapFactory::decodeStream)
            val legend = requireContext().assets.open("demo/sargassum/legend.png").use(BitmapFactory::decodeStream)
            binding.chartImage.setImageBitmap(chart)
            binding.legendImage.setImageBitmap(legend)
            binding.chartImage.showRegionalView()
            binding.tvChartMetadata.text = "Recorded demo · Jun 27–Jul 03, 2026 · USF Optical Oceanography Laboratory · 7-day FAD composite"
        } else {
            viewLifecycleOwner.lifecycleScope.launch {
                repeatOnLifecycle(Lifecycle.State.STARTED) {
                    conditions.uiState.collect { ui ->
                        val algae = (ui as? SnorkelUiState.Success)?.data?.algae ?: return@collect
                        binding.chartImage.load(algae.sourceImageUrl) {
                            crossfade(false)
                            allowHardware(false)
                            listener(onSuccess = { _, _ -> binding.chartImage.showRegionalView() })
                        }
                        binding.legendImage.load(algae.sourceLegendUrl) { crossfade(false); allowHardware(false) }
                        binding.tvChartMetadata.text = "${algae.periodStart ?: "?"}–${algae.periodEnd ?: "?"} · USF Optical Oceanography Laboratory · ${algae.composite ?: "composite"}"
                    }
                }
            }
        }
        val selected = locationSelection.selected
        binding.chartImage.setMarker(selected.lon, selected.lat)
        binding.tvMarkerStatus.text = "Amber marker: ${selected.name} · chart bounds verified from the USF GCOOS region definition (98°W–79°W, 18°N–31°N)."
        binding.btnRegionalView.setOnClickListener { binding.chartImage.showRegionalView() }
        binding.btnFullChart.setOnClickListener { binding.chartImage.showFullChart() }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

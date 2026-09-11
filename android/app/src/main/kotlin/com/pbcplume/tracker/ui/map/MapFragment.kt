package com.pbcplume.tracker.ui.map

import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.navigation.fragment.findNavController
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.Style
import com.pbcplume.tracker.R
import com.pbcplume.tracker.databinding.FragmentMapBinding
import com.pbcplume.tracker.ui.ConditionsUiState
import com.pbcplume.tracker.ui.ConditionsViewModel
import com.pbcplume.tracker.ui.sheet.ConditionsBottomSheet
import kotlinx.coroutines.launch
import timber.log.Timber
import kotlin.math.roundToInt

class MapFragment : Fragment() {

    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private val viewModel: ConditionsViewModel by activityViewModels()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Centre map on Boynton Inlet at launch
        binding.mapView.mapboxMap.setCamera(
            CameraOptions.Builder()
                .center(Point.fromLngLat(ConditionsViewModel.DEFAULT_LON, ConditionsViewModel.DEFAULT_LAT))
                .zoom(14.0)
                .build()
        )
        binding.mapView.mapboxMap.loadStyle(Style.MAPBOX_STREETS)

        binding.fabRefresh.setOnClickListener { viewModel.refresh() }

        binding.btnDetails.setOnClickListener {
            ConditionsBottomSheet().show(childFragmentManager, ConditionsBottomSheet.TAG)
        }

        binding.btnSettings.setOnClickListener {
            findNavController().navigate(R.id.action_map_to_settings)
        }

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

    private fun render(state: ConditionsUiState) {
        when (state) {
            is ConditionsUiState.Loading -> {
                binding.tvSnorkelScore.text = "--"
                binding.tvSnorkelLabel.text = getString(R.string.loading)
                binding.cardSnorkel.setCardBackgroundColor(
                    ContextCompat.getColor(requireContext(), R.color.badge_unknown))
                binding.groupCurrentArrow.visibility = View.INVISIBLE
            }
            is ConditionsUiState.Error -> {
                binding.tvSnorkelScore.text = "!"
                binding.tvSnorkelLabel.text = getString(R.string.error_fetch)
                binding.cardSnorkel.setCardBackgroundColor(
                    ContextCompat.getColor(requireContext(), R.color.badge_unknown))
                binding.groupCurrentArrow.visibility = View.INVISIBLE
                Timber.e("Map error: ${state.message}")
            }
            is ConditionsUiState.Success -> {
                val data = state.data
                val score = data.snorkelIndex.score
                binding.tvSnorkelScore.text = score.toString()
                binding.tvSnorkelLabel.text = data.snorkelIndex.label
                binding.cardSnorkel.setCardBackgroundColor(scoreColor(score))

                // Current arrow: rotate ImageView to match current direction
                val dir = data.current.directionDeg
                val spd = data.current.speedMps
                if (dir != null && spd != null) {
                    binding.ivCurrentArrow.rotation = dir.toFloat()
                    val knots = spd * 1.944
                    binding.tvCurrentSpeed.text = String.format("%.1f kt", knots)
                    binding.groupCurrentArrow.visibility = View.VISIBLE
                } else {
                    binding.groupCurrentArrow.visibility = View.INVISIBLE
                }

                // Clarity layer: tint an overlay circle by clarity score
                val clarity = data.turbidity.clarityScore ?: 50
                binding.viewClarityOverlay.setBackgroundColor(clarityColor(clarity))

                Timber.d("Map render OK: score=$score clarity=$clarity")
            }
        }
    }

    /** Snorkel badge color: green -> yellow -> orange -> red */
    private fun scoreColor(score: Int): Int = when {
        score >= 80 -> ContextCompat.getColor(requireContext(), R.color.score_excellent)
        score >= 60 -> ContextCompat.getColor(requireContext(), R.color.score_good)
        score >= 40 -> ContextCompat.getColor(requireContext(), R.color.score_fair)
        score >= 20 -> ContextCompat.getColor(requireContext(), R.color.score_marginal)
        else        -> ContextCompat.getColor(requireContext(), R.color.score_poor)
    }

    /** Clarity overlay: teal(100) -> green -> yellow -> brown(0) */
    private fun clarityColor(score: Int): Int {
        val t = score / 100f
        val r = ((1 - t) * 0x8B + t * 0x00).roundToInt()
        val g = ((1 - t) * 0x45 + t * 0x80).roundToInt()
        val b = ((1 - t) * 0x13 + t * 0x80).roundToInt()
        return Color.argb(120, r, g, b)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

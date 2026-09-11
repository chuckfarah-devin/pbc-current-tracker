package com.pbcplume.tracker.ui.sheet

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.pbcplume.tracker.R
import com.pbcplume.tracker.data.model.ConditionsResponse
import com.pbcplume.tracker.databinding.BottomSheetConditionsBinding
import com.pbcplume.tracker.ui.ConditionsUiState
import com.pbcplume.tracker.ui.ConditionsViewModel
import kotlinx.coroutines.launch

/**
 * Full conditions details panel (expanded bottom sheet).
 * All null fields are shown as "N/A" — never crashes on partial data.
 */
class ConditionsBottomSheet : BottomSheetDialogFragment() {

    companion object {
        const val TAG = "ConditionsBottomSheet"
    }

    private var _binding: BottomSheetConditionsBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ConditionsViewModel by activityViewModels()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = BottomSheetConditionsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    when (state) {
                        is ConditionsUiState.Success -> bind(state.data)
                        is ConditionsUiState.Error   -> showError(state.message)
                        is ConditionsUiState.Loading -> showLoading()
                    }
                }
            }
        }
    }

    private fun bind(d: ConditionsResponse) {
        val na = getString(R.string.na)

        // ── Current ──────────────────────────────────────────────────────────
        binding.tvCurrentSpeed.text    = d.current.speedMps?.let { "%.2f m/s".format(it) } ?: na
        binding.tvCurrentDir.text      = d.current.directionDeg?.let { "%.0f°".format(it) } ?: na
        binding.tvCurrentSource.text   = d.current.source ?: na
        binding.tvCurrentRes.text      = d.current.resolutionM?.let { "${it} m" } ?: na
        binding.tvCurrentError.apply {
            text       = d.current.error ?: ""
            visibility = if (d.current.error != null) View.VISIBLE else View.GONE
        }

        // ── Turbidity / Clarity ───────────────────────────────────────────────
        binding.tvClarityScore.text  = d.turbidity.clarityScore?.toString() ?: na
        binding.tvClarityNtu.text    = d.turbidity.ntu?.let { "%.1f NTU".format(it) } ?: na
        binding.tvClaritySource.text = d.turbidity.source ?: na
        binding.tvClarityRes.text    = d.turbidity.resolutionM?.let { "${it} m" } ?: na
        binding.tvClarityError.apply {
            text       = d.turbidity.error ?: ""
            visibility = if (d.turbidity.error != null) View.VISIBLE else View.GONE
        }

        // ── Runoff ────────────────────────────────────────────────────────────
        binding.tvC16Flow.text         = d.runoff.c16FlowCfs?.let { "%.0f cfs".format(it) } ?: na
        binding.tvRain24h.text         = d.runoff.recentRainMm?.let { "%.1f mm".format(it) } ?: na
        binding.tvRunoffIntensity.text = d.runoff.runoffIntensity?.replaceFirstChar { it.uppercase() } ?: na
        binding.tvRunoffError.apply {
            text       = d.runoff.error ?: ""
            visibility = if (d.runoff.error != null) View.VISIBLE else View.GONE
        }

        // ── Lake O ────────────────────────────────────────────────────────────
        binding.tvLakeStage.text    = d.lakeO.lakeStageFt?.let { "%.1f ft".format(it) } ?: na
        binding.tvLakeDischarge.text = d.lakeO.eastDischargeCfsTotal?.let { "%.0f cfs".format(it) } ?: na
        binding.tvLakeError.apply {
            text       = d.lakeO.error ?: ""
            visibility = if (d.lakeO.error != null) View.VISIBLE else View.GONE
        }

        // ── Plume ─────────────────────────────────────────────────────────────
        binding.tvPlumeSource.text     = d.plume.source ?: na
        binding.tvPlumeConf.text       = d.plume.confidence?.let { "%.0f%%".format(it * 100) } ?: na
        binding.tvPlumeResolution.text = d.plume.resolution?.replaceFirstChar { it.uppercase() } ?: na

        // ── Snorkel Index ─────────────────────────────────────────────────────
        binding.tvSnorkelScore.text  = "${d.snorkelIndex.score}/100"
        binding.tvSnorkelLabel.text  = d.snorkelIndex.label
        binding.tvSnorkelReasons.text = if (d.snorkelIndex.reasons.isEmpty()) na
            else d.snorkelIndex.reasons.joinToString("\n") { "• $it" }

        // ── Nearshore quality ─────────────────────────────────────────────────
        binding.tvNearshoreQuality.text =
            d.nearshoreQuality?.replaceFirstChar { it.uppercase() } ?: na
    }

    private fun showLoading() {
        val loading = getString(R.string.loading)
        listOf(
            binding.tvCurrentSpeed, binding.tvCurrentDir, binding.tvClarityScore,
            binding.tvC16Flow, binding.tvLakeStage, binding.tvPlumeSource,
            binding.tvSnorkelScore
        ).forEach { it.text = loading }
    }

    private fun showError(msg: String) {
        binding.tvCurrentSpeed.text = getString(R.string.error_fetch)
        binding.tvCurrentDir.text   = msg
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

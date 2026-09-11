package com.pbcplume.tracker.ui.debug

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.pbcplume.tracker.databinding.FragmentDebugBinding
import com.pbcplume.tracker.ui.ConditionsUiState
import com.pbcplume.tracker.ui.ConditionsViewModel
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.launch

/** Raw JSON viewer — shown via long-press on the snorkel badge in debug builds. */
class DebugFragment : Fragment() {

    private var _binding: FragmentDebugBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ConditionsViewModel by activityViewModels()

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentDebugBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        viewLifecycleOwner.lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.tvRawJson.text = when (state) {
                        is ConditionsUiState.Loading -> "Loading..."
                        is ConditionsUiState.Error   -> "Error: ${state.message}"
                        is ConditionsUiState.Success -> {
                            val adapter = moshi.adapter(state.data.javaClass).indent("  ")
                            runCatching { adapter.toJson(state.data) }
                                .getOrElse { "Serialisation error: ${it.message}" }
                        }
                    }
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

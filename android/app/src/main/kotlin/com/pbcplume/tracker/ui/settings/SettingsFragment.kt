package com.pbcplume.tracker.ui.settings

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import com.pbcplume.tracker.databinding.FragmentSettingsBinding
import com.pbcplume.tracker.ui.ConditionsViewModel

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ConditionsViewModel by activityViewModels()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Populate current backend URL
        binding.etBackendUrl.setText(viewModel.currentBackendUrl())

        binding.btnSave.setOnClickListener {
            val url = binding.etBackendUrl.text.toString().trim()
            if (url.isBlank()) {
                binding.etBackendUrl.error = "URL cannot be empty"
                return@setOnClickListener
            }
            viewModel.updateBackendUrl(url)
            Toast.makeText(requireContext(), "Settings saved", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

package com.pbcplume.tracker.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pbcplume.tracker.data.api.NetworkModule
import com.pbcplume.tracker.data.repository.AssetSnorkelDataSource
import com.pbcplume.tracker.data.repository.NetworkSnorkelDataSource
import com.pbcplume.tracker.data.repository.SnorkelConditionsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import timber.log.Timber

class SnorkelViewModel(app: Application) : AndroidViewModel(app) {

    private val prefs = app.getSharedPreferences(ConditionsViewModel.PREF_FILE, 0)

    private val _uiState = MutableStateFlow<SnorkelUiState>(SnorkelUiState.Loading)
    val uiState: StateFlow<SnorkelUiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init {
        load()
    }

    fun load() {
        fetch(mode = null)
    }

    fun refresh() {
        fetch(mode = "live")
    }

    private fun fetch(mode: String?) {
        if (_isRefreshing.value) return
        viewModelScope.launch {
            _isRefreshing.value = true
            val demoMode = prefs.getBoolean(ConditionsViewModel.PREF_DEMO_MODE, ConditionsViewModel.DEFAULT_DEMO_MODE)
            val repo = if (demoMode) {
                SnorkelConditionsRepository(AssetSnorkelDataSource(getApplication()))
            } else {
                val url = prefs.getString(ConditionsViewModel.PREF_URL, ConditionsViewModel.DEFAULT_URL)
                    ?: ConditionsViewModel.DEFAULT_URL
                SnorkelConditionsRepository(NetworkSnorkelDataSource(NetworkModule.buildSnorkelApiService(url)))
            }
            var attempts = 0
            do {
                val result = repo.fetch(mode, refresh = mode == "live" && attempts == 0)
                _uiState.value = result.fold(
                    onSuccess = { SnorkelUiState.Success(it) },
                    onFailure = {
                        Timber.e(it, "Snorkel fetch failed")
                        SnorkelUiState.Error(it.message ?: "Unknown error")
                    }
                )
                val running = result.getOrNull()?.refreshStatus == "running"
                attempts++
                if (mode == "live" && running && attempts < 180) delay(5_000)
            } while (mode == "live" && running && attempts < 180)
            _isRefreshing.value = false
        }
    }
}

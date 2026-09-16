package com.pbcplume.tracker.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pbcplume.tracker.data.api.NetworkModule
import com.pbcplume.tracker.data.repository.SnorkelConditionsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
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
        viewModelScope.launch {
            _isRefreshing.value = true
            val url = prefs.getString(ConditionsViewModel.PREF_URL, ConditionsViewModel.DEFAULT_URL)
                ?: ConditionsViewModel.DEFAULT_URL
            val repo = SnorkelConditionsRepository(NetworkModule.buildSnorkelApiService(url))
            _uiState.value = repo.fetch(mode).fold(
                onSuccess = { SnorkelUiState.Success(it) },
                onFailure = {
                    Timber.e(it, "Snorkel fetch failed")
                    SnorkelUiState.Error(it.message ?: "Unknown error")
                }
            )
            _isRefreshing.value = false
        }
    }
}

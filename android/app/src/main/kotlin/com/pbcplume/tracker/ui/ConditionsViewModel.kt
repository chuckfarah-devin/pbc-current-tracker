package com.pbcplume.tracker.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.pbcplume.tracker.data.api.NetworkModule
import com.pbcplume.tracker.data.repository.ConditionsRepository
import com.pbcplume.tracker.work.ConditionsRefreshWorker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import timber.log.Timber
import java.util.concurrent.TimeUnit

class ConditionsViewModel(app: Application) : AndroidViewModel(app) {

    companion object {
        const val DEFAULT_URL = "http://10.0.2.2:8000"
        const val PREF_FILE   = "pbc_settings"
        const val PREF_URL    = "backend_url"
        const val PREF_DEMO_MODE = "demo_mode"
        const val PREF_DEMO_MODE_SET = "demo_mode_set"
        const val DEFAULT_DEMO_MODE = true
        const val WORK_TAG    = "conditions_refresh"

        // Boynton Inlet default
        const val DEFAULT_LAT = 26.530
        const val DEFAULT_LON = -80.052
    }

    private val prefs = app.getSharedPreferences(PREF_FILE, 0)

    private val _uiState = MutableStateFlow<ConditionsUiState>(ConditionsUiState.Loading)
    val uiState: StateFlow<ConditionsUiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init {
        refresh()
        scheduleBackgroundRefresh(app)
    }

    /** Manual or automatic refresh. */
    fun refresh(lat: Double = DEFAULT_LAT, lon: Double = DEFAULT_LON) {
        viewModelScope.launch {
            _isRefreshing.value = true
            val url  = prefs.getString(PREF_URL, DEFAULT_URL) ?: DEFAULT_URL
            val repo = ConditionsRepository(NetworkModule.buildApiService(url))
            _uiState.value = repo.fetchConditions(lat, lon).fold(
                onSuccess = { ConditionsUiState.Success(it) },
                onFailure = {
                    Timber.e(it, "refresh() failed")
                    ConditionsUiState.Error(it.message ?: "Unknown error")
                }
            )
            _isRefreshing.value = false
        }
    }

    /** Save settings and re-fetch immediately. */
    fun updateBackendUrl(url: String) {
        prefs.edit().putString(PREF_URL, url).apply()
        refresh()
    }

    fun currentBackendUrl(): String =
        prefs.getString(PREF_URL, DEFAULT_URL) ?: DEFAULT_URL

    /** Returns whether the app should use bundled offline demo data.
     *  On first run: defaults to demo mode.
     *  On upgrade from a version that stored a custom backend URL: preserves live mode. */
    fun isDemoMode(): Boolean {
        if (prefs.contains(PREF_DEMO_MODE_SET)) {
            return prefs.getBoolean(PREF_DEMO_MODE, DEFAULT_DEMO_MODE)
        }
        // Migration path: if the user previously configured a non-default backend URL,
        // stay in live mode so we don't break an existing setup.
        val configuredUrl = prefs.getString(PREF_URL, DEFAULT_URL) ?: DEFAULT_URL
        val defaultToDemo = configuredUrl == DEFAULT_URL
        prefs.edit()
            .putBoolean(PREF_DEMO_MODE, defaultToDemo)
            .putBoolean(PREF_DEMO_MODE_SET, true)
            .apply()
        return defaultToDemo
    }

    fun setDemoMode(enabled: Boolean) {
        prefs.edit()
            .putBoolean(PREF_DEMO_MODE, enabled)
            .putBoolean(PREF_DEMO_MODE_SET, true)
            .apply()
    }

    // ── WorkManager 30-min background refresh ─────────────────────────────────
    private fun scheduleBackgroundRefresh(app: Application) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = PeriodicWorkRequestBuilder<ConditionsRefreshWorker>(
            30, TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .addTag(WORK_TAG)
            .build()
        WorkManager.getInstance(app).enqueueUniquePeriodicWork(
            WORK_TAG,
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }
}

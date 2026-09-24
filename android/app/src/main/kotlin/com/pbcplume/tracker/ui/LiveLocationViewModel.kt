package com.pbcplume.tracker.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pbcplume.tracker.ui.ConditionsViewModel.Companion.DEFAULT_DEMO_MODE
import com.pbcplume.tracker.ui.ConditionsViewModel.Companion.PREF_DEMO_MODE
import com.pbcplume.tracker.ui.ConditionsViewModel.Companion.PREF_FILE
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneOffset

 data class LocationWeatherState(
    val locationId: String,
    val status: String,
    val windMph: Double? = null,
    val windFromDegrees: Double? = null,
    val rain24hInches: Double? = null,
    val observedAt: String? = null,
    val source: String = "Open-Meteo",
)

class LiveLocationViewModel(app: Application) : AndroidViewModel(app) {
    private val client = OkHttpClient()
    private val prefs = app.getSharedPreferences(PREF_FILE, 0)
    private val cache = mutableMapOf<String, LocationWeatherState>()
    private val _weather = MutableStateFlow(LocationWeatherState("delray", "unavailable"))
    val weather = _weather.asStateFlow()

    fun load(location: BeachLocation, force: Boolean = false) {
        if (prefs.getBoolean(PREF_DEMO_MODE, DEFAULT_DEMO_MODE)) {
            _weather.value = LocationWeatherState(location.id, "demo")
            return
        }
        if (!force) cache[location.id]?.let { _weather.value = it; return }
        _weather.value = LocationWeatherState(location.id, "checking")
        viewModelScope.launch {
            val result = runCatching { fetch(location) }
            _weather.value = result.getOrElse { cache[location.id]?.copy(status = "cached") ?: LocationWeatherState(location.id, "unavailable") }
            result.getOrNull()?.let { cache[location.id] = it }
        }
    }

    private suspend fun fetch(location: BeachLocation) = withContext(Dispatchers.IO) {
        val url = "https://api.open-meteo.com/v1/forecast?latitude=${location.lat}&longitude=${location.lon}&current=wind_speed_10m,wind_direction_10m&hourly=precipitation&past_days=1&forecast_days=1&wind_speed_unit=mph&precipitation_unit=inch&timezone=UTC"
        val response = client.newCall(Request.Builder().url(url).build()).execute()
        if (!response.isSuccessful) error("Weather HTTP ${response.code}")
        val json = JSONObject(response.body?.string() ?: error("Empty weather response"))
        val current = json.getJSONObject("current")
        val hourly = json.getJSONObject("hourly")
        val times = hourly.getJSONArray("time")
        val precipitation = hourly.getJSONArray("precipitation")
        val cutoff = Instant.now().minusSeconds(24 * 60 * 60)
        var rain = 0.0
        for (index in 0 until times.length()) {
            val instant = OffsetDateTime.parse(times.getString(index) + ":00Z").toInstant()
            if (!instant.isBefore(cutoff) && !instant.isAfter(Instant.now())) rain += precipitation.optDouble(index, 0.0)
        }
        LocationWeatherState(
            location.id,
            "current",
            current.optDouble("wind_speed_10m").takeUnless(Double::isNaN),
            current.optDouble("wind_direction_10m").takeUnless(Double::isNaN),
            rain,
            current.optString("time").takeIf(String::isNotBlank)?.let { "$it ${ZoneOffset.UTC.id}" },
        )
    }
}

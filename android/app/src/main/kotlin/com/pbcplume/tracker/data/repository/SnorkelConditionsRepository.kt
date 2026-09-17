package com.pbcplume.tracker.data.repository

import com.pbcplume.tracker.data.api.SnorkelApiService
import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import timber.log.Timber

class SnorkelConditionsRepository(private val api: SnorkelApiService) {

    suspend fun fetch(mode: String? = null, refresh: Boolean = false): Result<SnorkelConditionsResponse> = try {
        val response = api.getSnorkelConditions(mode, refresh)
        Timber.d("Snorkel conditions fetched: mode=${response.mode}")
        Result.success(response)
    } catch (e: Exception) {
        Timber.e(e, "fetchSnorkelConditions failed")
        Result.failure(e)
    }
}

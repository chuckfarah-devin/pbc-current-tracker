package com.pbcplume.tracker.data.repository

import com.pbcplume.tracker.data.api.PlumeApiService
import com.pbcplume.tracker.data.model.ConditionsResponse
import timber.log.Timber

class ConditionsRepository(private val api: PlumeApiService) {

    /** Fetch conditions. Always returns a Result — never throws. */
    suspend fun fetchConditions(lat: Double, lon: Double): Result<ConditionsResponse> = try {
        val response = api.getConditions(lat, lon)
        Timber.d("Conditions fetched: score=${response.snorkelIndex.score}")
        Result.success(response)
    } catch (e: Exception) {
        Timber.e(e, "fetchConditions failed")
        Result.failure(e)
    }
}

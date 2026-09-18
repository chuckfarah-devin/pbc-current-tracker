package com.pbcplume.tracker.data.repository

import com.pbcplume.tracker.data.api.SnorkelApiService
import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import timber.log.Timber

class NetworkSnorkelDataSource(private val api: SnorkelApiService) : SnorkelDataSource {

    override suspend fun fetch(mode: String?, refresh: Boolean): Result<SnorkelConditionsResponse> = try {
        val response = api.getSnorkelConditions(mode, refresh)
        Timber.d("Network snorkel conditions fetched: mode=${response.mode}")
        Result.success(response)
    } catch (e: Exception) {
        Timber.e(e, "NetworkSnorkelDataSource fetch failed")
        Result.failure(e)
    }
}

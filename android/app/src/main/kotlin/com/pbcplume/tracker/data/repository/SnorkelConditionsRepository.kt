package com.pbcplume.tracker.data.repository

import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import timber.log.Timber

class SnorkelConditionsRepository(private val dataSource: SnorkelDataSource) {

    suspend fun fetch(mode: String? = null, refresh: Boolean = false): Result<SnorkelConditionsResponse> =
        dataSource.fetch(mode, refresh).also {
            it.fold(
                onSuccess = { data -> Timber.d("Snorkel conditions loaded: mode=${data.mode}") },
                onFailure = { e -> Timber.e(e, "SnorkelConditionsRepository fetch failed") }
            )
        }
}

package com.pbcplume.tracker.data.repository

import com.pbcplume.tracker.data.model.SnorkelConditionsResponse

interface SnorkelDataSource {
    suspend fun fetch(mode: String? = null, refresh: Boolean = false): Result<SnorkelConditionsResponse>
}

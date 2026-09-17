package com.pbcplume.tracker.data.api

import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import retrofit2.http.GET
import retrofit2.http.Query

interface SnorkelApiService {

    @GET("api/snorkel-conditions")
    suspend fun getSnorkelConditions(
        @Query("mode") mode: String? = null,
        @Query("refresh") refresh: Boolean = false
    ): SnorkelConditionsResponse
}

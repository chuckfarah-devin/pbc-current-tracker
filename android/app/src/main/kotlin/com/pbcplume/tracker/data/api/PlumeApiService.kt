package com.pbcplume.tracker.data.api

import com.pbcplume.tracker.data.model.ConditionsResponse
import com.pbcplume.tracker.data.model.StatusResponse
import retrofit2.http.GET
import retrofit2.http.Query

interface PlumeApiService {

    @GET("api/conditions")
    suspend fun getConditions(
        @Query("lat") lat: Double = 26.530,
        @Query("lon") lon: Double = -80.052
    ): ConditionsResponse

    @GET("api/status")
    suspend fun getStatus(): StatusResponse
}

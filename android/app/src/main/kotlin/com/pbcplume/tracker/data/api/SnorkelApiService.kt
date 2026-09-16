package com.pbcplume.tracker.data.api

import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import retrofit2.http.GET

interface SnorkelApiService {

    @GET("api/snorkel-conditions")
    suspend fun getSnorkelConditions(): SnorkelConditionsResponse
}

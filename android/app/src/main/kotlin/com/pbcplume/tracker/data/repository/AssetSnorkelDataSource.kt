package com.pbcplume.tracker.data.repository

import android.content.Context
import com.pbcplume.tracker.data.model.SnorkelConditionsResponse
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import timber.log.Timber

class AssetSnorkelDataSource(private val context: Context) : SnorkelDataSource {

    private val moshi: Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    override suspend fun fetch(mode: String?, refresh: Boolean): Result<SnorkelConditionsResponse> =
        withContext(Dispatchers.IO) {
            try {
                // Simulate a brief refresh so the UI still shows feedback when the user
                // pulls to refresh in offline demo mode.
                if (refresh) {
                    delay(500)
                }
                context.assets.open("demo/recorded_replay.json").use { stream ->
                    val json = stream.bufferedReader().use { it.readText() }
                    val adapter = moshi.adapter(SnorkelConditionsResponse::class.java)
                    val response = adapter.fromJson(json)
                        ?: throw IllegalStateException("Empty demo response")
                    Timber.d("Asset snorkel conditions loaded: mode=${response.mode}")
                    Result.success(response)
                }
            } catch (e: Exception) {
                Timber.e(e, "AssetSnorkelDataSource load failed")
                Result.failure(e)
            }
        }
}

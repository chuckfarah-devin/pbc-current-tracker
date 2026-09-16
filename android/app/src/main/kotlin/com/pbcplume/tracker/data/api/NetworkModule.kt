package com.pbcplume.tracker.data.api

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import timber.log.Timber
import java.util.concurrent.TimeUnit

object NetworkModule {

    private fun buildRetrofit(baseUrl: String): Retrofit {
        val normalised = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

        val logging = HttpLoggingInterceptor { msg -> Timber.tag("OkHttp").d(msg) }.apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        val moshi = Moshi.Builder()
            .addLast(KotlinJsonAdapterFactory())
            .build()

        return Retrofit.Builder()
            .baseUrl(normalised)
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
    }

    fun buildApiService(baseUrl: String): PlumeApiService =
        buildRetrofit(baseUrl).create(PlumeApiService::class.java)

    fun buildSnorkelApiService(baseUrl: String): SnorkelApiService =
        buildRetrofit(baseUrl).create(SnorkelApiService::class.java)
}

package com.pbcplume.tracker

import android.app.Application
import com.mapbox.maps.MapboxOptions
import timber.log.Timber

class PlumeApplication : Application() {

    override fun onCreate() {
        super.onCreate()

        // Set Mapbox access token (injected at build time from local.properties)
        MapboxOptions.accessToken = BuildConfig.MAPBOX_ACCESS_TOKEN

        // Timber logging — debug builds only
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
    }
}

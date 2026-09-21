package com.pbcplume.tracker.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.pbcplume.tracker.data.api.NetworkModule
import com.pbcplume.tracker.data.repository.ConditionsRepository
import com.pbcplume.tracker.ui.ConditionsViewModel
import timber.log.Timber

/**
 * WorkManager worker — refreshes conditions every 30 min in background.
 * On success, results are picked up by the ViewModel the next time
 * the user opens the app (no in-process state update from a background process).
 */
class ConditionsRefreshWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val prefs = applicationContext.getSharedPreferences(ConditionsViewModel.PREF_FILE, 0)
        val demoMode = prefs.getBoolean(ConditionsViewModel.PREF_DEMO_MODE, ConditionsViewModel.DEFAULT_DEMO_MODE)
        if (demoMode) {
            Timber.d("Background refresh skipped: demo mode is enabled")
            return Result.success()
        }
        val url   = prefs.getString(ConditionsViewModel.PREF_URL, ConditionsViewModel.DEFAULT_URL)
            ?: ConditionsViewModel.DEFAULT_URL

        return try {
            val repo = ConditionsRepository(NetworkModule.buildApiService(url))
            repo.fetchConditions(
                ConditionsViewModel.DEFAULT_LAT,
                ConditionsViewModel.DEFAULT_LON
            ).fold(
                onSuccess = {
                    Timber.d("Background refresh OK: score=${it.snorkelIndex.score}")
                    Result.success()
                },
                onFailure = {
                    Timber.w(it, "Background refresh failed")
                    Result.retry()
                }
            )
        } catch (e: Exception) {
            Timber.e(e, "ConditionsRefreshWorker exception")
            Result.retry()
        }
    }
}

package com.pbcplume.tracker.util

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
import kotlin.math.roundToInt

object SnorkelFormat {

    private val localTimeFormatter = DateTimeFormatter
        .ofPattern("MMM d, h:mm a z", Locale.US)
        .withZone(ZoneId.of("America/New_York"))

    fun time(iso: String?): String? {
        if (iso.isNullOrBlank()) return null
        return try {
            localTimeFormatter.format(Instant.parse(iso))
        } catch (_: Exception) {
            null
        }
    }

    fun ageLabel(ageMinutes: Double?): String? {
        if (ageMinutes == null) return null
        return when {
            ageMinutes < 1.0 -> "just now"
            ageMinutes < 60.0 -> "%.0f min old".format(ageMinutes)
            ageMinutes < 24 * 60.0 -> {
                val h = (ageMinutes / 60.0).roundToInt()
                "$h hour${if (h == 1) "" else "s"} old"
            }
            else -> {
                val d = (ageMinutes / (24 * 60.0)).roundToInt()
                "$d day${if (d == 1) "" else "s"} old"
            }
        }
    }

    fun cameraTime(observed: String?, age: Double?, provider: String?, retrieved: String?): String {
        val ageText = ageLabel(age)?.let { " · $it" } ?: ""
        return when {
            observed != null -> "Observed $observed$ageText"
            provider != null -> "Capture shown: $provider · capture time unverified"
            retrieved != null -> "Retrieved $retrieved · capture time unverified"
            else -> "Time unavailable"
        }
    }

    fun periodAge(periodEnd: String?): String? {
        if (periodEnd.isNullOrBlank()) return null
        return try {
            val end = LocalDate.parse(periodEnd)
            val today = LocalDate.now(ZoneId.of("America/New_York"))
            val days = ChronoUnit.DAYS.between(end, today)
            when {
                days < 0 -> "period ends in the future"
                days == 0L -> "ended today"
                days == 1L -> "ended 1 day ago"
                else -> "ended $days days ago"
            }
        } catch (_: Exception) {
            null
        }
    }

    fun colorLabel(s: com.pbcplume.tracker.data.model.WaterColourSample): String {
        return when {
            s.blueGreenPercent >= 45.0 -> "blue-green"
            s.warmPercent >= 45.0 -> "brown/olive"
            s.otherPercent >= 45.0 -> "mixed"
            s.blueGreenPercent >= s.warmPercent && s.blueGreenPercent >= s.otherPercent -> "mostly blue-green"
            s.warmPercent >= s.otherPercent -> "mostly brown/olive"
            else -> "mixed"
        }
    }

    fun statusLabel(status: String?): String = when (status) {
        "stream_advancing_capture_unverified" -> "Stream active, capture time unverified"
        "fresh_image_review_needed" -> "Fresh image, needs framing review"
        "stream_not_advancing_in_short_check" -> "Stream not advancing in short check"
        "framing_unverified" -> "Framing not verified · no colour claim"
        "OFFSHORE ALGAE SIGNAL PRESENT", "Offshore algae signal present" -> "Image colors consistent with sargassum"
        "NO COLORED SIGNAL IDENTIFIED", "No colored signal identified" -> "No sargassum image colors identified"
        "INSUFFICIENT IMAGE DATA", "Insufficient image data" -> "Insufficient image data"
        "stale" -> "Earlier view"
        "unavailable" -> "Source unavailable"
        "unknown" -> "Unverified time"
        "fresh" -> "Recent view"
        "maintenance_notice" -> "Maintenance notice"
        "uncertain" -> "Uncertain"
        "cached" -> "Cached result"
        "recorded; manual review needed" -> "Recorded; manual framing review needed"
        "experimental; developer-only" -> "Experimental"
        null, "" -> "Unknown"
        else -> status.replace("_", " ").replaceFirstChar { it.uppercase() }
    }
}

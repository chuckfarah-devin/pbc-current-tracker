package com.pbcplume.tracker.util

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

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

    fun statusLabel(status: String?): String = when (status) {
        "stream_advancing_capture_unverified" -> "Stream active, capture time unverified"
        "fresh_image_review_needed" -> "Fresh image, needs framing review"
        "stale" -> "Earlier view"
        "unavailable" -> "Source unavailable"
        "unknown" -> "Unverified time"
        "fresh" -> "Recent view"
        "recorded; manual review needed" -> "Recorded; manual framing review needed"
        "experimental; developer-only" -> "Experimental"
        null, "" -> "Unknown"
        else -> status.replace("_", " ").replaceFirstChar { it.uppercase() }
    }
}

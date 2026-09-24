package com.pbcplume.tracker.ui.map

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot

class MapPreviewView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    data class Marker(val id: String, val label: String, val lat: Double, val lon: Double)

    var markers: List<Marker> = emptyList()
        set(value) { field = value; invalidate() }
    var selectedId: String? = null
        set(value) { field = value; invalidate() }
    var onMarkerSelected: ((String) -> Unit)? = null

    private val ocean = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(39, 145, 172) }
    private val shallow = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(79, 186, 183) }
    private val land = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(226, 239, 226) }
    private val road = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(110, 255, 255, 255); strokeWidth = 3f }
    private val marker = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(0, 96, 100) }
    private val selected = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(255, 255, 255); style = Paint.Style.STROKE; strokeWidth = 7f }
    private val label = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(11, 32, 43); textSize = 24f; isFakeBoldText = true }
    private val waterLabel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(205, 255, 255, 255); textSize = 30f }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), ocean)
        val coastX = width * .43f
        val coast = Path().apply {
            moveTo(coastX, 0f)
            cubicTo(width * .48f, height * .23f, width * .39f, height * .52f, width * .46f, height.toFloat())
            lineTo(0f, height.toFloat())
            lineTo(0f, 0f)
            close()
        }
        canvas.drawPath(coast, shallow)
        val inland = Path().apply {
            moveTo(coastX - 28f, 0f)
            cubicTo(width * .43f, height * .23f, width * .34f, height * .52f, width * .41f, height.toFloat())
            lineTo(0f, height.toFloat())
            lineTo(0f, 0f)
            close()
        }
        canvas.drawPath(inland, land)
        canvas.drawLine(width * .25f, 0f, width * .25f, height.toFloat(), road)
        canvas.drawLine(width * .34f, 0f, width * .34f, height.toFloat(), road)
        canvas.drawText("Atlantic Ocean", width * .58f, height * .52f, waterLabel)
        markers.forEach { item ->
            val (x, y) = point(item)
            canvas.drawCircle(x, y, if (item.id == selectedId) 21f else 16f, marker)
            if (item.id == selectedId) canvas.drawCircle(x, y, 27f, selected)
            canvas.drawText(item.label, x + 31f, y + 8f, label)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.action != MotionEvent.ACTION_UP) return true
        val closest = markers.minByOrNull { val p = point(it); hypot(event.x - p.first, event.y - p.second) }
        if (closest != null) {
            val p = point(closest)
            if (hypot(event.x - p.first, event.y - p.second) < 70f) onMarkerSelected?.invoke(closest.id)
        }
        return true
    }

    private fun point(marker: Marker): Pair<Float, Float> {
        val minLat = 26.08
        val maxLat = 26.98
        val x = width * (.41 + ((marker.lon + 80.11) / .09) * .09).toFloat()
        val y = height * (1.0 - (marker.lat - minLat) / (maxLat - minLat)).toFloat()
        return x.coerceIn(width * .34f, width * .52f) to y.coerceIn(40f, height - 40f)
    }
}

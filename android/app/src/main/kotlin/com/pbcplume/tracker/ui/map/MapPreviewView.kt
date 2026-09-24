package com.pbcplume.tracker.ui.map

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import kotlin.math.hypot

class MapPreviewView @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : View(context, attrs) {
    data class Marker(val id: String, val label: String, val municipality: String, val lat: Double, val lon: Double)

    var markers: List<Marker> = emptyList()
        set(value) { field = value; invalidate() }
    var selectedId: String? = null
        set(value) { field = value; invalidate() }
    var onMarkerSelected: ((String) -> Unit)? = null

    private var scale = 1f
    private var offsetX = 0f
    private var offsetY = 0f
    private var lastX = 0f
    private var lastY = 0f
    private var dragging = false
    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            scale = (scale * detector.scaleFactor).coerceIn(1f, 3.2f)
            invalidate()
            return true
        }
    })

    private val ocean = paint(Color.rgb(35, 139, 168))
    private val shelf = paint(Color.rgb(79, 183, 181))
    private val land = paint(Color.rgb(225, 238, 223))
    private val park = paint(Color.rgb(188, 220, 190))
    private val waterway = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(78, 170, 181); strokeWidth = 9f; style = Paint.Style.STROKE }
    private val majorRoad = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; strokeWidth = 5f; style = Paint.Style.STROKE }
    private val minorRoad = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(165, 255, 255, 255); strokeWidth = 2f; style = Paint.Style.STROKE }
    private val cityPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(52, 91, 98); textSize = 21f; isFakeBoldText = true }
    private val oceanLabel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(210, 255, 255, 255); textSize = 27f }
    private val pin = paint(Color.rgb(0, 96, 100))
    private val selectedPin = paint(Color.rgb(255, 184, 0))
    private val pinStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; strokeWidth = 5f; style = Paint.Style.STROKE }
    private val pinCamera = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; strokeWidth = 3f; style = Paint.Style.STROKE }
    private val markerLabel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(11, 48, 64); textSize = 22f; isFakeBoldText = true }

    override fun onDraw(canvas: Canvas) {
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), ocean)
        canvas.save()
        canvas.translate(offsetX, offsetY)
        canvas.scale(scale, scale, width * .45f, height * .45f)
        drawGeography(canvas)
        markers.forEach { drawMarker(canvas, it) }
        canvas.restore()
    }

    private fun drawGeography(canvas: Canvas) {
        val coast = Path().apply {
            moveTo(width * .58f, -100f)
            cubicTo(width * .55f, height * .18f, width * .60f, height * .38f, width * .53f, height * .58f)
            cubicTo(width * .49f, height * .72f, width * .57f, height * .88f, width * .50f, height + 100f)
            lineTo(-100f, height + 100f); lineTo(-100f, -100f); close()
        }
        canvas.drawPath(coast, shelf)
        val landPath = Path().apply {
            moveTo(width * .54f, -100f)
            cubicTo(width * .51f, height * .18f, width * .56f, height * .38f, width * .49f, height * .58f)
            cubicTo(width * .45f, height * .72f, width * .53f, height * .88f, width * .46f, height + 100f)
            lineTo(-100f, height + 100f); lineTo(-100f, -100f); close()
        }
        canvas.drawPath(landPath, land)
        canvas.drawRect(width * .37f, height * .03f, width * .47f, height * .10f, park)
        canvas.drawRect(width * .38f, height * .49f, width * .49f, height * .56f, park)
        canvas.drawRect(width * .35f, height * .70f, width * .47f, height * .76f, park)

        val intracoastal = Path().apply { moveTo(width * .41f, -50f); cubicTo(width * .44f, height * .27f, width * .40f, height * .65f, width * .42f, height + 50f) }
        canvas.drawPath(intracoastal, waterway)
        canvas.drawLine(width * .25f, -50f, width * .25f, height + 50f, majorRoad)
        canvas.drawLine(width * .35f, -50f, width * .35f, height + 50f, majorRoad)
        repeat(9) { i -> canvas.drawLine(width * .08f, height * (i + 1) / 10f, width * .49f, height * (i + 1) / 10f, minorRoad) }
        canvas.drawText("I-95", width * .22f, height * .42f, cityPaint)
        canvas.drawText("US 1", width * .31f, height * .60f, cityPaint)
        canvas.drawText("Intracoastal", width * .29f, height * .31f, cityPaint)
        canvas.drawText("Atlantic Ocean", width * .67f, height * .42f, oceanLabel)
        canvas.drawText("Jupiter", width * .08f, height * .08f, cityPaint)
        canvas.drawText("Riviera Beach", width * .07f, height * .25f, cityPaint)
        canvas.drawText("Boynton Beach", width * .06f, height * .49f, cityPaint)
        canvas.drawText("Delray Beach", width * .08f, height * .59f, cityPaint)
        canvas.drawText("Boca Raton", width * .09f, height * .70f, cityPaint)
        canvas.drawText("Pompano Beach", width * .07f, height * .84f, cityPaint)
        canvas.drawText("Fort Lauderdale", width * .06f, height * .94f, cityPaint)
    }

    private fun drawMarker(canvas: Canvas, item: Marker) {
        val (x, y) = rawPoint(item)
        val chosen = item.id == selectedId
        val body = if (chosen) selectedPin else pin
        val path = Path().apply {
            moveTo(x, y + 25f); cubicTo(x - 30f, y - 5f, x - 24f, y - 35f, x, y - 35f)
            cubicTo(x + 24f, y - 35f, x + 30f, y - 5f, x, y + 25f); close()
        }
        canvas.drawPath(path, body)
        if (chosen) canvas.drawPath(path, pinStroke)
        canvas.drawRoundRect(RectF(x - 10f, y - 20f, x + 10f, y - 6f), 3f, 3f, pinCamera)
        canvas.drawCircle(x, y - 13f, 4f, pinCamera)
        canvas.drawText(item.label, x + 29f, y - 5f, markerLabel)
    }

    fun zoomBy(factor: Float) { scale = (scale * factor).coerceIn(1f, 3.2f); invalidate() }
    fun showAll() { scale = 1f; offsetX = 0f; offsetY = 0f; invalidate() }
    fun centerOn(id: String) {
        val target = markers.firstOrNull { it.id == id } ?: return
        val p = rawPoint(target)
        offsetX = width * .52f - p.first
        offsetY = height * .42f - p.second
        invalidate()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { lastX = event.x; lastY = event.y; dragging = false }
            MotionEvent.ACTION_MOVE -> if (!scaleDetector.isInProgress) {
                val dx = event.x - lastX; val dy = event.y - lastY
                if (hypot(dx, dy) > 3f) dragging = true
                offsetX += dx; offsetY += dy; lastX = event.x; lastY = event.y; invalidate()
            }
            MotionEvent.ACTION_UP -> if (!dragging) {
                val closest = markers.minByOrNull { val p = displayPoint(it); hypot(event.x - p.first, event.y - p.second) }
                if (closest != null && displayPoint(closest).let { hypot(event.x - it.first, event.y - it.second) } < 75f) onMarkerSelected?.invoke(closest.id)
            }
        }
        return true
    }

    private fun displayPoint(marker: Marker): Pair<Float, Float> {
        val p = rawPoint(marker)
        val pivotX = width * .45f; val pivotY = height * .45f
        return (pivotX + (p.first - pivotX) * scale + offsetX) to (pivotY + (p.second - pivotY) * scale + offsetY)
    }

    private fun rawPoint(marker: Marker): Pair<Float, Float> {
        val minLat = 26.08; val maxLat = 26.98
        val x = width * (.50 + ((marker.lon + 80.11) / .09) * .08).toFloat()
        val y = height * (1.0 - (marker.lat - minLat) / (maxLat - minLat)).toFloat()
        return x.coerceIn(width * .47f, width * .59f) to y.coerceIn(38f, height - 55f)
    }

    private fun paint(colorValue: Int) = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = colorValue }
}

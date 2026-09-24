package com.pbcplume.tracker.ui.map

import android.animation.ValueAnimator
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
import android.view.animation.DecelerateInterpolator
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.hypot

class MapPreviewView @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : View(context, attrs) {
    data class Marker(val id: String, val label: String, val municipality: String, val lat: Double, val lon: Double)
    private data class Shape(val layer: String, val rings: List<List<Pair<Double, Double>>>)

    var markers: List<Marker> = emptyList()
        set(value) { field = value; invalidate() }
    var selectedId: String? = null
        set(value) { field = value; invalidate() }
    var onMarkerSelected: ((String) -> Unit)? = null

    private val bounds = doubleArrayOf(-80.18, 25.65, -79.96, 27.20)
    private val shapes = loadShapes()
    private var scale = 1f
    private var offsetX = 0f
    private var offsetY = 0f
    private var lastX = 0f
    private var lastY = 0f
    private var dragging = false
    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            scale = (scale * detector.scaleFactor).coerceIn(1f, 3.2f)
            clampOffsets()
            invalidate()
            return true
        }
    })

    private val ocean = paint(Color.rgb(35, 139, 168))
    private val land = paint(Color.rgb(225, 238, 223))
    private val waterway = paint(Color.rgb(65, 165, 181))
    private val pin = paint(Color.rgb(0, 96, 100))
    private val selectedPin = paint(Color.rgb(255, 184, 0))
    private val pinStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; strokeWidth = 4f; style = Paint.Style.STROKE }
    private val pinCamera = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; strokeWidth = 3f; style = Paint.Style.STROKE }
    private val markerLabel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(11, 48, 64); textSize = 21f; isFakeBoldText = true }
    private val attribution = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(51, 94, 105); textSize = 18f }

    override fun onDraw(canvas: Canvas) {
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), ocean)
        canvas.save()
        applyTransform(canvas)
        drawGeography(canvas)
        drawMarkers(canvas)
        canvas.restore()
        canvas.drawText("Florida shoreline + Intracoastal · FWC Open Data", 12f, height - 12f, attribution)
    }

    private fun applyTransform(canvas: Canvas) {
        canvas.translate(offsetX, offsetY)
        canvas.scale(scale, scale, width / 2f, height / 2f)
    }

    private fun drawGeography(canvas: Canvas) {
        shapes.forEach { shape ->
            val path = Path()
            shape.rings.forEach { ring ->
                ring.forEachIndexed { index, point ->
                    val screen = rawPoint(point.first, point.second)
                    if (index == 0) path.moveTo(screen.first, screen.second) else path.lineTo(screen.first, screen.second)
                }
                path.close()
            }
            path.fillType = Path.FillType.EVEN_ODD
            canvas.drawPath(path, if (shape.layer == "intracoastal") waterway else land)
        }
    }

    private fun drawMarkers(canvas: Canvas) {
        val occupied = mutableListOf<RectF>()
        markers.sortedBy { it.id != selectedId }.forEach { item ->
            val (x, y) = rawPoint(item.lon, item.lat)
            val chosen = item.id == selectedId
            val path = Path().apply {
                moveTo(x, y + 22f); cubicTo(x - 27f, y - 4f, x - 22f, y - 32f, x, y - 32f)
                cubicTo(x + 22f, y - 32f, x + 27f, y - 4f, x, y + 22f); close()
            }
            canvas.drawPath(path, if (chosen) selectedPin else pin)
            if (chosen) canvas.drawPath(path, pinStroke)
            canvas.drawRoundRect(RectF(x - 9f, y - 19f, x + 9f, y - 7f), 3f, 3f, pinCamera)
            canvas.drawCircle(x, y - 13f, 3.5f, pinCamera)
            val labelWidth = markerLabel.measureText(item.label)
            val labelBounds = RectF(x + 25f, y - 27f, x + 31f + labelWidth, y + 3f)
            if (chosen || occupied.none { RectF.intersects(it, labelBounds) }) {
                canvas.drawText(item.label, x + 28f, y - 5f, markerLabel)
                occupied += labelBounds
            }
        }
    }

    fun zoomBy(factor: Float) {
        scale = (scale * factor).coerceIn(1f, 3.2f)
        clampOffsets()
        invalidate()
    }

    fun showAll() {
        scale = 1f
        offsetX = 0f
        offsetY = 0f
        invalidate()
    }

    fun centerOn(id: String, usableBottom: Int = height) {
        val target = markers.firstOrNull { it.id == id } ?: return
        scale = scale.coerceAtLeast(1.35f)
        val point = rawPoint(target.lon, target.lat)
        val pivotX = width / 2f
        val pivotY = height / 2f
        val desiredX = width * .55f
        val desiredY = usableBottom.coerceAtLeast((height * .35f).toInt()) * .52f
        val endX = desiredX - (pivotX + (point.first - pivotX) * scale)
        val endY = desiredY - (pivotY + (point.second - pivotY) * scale)
        animateOffsets(endX, endY)
    }

    private fun animateOffsets(targetX: Float, targetY: Float) {
        val startX = offsetX
        val startY = offsetY
        ValueAnimator.ofFloat(0f, 1f).apply {
            duration = 260
            interpolator = DecelerateInterpolator()
            addUpdateListener {
                val fraction = it.animatedFraction
                offsetX = startX + (targetX - startX) * fraction
                offsetY = startY + (targetY - startY) * fraction
                clampOffsets()
                invalidate()
            }
            start()
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { lastX = event.x; lastY = event.y; dragging = false }
            MotionEvent.ACTION_MOVE -> if (!scaleDetector.isInProgress) {
                val dx = event.x - lastX
                val dy = event.y - lastY
                if (hypot(dx, dy) > 3f) dragging = true
                offsetX += dx
                offsetY += dy
                clampOffsets()
                lastX = event.x
                lastY = event.y
                invalidate()
            }
            MotionEvent.ACTION_UP -> if (!dragging) {
                val closest = markers.minByOrNull { displayPoint(it).let { point -> hypot(event.x - point.first, event.y - point.second) } }
                if (closest != null && displayPoint(closest).let { hypot(event.x - it.first, event.y - it.second) } < 75f) onMarkerSelected?.invoke(closest.id)
            }
        }
        return true
    }

    private fun clampOffsets() {
        val maxX = width * (scale - 1f) / 2f
        val maxY = height * (scale - 1f) / 2f
        offsetX = offsetX.coerceIn(-maxX, maxX)
        offsetY = offsetY.coerceIn(-maxY, maxY)
    }

    private fun displayPoint(marker: Marker): Pair<Float, Float> {
        val point = rawPoint(marker.lon, marker.lat)
        return width / 2f + (point.first - width / 2f) * scale + offsetX to height / 2f + (point.second - height / 2f) * scale + offsetY
    }

    private fun rawPoint(lon: Double, lat: Double): Pair<Float, Float> {
        val x = ((lon - bounds[0]) / (bounds[2] - bounds[0]) * width).toFloat()
        val y = ((bounds[3] - lat) / (bounds[3] - bounds[1]) * height).toFloat()
        return x to y
    }

    private fun loadShapes(): List<Shape> = runCatching {
        val text = context.assets.open("map/southeast_florida.geojson").bufferedReader().use { it.readText() }
        val features = JSONObject(text).getJSONArray("features")
        buildList {
            for (index in 0 until features.length()) {
                val feature = features.getJSONObject(index)
                val layer = feature.getJSONObject("properties").getString("layer")
                val geometry = feature.getJSONObject("geometry")
                when (geometry.getString("type")) {
                    "Polygon" -> add(Shape(layer, rings(geometry.getJSONArray("coordinates"))))
                    "MultiPolygon" -> geometry.getJSONArray("coordinates").forEachArray { add(Shape(layer, rings(it))) }
                    "LineString" -> add(Shape(layer, listOf(points(geometry.getJSONArray("coordinates")))))
                    "MultiLineString" -> geometry.getJSONArray("coordinates").forEachArray { add(Shape(layer, listOf(points(it)))) }
                }
            }
        }
    }.getOrDefault(emptyList())

    private fun rings(array: JSONArray) = buildList { array.forEachArray { add(points(it)) } }
    private fun points(array: JSONArray) = buildList {
        array.forEachArray { add(it.getDouble(0) to it.getDouble(1)) }
    }
    private inline fun JSONArray.forEachArray(block: (JSONArray) -> Unit) {
        for (index in 0 until length()) block(getJSONArray(index))
    }
    private fun paint(colorValue: Int) = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = colorValue }
}

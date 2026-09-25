package com.pbcplume.tracker.ui.sargassum

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.drawable.Drawable
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import androidx.appcompat.widget.AppCompatImageView

class ZoomImageView @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null) : AppCompatImageView(context, attrs) {
    private val transform = Matrix()
    private var lastX = 0f
    private var lastY = 0f
    private var scale = 1f
    private var markerLon: Double? = null
    private var markerLat: Double? = null
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(255, 184, 0); style = Paint.Style.FILL }
    private val markerStroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; strokeWidth = 4f; style = Paint.Style.STROKE }
    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            val next = (scale * detector.scaleFactor).coerceIn(.5f, 40f)
            transform.postScale(next / scale, next / scale, detector.focusX, detector.focusY)
            scale = next
            imageMatrix = transform
            return true
        }
    })

    init { scaleType = ScaleType.MATRIX }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { lastX = event.x; lastY = event.y }
            MotionEvent.ACTION_MOVE -> if (!scaleDetector.isInProgress) {
                transform.postTranslate(event.x - lastX, event.y - lastY)
                lastX = event.x
                lastY = event.y
                imageMatrix = transform
            }
        }
        return true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val drawable = drawable ?: return
        val lon = markerLon ?: return
        val lat = markerLat ?: return
        val point = floatArrayOf(
            ((lon + 98.0) / 19.0 * drawable.intrinsicWidth).toFloat(),
            ((31.0 - lat) / 13.0 * drawable.intrinsicHeight).toFloat(),
        )
        transform.mapPoints(point)
        canvas.drawCircle(point[0], point[1], 12f, markerPaint)
        canvas.drawCircle(point[0], point[1], 12f, markerStroke)
    }

    fun setMarker(lon: Double, lat: Double) {
        markerLon = lon
        markerLat = lat
        invalidate()
    }

    fun showFullChart() = post {
        val drawable = drawable ?: return@post
        val fit = minOf(width.toFloat() / drawable.intrinsicWidth, height.toFloat() / drawable.intrinsicHeight)
        scale = fit
        transform.reset()
        transform.postScale(fit, fit)
        transform.postTranslate((width - drawable.intrinsicWidth * fit) / 2f, (height - drawable.intrinsicHeight * fit) / 2f)
        imageMatrix = transform
    }

    fun showRegionalView() = post {
        val drawable: Drawable = drawable ?: return@post
        val left = drawable.intrinsicWidth * ((-81.9 + 98.0) / 19.0).toFloat()
        val top = drawable.intrinsicHeight * ((31.0 - 27.2) / 13.0).toFloat()
        val right = drawable.intrinsicWidth * ((-79.4 + 98.0) / 19.0).toFloat()
        val bottom = drawable.intrinsicHeight * ((31.0 - 24.3) / 13.0).toFloat()
        val fit = minOf(width / (right - left), height / (bottom - top))
        scale = fit
        transform.reset()
        transform.postScale(fit, fit)
        transform.postTranslate((width - (right - left) * fit) / 2f - left * fit, (height - (bottom - top) * fit) / 2f - top * fit)
        imageMatrix = transform
    }
}

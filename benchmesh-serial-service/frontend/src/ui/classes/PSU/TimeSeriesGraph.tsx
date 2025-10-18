import React, { useEffect, useRef, useState } from 'react'

interface DataPoint {
  timestamp: number
  value: number
}

interface TimeSeriesGraphProps {
  channelPath?: string
  getValue: () => number | null  // Function to get current value from parent
  label?: string                  // Label for the graph (e.g., "Voltage", "Current")
  unit?: string                   // Unit for the graph (e.g., "V", "A")
  color?: string                  // Line color (default: '#ff4444')
}

export function TimeSeriesGraph({
  channelPath,
  getValue,
  label = 'Value',
  unit = '',
  color = '#ff4444'
}: TimeSeriesGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<DataPoint[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const intervalRef = useRef<number | null>(null)

  // Hardcoded time base: 0.5 seconds (500ms)
  const TIME_BASE_MS = 500
  const MAX_DATA_POINTS = 100

  // Data collection - runs every 0.5 seconds when expanded
  useEffect(() => {
    if (!isExpanded) {
      // Clear interval when collapsed
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // Collect first data point immediately
    const collectDataPoint = () => {
      const value = getValue()
      if (value !== null && !isNaN(value)) {
        setData(prevData => {
          const newPoint: DataPoint = {
            timestamp: Date.now(),
            value: value
          }
          const newData = [...prevData, newPoint]
          // Keep only last MAX_DATA_POINTS
          if (newData.length > MAX_DATA_POINTS) {
            return newData.slice(newData.length - MAX_DATA_POINTS)
          }
          return newData
        })
      }
    }

    // Collect first point immediately
    collectDataPoint()

    // Start collecting data every TIME_BASE_MS
    intervalRef.current = window.setInterval(collectDataPoint, TIME_BASE_MS)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [isExpanded, getValue])

  // Reset button handler - wipes all data and starts fresh
  const handleReset = () => {
    setData([])
  }

  // Draw the graph
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = { top: 30, right: 60, bottom: 30, left: 60 }
    const graphWidth = width - padding.left - padding.right
    const graphHeight = height - padding.top - padding.bottom

    // Clear canvas
    ctx.fillStyle = '#1a1a1a'
    ctx.fillRect(0, 0, width, height)

    if (data.length < 1) {
      // Show "waiting for data" message
      ctx.fillStyle = '#666'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Waiting for data...', width / 2, height / 2)
      return
    }

    // Calculate value range
    const values = data.map(d => d.value)
    const vMin = Math.min(...values)
    const vMax = Math.max(...values)

    // Add 10% padding to range
    const vRange = vMax - vMin || 1
    const vPadded = { min: vMin - vRange * 0.1, max: vMax + vRange * 0.1 }

    // Helper functions
    const scaleX = (index: number) => {
      // Handle single point case
      if (data.length === 1) return padding.left + graphWidth / 2
      return padding.left + (index / (data.length - 1)) * graphWidth
    }
    const scaleY = (value: number) =>
      padding.top + graphHeight - ((value - vPadded.min) / (vPadded.max - vPadded.min)) * graphHeight

    // Draw grid
    ctx.strokeStyle = '#333'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (i / 5) * graphHeight
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(width - padding.right, y)
      ctx.stroke()
    }

    // Draw vertical time grid lines
    for (let i = 0; i <= 10; i++) {
      const x = padding.left + (i / 10) * graphWidth
      ctx.beginPath()
      ctx.moveTo(x, padding.top)
      ctx.lineTo(x, height - padding.bottom)
      ctx.stroke()
    }

    // Draw value line
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.value)
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // Draw axes
    ctx.strokeStyle = '#666'
    ctx.lineWidth = 2
    ctx.beginPath()
    // Left Y-axis
    ctx.moveTo(padding.left, padding.top)
    ctx.lineTo(padding.left, height - padding.bottom)
    // Bottom X-axis
    ctx.lineTo(width - padding.right, height - padding.bottom)
    ctx.stroke()

    // Draw labels
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'right'

    // Y-axis labels
    ctx.fillStyle = color
    ctx.fillText(`${vPadded.max.toFixed(3)}${unit}`, padding.left - 5, padding.top + 5)
    ctx.fillText(`${vPadded.min.toFixed(3)}${unit}`, padding.left - 5, height - padding.bottom + 5)

    // Y-axis title (rotated)
    ctx.textAlign = 'center'
    ctx.save()
    ctx.translate(15, height / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText(`${label} (${unit})`, 0, 0)
    ctx.restore()

    // X-axis label
    ctx.fillStyle = '#aaa'
    ctx.textAlign = 'center'
    const timeSpanSeconds = (data.length * TIME_BASE_MS) / 1000
    ctx.fillText(`Time (${timeSpanSeconds.toFixed(1)}s span, ${TIME_BASE_MS}ms/sample)`, width / 2, height - 5)

    // Title
    ctx.fillStyle = color
    ctx.font = '14px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(`${label} - ${data[data.length - 1].value.toFixed(3)}${unit}`, padding.left + 10, padding.top - 10)

  }, [data, color, label, unit, TIME_BASE_MS])

  return (
    <div style={{
      marginTop: '12px',
      padding: '8px',
      backgroundColor: '#0a0a0a',
      borderRadius: '4px',
      border: '1px solid #333'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: isExpanded ? '8px' : '0'
      }}>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#b7c0d1',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px'
          }}
        >
          <span style={{
            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
            display: 'inline-block'
          }}>▶</span>
          Time Series Graph
        </button>
        {isExpanded && (
          <button
            onClick={handleReset}
            style={{
              background: 'rgba(239,68,68,.15)',
              border: '1px solid rgba(239,68,68,.35)',
              color: '#fca5a5',
              cursor: 'pointer',
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: '4px',
              fontWeight: 600
            }}
            title="Reset graph and start from scratch"
          >
            🔄 Reset
          </button>
        )}
      </div>
      {isExpanded && (
        <canvas
          ref={canvasRef}
          width={600}
          height={300}
          style={{
            width: '100%',
            height: 'auto',
            display: 'block'
          }}
        />
      )}
    </div>
  )
}

export default TimeSeriesGraph

import React, { useEffect, useRef, useState } from 'react'

interface DataPoint {
  timestamp: number
  voltage: number
  current: number
  power: number
}

interface TimeSeriesGraphProps {
  channelPath?: string
  maxDataPoints?: number
  updateInterval?: number
}

export function TimeSeriesGraph({
  channelPath,
  maxDataPoints = 100,
  updateInterval = 1000
}: TimeSeriesGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<DataPoint[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const [showPopup, setShowPopup] = useState(false)
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`

  // Fetch data from API
  useEffect(() => {
    if (!channelPath) return

    const fetchData = async () => {
      try {
        const [vRes, iRes, pRes] = await Promise.all([
         // fetch(`${apiBase}${channelPath}/query_output_voltage`),
         // fetch(`${apiBase}${channelPath}/query_output_current`),
         // fetch(`${apiBase}${channelPath}/query_output_power`)
        ])

        const [vData, iData, pData] = await Promise.all([
          vRes.ok ? vRes.json().catch(() => ({ value: 0 })) : { value: 0 },
          iRes.ok ? iRes.json().catch(() => ({ value: 0 })) : { value: 0 },
          pRes.ok ? pRes.json().catch(() => ({ value: 0 })) : { value: 0 }
        ])

        const newPoint: DataPoint = {
          timestamp: Date.now(),
          voltage: parseFloat(vData.value) || 0,
          current: parseFloat(iData.value) || 0,
          power: parseFloat(pData.value) || 0
        }

        setData(prev => {
          const updated = [...prev, newPoint]
          return updated.slice(-maxDataPoints)
        })
      } catch (err) {
        console.debug('Failed to fetch data for graph:', err)
      }
    }

    // Initial fetch
    fetchData()

    // Set up interval
    const interval = setInterval(fetchData, updateInterval)
    return () => clearInterval(interval)
  }, [channelPath, apiBase, maxDataPoints, updateInterval])

  // Draw the graph
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = { top: 20, right: 60, bottom: 30, left: 60 }
    const graphWidth = width - padding.left - padding.right
    const graphHeight = height - padding.top - padding.bottom

    // Clear canvas
    ctx.fillStyle = '#1a1a1a'
    ctx.fillRect(0, 0, width, height)

    if (data.length < 2) {
      // Show "waiting for data" message
      ctx.fillStyle = '#666'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Waiting for data...', width / 2, height / 2)
      return
    }

    // Calculate ranges
    const voltages = data.map(d => d.voltage)
    const currents = data.map(d => d.current)
    const powers = data.map(d => d.power)

    const vMin = Math.min(...voltages)
    const vMax = Math.max(...voltages)
    const iMin = Math.min(...currents)
    const iMax = Math.max(...currents)
    const pMin = Math.min(...powers)
    const pMax = Math.max(...powers)

    // Add 10% padding to ranges
    const vRange = vMax - vMin || 1
    const iRange = iMax - iMin || 1
    const pRange = pMax - pMin || 1

    const vPadded = { min: vMin - vRange * 0.1, max: vMax + vRange * 0.1 }
    const iPadded = { min: iMin - iRange * 0.1, max: iMax + iRange * 0.1 }
    const pPadded = { min: pMin - pRange * 0.1, max: pMax + pRange * 0.1 }

    // Helper functions
    const scaleX = (index: number) => padding.left + (index / (data.length - 1)) * graphWidth
    const scaleY = (value: number, min: number, max: number) =>
      padding.top + graphHeight - ((value - min) / (max - min)) * graphHeight

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

    // Draw voltage line (red)
    ctx.strokeStyle = '#ff4444'
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.voltage, vPadded.min, vPadded.max)
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // Draw current line (green)
    ctx.strokeStyle = '#44ff44'
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.current, iPadded.min, iPadded.max)
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // Draw power line (blue)
    ctx.strokeStyle = '#4444ff'
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.power, pPadded.min, pPadded.max)
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
    // Right Y-axis
    ctx.moveTo(width - padding.right, padding.top)
    ctx.lineTo(width - padding.right, height - padding.bottom)
    ctx.stroke()

    // Draw labels
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'right'

    // Left Y-axis labels (Voltage - red)
    ctx.fillStyle = '#ff4444'
    ctx.fillText(`${vPadded.max.toFixed(2)}V`, padding.left - 5, padding.top + 5)
    ctx.fillText(`${vPadded.min.toFixed(2)}V`, padding.left - 5, height - padding.bottom + 5)
    ctx.textAlign = 'center'
    ctx.save()
    ctx.translate(15, height / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText('Voltage (V)', 0, 0)
    ctx.restore()

    // Right Y-axis labels (Current - green, Power - blue)
    ctx.textAlign = 'left'
    ctx.fillStyle = '#44ff44'
    ctx.fillText(`${iPadded.max.toFixed(3)}A`, width - padding.right + 5, padding.top + 5)
    ctx.fillText(`${iPadded.min.toFixed(3)}A`, width - padding.right + 5, padding.top + graphHeight * 0.33)

    ctx.fillStyle = '#4444ff'
    ctx.fillText(`${pPadded.max.toFixed(2)}W`, width - padding.right + 5, padding.top + graphHeight * 0.66)
    ctx.fillText(`${pPadded.min.toFixed(2)}W`, width - padding.right + 5, height - padding.bottom + 5)

    // X-axis label
    ctx.fillStyle = '#aaa'
    ctx.textAlign = 'center'
    ctx.fillText('Time', width / 2, height - 5)

    // Legend
    const legendX = padding.left + 10
    const legendY = padding.top + 10
    const legendSpacing = 80

    ctx.textAlign = 'left'

    ctx.fillStyle = '#ff4444'
    ctx.fillRect(legendX, legendY, 15, 3)
    ctx.fillText('U (V)', legendX + 20, legendY + 5)

    ctx.fillStyle = '#44ff44'
    ctx.fillRect(legendX + legendSpacing, legendY, 15, 3)
    ctx.fillText('I (A)', legendX + legendSpacing + 20, legendY + 5)

    ctx.fillStyle = '#4444ff'
    ctx.fillRect(legendX + legendSpacing * 2, legendY, 15, 3)
    ctx.fillText('P (W)', legendX + legendSpacing * 2 + 20, legendY + 5)

  }, [data])

  return (
    <>
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
              onClick={() => setShowPopup(true)}
              style={{
                background: 'rgba(96,165,250,.15)',
                border: '1px solid rgba(96,165,250,.35)',
                color: '#bcd9ff',
                cursor: 'pointer',
                fontSize: '11px',
                padding: '4px 8px',
                borderRadius: '4px'
              }}
              title="Zoom in (3x)"
            >
              🔍 Zoom
            </button>
          )}
        </div>
        {isExpanded && (
          <GraphCanvas
            canvasRef={canvasRef}
            data={data}
            width={600}
            height={300}
          />
        )}
      </div>

      {showPopup && (
        <GraphPopup
          data={data}
          onClose={() => setShowPopup(false)}
        />
      )}
    </>
  )
}

function GraphCanvas({
  canvasRef,
  data,
  width,
  height
}: {
  canvasRef: React.RefObject<HTMLCanvasElement>
  data: DataPoint[]
  width: number
  height: number
}) {
  // Draw the graph
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const padding = { top: 20, right: 60, bottom: 30, left: 60 }
    const graphWidth = width - padding.left - padding.right
    const graphHeight = height - padding.top - padding.bottom

    // Clear canvas
    ctx.fillStyle = '#1a1a1a'
    ctx.fillRect(0, 0, width, height)

    if (data.length < 2) {
      // Show "waiting for data" message
      ctx.fillStyle = '#666'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Waiting for data...', width / 2, height / 2)
      return
    }

    // Calculate ranges
    const voltages = data.map(d => d.voltage)
    const currents = data.map(d => d.current)
    const powers = data.map(d => d.power)

    const vMin = Math.min(...voltages)
    const vMax = Math.max(...voltages)
    const iMin = Math.min(...currents)
    const iMax = Math.max(...currents)
    const pMin = Math.min(...powers)
    const pMax = Math.max(...powers)

    // Add 10% padding to ranges
    const vRange = vMax - vMin || 1
    const iRange = iMax - iMin || 1
    const pRange = pMax - pMin || 1

    const vPadded = { min: vMin - vRange * 0.1, max: vMax + vRange * 0.1 }
    const iPadded = { min: iMin - iRange * 0.1, max: iMax + iRange * 0.1 }
    const pPadded = { min: pMin - pRange * 0.1, max: pMax + pRange * 0.1 }

    // Helper functions
    const scaleX = (index: number) => padding.left + (index / (data.length - 1)) * graphWidth
    const scaleY = (value: number, min: number, max: number) =>
      padding.top + graphHeight - ((value - min) / (max - min)) * graphHeight

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

    // Draw voltage line (red)
    ctx.strokeStyle = '#ff4444'
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.voltage, vPadded.min, vPadded.max)
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // Draw current line (green)
    ctx.strokeStyle = '#44ff44'
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.current, iPadded.min, iPadded.max)
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // Draw power line (blue)
    ctx.strokeStyle = '#4444ff'
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, index) => {
      const x = scaleX(index)
      const y = scaleY(point.power, pPadded.min, pPadded.max)
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
    // Right Y-axis
    ctx.moveTo(width - padding.right, padding.top)
    ctx.lineTo(width - padding.right, height - padding.bottom)
    ctx.stroke()

    // Draw labels
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'right'

    // Left Y-axis labels (Voltage - red)
    ctx.fillStyle = '#ff4444'
    ctx.fillText(`${vPadded.max.toFixed(2)}V`, padding.left - 5, padding.top + 5)
    ctx.fillText(`${vPadded.min.toFixed(2)}V`, padding.left - 5, height - padding.bottom + 5)
    ctx.textAlign = 'center'
    ctx.save()
    ctx.translate(15, height / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText('Voltage (V)', 0, 0)
    ctx.restore()

    // Right Y-axis labels (Current - green, Power - blue)
    ctx.textAlign = 'left'
    ctx.fillStyle = '#44ff44'
    ctx.fillText(`${iPadded.max.toFixed(3)}A`, width - padding.right + 5, padding.top + 5)
    ctx.fillText(`${iPadded.min.toFixed(3)}A`, width - padding.right + 5, padding.top + graphHeight * 0.33)

    ctx.fillStyle = '#4444ff'
    ctx.fillText(`${pPadded.max.toFixed(2)}W`, width - padding.right + 5, padding.top + graphHeight * 0.66)
    ctx.fillText(`${pPadded.min.toFixed(2)}W`, width - padding.right + 5, height - padding.bottom + 5)

    // X-axis label
    ctx.fillStyle = '#aaa'
    ctx.textAlign = 'center'
    ctx.fillText('Time', width / 2, height - 5)

    // Legend
    const legendX = padding.left + 10
    const legendY = padding.top + 10
    const legendSpacing = 80

    ctx.textAlign = 'left'

    ctx.fillStyle = '#ff4444'
    ctx.fillRect(legendX, legendY, 15, 3)
    ctx.fillText('U (V)', legendX + 20, legendY + 5)

    ctx.fillStyle = '#44ff44'
    ctx.fillRect(legendX + legendSpacing, legendY, 15, 3)
    ctx.fillText('I (A)', legendX + legendSpacing + 20, legendY + 5)

    ctx.fillStyle = '#4444ff'
    ctx.fillRect(legendX + legendSpacing * 2, legendY, 15, 3)
    ctx.fillText('P (W)', legendX + legendSpacing * 2 + 20, legendY + 5)

  }, [data, width, height])

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        width: '100%',
        height: 'auto',
        display: 'block'
      }}
    />
  )
}

function GraphPopup({ data, onClose }: { data: DataPoint[], onClose: () => void }) {
  const [position, setPosition] = useState({ x: 100, y: 100 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const popupRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y
      })
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, dragOffset])

  const handleMouseDown = (e: React.MouseEvent) => {
    if (popupRef.current) {
      const rect = popupRef.current.getBoundingClientRect()
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      })
      setIsDragging(true)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      zIndex: 10000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div
        ref={popupRef}
        style={{
          position: 'absolute',
          left: `${position.x}px`,
          top: `${position.y}px`,
          backgroundColor: '#161d2a',
          border: '2px solid #202737',
          borderRadius: '8px',
          boxShadow: '0 10px 40px rgba(0,0,0,.5)',
          overflow: 'hidden',
          cursor: isDragging ? 'grabbing' : 'grab'
        }}
      >
        <div
          onMouseDown={handleMouseDown}
          style={{
            padding: '12px 16px',
            background: 'linear-gradient(180deg, #1a2230, #161d2a)',
            borderBottom: '1px solid #202737',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: isDragging ? 'grabbing' : 'grab'
          }}
        >
          <span style={{ color: '#b7c0d1', fontWeight: 600, fontSize: '14px' }}>
            Time Series Graph (Zoomed)
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ef4444',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '0 8px',
              lineHeight: '20px'
            }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: '16px', backgroundColor: '#0f1216' }}>
          <GraphCanvas
            canvasRef={canvasRef}
            data={data}
            width={1800}
            height={900}
          />
        </div>
      </div>
    </div>
  )
}

export default TimeSeriesGraph

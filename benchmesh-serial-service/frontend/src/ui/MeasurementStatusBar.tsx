import React, { useState, useEffect, useRef } from 'react'
import { useMeasurement, MeasurementSource } from './MeasurementContext'

interface MeasurementRecord {
  timestamp: Date
  values: Record<string, number | null>
}

// Helper function to extract measurement value from registry
function getValueFromRegistry(registry: any, source: MeasurementSource): number | null {
  if (!registry || !source) {
    console.debug('[getValueFromRegistry] No registry or source')
    return null
  }

  // Parse channelPath like /instruments/PSU/{deviceId}/{channel} or /instruments/DMM/{deviceId}/{channel}
  const parts = source.channelPath.split('/').filter(Boolean)
  if (parts.length < 4) {
    console.debug('[getValueFromRegistry] Invalid channelPath:', source.channelPath)
    return null
  }

  const klass = parts[1]  // e.g., "PSU", "DMM"
  const deviceId = parts[2]  // e.g., "psu-1", "dmm-1"
  const channel = parts[3]  // e.g., "1"
  const statusKey = `status_ch${channel}`

  console.debug(`[getValueFromRegistry] Looking for: deviceId=${deviceId}, klass=${klass}, statusKey=${statusKey}`)

  // Navigate registry: registry[deviceId][klass][statusKey]
  const deviceData = registry[deviceId]
  if (!deviceData) {
    console.debug(`[getValueFromRegistry] Device not found: ${deviceId}, available:`, Object.keys(registry))
    return null
  }

  const classData = deviceData[klass]
  if (!classData) {
    console.debug(`[getValueFromRegistry] Class not found: ${klass}, available:`, Object.keys(deviceData))
    return null
  }

  const channelData = classData[statusKey]
  if (!channelData) {
    console.debug(`[getValueFromRegistry] Channel not found: ${statusKey}, available:`, Object.keys(classData))
    return null
  }

  console.debug(`[getValueFromRegistry] channelData keys:`, Object.keys(channelData))
  console.debug(`[getValueFromRegistry] channelData:`, channelData)

  // Different instruments store values differently
  let rawValue: any = null

  // DMM uses measurement1_num
  if (channelData.measurement1_num !== undefined && channelData.measurement1_num !== null) {
    rawValue = channelData.measurement1_num
    console.debug(`[getValueFromRegistry] Found DMM value: measurement1_num=${rawValue}`)
  }
  // PSU can use various field names - try multiple possibilities
  else if (source.parameter === 'voltage') {
    // Try different field names
    if (channelData.output_voltage_num !== undefined) {
      rawValue = channelData.output_voltage_num
      console.debug(`[getValueFromRegistry] Found PSU voltage: output_voltage_num=${rawValue}`)
    } else if (channelData.voltage_num !== undefined) {
      rawValue = channelData.voltage_num
      console.debug(`[getValueFromRegistry] Found PSU voltage: voltage_num=${rawValue}`)
    } else if (channelData.voltage !== undefined) {
      rawValue = channelData.voltage
      console.debug(`[getValueFromRegistry] Found PSU voltage: voltage=${rawValue}`)
    }
  }
  else if (source.parameter === 'current') {
    if (channelData.output_current_num !== undefined) {
      rawValue = channelData.output_current_num
      console.debug(`[getValueFromRegistry] Found PSU current: output_current_num=${rawValue}`)
    } else if (channelData.current_num !== undefined) {
      rawValue = channelData.current_num
      console.debug(`[getValueFromRegistry] Found PSU current: current_num=${rawValue}`)
    } else if (channelData.current !== undefined) {
      rawValue = channelData.current
      console.debug(`[getValueFromRegistry] Found PSU current: current=${rawValue}`)
    }
  }
  else if (source.parameter === 'power') {
    if (channelData.output_power_num !== undefined) {
      rawValue = channelData.output_power_num
      console.debug(`[getValueFromRegistry] Found PSU power: output_power_num=${rawValue}`)
    } else if (channelData.power_num !== undefined) {
      rawValue = channelData.power_num
      console.debug(`[getValueFromRegistry] Found PSU power: power_num=${rawValue}`)
    } else if (channelData.power !== undefined) {
      rawValue = channelData.power
      console.debug(`[getValueFromRegistry] Found PSU power: power=${rawValue}`)
    }
  }

  if (rawValue === undefined || rawValue === null) {
    console.debug(`[getValueFromRegistry] No value found for parameter=${source.parameter}, available keys:`, Object.keys(channelData))
    return null
  }

  const result = parseFloat(String(rawValue))
  console.debug(`[getValueFromRegistry] Returning value: ${result}`)
  return result
}

const FREQUENCIES = [
  { label: '0.5s', value: 500 },
  { label: '1s', value: 1000 },
  { label: '2s', value: 2000 },
  { label: '4s', value: 4000 },
  { label: '5s', value: 5000 },
  { label: '10s', value: 10000 }
]

export function MeasurementStatusBar() {
  const [recordOpen, setRecordOpen] = useState(false)
  const [graphOpen, setGraphOpen] = useState(false)
  const [recordHeight, setRecordHeight] = useState(300)
  const [graphHeight, setGraphHeight] = useState(300)
  const [recordFrequency, setRecordFrequency] = useState(1000)
  const [graphFrequency, setGraphFrequency] = useState(1000)
  const [records, setRecords] = useState<MeasurementRecord[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isGraphing, setIsGraphing] = useState(false)
  const [nodeRedActive, setNodeRedActive] = useState(false)
  const [automationCount, setAutomationCount] = useState({ total: 0, running: 0 })

  const { selectedForRecord, selectedForGraph, sources, registry } = useMeasurement()

  // Check BenchMesh automations
  useEffect(() => {
    const checkAutomations = async () => {
      try {
        const autoResponse = await fetch(`http://${window.location.hostname}:1880/benchmesh/automations`)
        if (autoResponse.ok) {
          const automations = await autoResponse.json()
          const automationArray = Object.values(automations)
          const total = automationArray.length
          const running = automationArray.filter((a: any) => a.enabled).length

          // Button is RED when any automations are running, GREEN when all stopped
          setNodeRedActive(running > 0)
          setAutomationCount({ total, running })

          console.log('[BenchMesh] Automations:', { total, running, active: running > 0 })
        } else {
          // No automations endpoint or error
          setNodeRedActive(false)
          setAutomationCount({ total: 0, running: 0 })
        }
      } catch (e) {
        setNodeRedActive(false)
        setAutomationCount({ total: 0, running: 0 })
      }
    }

    checkAutomations()
    const interval = setInterval(checkAutomations, 5000)
    return () => clearInterval(interval)
  }, [])

  // Recording logic using WebSocket registry data
  useEffect(() => {
    if (!isRecording || selectedForRecord.size === 0) return

    const interval = setInterval(() => {
      const values: Record<string, number | null> = {}

      for (const sourceId of selectedForRecord) {
        const source = sources.get(sourceId)
        if (!source) continue

        values[sourceId] = getValueFromRegistry(registry, source)
      }

      setRecords(prev => [...prev, { timestamp: new Date(), values }])
    }, recordFrequency)

    return () => clearInterval(interval)
  }, [isRecording, recordFrequency, selectedForRecord, sources, registry])

  const exportCSV = () => {
    if (records.length === 0) return

    const headers = ['Timestamp', ...Array.from(selectedForRecord).map(id => {
      const source = sources.get(id)
      return source ? `${source.label} [${source.unit}]` : id
    })]

    const rows = records.map(record => {
      const timestamp = record.timestamp.toLocaleString()
      const values = Array.from(selectedForRecord).map(id =>
        record.values[id] !== null ? record.values[id] : ''
      )
      return [timestamp, ...values].join(',')
    })

    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `measurements_${new Date().toISOString()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const clearRecords = () => {
    setRecords([])
  }

  return (
    <>
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'linear-gradient(180deg, var(--bg-1), var(--bg-2))',
        borderTop: '1px solid var(--border)',
        padding: '8px 16px',
        display: 'flex',
        gap: '8px',
        alignItems: 'center',
        zIndex: 100
      }}>
        <button
          onClick={() => {
            setRecordOpen(!recordOpen)
            if (graphOpen && !recordOpen) setGraphOpen(false)
          }}
          style={{
            padding: '6px 12px',
            background: recordOpen ? 'var(--accent)' : 'rgba(255,255,255,.05)',
            color: recordOpen ? '#000' : 'var(--text-0)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600
          }}
        >
          📊 Measurements Record
        </button>
        <button
          onClick={() => {
            setGraphOpen(!graphOpen)
            if (recordOpen && !graphOpen) setRecordOpen(false)
          }}
          style={{
            padding: '6px 12px',
            background: graphOpen ? 'var(--accent)' : 'rgba(255,255,255,.05)',
            color: graphOpen ? '#000' : 'var(--text-0)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600
          }}
        >
          📈 Measurements Graph
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => {
              const nodeRedUrl = `${window.location.protocol}//${window.location.hostname}:1880`
              window.open(nodeRedUrl, '_blank', 'noopener,noreferrer')
            }}
            style={{
              padding: '6px 12px',
              background: nodeRedActive ? 'rgba(255,68,68,.15)' : 'rgba(68,255,68,.15)',
              color: nodeRedActive ? '#ff6b6b' : '#6bff6b',
              border: nodeRedActive ? '1px solid rgba(255,68,68,.35)' : '1px solid rgba(68,255,68,.35)',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              position: 'relative'
            }}
            title={nodeRedActive
              ? `${automationCount.running} automations running - Click to open Node-RED`
              : automationCount.total > 0
                ? `All ${automationCount.total} automations stopped - Click to open Node-RED`
                : 'No automations configured - Click to open Node-RED'}
          >
            <span style={{ fontSize: '14px' }}>{nodeRedActive ? '🔴' : '🟢'}</span>
            <span>Node-RED Automations</span>
            {automationCount.total > 0 && (
              <span style={{
                marginLeft: '4px',
                fontSize: '10px',
                background: nodeRedActive ? 'rgba(255,68,68,.3)' : 'rgba(68,255,68,.3)',
                padding: '2px 6px',
                borderRadius: '10px',
                fontWeight: 700
              }}>
                {automationCount.running}/{automationCount.total}
              </span>
            )}
          </button>
        </div>
      </div>

      {recordOpen && (
        <RecordPanel
          height={recordHeight}
          onHeightChange={setRecordHeight}
          frequency={recordFrequency}
          onFrequencyChange={setRecordFrequency}
          records={records}
          isRecording={isRecording}
          onToggleRecording={() => setIsRecording(!isRecording)}
          onExportCSV={exportCSV}
          onClear={clearRecords}
          selectedSources={Array.from(selectedForRecord).map(id => sources.get(id)!).filter(Boolean)}
        />
      )}

      {graphOpen && (
        <GraphPanel
          height={graphHeight}
          onHeightChange={setGraphHeight}
          frequency={graphFrequency}
          onFrequencyChange={setGraphFrequency}
          isGraphing={isGraphing}
          onToggleGraphing={() => setIsGraphing(!isGraphing)}
          selectedSources={Array.from(selectedForGraph).map(id => sources.get(id)!).filter(Boolean)}
        />
      )}
    </>
  )
}

function RecordPanel({
  height,
  onHeightChange,
  frequency,
  onFrequencyChange,
  records,
  isRecording,
  onToggleRecording,
  onExportCSV,
  onClear,
  selectedSources
}: any) {
  const resizeRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY
      onHeightChange(Math.max(200, Math.min(800, newHeight)))
    }

    const handleMouseUp = () => setIsDragging(false)

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, onHeightChange])

  return (
    <div style={{
      position: 'fixed',
      bottom: 40,
      left: 0,
      right: 0,
      height: `${height}px`,
      background: 'var(--bg-0)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 99
    }}>
      <div
        ref={resizeRef}
        onMouseDown={() => setIsDragging(true)}
        style={{
          height: '6px',
          cursor: 'ns-resize',
          background: 'var(--border)',
          borderBottom: '1px solid var(--border)'
        }}
      />

      <div style={{ padding: '12px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ fontSize: '12px', color: 'var(--text-1)' }}>
          Frequency:
          <select
            value={frequency}
            onChange={(e) => onFrequencyChange(Number(e.target.value))}
            style={{
              marginLeft: '8px',
              padding: '4px 8px',
              background: 'var(--bg-2)',
              color: 'var(--text-0)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '12px'
            }}
          >
            {FREQUENCIES.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>

        <button
          onClick={onToggleRecording}
          disabled={selectedSources.length === 0}
          style={{
            padding: '6px 12px',
            background: isRecording ? 'var(--bad)' : 'var(--good)',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: selectedSources.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            opacity: selectedSources.length === 0 ? 0.5 : 1
          }}
        >
          {isRecording ? '⏹ Stop' : '▶ Start'} Recording
        </button>

        <button
          onClick={onExportCSV}
          disabled={records.length === 0}
          style={{
            padding: '6px 12px',
            background: 'var(--accent)',
            color: '#000',
            border: 'none',
            borderRadius: '4px',
            cursor: records.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            opacity: records.length === 0 ? 0.5 : 1
          }}
        >
          💾 Export CSV
        </button>

        <button
          onClick={onClear}
          disabled={records.length === 0}
          style={{
            padding: '6px 12px',
            background: 'rgba(255,255,255,.05)',
            color: 'var(--text-1)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            cursor: records.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            opacity: records.length === 0 ? 0.5 : 1
          }}
        >
          🗑 Clear
        </button>

        <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--text-2)' }}>
          {records.length} records | {selectedSources.length} sources selected
        </span>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
        {selectedSources.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-2)', padding: '40px' }}>
            No measurements selected. Check measurement boxes in instrument panels above.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: 'var(--bg-2)', position: 'sticky', top: 0 }}>
                <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}>
                  Timestamp
                </th>
                {selectedSources.map((source: any) => (
                  <th key={source.id} style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}>
                    {source.label} [{source.unit}]
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((record: MeasurementRecord, idx: number) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '6px 8px', color: 'var(--text-2)' }}>
                    {record.timestamp.toLocaleString()}
                  </td>
                  {selectedSources.map((source: any) => (
                    <td key={source.id} style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-0)', fontVariantNumeric: 'tabular-nums' }}>
                      {record.values[source.id] !== null ? record.values[source.id]?.toFixed(3) : '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function GraphPanel({
  height,
  onHeightChange,
  frequency,
  onFrequencyChange,
  isGraphing,
  onToggleGraphing,
  selectedSources
}: any) {
  const resizeRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const canvasRefs = useRef<Map<string, HTMLCanvasElement>>(new Map())
  const [graphData, setGraphData] = useState<Map<string, Array<{ time: number, value: number }>>>(new Map())

  const { sources, registry } = useMeasurement()

  // Store the frequency at the time graphing starts
  const activeFrequencyRef = useRef(frequency)

  useEffect(() => {
    if (isGraphing) {
      activeFrequencyRef.current = frequency
    }
  }, [isGraphing])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY
      onHeightChange(Math.max(200, Math.min(800, newHeight)))
    }

    const handleMouseUp = () => setIsDragging(false)

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, onHeightChange])

  // Fetch data for graphing using WebSocket registry data
  useEffect(() => {
    if (!isGraphing || selectedSources.length === 0) {
      console.log('[Graph] Effect triggered but not starting:', { isGraphing, sourcesCount: selectedSources.length })
      return
    }

    console.log('[Graph] Starting graphing for sources:', selectedSources.map((s: any) => s.id))
    console.log('[Graph] Frequency:', activeFrequencyRef.current, 'ms')
    console.log('[Graph] Registry exists:', !!registry, 'Registry keys:', registry ? Object.keys(registry) : 'none')

    // Run immediately once
    console.log('[Graph] Running initial data collection...')
    const collectData = () => {
      console.log('[Graph] collectData() called at', new Date().toISOString())
      const now = Date.now()

      for (const source of selectedSources) {
        console.log(`[Graph] Processing source: ${source.id}`)
        const value = getValueFromRegistry(registry, source)
        console.log(`[Graph] ${source.id}: value=${value}, parameter=${source.parameter}, channelPath=${source.channelPath}`)

        if (value === null) {
          console.warn(`[Graph] Null value for ${source.id}, skipping`)
          continue
        }

        setGraphData(prev => {
          const next = new Map(prev)
          const points = next.get(source.id) || []
          const newPoints = [...points, { time: now, value }].slice(-100)
          next.set(source.id, newPoints)
          console.log(`[Graph] ${source.id}: added point, total points=${newPoints.length}`)
          return next
        })
      }
    }

    collectData()

    const interval = setInterval(collectData, activeFrequencyRef.current)
    console.log('[Graph] Interval set with ID:', interval, 'frequency:', activeFrequencyRef.current)

    return () => {
      console.log('[Graph] Stopping graphing, clearing interval:', interval)
      clearInterval(interval)
    }
  }, [isGraphing, selectedSources, registry])

  // Draw individual graphs for each source
  useEffect(() => {
    console.log('[Graph Draw] Redrawing graphs, selectedSources:', selectedSources.length, 'graphData size:', graphData.size)

    selectedSources.forEach((source: any) => {
      const canvas = canvasRefs.current.get(source.id)
      if (!canvas) {
        console.warn(`[Graph Draw] No canvas found for ${source.id}`)
        return
      }

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        console.warn(`[Graph Draw] No context for ${source.id}`)
        return
      }

      const width = canvas.width
      const height = canvas.height
      const padding = { top: 40, right: 80, bottom: 40, left: 80 }

      // Clear canvas
      ctx.fillStyle = '#0f1216'
      ctx.fillRect(0, 0, width, height)

      const points = graphData.get(source.id) || []
      console.log(`[Graph Draw] ${source.id}: ${points.length} points`)

      if (points.length < 2) {
        ctx.fillStyle = '#666'
        ctx.font = '14px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText('Waiting for data...', width / 2, height / 2)
        console.log(`[Graph Draw] ${source.id}: Not enough points (${points.length}), showing "Waiting for data..."`)
        return
      }

      console.log(`[Graph Draw] ${source.id}: Drawing ${points.length} points`)

      const values = points.map(p => p.value)
      const min = Math.min(...values)
      const max = Math.max(...values)
      const range = max - min || 1

      // Draw grid
      ctx.strokeStyle = '#202737'
      ctx.lineWidth = 1
      for (let i = 0; i <= 5; i++) {
        const y = padding.top + (i / 5) * (height - padding.top - padding.bottom)
        ctx.beginPath()
        ctx.moveTo(padding.left, y)
        ctx.lineTo(width - padding.right, y)
        ctx.stroke()
      }

      // Draw vertical grid
      for (let i = 0; i <= 10; i++) {
        const x = padding.left + (i / 10) * (width - padding.left - padding.right)
        ctx.beginPath()
        ctx.moveTo(x, padding.top)
        ctx.lineTo(x, height - padding.bottom)
        ctx.stroke()
      }

      // Draw the line
      ctx.strokeStyle = '#60a5fa'
      ctx.lineWidth = 2
      ctx.beginPath()

      points.forEach((point, idx) => {
        const x = padding.left + (idx / (points.length - 1)) * (width - padding.left - padding.right)
        const y = padding.top + (height - padding.top - padding.bottom) * (1 - (point.value - min) / range)

        if (idx === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()

      // Draw title
      ctx.fillStyle = '#b7c0d1'
      ctx.font = 'bold 14px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(`${source.label}`, padding.left, 20)

      // Draw Y-axis scale
      ctx.fillStyle = '#b7c0d1'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'right'
      for (let i = 0; i <= 5; i++) {
        const value = max - (i / 5) * range
        const y = padding.top + (i / 5) * (height - padding.top - padding.bottom)
        ctx.fillText(`${value.toFixed(3)} ${source.unit}`, padding.left - 10, y + 4)
      }

      // Draw current value indicator
      const lastValue = values[values.length - 1]
      ctx.fillStyle = '#60a5fa'
      ctx.font = 'bold 12px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(`Current: ${lastValue.toFixed(3)} ${source.unit}`, width - padding.right - 150, 20)
    })
  }, [graphData, selectedSources])

  const clearGraph = () => {
    setGraphData(new Map())
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: 40,
      left: 0,
      right: 0,
      height: `${height}px`,
      background: 'var(--bg-0)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 99
    }}>
      <div
        ref={resizeRef}
        onMouseDown={() => setIsDragging(true)}
        style={{
          height: '6px',
          cursor: 'ns-resize',
          background: 'var(--border)',
          borderBottom: '1px solid var(--border)'
        }}
      />

      <div style={{ padding: '12px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ fontSize: '12px', color: 'var(--text-1)' }}>
          Frequency:
          <select
            value={frequency}
            onChange={(e) => onFrequencyChange(Number(e.target.value))}
            disabled={isGraphing}
            style={{
              marginLeft: '8px',
              padding: '4px 8px',
              background: 'var(--bg-2)',
              color: 'var(--text-0)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '12px',
              cursor: isGraphing ? 'not-allowed' : 'pointer',
              opacity: isGraphing ? 0.5 : 1
            }}
          >
            {FREQUENCIES.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>

        <button
          onClick={onToggleGraphing}
          disabled={selectedSources.length === 0}
          style={{
            padding: '6px 12px',
            background: isGraphing ? 'var(--bad)' : 'var(--good)',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: selectedSources.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            opacity: selectedSources.length === 0 ? 0.5 : 1
          }}
        >
          {isGraphing ? '⏹ Stop' : '▶ Start'} Graphing
        </button>

        <button
          onClick={clearGraph}
          disabled={isGraphing}
          style={{
            padding: '6px 12px',
            background: 'rgba(255,255,255,.05)',
            color: 'var(--text-1)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            cursor: isGraphing ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            opacity: isGraphing ? 0.5 : 1
          }}
        >
          🗑 Clear
        </button>

        <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--text-2)' }}>
          {selectedSources.length} sources selected
        </span>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
        {selectedSources.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-2)', padding: '40px' }}>
            No measurements selected. Check measurement boxes in instrument panels above.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {selectedSources.map((source: any) => (
              <canvas
                key={source.id}
                ref={(el) => {
                  if (el) {
                    canvasRefs.current.set(source.id, el)
                  } else {
                    canvasRefs.current.delete(source.id)
                  }
                }}
                width={1200}
                height={400}
                style={{ width: '100%', height: '200px', display: 'block', border: '1px solid var(--border)', borderRadius: '4px' }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

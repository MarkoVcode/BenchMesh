import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useMeasurement } from '../../MeasurementContext'

// Generic DMM component styled similarly to GenericPSU
// - Before rendering, fetch GET /instruments/DMM/{device_id} to obtain features (modes list)
// - Settings: full-width dropdown to select mode; hover tooltip shows POST endpoint template
// - Readings: placeholder big-number display U[V] with 5-digit readonly value
export function GenericDMM({ channelPath }: { channelPath?: string }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { registerSource } = useMeasurement()

  // Parse class, device id, and channel from channelPath like /instruments/DMM/{id}/{ch}
  const { klass, deviceId, channel } = useMemo(() => parsePath(channelPath), [channelPath])

  const [modes, setModes] = useState<string[]>([])
  const [mode, setMode] = useState<string>('')
  const [busy, setBusy] = useState(false)

  // Register measurement sources
  useEffect(() => {
    if (!channelPath || !deviceId) return

    registerSource({
      id: `${deviceId}-${channel}-U`,
      deviceId,
      channelPath,
      parameter: 'voltage',
      label: `${deviceId} Ch${channel} U`,
      unit: 'V'
    })
  }, [channelPath, deviceId, channel, registerSource])

  // Fetch class features (modes) before rendering content
  useEffect(() => {
    let cancelled = false
    async function loadFeatures() {
      if (!deviceId || !klass) return
      try {
        const r = await fetch(`${apiBase}/instruments/${klass}/${deviceId}`)
        if (!r.ok) return
        const j = await r.json().catch(() => ({} as any))
        if (!cancelled) {
          const mm = Array.isArray(j?.modes) ? (j.modes as any[]).map(String) : []
          setModes(mm)
          if (!mode && mm.length) setMode(String(mm[0]))
        }
      } catch {}
    }
    loadFeatures()
    return () => { cancelled = true }
  }, [apiBase, deviceId, klass])

  const endpointTemplate = useMemo(() => {
    const k = klass || 'DMM'
    const did = deviceId || '{id}'
    const ch = channel || '1'
    return `/instruments/${k}/${did}/${ch}/set_mode/{value}`
  }, [klass, deviceId, channel])

  const handleModeChange = async (newMode: string) => {
    setMode(newMode)
    if (!klass || !deviceId || busy) return
    setBusy(true)
    try {
      const ch = channel || '1'
      await fetch(`${apiBase}/instruments/${klass}/${deviceId}/${ch}/set_mode/${encodeURIComponent(newMode)}`, { method: 'POST' })
    } catch (err) {
      console.debug('Mode change failed', err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section" style={{ width: '100%' }}>
          <div className="psu-section-title">Settings</div>
          <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto auto', width: '100%' }}>
            <div className="psu-label">
              <span className="psu-symbol">Mode</span>
            </div>
            <CustomDropdown
              options={modes}
              value={mode}
              onChange={handleModeChange}
              disabled={busy || modes.length === 0}
              title={`POST ${endpointTemplate}`}
            />
            <button
              className="psu-set"
              type="button"
              disabled={busy}
              title={`POST ${endpointTemplate.replace('{value}', mode)}`}
              onClick={() => handleModeChange(mode)}
            >
              {busy ? (<><span className="spinner"/>SET</>) : 'SET'}
            </button>
            <span className="psu-api" title={`GET /instruments/${klass || 'DMM'}/${deviceId || '{id}'}`}>API</span>
          </div>
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber kind="U" label={<Label symbol="U" unit="V"/>} value={"00000"} channelPath={channelPath} parameter="voltage" />
        </div>
        <hr className="sep"/>
      </div>
    </div>
  )
}

function CustomDropdown({
  options,
  value,
  onChange,
  disabled,
  title
}: {
  options: string[]
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  title?: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (option: string) => {
    onChange(option)
    setIsOpen(false)
  }

  return (
    <div ref={dropdownRef} style={{ position: 'relative', width: '100%' }}>
      <button
        type="button"
        className="psu-number editable"
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        title={title}
        style={{
          width: '100%',
          padding: '4px 8px',
          cursor: disabled ? 'not-allowed' : 'pointer',
          background: 'rgba(255,255,255,.03)',
          border: '1px solid rgba(255,255,255,.25)',
          borderRadius: '4px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          textAlign: 'left',
          opacity: disabled ? 0.5 : 1
        }}
      >
        <span style={{
          fontVariantNumeric: 'tabular-nums',
          fontWeight: 700,
          fontSize: '16px',
          color: '#c26a1a'
        }}>
          {value || (options.length === 0 ? 'No modes' : 'Select...')}
        </span>
        <span style={{
          fontSize: '12px',
          color: 'rgba(255,255,255,.5)',
          marginLeft: '8px'
        }}>
          {isOpen ? '▲' : '▼'}
        </span>
      </button>
      {isOpen && options.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          marginTop: '4px',
          background: '#161d2a',
          border: '1px solid #202737',
          borderRadius: '6px',
          boxShadow: '0 4px 12px rgba(0,0,0,.4)',
          zIndex: 1000,
          maxHeight: '200px',
          overflowY: 'auto'
        }}>
          {options.map((option) => (
            <div
              key={option}
              onClick={() => handleSelect(option)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                background: option === value ? 'rgba(96,165,250,.15)' : 'transparent',
                color: option === value ? '#bcd9ff' : '#b7c0d1',
                fontSize: '14px',
                fontWeight: option === value ? 600 : 400,
                borderBottom: '1px solid rgba(255,255,255,.05)',
                transition: 'background .15s ease'
              }}
              onMouseEnter={(e) => {
                if (option !== value) {
                  e.currentTarget.style.background = 'rgba(255,255,255,.05)'
                }
              }}
              onMouseLeave={(e) => {
                if (option !== value) {
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              {option}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function parsePath(channelPath?: string): { klass?: string, deviceId?: string, channel?: string } {
  if (!channelPath) return {}
  const parts = channelPath.split('/').filter(Boolean)
  // [instruments, CLASS, device_id, channel, ...]
  if (parts.length < 4) return {}
  return { klass: parts[1], deviceId: parts[2], channel: parts[3] }
}

function ReadonlyBigNumber({ kind, label, value, channelPath, parameter }: { kind?: 'U' | 'I' | 'P', label: React.ReactNode, value: string, channelPath?: string, parameter?: string }) {
  const { selectedForRecord, selectedForGraph, toggleRecord, toggleGraph } = useMeasurement()

  const sourceId = useMemo(() => {
    if (!channelPath || !parameter) return ''
    const deviceId = channelPath.split('/')[3] || 'unknown'
    const channel = channelPath.split('/')[4] || '1'
    return `${deviceId}-${channel}-${kind}`
  }, [channelPath, parameter, kind])

  return (
    <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto auto auto' }}>
      <div className="psu-label">{label}</div>
      <span className="psu-number readonly" aria-hidden>
        <span>{value || '0'}</span>
      </span>
      {channelPath && (
        <>
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <label
              style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '10px', color: 'var(--text-2)' }}
              title="Record in table"
            >
              <input
                type="checkbox"
                checked={selectedForRecord.has(sourceId)}
                onChange={() => toggleRecord(sourceId)}
                style={{ width: '12px', height: '12px', cursor: 'pointer', accentColor: 'var(--accent)' }}
              />
              <span style={{ marginLeft: '2px' }}>📊</span>
            </label>
            <label
              style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '10px', color: 'var(--text-2)' }}
              title="Show in graph"
            >
              <input
                type="checkbox"
                checked={selectedForGraph.has(sourceId)}
                onChange={() => toggleGraph(sourceId)}
                style={{ width: '12px', height: '12px', cursor: 'pointer', accentColor: 'var(--good)' }}
              />
              <span style={{ marginLeft: '2px' }}>📈</span>
            </label>
          </div>
          <span className="psu-api" title={
            kind === 'U' ? `GET ${channelPath}/query_voltage` :
            kind === 'I' ? `GET ${channelPath}/query_current` :
            kind === 'P' ? `GET ${channelPath}/query_power` : ''
          }>API</span>
        </>
      )}
    </div>
  )
}

function Label({ symbol, unit }: { symbol: string, unit: string }) {
  return (
    <>
      <span className="psu-symbol">{symbol}</span><span className="psu-unit">[{unit}]</span>
    </>
  )
}

export default GenericDMM

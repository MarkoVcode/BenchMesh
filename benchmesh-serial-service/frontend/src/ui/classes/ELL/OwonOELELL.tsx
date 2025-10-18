import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useMeasurement } from '../../MeasurementContext'
import { RemoteLockWarning } from '../../components/RemoteLockWarning'

// OWON OEL Electronic Load component
// - Settings: Mode dropdown (like DMM) populated from /instruments/ELL/{device_id}
// - Readings: U/I/P displays (like PSU) with measurement checkboxes
export function OwonOELELL({ channelPath, registry }: { channelPath?: string, registry?: any }) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const { registerSource } = useMeasurement()

  // Parse class, device id, and channel from channelPath
  const { klass, deviceId, channel } = useMemo(() => parsePath(channelPath), [channelPath])

  const [modes, setModes] = useState<Record<string, any>>({})
  const [mode, setMode] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [inputEnabled, setInputEnabled] = useState(false)
  const [busyInput, setBusyInput] = useState(false)
  const [remoteMode, setRemoteMode] = useState(false)
  const [busyRemote, setBusyRemote] = useState(false)
  const [setpointValue, setSetpointValue] = useState<string>('')
  const [busySetpoint, setBusySetpoint] = useState(false)
  const [voltage, setVoltage] = useState<number | null>(null)
  const [current, setCurrent] = useState<number | null>(null)
  const [power, setPower] = useState<number | null>(null)
  const [lockEnabled, setLockEnabled] = useState(false)
  const [compulsoryLock, setCompulsoryLock] = useState(false)

  // Function to fetch current setpoint value for a given mode
  const fetchSetpointValue = async (modeKey: string) => {
    if (!klass || !deviceId || !modeKey) return

    try {
      const ch = channel || '1'
      const modeKeyLower = modeKey.toLowerCase()
      // Use partial name - API will resolve to query_{mode}
      const url = `${apiBase}/instruments/${klass}/${deviceId}/${ch}/${modeKeyLower}`
      const resp = await fetch(url)
      if (!resp.ok) return

      // Response comes as JSON with "value" field
      const json = await resp.json()
      if (json && typeof json.value !== 'undefined') {
        const numVal = parseFloat(json.value)
        if (!isNaN(numVal)) {
          setSetpointValue(String(numVal))
        }
      }
    } catch (err) {
      console.debug(`Failed to fetch setpoint for mode ${modeKey}:`, err)
    }
  }

  // Monitor WebSocket registry for remote mode, input status, current mode, and readings
  useEffect(() => {
    if (!registry || !deviceId) return

    const deviceData = registry[deviceId]
    if (!deviceData) return

    // Check for remote mode, input state, mode, and readings in status_ch{channel}
    const statusKey = `status_ch${channel || '1'}`
    const status = deviceData.ELL?.[statusKey]

    if (status) {
      if (typeof status.REMOTE === 'string') {
        const isRemote = status.REMOTE === 'ON'
        setRemoteMode(isRemote)
      }

      if (typeof status.INPUT === 'string') {
        const isInputOn = status.INPUT === 'ON'
        setInputEnabled(isInputOn)
      }

      if (typeof status.MODE === 'string' && status.MODE !== mode) {
        const newMode = status.MODE
        setMode(newMode)
        // Fetch setpoint value when mode changes from WebSocket
        if (Object.keys(modes).length > 0 && modes[newMode]?.setpoint && !setpointValue) {
          fetchSetpointValue(newMode)
        }
      }

      // Update readings from registry
      if (typeof status.VOUT === 'number') {
        setVoltage(status.VOUT)
      }

      if (typeof status.IOUT === 'number') {
        setCurrent(status.IOUT)
      }

      if (typeof status.POUT === 'number') {
        setPower(status.POUT)
      }
    }
  }, [registry, deviceId, channel, mode, modes, setpointValue])

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

    registerSource({
      id: `${deviceId}-${channel}-I`,
      deviceId,
      channelPath,
      parameter: 'current',
      label: `${deviceId} Ch${channel} I`,
      unit: 'A'
    })

    registerSource({
      id: `${deviceId}-${channel}-P`,
      deviceId,
      channelPath,
      parameter: 'power',
      label: `${deviceId} Ch${channel} P`,
      unit: 'W'
    })
  }, [channelPath, deviceId, channel, registerSource])

  // Fetch modes and lock settings from API
  useEffect(() => {
    let cancelled = false
    async function loadFeatures() {
      if (!deviceId || !klass) return
      const url = `${apiBase}/instruments/${klass}/${deviceId}`
      try {
        const r = await fetch(url, { cache: 'no-store' })
        if (!r.ok) return
        const j = await r.json().catch(() => ({} as any))
        if (!cancelled) {
          // modes is an object with mode data
          if (j?.modes && typeof j.modes === 'object') {
            setModes(j.modes)
            // Set initial mode if not already set
            if (!mode && Object.keys(j.modes).length > 0) {
              setMode(Object.keys(j.modes)[0])
            }
          }
          // Load lock settings from manifest
          if (typeof j?.lock === 'boolean') {
            setLockEnabled(j.lock)
          }
          if (typeof j?.compulsory_lock === 'boolean') {
            setCompulsoryLock(j.compulsory_lock)
          }
        }
      } catch {}
    }
    loadFeatures()
    return () => { cancelled = true }
  }, [apiBase, deviceId, klass, channelPath, mode])

  const endpointTemplate = useMemo(() => {
    const k = klass || 'ELL'
    const did = deviceId || '{id}'
    const ch = channel || '1'
    return `/instruments/${k}/${did}/${ch}/set_mode/{value}`
  }, [klass, deviceId, channel])

  const handleModeChange = async (newMode: string) => {
    setMode(newMode)
    setSetpointValue('') // Clear setpoint when mode changes
    if (!klass || !deviceId || busy) return
    setBusy(true)
    try {
      const ch = channel || '1'
      // Use partial name - API will resolve to set_mode
      await fetch(`${apiBase}/instruments/${klass}/${deviceId}/${ch}/mode/${encodeURIComponent(newMode)}`, { method: 'POST' })

      // After mode change, fetch the current setpoint value for this mode
      // Only fetch if the new mode has a setpoint definition (not DYN)
      if (modes[newMode]?.setpoint) {
        setTimeout(() => fetchSetpointValue(newMode), 500) // Small delay to let device update
      }
    } catch (err) {
      console.debug('Mode change failed', err)
    } finally {
      setBusy(false)
    }
  }

  const handleInputToggle = async () => {
    if (!klass || !deviceId || busyInput) return
    setBusyInput(true)
    try {
      const ch = channel || '1'
      const next = !inputEnabled
      const cmd = next ? 'ON' : 'OFF'
      // Use partial name - API will resolve to set_input
      await fetch(`${apiBase}/instruments/${klass}/${deviceId}/${ch}/input/${cmd}`, { method: 'POST' })
      // Don't optimistically set state - wait for WebSocket update
    } catch (err) {
      console.debug('Input toggle failed', err)
    } finally {
      setBusyInput(false)
    }
  }

  const handleRemoteToggle = async () => {
    if (!klass || !deviceId || busyRemote) return
    setBusyRemote(true)
    try {
      const ch = channel || '1'
      const next = !remoteMode
      const cmd = next ? 'ON' : 'OFF'
      // Use partial name - API will resolve to set_remote
      await fetch(`${apiBase}/instruments/${klass}/${deviceId}/${ch}/remote/${cmd}`, { method: 'POST' })
      // Don't optimistically set state - wait for WebSocket update
    } catch (err) {
      console.debug('Remote toggle failed', err)
    } finally {
      setBusyRemote(false)
    }
  }

  const handleSetpointSet = async () => {
    if (!klass || !deviceId || busySetpoint || !setpointValue || !mode) return

    const numVal = parseFloat(setpointValue)
    if (isNaN(numVal)) return

    // Validate against min/max
    const setpoint = modes[mode]?.setpoint
    if (!setpoint) return
    if (numVal < setpoint.min || numVal > setpoint.max) return

    setBusySetpoint(true)
    try {
      const ch = channel || '1'
      // Convert mode to lowercase (CURR -> curr, VOLT -> volt, RES -> res, POW -> pow)
      // Use partial name - API will resolve to set_{mode}
      const modeKey = mode.toLowerCase()
      await fetch(`${apiBase}/instruments/${klass}/${deviceId}/${ch}/${modeKey}/${numVal}`, { method: 'POST' })
    } catch (err) {
      console.debug('Setpoint set failed', err)
    } finally {
      setBusySetpoint(false)
    }
  }

  // Determine if controls should be shown based on lock settings
  const shouldShowControls = !lockEnabled || !compulsoryLock || remoteMode
  const shouldShowWarning = lockEnabled && compulsoryLock && !remoteMode

  return (
    <div className="psu-face">
      <div className="psu-main">
        <div className="psu-section" style={{ width: '100%' }}>
          <div className="psu-section-title">Settings</div>

          {/* Remote Mode Toggle - visible only when lock is enabled */}
          {lockEnabled && (
            <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr', width: '100%', marginBottom: '12px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: busyRemote ? 'wait' : 'pointer',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: remoteMode ? 'var(--good)' : 'var(--text-2)',
                  gap: '8px',
                  opacity: busyRemote ? 0.5 : 1
                }}
                title={`POST ${apiBase}/instruments/${klass || 'ELL'}/${deviceId || '{id}'}/${channel || '1'}/set_remote/${remoteMode ? 'OFF' : 'ON'}`}
              >
                <input
                  type="checkbox"
                  checked={remoteMode}
                  onChange={handleRemoteToggle}
                  disabled={busyRemote}
                  style={{
                    width: '16px',
                    height: '16px',
                    cursor: busyRemote ? 'wait' : 'pointer',
                    accentColor: 'var(--good)'
                  }}
                />
                <span>Enable Remote Mode</span>
                {busyRemote && <span className="spinner" style={{ marginLeft: '4px' }} />}
              </label>
            </div>
          )}

          {/* Mode and Input controls - visibility depends on lock settings */}
          {shouldShowControls && (
            <>
              <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto auto', width: '100%' }}>
                <div className="psu-label">
                  <span className="psu-symbol">Mode</span>
                </div>
                <CustomDropdown
                  modes={modes}
                  value={mode}
                  onChange={handleModeChange}
                  disabled={busy || Object.keys(modes).length === 0}
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
                <span className="psu-api" title={`GET /instruments/${klass || 'ELL'}/${deviceId || '{id}'}`}>API</span>
              </div>

              {/* Setpoint input - only show if current mode has a setpoint definition */}
              {mode && modes[mode]?.setpoint && (
                <div style={{ marginTop: '12px', width: '100%' }}>
                  <div className="psu-block" style={{ gridTemplateColumns: 'auto 0.5fr auto auto', width: '100%' }}>
                    <div className="psu-label">
                      <span className="psu-symbol">{modes[mode].setpoint.symbol}</span>
                      <span className="psu-unit">[{modes[mode].setpoint.unit}]</span>
                    </div>
                    <input
                      type="text"
                      className="psu-number editable"
                      value={setpointValue}
                      onChange={(e) => {
                        const val = e.target.value
                        // Only allow numbers and decimal point
                        if (/^[0-9]*\.?[0-9]*$/.test(val)) {
                          setSetpointValue(val)
                        }
                      }}
                      onBlur={() => {
                        // Validate against min/max
                        const numVal = parseFloat(setpointValue)
                        if (!isNaN(numVal)) {
                          const { min, max } = modes[mode].setpoint
                          if (numVal < min) setSetpointValue(String(min))
                          else if (numVal > max) setSetpointValue(String(max))
                        }
                      }}
                      title={`Min: ${modes[mode].setpoint.min}, Max: ${modes[mode].setpoint.max}`}
                      style={{
                        width: '100%',
                        padding: '4px 8px',
                        background: 'rgba(255,255,255,.03)',
                        border: '1px solid rgba(255,255,255,.25)',
                        borderRadius: '4px',
                        color: '#c26a1a',
                        fontVariantNumeric: 'tabular-nums',
                        fontWeight: 700,
                        fontSize: '16px'
                      }}
                    />
                    <button
                      className="psu-set"
                      type="button"
                      disabled={busySetpoint || !setpointValue}
                      title={`POST ${apiBase}/instruments/${klass || 'ELL'}/${deviceId || '{id}'}/${channel || '1'}/set_${mode.toLowerCase()}/${setpointValue}`}
                      onClick={handleSetpointSet}
                    >
                      {busySetpoint ? (<><span className="spinner"/>SET</>) : 'SET'}
                    </button>
                    <span className="psu-api" title={`POST /instruments/${klass || 'ELL'}/${deviceId || '{id}'}/${channel || '1'}/set_${mode.toLowerCase()}/{value}`}>API</span>
                  </div>
                  <div style={{
                    fontSize: '11px',
                    color: 'var(--text-2)',
                    marginTop: '4px',
                    marginLeft: '100px'
                  }}>
                    Range: {modes[mode].setpoint.min} - {modes[mode].setpoint.max} {modes[mode].setpoint.unit}
                  </div>
                </div>
              )}

              <div className="psu-actions" style={{ marginTop: '12px' }}>
                <button
                  className={`psu-set psu-output ${inputEnabled ? 'danger' : ''}`}
                  style={{ width: '100%', padding: '8px 12px', fontSize: '12px' }}
                  onClick={handleInputToggle}
                  title={`POST ${apiBase}/instruments/${klass || 'ELL'}/${deviceId || '{id}'}/${channel || '1'}/set_input/${inputEnabled ? 'OFF' : 'ON'}`}
                >
                  {busyInput ? (<><span className="spinner"/>{inputEnabled ? 'DISABLE INPUT' : 'ENABLE INPUT'}</>) : (inputEnabled ? 'DISABLE INPUT' : 'ENABLE INPUT')}
                </button>
              </div>
            </>
          )}

          {/* Warning when compulsory lock is enabled and in local mode */}
          {shouldShowWarning && <RemoteLockWarning />}
        </div>
        <div className="psu-section">
          <div className="psu-section-title">Readings</div>
          <ReadonlyBigNumber kind="U" label={<Label symbol="U" unit="V"/>} value={voltage !== null ? voltage.toFixed(4) : "—"} channelPath={channelPath} parameter="voltage" />
          <ReadonlyBigNumber kind="I" label={<Label symbol="I" unit="A"/>} value={current !== null ? current.toFixed(4) : "—"} channelPath={channelPath} parameter="current" />
          <ReadonlyBigNumber kind="P" label={<Label symbol="P" unit="W"/>} value={power !== null ? power.toFixed(4) : "—"} channelPath={channelPath} parameter="power" />
        </div>
        <hr className="sep"/>
      </div>
    </div>
  )
}

function CustomDropdown({
  modes,
  value,
  onChange,
  disabled,
  title
}: {
  modes: Record<string, any>
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

  const handleSelect = (modeKey: string) => {
    onChange(modeKey)
    setIsOpen(false)
  }

  const modeKeys = Object.keys(modes)
  const displayText = value && modes[value]?.ui_name ? modes[value].ui_name : value

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
          {displayText || (modeKeys.length === 0 ? 'No modes' : 'Select...')}
        </span>
        <span style={{
          fontSize: '12px',
          color: 'rgba(255,255,255,.5)',
          marginLeft: '8px'
        }}>
          {isOpen ? '▲' : '▼'}
        </span>
      </button>
      {isOpen && modeKeys.length > 0 && (
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
          {modeKeys.map((modeKey) => {
            const modeData = modes[modeKey]
            const displayName = modeData?.ui_name || modeKey
            return (
              <div
                key={modeKey}
                onClick={() => handleSelect(modeKey)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: modeKey === value ? 'rgba(96,165,250,.15)' : 'transparent',
                  color: modeKey === value ? '#bcd9ff' : '#b7c0d1',
                  fontSize: '14px',
                  fontWeight: modeKey === value ? 600 : 400,
                  borderBottom: '1px solid rgba(255,255,255,.05)',
                  transition: 'background .15s ease'
                }}
                onMouseEnter={(e) => {
                  if (modeKey !== value) {
                    e.currentTarget.style.background = 'rgba(255,255,255,.05)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (modeKey !== value) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                {displayName}
              </div>
            )
          })}
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
            kind === 'U' ? `GET ${channelPath}/query_output_voltage` :
            kind === 'I' ? `GET ${channelPath}/query_output_current` :
            kind === 'P' ? `GET ${channelPath}/query_output_power` : ''
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

export default OwonOELELL

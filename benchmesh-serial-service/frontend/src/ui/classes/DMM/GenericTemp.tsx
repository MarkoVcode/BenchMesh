import React, { useState, useEffect } from 'react'

interface TempOption {
  value?: string
  display: string
  unit?: string
  symbol?: string
}

interface TempConfig {
  Sensor?: TempOption[]
  Scale?: TempOption[]
}

interface GenericTempProps {
  mode: string
  channelPath?: string
  tempConfig?: TempConfig
  klass?: string
  deviceId?: string
  channel?: string
}

export function GenericTemp({ mode, channelPath, tempConfig, klass, deviceId, channel }: GenericTempProps) {
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`
  const [selectedSensor, setSelectedSensor] = useState<string>('')
  const [selectedScale, setSelectedScale] = useState<string>('')
  const [busySensor, setBusySensor] = useState(false)
  const [busyScale, setBusyScale] = useState(false)

  // Initialize defaults
  useEffect(() => {
    if (tempConfig?.Sensor && tempConfig.Sensor.length > 0 && !selectedSensor) {
      setSelectedSensor(tempConfig.Sensor[0].value || tempConfig.Sensor[0].display)
    }
    if (tempConfig?.Scale && tempConfig.Scale.length > 0 && !selectedScale) {
      setSelectedScale(tempConfig.Scale[0].symbol || tempConfig.Scale[0].display)
    }
  }, [tempConfig])

  const handleSensorChange = async (newSensor: string) => {
    setSelectedSensor(newSensor)

    if (!klass || !deviceId || !channelPath) return

    setBusySensor(true)
    try {
      const ch = channel || '1'
      const endpoint = `${apiBase}/instruments/${klass}/${deviceId}/${ch}/set_temp_sensor/${encodeURIComponent(newSensor)}`
      await fetch(endpoint, { method: 'POST' })
    } catch (err) {
      console.debug('Sensor change failed', err)
    } finally {
      setBusySensor(false)
    }
  }

  const handleScaleChange = async (newScale: string) => {
    setSelectedScale(newScale)

    if (!klass || !deviceId || !channelPath) return

    setBusyScale(true)
    try {
      const ch = channel || '1'
      const endpoint = `${apiBase}/instruments/${klass}/${deviceId}/${ch}/set_temp_scale/${encodeURIComponent(newScale)}`
      await fetch(endpoint, { method: 'POST' })
    } catch (err) {
      console.debug('Scale change failed', err)
    } finally {
      setBusyScale(false)
    }
  }

  if (!tempConfig || (!tempConfig.Sensor && !tempConfig.Scale)) {
    return null
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {tempConfig.Sensor && tempConfig.Sensor.length > 0 && (
        <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto', width: '100%' }}>
          <div className="psu-label">
            <span className="psu-symbol">Sensor</span>
          </div>
          <select
            value={selectedSensor}
            onChange={(e) => handleSensorChange(e.target.value)}
            disabled={busySensor}
            style={{
              padding: '4px 8px',
              background: 'var(--bg-2)',
              color: 'var(--text-0)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '12px',
              cursor: busySensor ? 'not-allowed' : 'pointer',
              opacity: busySensor ? 0.5 : 1
            }}
          >
            {tempConfig.Sensor.map((opt) => (
              <option key={opt.value || opt.display} value={opt.value || opt.display}>
                {opt.display}
              </option>
            ))}
          </select>
          <span className="psu-api" title={`POST /instruments/${klass || 'DMM'}/${deviceId || '{id}'}/${channel || '1'}/set_temp_sensor/{value}`}>API</span>
        </div>
      )}

      {tempConfig.Scale && tempConfig.Scale.length > 0 && (
        <div className="psu-block" style={{ gridTemplateColumns: 'auto 1fr auto', width: '100%' }}>
          <div className="psu-label">
            <span className="psu-symbol">Scale</span>
          </div>
          <select
            value={selectedScale}
            onChange={(e) => handleScaleChange(e.target.value)}
            disabled={busyScale}
            style={{
              padding: '4px 8px',
              background: 'var(--bg-2)',
              color: 'var(--text-0)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              fontSize: '12px',
              cursor: busyScale ? 'not-allowed' : 'pointer',
              opacity: busyScale ? 0.5 : 1
            }}
          >
            {tempConfig.Scale.map((opt) => (
              <option key={opt.symbol || opt.display} value={opt.symbol || opt.display}>
                {opt.display} ({opt.unit})
              </option>
            ))}
          </select>
          <span className="psu-api" title={`POST /instruments/${klass || 'DMM'}/${deviceId || '{id}'}/${channel || '1'}/set_temp_scale/{value}`}>API</span>
        </div>
      )}
    </div>
  )
}

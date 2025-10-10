import React, { useEffect, useState } from 'react'

interface Device {
  id: string
  name: string
  driver: string
  port: string
  baud: number
  serial: string
  model: string
}

interface DriverInfo {
  vendor: string
  family: string
}

interface ConfigModalProps {
  isOpen: boolean
  onClose: () => void
  apiBase: string
  onConfigUpdated: () => void
}

// Cache for drivers list - never changes during runtime
let driversCache: Record<string, DriverInfo> | null = null
// Cache for models per driver - never changes during runtime
let modelsCache: Record<string, string[]> = {}

export function ConfigModal({ isOpen, onClose, apiBase, onConfigUpdated }: ConfigModalProps) {
  const [devices, setDevices] = useState<Device[]>([])
  const [drivers, setDrivers] = useState<Record<string, DriverInfo>>({})
  const [driverModels, setDriverModels] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadConfig()
      loadDrivers()
    }
  }, [isOpen, apiBase])

  async function loadDrivers() {
    // Use cache if available
    if (driversCache) {
      setDrivers(driversCache)
      // Also preload models for all drivers
      await preloadAllModels(Object.keys(driversCache))
      return
    }

    try {
      const resp = await fetch(`${apiBase}/drivers`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      driversCache = data
      setDrivers(data)
      // Preload models for all drivers
      await preloadAllModels(Object.keys(data))
    } catch (e: any) {
      console.error('Failed to load drivers:', e)
      // Non-fatal - user can still type driver name manually
    }
  }

  async function preloadAllModels(driverIds: string[]) {
    // Load models for all drivers in parallel
    const promises = driverIds.map(driverId => loadModelsForDriver(driverId))
    await Promise.all(promises)
  }

  async function loadModelsForDriver(driverId: string) {
    // Check cache first
    if (modelsCache[driverId]) {
      setDriverModels(prev => ({ ...prev, [driverId]: modelsCache[driverId] }))
      return
    }

    try {
      const resp = await fetch(`${apiBase}/drivers/${driverId}`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const models = await resp.json()
      modelsCache[driverId] = models
      setDriverModels(prev => ({ ...prev, [driverId]: models }))
    } catch (e: any) {
      console.error(`Failed to load models for ${driverId}:`, e)
      // Non-fatal
    }
  }

  async function loadConfig() {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${apiBase}/config`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setDevices(data.devices || [])
    } catch (e: any) {
      setError(`Failed to load config: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function saveConfig() {
    setSaving(true)
    setError(null)
    setSaveSuccess(false)
    try {
      const resp = await fetch(`${apiBase}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ devices })
      })
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${resp.status}`)
      }
      setSaveSuccess(true)
      setTimeout(() => {
        onConfigUpdated()
        onClose()
      }, 1000)
    } catch (e: any) {
      setError(`Failed to save config: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  function addDevice() {
    setDevices([...devices, {
      id: `device-${Date.now()}`,
      name: 'New Device',
      driver: '',
      port: '/dev/ttyUSB0',
      baud: 115200,
      serial: '8N1',
      model: ''
    }])
  }

  function removeDevice(index: number) {
    setDevices(devices.filter((_, i) => i !== index))
  }

  function updateDevice(index: number, field: keyof Device, value: any) {
    const updated = [...devices]
    updated[index] = { ...updated[index], [field]: value }
    setDevices(updated)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Configuration</h2>
          <button className="modal-close" onClick={onClose} title="Close">✕</button>
        </div>

        <div className="modal-body">
          {loading && <p className="subtle">Loading configuration...</p>}
          {error && <div className="error-message">{error}</div>}
          {saveSuccess && <div className="success-message">✓ Configuration saved and applied!</div>}

          {!loading && (
            <>
              <div style={{ marginBottom: '16px', color: 'var(--text-2)', fontSize: '14px' }}>
                Configure your instruments below. Each device requires a unique ID, driver, and serial port.
                Changes will restart all instrument connections.
              </div>

              {devices.length === 0 && (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-2)' }}>
                  No devices configured. Click "Add Device" to get started.
                </div>
              )}

              {devices.map((device, index) => (
                <div key={index} className="device-form">
                  <div className="device-form-header">
                    <h3>Device {index + 1}</h3>
                    <button
                      className="btn-remove"
                      onClick={() => removeDevice(index)}
                      title="Remove this device"
                    >
                      Remove
                    </button>
                  </div>

                  {/* Row 1: ID and Name */}
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        ID<span className="required">*</span>
                        <span className="field-hint">Unique identifier (e.g., psu-1, dmm-1)</span>
                      </label>
                      <input
                        type="text"
                        value={device.id}
                        onChange={(e) => updateDevice(index, 'id', e.target.value)}
                        placeholder="device-id"
                      />
                    </div>

                    <div className="form-field">
                      <label>
                        Name<span className="required">*</span>
                        <span className="field-hint">Display name for this device</span>
                      </label>
                      <input
                        type="text"
                        value={device.name}
                        onChange={(e) => updateDevice(index, 'name', e.target.value)}
                        placeholder="My Device"
                      />
                    </div>
                  </div>

                  {/* Row 2: Port, Baud Rate, Data Bits/Parity/Stop */}
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        Port<span className="required">*</span>
                        <span className="field-hint">Serial port path</span>
                      </label>
                      <input
                        type="text"
                        value={device.port}
                        onChange={(e) => updateDevice(index, 'port', e.target.value)}
                        placeholder="/dev/ttyUSB0"
                      />
                    </div>

                    <div className="form-field">
                      <label>
                        Baud Rate<span className="required">*</span>
                        <span className="field-hint">Communication speed (bps)</span>
                      </label>
                      <select
                        value={device.baud}
                        onChange={(e) => updateDevice(index, 'baud', parseInt(e.target.value))}
                      >
                        <option value={9600}>9600</option>
                        <option value={19200}>19200</option>
                        <option value={38400}>38400</option>
                        <option value={57600}>57600</option>
                        <option value={115200}>115200</option>
                      </select>
                    </div>

                    <div className="form-field">
                      <label>
                        Data Bits/Parity/Stop<span className="required">*</span>
                        <span className="field-hint">Serial port configuration</span>
                      </label>
                      <select
                        value={device.serial}
                        onChange={(e) => updateDevice(index, 'serial', e.target.value)}
                      >
                        <option value="8N1">8N1 (8 bits, no parity, 1 stop)</option>
                        <option value="8N2">8N2 (8 bits, no parity, 2 stop)</option>
                        <option value="8E1">8E1 (8 bits, even parity, 1 stop)</option>
                        <option value="8O1">8O1 (8 bits, odd parity, 1 stop)</option>
                        <option value="7E1">7E1 (7 bits, even parity, 1 stop)</option>
                        <option value="7O1">7O1 (7 bits, odd parity, 1 stop)</option>
                      </select>
                    </div>
                  </div>

                  {/* Row 3: Driver and Model */}
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        Driver<span className="required">*</span>
                        <span className="field-hint">Driver module</span>
                      </label>
                      <select
                        value={device.driver}
                        onChange={(e) => updateDevice(index, 'driver', e.target.value)}
                      >
                        <option value="">Select driver...</option>
                        {Object.keys(drivers).sort().map((driverId) => (
                          <option key={driverId} value={driverId}>
                            {drivers[driverId].vendor} {drivers[driverId].family} ({driverId})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="form-field">
                      <label>
                        Model<span className="required">*</span>
                        <span className="field-hint">Device model number</span>
                      </label>
                      {device.driver && driverModels[device.driver] && driverModels[device.driver].length > 0 ? (
                        <select
                          value={device.model}
                          onChange={(e) => updateDevice(index, 'model', e.target.value)}
                        >
                          <option value="">Select model...</option>
                          {driverModels[device.driver].map((model) => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={device.model}
                          onChange={(e) => updateDevice(index, 'model', e.target.value)}
                          placeholder="SPM3103"
                        />
                      )}
                    </div>
                  </div>
                </div>
              ))}

              <button className="btn-add" onClick={addDevice}>
                + Add Device
              </button>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={saveConfig}
            disabled={saving || loading || devices.length === 0}
          >
            {saving ? 'Saving...' : 'Save & Apply'}
          </button>
        </div>
      </div>
    </div>
  )
}

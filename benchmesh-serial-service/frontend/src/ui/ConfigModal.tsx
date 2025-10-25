import React, { useEffect, useState } from 'react'

interface Device {
  id: string
  name: string
  driver: string
  transport?: string  // 'serial' (default) | 'usbtmc' | 'tcpip'
  // Serial transport fields
  port?: string
  baud?: number
  serial?: string
  // USB TMC transport fields
  device?: string
  // TCP/IP transport fields (future)
  host?: string
  model: string
}

interface DriverInfo {
  vendor: string
  family: string
  supported_transports: string[]
}

interface SerialPortInfo {
  device: string
  description: string
  manufacturer: string | null
  serial_number: string | null
  hwid: string | null
}

interface UsbTmcDeviceInfo {
  device: string
  name: string
  vendor_id?: string
  product_id?: string
  manufacturer?: string
  product?: string
  serial?: string
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
  const [availablePorts, setAvailablePorts] = useState<SerialPortInfo[]>([])
  const [availableUsbTmcDevices, setAvailableUsbTmcDevices] = useState<UsbTmcDeviceInfo[]>([])
  const [loadingPorts, setLoadingPorts] = useState(false)
  const [loadingUsbTmc, setLoadingUsbTmc] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadConfig()
      loadDrivers()
      loadSerialPorts()
      loadUsbTmcDevices()
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

  async function loadSerialPorts() {
    setLoadingPorts(true)
    try {
      // Get list of currently used ports to exclude
      const usedPorts = devices.map(d => d.port).filter(p => p).join(',')
      const url = usedPorts
        ? `${apiBase}/serial-ports?exclude=${encodeURIComponent(usedPorts)}`
        : `${apiBase}/serial-ports`

      const resp = await fetch(url)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const ports = await resp.json()
      setAvailablePorts(ports)
    } catch (e: any) {
      console.error('Failed to load serial ports:', e)
      // Non-fatal - user can still enter port manually
      setAvailablePorts([])
    } finally {
      setLoadingPorts(false)
    }
  }

  async function loadUsbTmcDevices() {
    setLoadingUsbTmc(true)
    try {
      // Get list of currently used USB TMC devices to exclude
      const usedDevices = devices.map(d => d.device).filter(d => d).join(',')
      const url = usedDevices
        ? `${apiBase}/usbtmc-devices?exclude=${encodeURIComponent(usedDevices)}`
        : `${apiBase}/usbtmc-devices`

      const resp = await fetch(url)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const tmcDevices = await resp.json()
      setAvailableUsbTmcDevices(tmcDevices)
    } catch (e: any) {
      console.error('Failed to load USB TMC devices:', e)
      // Non-fatal - user can still enter device path manually
      setAvailableUsbTmcDevices([])
    } finally {
      setLoadingUsbTmc(false)
    }
  }

  function getAvailablePortsForDevice(deviceIndex: number): SerialPortInfo[] {
    // Get all ports currently used by OTHER devices
    const otherDevicePorts = devices
      .filter((_, i) => i !== deviceIndex)
      .map(d => d.port)
      .filter(p => p)

    // Filter available ports to exclude those used by other devices
    const filtered = availablePorts.filter(port => !otherDevicePorts.includes(port.device))

    // If current device has a port that's not in available list, add it
    const currentPort = devices[deviceIndex]?.port
    if (currentPort && !filtered.find(p => p.device === currentPort)) {
      // Try to find it in original available ports (might have been filtered)
      const originalPort = availablePorts.find(p => p.device === currentPort)
      if (originalPort) {
        filtered.push(originalPort)
      }
    }

    return filtered
  }

  function getAvailableUsbTmcDevicesForDevice(deviceIndex: number): UsbTmcDeviceInfo[] {
    // Get all USB TMC devices currently used by OTHER devices
    const otherDeviceDevices = devices
      .filter((_, i) => i !== deviceIndex)
      .map(d => d.device)
      .filter(d => d)

    // Filter available USB TMC devices to exclude those used by other devices
    const filtered = availableUsbTmcDevices.filter(dev => !otherDeviceDevices.includes(dev.device))

    // If current device has a USB TMC device that's not in available list, add it
    const currentDevice = devices[deviceIndex]?.device
    if (currentDevice && !filtered.find(d => d.device === currentDevice)) {
      // Try to find it in original available devices (might have been filtered)
      const originalDevice = availableUsbTmcDevices.find(d => d.device === currentDevice)
      if (originalDevice) {
        filtered.push(originalDevice)
      }
    }

    return filtered
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
      id: `instrument-${Date.now()}`,
      name: 'New Instrument',
      driver: '',
      transport: 'serial',  // Default to serial transport
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

  function sanitizeDeviceId(value: string): string {
    // Only allow lowercase letters, digits, and hyphens
    // Max 20 characters
    return value
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '')
      .slice(0, 20)
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
                Configure your instruments below. Each instrument requires a unique ID, driver, and serial port.
                Changes will restart all instrument connections.
              </div>

              {devices.length === 0 && (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-2)' }}>
                  No instruments configured. Click "Add Instrument" to get started.
                </div>
              )}

              {devices.map((device, index) => (
                <div key={index} className="device-form">
                  <div className="device-form-header">
                    <h3>Instrument {index + 1}</h3>
                    <button
                      className="btn-remove"
                      onClick={() => removeDevice(index)}
                      title="Remove this instrument"
                    >
                      Remove
                    </button>
                  </div>

                  {/* Row 1: ID and Name */}
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        ID<span className="required">*</span>
                        <span className="field-hint">Only lowercase letters, digits, and "-" allowed (max 20 chars)</span>
                      </label>
                      <input
                        type="text"
                        value={device.id}
                        onChange={(e) => updateDevice(index, 'id', sanitizeDeviceId(e.target.value))}
                        placeholder="psu-1"
                        maxLength={20}
                      />
                    </div>

                    <div className="form-field">
                      <label>
                        Name<span className="required">*</span>
                        <span className="field-hint">Display name for this instrument</span>
                      </label>
                      <input
                        type="text"
                        value={device.name}
                        onChange={(e) => updateDevice(index, 'name', e.target.value)}
                        placeholder="My Instrument"
                      />
                    </div>
                  </div>

                  {/* Row 2: Transport Type */}
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        Transport<span className="required">*</span>
                        <span className="field-hint">Communication interface type</span>
                      </label>
                      <select
                        value={device.transport || 'serial'}
                        onChange={(e) => {
                          const newTransport = e.target.value
                          updateDevice(index, 'transport', newTransport)
                          // Clear transport-specific fields when switching
                          if (newTransport === 'serial') {
                            updateDevice(index, 'device', undefined)
                            if (!device.port) updateDevice(index, 'port', '/dev/ttyUSB0')
                            if (!device.baud) updateDevice(index, 'baud', 115200)
                            if (!device.serial) updateDevice(index, 'serial', '8N1')
                          } else if (newTransport === 'usbtmc') {
                            updateDevice(index, 'port', undefined)
                            updateDevice(index, 'baud', undefined)
                            updateDevice(index, 'serial', undefined)
                            if (!device.device) updateDevice(index, 'device', '/dev/usbtmc0')
                          }
                        }}
                      >
                        <option value="serial">Serial (RS232/USB-Serial)</option>
                        <option value="usbtmc">USB TMC (Test & Measurement Class)</option>
                      </select>
                    </div>
                  </div>

                  {/* Row 3: Serial Transport Fields - Port, Baud Rate, Data Bits/Parity/Stop */}
                  {(device.transport || 'serial') === 'serial' && (
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        Port<span className="required">*</span>
                        <span className="field-hint">Serial port path</span>
                      </label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <select
                          style={{ flex: 1 }}
                          value={device.port}
                          onChange={(e) => {
                            const value = e.target.value
                            if (value === '__custom__') {
                              // Switch to manual entry
                              updateDevice(index, 'port', '')
                            } else {
                              updateDevice(index, 'port', value)
                            }
                          }}
                        >
                          {device.port && !getAvailablePortsForDevice(index).find(p => p.device === device.port) && (
                            <option value={device.port}>{device.port} (current)</option>
                          )}
                          {getAvailablePortsForDevice(index).map((port) => (
                            <option key={port.device} value={port.device}>
                              {port.device} - {port.description}
                              {port.manufacturer ? ` (${port.manufacturer})` : ''}
                            </option>
                          ))}
                          <option value="__custom__">Manual entry...</option>
                        </select>
                        <button
                          type="button"
                          onClick={loadSerialPorts}
                          disabled={loadingPorts}
                          style={{
                            padding: '8px 12px',
                            background: 'var(--bg-2)',
                            border: '1px solid var(--border)',
                            borderRadius: '4px',
                            cursor: loadingPorts ? 'wait' : 'pointer',
                            color: 'var(--text-1)',
                            fontSize: '14px'
                          }}
                          title="Refresh serial ports"
                        >
                          {loadingPorts ? '↻' : '⟳'}
                        </button>
                      </div>
                      {device.port === '' && (
                        <input
                          type="text"
                          value={device.port}
                          onChange={(e) => updateDevice(index, 'port', e.target.value)}
                          placeholder="/dev/ttyUSB0 or COM3"
                          style={{ marginTop: '8px' }}
                        />
                      )}
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
                  )}

                  {/* Row 4: USB TMC Transport Fields - Device */}
                  {(device.transport || 'serial') === 'usbtmc' && (
                  <div className="form-grid">
                    <div className="form-field">
                      <label>
                        USB TMC Device<span className="required">*</span>
                        <span className="field-hint">USB TMC device path</span>
                      </label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <select
                          style={{ flex: 1 }}
                          value={device.device || ''}
                          onChange={(e) => {
                            const value = e.target.value
                            if (value === '__custom__') {
                              // Switch to manual entry
                              updateDevice(index, 'device', '')
                            } else {
                              updateDevice(index, 'device', value)
                            }
                          }}
                        >
                          {device.device && !getAvailableUsbTmcDevicesForDevice(index).find(d => d.device === device.device) && (
                            <option value={device.device}>{device.device} (current)</option>
                          )}
                          {getAvailableUsbTmcDevicesForDevice(index).map((dev) => (
                            <option key={dev.device} value={dev.device}>
                              {dev.device} - {dev.product || 'USB TMC Device'}
                              {dev.manufacturer ? ` (${dev.manufacturer})` : ''}
                            </option>
                          ))}
                          <option value="__custom__">Manual entry...</option>
                        </select>
                        <button
                          type="button"
                          onClick={loadUsbTmcDevices}
                          disabled={loadingUsbTmc}
                          style={{
                            padding: '8px 12px',
                            background: 'var(--bg-2)',
                            border: '1px solid var(--border)',
                            borderRadius: '4px',
                            cursor: loadingUsbTmc ? 'wait' : 'pointer',
                            color: 'var(--text-1)',
                            fontSize: '14px'
                          }}
                          title="Refresh USB TMC devices"
                        >
                          {loadingUsbTmc ? '↻' : '⟳'}
                        </button>
                      </div>
                      {device.device === '' && (
                        <input
                          type="text"
                          value={device.device || ''}
                          onChange={(e) => updateDevice(index, 'device', e.target.value)}
                          placeholder="/dev/usbtmc0 or /dev/tmcDGE2070"
                          style={{ marginTop: '8px' }}
                        />
                      )}
                    </div>
                  </div>
                  )}

                  {/* Row 5: Driver and Model */}
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
                        {drivers && Object.keys(drivers)
                          .filter(driverId => {
                            // Filter drivers by supported transports
                            const selectedTransport = device.transport || 'serial'
                            const supportedTransports = drivers[driverId].supported_transports || ['serial']
                            return supportedTransports.includes(selectedTransport)
                          })
                          .sort()
                          .map((driverId) => (
                            <option key={driverId} value={driverId}>
                              {drivers[driverId].vendor} {drivers[driverId].family} ({driverId})
                            </option>
                          ))}
                      </select>
                    </div>

                    <div className="form-field">
                      <label>
                        Model<span className="required">*</span>
                        <span className="field-hint">Instrument model number</span>
                      </label>
                      {device.driver && driverModels[device.driver] && driverModels[device.driver].length > 0 ? (
                        <select
                          value={device.model}
                          onChange={(e) => updateDevice(index, 'model', e.target.value)}
                        >
                          <option value="">Select model...</option>
                          {driverModels[device.driver]
                            .filter((model) => model !== 'DEFAULT')
                            .map((model) => (
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
                + Add Instrument
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

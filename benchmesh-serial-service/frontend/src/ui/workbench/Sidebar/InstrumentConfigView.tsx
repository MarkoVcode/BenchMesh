/**
 * InstrumentConfigView - Instrument configuration in Settings sidebar
 *
 * Features:
 * - Accordion layout for space-constrained sidebar
 * - Single-expand mode (one device open at a time)
 * - Transport-specific fields (Serial, USB TMC)
 * - Port/device scanning and smart filtering
 * - Per-device Save/Apply/Remove buttons with inline validation
 * - Hot-reload support (add/update/remove without service restart)
 */

import React, { useEffect, useState, useRef } from 'react';
import { Accordion, AccordionItem } from './Accordion';

interface Device {
  id: string;
  name: string;
  driver: string;
  transport?: string; // 'serial' (default) | 'usbtmc' | 'tcpip'
  // Serial transport fields
  port?: string;
  baud?: number;
  serial?: string;
  // USB TMC transport fields
  device?: string;
  // TCP/IP transport fields (future)
  host?: string;
  model: string;
  // Internal UUID for stable accordion tracking (not sent to backend)
  _uuid?: string;
}

interface DriverInfo {
  vendor: string;
  family: string;
  supported_transports: string[];
}

interface SerialPortInfo {
  device: string;
  description: string;
  manufacturer: string | null;
  serial_number: string | null;
  hwid: string | null;
}

interface UsbTmcDeviceInfo {
  device: string;
  name: string;
  vendor_id?: string;
  product_id?: string;
  manufacturer?: string;
  product?: string;
  serial?: string;
}

interface InstrumentConfigViewProps {
  apiBase: string;
  onConfigUpdated: () => void;
  autoAddNew?: boolean; // Auto-open the add instrument form
  onAutoAddComplete?: () => void; // Callback after auto-add is triggered
}

interface DeviceState {
  saving: boolean;
  error: string | null;
  success: boolean;
}

// Cache for drivers list - never changes during runtime
let driversCache: Record<string, DriverInfo> | null = null;
// Cache for models per driver - never changes during runtime
let modelsCache: Record<string, string[]> = {};

/**
 * Generate a deterministic UUID based on device ID.
 * This ensures the same device always gets the same UUID across page reloads,
 * which is critical for persistence of UI state (accordion expansion, etc.)
 */
function generateDeterministicUuid(deviceId: string): string {
  // Simple hash function to convert device ID to a stable UUID-like string
  let hash = 0;
  for (let i = 0; i < deviceId.length; i++) {
    const char = deviceId.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }

  // Convert hash to hex and pad to create UUID-like format
  const hashHex = Math.abs(hash).toString(16).padStart(8, '0');
  return `uuid-${hashHex}-${deviceId.replace(/[^a-zA-Z0-9]/g, '-')}`;
}

export function InstrumentConfigView({ apiBase, onConfigUpdated, autoAddNew, onAutoAddComplete }: InstrumentConfigViewProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [originalDevices, setOriginalDevices] = useState<Map<string, Device>>(new Map());
  const [deviceStates, setDeviceStates] = useState<Record<string, DeviceState>>({});
  const [drivers, setDrivers] = useState<Record<string, DriverInfo>>({});
  const [driverModels, setDriverModels] = useState<Record<string, string[]>>({});
  const [availablePorts, setAvailablePorts] = useState<SerialPortInfo[]>([]);
  const [availableUsbTmcDevices, setAvailableUsbTmcDevices] = useState<UsbTmcDeviceInfo[]>([]);
  const [loadingPorts, setLoadingPorts] = useState(false);
  const [loadingUsbTmc, setLoadingUsbTmc] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedDeviceUuid, setExpandedDeviceUuid] = useState<string | null>(null);

  // Track if auto-add was already triggered to prevent multiple executions
  const autoAddTriggeredRef = useRef(false);

  // Load initial data on mount
  useEffect(() => {
    loadConfig();
    loadDrivers();
    loadSerialPorts();
    loadUsbTmcDevices();
  }, [apiBase]);

  // Auto-add new instrument when requested (e.g., from "+" button)
  useEffect(() => {
    if (autoAddNew && !autoAddTriggeredRef.current) {
      // Check if there's not already a new unsaved device
      const hasNewDevice = devices.some(d => !originalDevices.has(d.id));
      if (!hasNewDevice) {
        addDevice();
        autoAddTriggeredRef.current = true;
      }
      // Notify parent that auto-add was triggered
      if (onAutoAddComplete) {
        onAutoAddComplete();
      }
    } else if (!autoAddNew) {
      // Reset the ref when flag is cleared so it can trigger again next time
      autoAddTriggeredRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoAddNew]); // Only trigger when autoAddNew changes, not on every device state change

  async function loadDrivers() {
    // Use cache if available
    if (driversCache) {
      setDrivers(driversCache);
      // Also preload models for all drivers
      await preloadAllModels(Object.keys(driversCache));
      return;
    }

    try {
      const resp = await fetch(`${apiBase}/drivers`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      driversCache = data;
      setDrivers(data);
      // Preload models for all drivers
      await preloadAllModels(Object.keys(data));
    } catch (e: any) {
      console.error('Failed to load drivers:', e);
      // Non-fatal - user can still type driver name manually
    }
  }

  async function preloadAllModels(driverIds: string[]) {
    // Load models for all drivers in parallel
    const promises = driverIds.map((driverId) => loadModelsForDriver(driverId));
    await Promise.all(promises);
  }

  async function loadModelsForDriver(driverId: string) {
    // Check cache first
    if (modelsCache[driverId]) {
      setDriverModels((prev) => ({ ...prev, [driverId]: modelsCache[driverId] }));
      return;
    }

    try {
      const resp = await fetch(`${apiBase}/drivers/${driverId}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const models = await resp.json();
      modelsCache[driverId] = models;
      setDriverModels((prev) => ({ ...prev, [driverId]: models }));
    } catch (e: any) {
      console.error(`Failed to load models for ${driverId}:`, e);
      // Non-fatal
    }
  }

  async function loadConfig() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${apiBase}/config`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const loadedDevices = (data.devices || []).map((device: Device) => ({
        ...device,
        // Generate deterministic UUID for stable accordion tracking across reloads
        _uuid: generateDeterministicUuid(device.id)
      }));
      setDevices(loadedDevices);

      // Track original devices for dirty detection
      const originals = new Map<string, Device>();
      loadedDevices.forEach((device: Device) => {
        originals.set(device.id, { ...device });
      });
      setOriginalDevices(originals);
    } catch (e: any) {
      setError(`Failed to load config: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadSerialPorts() {
    setLoadingPorts(true);
    try {
      // Get list of currently used ports to exclude
      const usedPorts = devices.map((d) => d.port).filter((p) => p).join(',');
      const url = usedPorts
        ? `${apiBase}/serial-ports?exclude=${encodeURIComponent(usedPorts)}`
        : `${apiBase}/serial-ports`;

      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const ports = await resp.json();
      setAvailablePorts(ports);
    } catch (e: any) {
      console.error('Failed to load serial ports:', e);
      // Non-fatal - user can still enter port manually
      setAvailablePorts([]);
    } finally {
      setLoadingPorts(false);
    }
  }

  async function loadUsbTmcDevices() {
    setLoadingUsbTmc(true);
    try {
      // Get list of currently used USB TMC devices to exclude
      const usedDevices = devices.map((d) => d.device).filter((d) => d).join(',');
      const url = usedDevices
        ? `${apiBase}/usbtmc-devices?exclude=${encodeURIComponent(usedDevices)}`
        : `${apiBase}/usbtmc-devices`;

      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const tmcDevices = await resp.json();
      setAvailableUsbTmcDevices(tmcDevices);
    } catch (e: any) {
      console.error('Failed to load USB TMC devices:', e);
      // Non-fatal - user can still enter device path manually
      setAvailableUsbTmcDevices([]);
    } finally {
      setLoadingUsbTmc(false);
    }
  }

  function getAvailablePortsForDevice(deviceIndex: number): SerialPortInfo[] {
    // Get all ports currently used by OTHER devices
    const otherDevicePorts = devices
      .filter((_, i) => i !== deviceIndex)
      .map((d) => d.port)
      .filter((p) => p);

    // Filter available ports to exclude those used by other devices
    const filtered = availablePorts.filter((port) => !otherDevicePorts.includes(port.device));

    // If current device has a port that's not in available list, add it
    const currentPort = devices[deviceIndex]?.port;
    if (currentPort && !filtered.find((p) => p.device === currentPort)) {
      // Try to find it in original available ports (might have been filtered)
      const originalPort = availablePorts.find((p) => p.device === currentPort);
      if (originalPort) {
        filtered.push(originalPort);
      }
    }

    return filtered;
  }

  function getAvailableUsbTmcDevicesForDevice(deviceIndex: number): UsbTmcDeviceInfo[] {
    // Get all USB TMC devices currently used by OTHER devices
    const otherDeviceDevices = devices
      .filter((_, i) => i !== deviceIndex)
      .map((d) => d.device)
      .filter((d) => d);

    // Filter available USB TMC devices to exclude those used by other devices
    const filtered = availableUsbTmcDevices.filter((dev) => !otherDeviceDevices.includes(dev.device));

    // If current device has a USB TMC device that's not in available list, add it
    const currentDevice = devices[deviceIndex]?.device;
    if (currentDevice && !filtered.find((d) => d.device === currentDevice)) {
      // Try to find it in original available devices (might have been filtered)
      const originalDevice = availableUsbTmcDevices.find((d) => d.device === currentDevice);
      if (originalDevice) {
        filtered.push(originalDevice);
      }
    }

    return filtered;
  }

  function sanitizeDeviceForSave(device: Device): any {
    // Ensure all required fields are present and remove internal _uuid
    const sanitized: any = {
      id: device.id || '',
      name: device.name || '',
      driver: device.driver || '',
      model: device.model || '',
      transport: device.transport || 'serial',
    };
    // Note: _uuid is intentionally omitted - it's for internal UI use only

    // Add transport-specific required fields
    if (sanitized.transport === 'serial') {
      sanitized.port = device.port || '';
      sanitized.baud = device.baud || 115200;
      sanitized.serial = device.serial || '8N1';
    } else if (sanitized.transport === 'usbtmc') {
      sanitized.device = device.device || '';
    }

    return sanitized;
  }

  function setDeviceState(deviceId: string, state: Partial<DeviceState>) {
    setDeviceStates((prev) => ({
      ...prev,
      [deviceId]: { ...prev[deviceId], ...state },
    }));
  }

  async function saveNewDevice(device: Device) {
    const deviceId = device.id;
    setDeviceState(deviceId, { saving: true, error: null, success: false });

    try {
      const sanitized = sanitizeDeviceForSave(device);
      const resp = await fetch(`${apiBase}/devices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sanitized),
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail));
      }

      // Update originalDevices to mark as existing
      setOriginalDevices((prev) => new Map(prev).set(deviceId, { ...sanitized }));

      setDeviceState(deviceId, { saving: false, error: null, success: true });
      setTimeout(() => {
        setDeviceState(deviceId, { saving: false, error: null, success: false });
        onConfigUpdated();
      }, 2000);
    } catch (e: any) {
      console.error('Failed to add device:', e);
      setDeviceState(deviceId, { saving: false, error: e.message, success: false });
    }
  }

  async function saveExistingDevice(device: Device) {
    const deviceId = device.id;
    setDeviceState(deviceId, { saving: true, error: null, success: false });

    try {
      const sanitized = sanitizeDeviceForSave(device);
      const resp = await fetch(`${apiBase}/devices/${deviceId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sanitized),
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail));
      }

      // Update originalDevices with new config
      setOriginalDevices((prev) => new Map(prev).set(deviceId, { ...sanitized }));

      setDeviceState(deviceId, { saving: false, error: null, success: true });
      setTimeout(() => {
        setDeviceState(deviceId, { saving: false, error: null, success: false });
        onConfigUpdated();
      }, 2000);
    } catch (e: any) {
      console.error('Failed to update device:', e);
      setDeviceState(deviceId, { saving: false, error: e.message, success: false });
    }
  }

  async function removeDeviceFromServer(deviceId: string) {
    setDeviceState(deviceId, { saving: true, error: null, success: false });

    try {
      const resp = await fetch(`${apiBase}/devices/${deviceId}`, {
        method: 'DELETE',
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail));
      }

      // Remove from UI and state
      setDevices((prev) => prev.filter((d) => d.id !== deviceId));
      setOriginalDevices((prev) => {
        const updated = new Map(prev);
        updated.delete(deviceId);
        return updated;
      });
      setDeviceStates((prev) => {
        const updated = { ...prev };
        delete updated[deviceId];
        return updated;
      });

      // Clear expanded state if we removed the expanded device
      const removedDevice = devices.find(d => d.id === deviceId);
      if (removedDevice && expandedDeviceUuid === removedDevice._uuid) {
        setExpandedDeviceUuid(null);
      }

      onConfigUpdated();
    } catch (e: any) {
      console.error('Failed to remove device:', e);
      setDeviceState(deviceId, { saving: false, error: e.message, success: false });
    }
  }

  function addDevice() {
    // Generate temporary ID for new device
    const newId = `new-instrument-${Date.now()}`;
    // Generate deterministic UUID based on the temp ID
    const uuid = generateDeterministicUuid(newId);
    const newDevice: Device = {
      id: newId,
      name: 'New Instrument',
      driver: '',
      transport: 'serial', // Default to serial transport
      port: '/dev/ttyUSB0',
      baud: 115200,
      serial: '8N1',
      model: '',
      _uuid: uuid,
    };
    setDevices([...devices, newDevice]);
    // Auto-expand the new device using stable UUID
    setExpandedDeviceUuid(uuid);
  }

  function removeDeviceLocally(index: number) {
    // Remove from local state only (for new devices that haven't been saved yet)
    const removedDeviceUuid = devices[index]._uuid;
    setDevices(devices.filter((_, i) => i !== index));
    // Clear expanded state if we removed the expanded device
    if (expandedDeviceUuid === removedDeviceUuid) {
      setExpandedDeviceUuid(null);
    }
  }

  function isDeviceNew(deviceId: string): boolean {
    return !originalDevices.has(deviceId);
  }

  function isDeviceModified(device: Device): boolean {
    const original = originalDevices.get(device.id);
    if (!original) return false; // New device
    return JSON.stringify(device) !== JSON.stringify(original);
  }

  function updateDevice(index: number, field: keyof Device, value: any) {
    const updated = [...devices];
    updated[index] = { ...updated[index], [field]: value };
    setDevices(updated);
  }

  function updateDeviceMultiple(index: number, updates: Partial<Device>) {
    const updated = [...devices];
    updated[index] = { ...updated[index], ...updates };
    setDevices(updated);
  }

  function sanitizeDeviceId(value: string): string {
    // Only allow lowercase letters, digits, and hyphens
    // Max 20 characters
    return value
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '')
      .slice(0, 20);
  }

  function handleAccordionToggle(deviceUuid: string) {
    setExpandedDeviceUuid(expandedDeviceUuid === deviceUuid ? null : deviceUuid);
  }

  function renderDeviceForm(device: Device, index: number) {
    return (
      <div className="instrument-config__form">
        {/* ID and Name */}
        <div className="instrument-config__field">
          <label>
            ID<span className="required">*</span>
          </label>
          <input
            type="text"
            value={device.id}
            onChange={(e) => updateDevice(index, 'id', sanitizeDeviceId(e.target.value))}
            placeholder="psu-1"
            maxLength={20}
          />
          <span className="instrument-config__hint">Lowercase letters, digits, and "-" only (max 20 chars)</span>
        </div>

        <div className="instrument-config__field">
          <label>
            Name<span className="required">*</span>
          </label>
          <input
            type="text"
            value={device.name}
            onChange={(e) => updateDevice(index, 'name', e.target.value)}
            placeholder="My Instrument"
          />
          <span className="instrument-config__hint">Display name</span>
        </div>

        {/* Transport Type */}
        <div className="instrument-config__field">
          <label>
            Transport<span className="required">*</span>
          </label>
          <select
            value={device.transport || 'serial'}
            onChange={(e) => {
              const newTransport = e.target.value;
              if (newTransport === 'serial') {
                updateDeviceMultiple(index, {
                  transport: newTransport,
                  device: undefined,
                  port: device.port || '/dev/ttyUSB0',
                  baud: device.baud || 115200,
                  serial: device.serial || '8N1',
                });
              } else if (newTransport === 'usbtmc') {
                updateDeviceMultiple(index, {
                  transport: newTransport,
                  port: undefined,
                  baud: undefined,
                  serial: undefined,
                  device: device.device || '/dev/usbtmc0',
                });
              }
            }}
          >
            <option value="serial">Serial (RS232/USB-Serial)</option>
            <option value="usbtmc">USB TMC (Test & Measurement)</option>
          </select>
          <span className="instrument-config__hint">Communication interface</span>
        </div>

        {/* Serial Transport Fields */}
        {(device.transport || 'serial') === 'serial' && (
          <>
            <div className="instrument-config__field">
              <label>
                Port<span className="required">*</span>
              </label>
              <div className="instrument-config__field-with-button">
                <select
                  value={device.port || ''}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === '__custom__') {
                      updateDevice(index, 'port', '');
                    } else {
                      updateDevice(index, 'port', value);
                    }
                  }}
                >
                  {device.port && !getAvailablePortsForDevice(index).find((p) => p.device === device.port) && (
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
                  className="instrument-config__refresh-btn"
                  onClick={loadSerialPorts}
                  disabled={loadingPorts}
                  title="Refresh serial ports"
                >
                  {loadingPorts ? '↻' : '⟳'}
                </button>
              </div>
              {device.port === '' && (
                <input
                  type="text"
                  value={device.port || ''}
                  onChange={(e) => updateDevice(index, 'port', e.target.value)}
                  placeholder="/dev/ttyUSB0 or COM3"
                  style={{ marginTop: '4px' }}
                />
              )}
              <span className="instrument-config__hint">Serial port path</span>
            </div>

            <div className="instrument-config__field">
              <label>
                Baud Rate<span className="required">*</span>
              </label>
              <select value={device.baud} onChange={(e) => updateDevice(index, 'baud', parseInt(e.target.value))}>
                <option value={9600}>9600</option>
                <option value={19200}>19200</option>
                <option value={38400}>38400</option>
                <option value={57600}>57600</option>
                <option value={115200}>115200</option>
              </select>
              <span className="instrument-config__hint">Communication speed (bps)</span>
            </div>

            <div className="instrument-config__field">
              <label>
                Data Bits/Parity/Stop<span className="required">*</span>
              </label>
              <select value={device.serial} onChange={(e) => updateDevice(index, 'serial', e.target.value)}>
                <option value="8N1">8N1 (8 bits, no parity, 1 stop)</option>
                <option value="8N2">8N2 (8 bits, no parity, 2 stop)</option>
                <option value="8E1">8E1 (8 bits, even parity, 1 stop)</option>
                <option value="8O1">8O1 (8 bits, odd parity, 1 stop)</option>
                <option value="7E1">7E1 (7 bits, even parity, 1 stop)</option>
                <option value="7O1">7O1 (7 bits, odd parity, 1 stop)</option>
              </select>
              <span className="instrument-config__hint">Serial configuration</span>
            </div>
          </>
        )}

        {/* USB TMC Transport Fields */}
        {(device.transport || 'serial') === 'usbtmc' && (
          <div className="instrument-config__field">
            <label>
              USB TMC Device<span className="required">*</span>
            </label>
            <div className="instrument-config__field-with-button">
              <select
                value={device.device || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value === '__custom__') {
                    updateDevice(index, 'device', '');
                  } else {
                    updateDevice(index, 'device', value);
                  }
                }}
              >
                {device.device && !getAvailableUsbTmcDevicesForDevice(index).find((d) => d.device === device.device) && (
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
                className="instrument-config__refresh-btn"
                onClick={loadUsbTmcDevices}
                disabled={loadingUsbTmc}
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
                style={{ marginTop: '4px' }}
              />
            )}
            <span className="instrument-config__hint">USB TMC device path</span>
          </div>
        )}

        {/* Driver and Model */}
        <div className="instrument-config__field">
          <label>
            Driver<span className="required">*</span>
          </label>
          <select
            value={device.driver}
            onChange={(e) => updateDevice(index, 'driver', e.target.value)}
          >
            <option value="">Select driver...</option>
            {drivers &&
              Object.keys(drivers)
                .filter((driverId) => {
                  // Filter drivers by supported transports
                  const selectedTransport = device.transport || 'serial';
                  const supportedTransports = drivers[driverId].supported_transports || ['serial'];
                  return supportedTransports.includes(selectedTransport);
                })
                .sort()
                .map((driverId) => (
                  <option key={driverId} value={driverId}>
                    {drivers[driverId].vendor} {drivers[driverId].family} ({driverId})
                  </option>
                ))}
          </select>
          <span className="instrument-config__hint">Driver module</span>
        </div>

        <div className="instrument-config__field">
          <label>
            Model<span className="required">*</span>
          </label>
          {device.driver && driverModels[device.driver] && driverModels[device.driver].length > 0 ? (
            <select value={device.model} onChange={(e) => updateDevice(index, 'model', e.target.value)}>
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
          <span className="instrument-config__hint">Instrument model number</span>
        </div>

        {/* Per-device action buttons and status */}
        <div className="instrument-config__device-actions">
          {isDeviceNew(device.id) ? (
            // NEW device: Show "Add Instrument" button
            <button
              type="button"
              className="instrument-config__save-btn"
              onClick={() => saveNewDevice(device)}
              disabled={deviceStates[device.id]?.saving}
              title="Add this instrument to the service"
            >
              {deviceStates[device.id]?.saving ? 'Adding...' : 'Add Instrument'}
            </button>
          ) : isDeviceModified(device) ? (
            // EXISTING modified: Show "Save & Apply" and "Remove" buttons
            <>
              <button
                type="button"
                className="instrument-config__save-btn"
                onClick={() => saveExistingDevice(device)}
                disabled={deviceStates[device.id]?.saving}
                title="Save changes and reconnect device"
              >
                {deviceStates[device.id]?.saving ? 'Saving...' : 'Save & Apply'}
              </button>
              <button
                type="button"
                className="instrument-config__remove-btn"
                onClick={() => removeDeviceFromServer(device.id)}
                disabled={deviceStates[device.id]?.saving}
                title="Remove this instrument"
              >
                Remove
              </button>
            </>
          ) : (
            // EXISTING unchanged: Show "Remove" button only
            <button
              type="button"
              className="instrument-config__remove-btn"
              onClick={() => removeDeviceFromServer(device.id)}
              disabled={deviceStates[device.id]?.saving}
              title="Remove this instrument"
            >
              {deviceStates[device.id]?.saving ? 'Removing...' : 'Remove'}
            </button>
          )}

          {/* Inline error/success feedback */}
          {deviceStates[device.id]?.error && (
            <div className="instrument-config__inline-error">{deviceStates[device.id].error}</div>
          )}
          {deviceStates[device.id]?.success && (
            <div className="instrument-config__inline-success">✓ Applied successfully!</div>
          )}
        </div>

        {/* Local remove for unsaved devices */}
        {isDeviceNew(device.id) && (
          <button
            type="button"
            className="instrument-config__cancel-btn"
            onClick={() => removeDeviceLocally(index)}
            title="Cancel adding this device"
          >
            Cancel
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="instrument-config" data-testid="instrument-config-view">
      <div className="instrument-config__content">
        {loading && <p className="instrument-config__loading">Loading configuration...</p>}
        {error && <div className="instrument-config__error">{error}</div>}

        {!loading && (
          <>
            {devices.length === 0 ? (
              <div className="instrument-config__empty">
                <p>No instruments configured.</p>
                <p>Click "Add Instrument" below to get started.</p>
              </div>
            ) : (
              <Accordion>
                {devices.map((device, index) => (
                  <AccordionItem
                    key={device._uuid}
                    id={device._uuid!}
                    header={
                      <span>
                        {device.name || 'New Instrument'} {device.id && `(${device.id})`}
                      </span>
                    }
                    isExpanded={expandedDeviceUuid === device._uuid}
                    onToggle={handleAccordionToggle}
                  >
                    {renderDeviceForm(device, index)}
                  </AccordionItem>
                ))}
              </Accordion>
            )}

            <button className="instrument-config__add-btn" onClick={addDevice} data-testid="add-instrument-btn">
              + Add Instrument
            </button>
          </>
        )}
      </div>
    </div>
  );
}

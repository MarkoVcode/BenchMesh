import os
import yaml
import tempfile
import shutil
from pathlib import Path

class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.devices = self.load_config()

    def load_config(self):
        with open(self.config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config.get('devices', [])

    def get_device(self, device_id):
        for device in self.devices:
            if device['id'] == device_id:
                return device
        return None

    def get_all_devices(self):
        return self.devices
    
def load_config(path):
    """
    Convenience function used by main.py.
    Returns the full parsed YAML as a dict (or empty dict on missing/empty file).
    """
    try:
        with open(path, 'r') as f:
            cfg = yaml.safe_load(f) or {}
        return cfg
    except FileNotFoundError:
        # Return empty config if file doesn't exist - allows starting without config
        return {}


def save_config(path, devices):
    """
    Save device configuration to YAML file atomically.

    Writes to a temporary file first, then renames to the target path to ensure
    atomic write operation. This prevents corruption if the process is interrupted.

    Args:
        path: Path to config.yaml file
        devices: List of device configuration dictionaries

    Raises:
        OSError: If unable to write to the file
        yaml.YAMLError: If unable to serialize the configuration
    """
    # Prepare config structure
    config_data = {
        'version': 1,
        'devices': devices
    }

    # Get directory path and ensure it exists
    config_path = Path(path)
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write to temporary file in the same directory (ensures same filesystem)
    fd, temp_path = tempfile.mkstemp(
        dir=str(config_dir),
        prefix='.config_',
        suffix='.yaml.tmp'
    )

    try:
        # Write YAML to temp file
        with os.fdopen(fd, 'w') as f:
            yaml.safe_dump(
                config_data,
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2
            )

        # Atomically replace the original file
        shutil.move(temp_path, str(config_path))

    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def add_device_to_config(path, device):
    """
    Add a new device to the config file.

    Args:
        path: Path to config.yaml file
        device: Device configuration dictionary

    Raises:
        ValueError: If device with same ID already exists
        OSError: If unable to write to the file
    """
    # Load current config
    cfg = load_config(path)
    devices = cfg.get('devices', [])

    # Check for duplicate
    if any(d.get('id') == device.get('id') for d in devices):
        raise ValueError(f"Device {device.get('id')} already exists in config")

    # Add device
    devices.append(device)

    # Save atomically
    save_config(path, devices)


def update_device_in_config(path, device_id, new_device):
    """
    Update an existing device in the config file.

    Args:
        path: Path to config.yaml file
        device_id: ID of device to update
        new_device: New device configuration dictionary

    Raises:
        ValueError: If device not found or new_device ID doesn't match
        OSError: If unable to write to the file
    """
    # Validate IDs match
    if new_device.get('id') != device_id:
        raise ValueError(f"Device ID mismatch: {device_id} != {new_device.get('id')}")

    # Load current config
    cfg = load_config(path)
    devices = cfg.get('devices', [])

    # Find and update device
    found = False
    for i, dev in enumerate(devices):
        if dev.get('id') == device_id:
            devices[i] = new_device
            found = True
            break

    if not found:
        raise ValueError(f"Device {device_id} not found in config")

    # Save atomically
    save_config(path, devices)


def remove_device_from_config(path, device_id):
    """
    Remove a device from the config file.

    Args:
        path: Path to config.yaml file
        device_id: ID of device to remove

    Raises:
        ValueError: If device not found
        OSError: If unable to write to the file
    """
    # Load current config
    cfg = load_config(path)
    devices = cfg.get('devices', [])

    # Remove device
    original_len = len(devices)
    devices = [d for d in devices if d.get('id') != device_id]

    if len(devices) == original_len:
        raise ValueError(f"Device {device_id} not found in config")

    # Save atomically
    save_config(path, devices)
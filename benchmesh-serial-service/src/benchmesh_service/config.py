import yaml

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
    with open(path, 'r') as f:
        cfg = yaml.safe_load(f) or {}
    return cfg
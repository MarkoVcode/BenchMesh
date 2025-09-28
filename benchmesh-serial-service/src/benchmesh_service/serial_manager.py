import serial
import time
import threading
import yaml
from src.benchmesh_service.logger import setup_logger

class SerialManager:
    def __init__(self, config_file):
        self.logger = setup_logger()
        self.devices = self.load_config(config_file)
        self.connections = {}
        self.keep_running = True

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config['devices']

    def establish_connections(self):
        for device in self.devices:
            try:
                ser = serial.Serial(
                    port=device['port'],
                    baudrate=device['baud'],
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1.0
                )
                self.connections[device['id']] = ser
                self.logger.info(f"Established connection to {device['name']} on {device['port']}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {device['name']} on {device['port']}: {e}")

    def monitor_connections(self):
        while self.keep_running:
            for device_id, connection in self.connections.items():
                if connection.is_open:
                    self.logger.info(f"{device_id} is connected.")
                else:
                    self.logger.warning(f"{device_id} is not connected. Attempting to reconnect...")
                    self.reconnect(device_id)
            time.sleep(0.5)

    def reconnect(self, device_id):
        device = next((d for d in self.devices if d['id'] == device_id), None)
        if device:
            try:
                self.connections[device_id].close()
                self.establish_connections()
            except Exception as e:
                self.logger.error(f"Reconnection failed for {device['name']}: {e}")

    def start(self):
        self.establish_connections()
        monitor_thread = threading.Thread(target=self.monitor_connections)
        monitor_thread.start()

    def stop(self):
        self.keep_running = False
        for connection in self.connections.values():
            connection.close()
        self.logger.info("All connections closed.")
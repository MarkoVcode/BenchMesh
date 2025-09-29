import serial
import time
import threading
import yaml
import logging
from typing import Dict
from .logger import setup_logger

logger = logging.getLogger(__name__)

class SerialManager:
    def __init__(self, config_file):
        print("Initializing SerialManager with config:", config_file)
        self.logger = setup_logger()
        self.devices = config_file
        self.connections = {}
        self.keep_running = True
        self.last_open_attempt: Dict[str, float] = {}
        self.last_ok: Dict[str, float] = {}

        self.establish_connections()
    # def load_config(self, config_file):
    #     with open(config_file, 'r') as file:
    #         config = yaml.safe_load(file)
    #     return config['devices']

    def establish_connections(self):
        print("Establishing connections to devices...")
        for device in self.devices:
            print("Establishing connections to devices...", device)
            try:
                self.reconnect(device)
            except Exception as e:
                self.logger.info(f"Failed to connect to {device['name']} on {device['port']}: {e}")

    def monitor_connections(self):
        print("Starting connection monitor thread.")
        while self.keep_running:
            for device_id, connection in self.connections.items():
                if connection.is_open:
                    self.logger.info(f"{device_id} is connected.")
                    self.last_ok[device_id] = 0.0
                    self.last_open_attempt[device_id] = 0.0
                else:
                    self.logger.warning(f"{device_id} is not connected. Attempting to reconnect...")
                    self.reconnect(device_id)
            time.sleep(0.5)

    def reconnect(self, device_or_id):
        """
        Attempt to (re)open a connection for a single device.
        Accepts either the device dict or its id string. Returns the new serial
        connection on success, or None on failure.
        """
        if isinstance(device_or_id, dict):
            dev = device_or_id
            device_id = dev.get('id')
        else:
            device_id = device_or_id
            dev = next((d for d in self.devices if d.get('id') == device_id), None)

        if not dev or not device_id:
            return None

        # Close existing connection if present
        try:
            old = self.connections.get(device_id)
            if old:
                old.close()
        except Exception:
            pass

        # Open fresh connection for this device only
        try:
            ser = serial.Serial(
                port=dev['port'],
                baudrate=dev['baud'],
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            self.connections[device_id] = ser
            self.logger.info(f"(Re)connected to {dev['name']} on {dev['port']}")
            return ser
        except Exception as e:
            self.logger.error(f"Reconnection failed for {dev.get('name', device_id)}: {e}")
            self.connections[device_id] = None
            return None

    def start(self):
        self.establish_connections()
        monitor_thread = threading.Thread(target=self.monitor_connections)
        monitor_thread.start()

    def stop(self):
        self.keep_running = False
        for connection in self.connections.values():
            connection.close()
        self.logger.info("All connections closed.")

    def close_connections(self):
            for dev_id, ser in list(self.connections.items()):
                if ser:
                    try:
                        ser.close()
                        logger.info("Closed connection %s", dev_id)
                    except Exception:
                        logger.exception("Error closing %s", dev_id)
                self.connections[dev_id] = None
    
    def check_status(self):
        """
        Ensure each configured device has a working connection.
        Called periodically (main() schedules every 0.5s).
        """
        now = time.time()
        for dev in self.devices:
            dev_id = dev.get('id')
            if not dev_id:
                continue
            ser = self.connections.get(dev_id)

            # If no connection, try to open (with simple backoff)
            if ser is None:
                last_attempt = self.last_open_attempt.get(dev_id, 0.0)
                # backoff 2s between attempts
                if now - last_attempt >= 2.0:
                    self.last_open_attempt[dev_id] = now
                    new_ser = self.reconnect(dev)
                    if new_ser:
                        print("Opened connection to", dev_id)
                        self.connections[dev_id] = new_ser
                        self.last_ok[dev_id] = 0.0
                continue

            # If we have a connection, probe it
            try:
                seol = dev.get('seol', "\r")
                # Try SCPI identity probe first, fall back to EOL if write fails
                try:
                    ser.write(b'*IDN?\r')
                except Exception:
                    try:
                        ser.write(seol.encode('utf-8') if isinstance(seol, str) else b'\r')
                    except Exception:
                        pass

                # brief wait then read
                time.sleep(0.05)
                resp = b''
                try:
                    resp = ser.read(256)
                except Exception as e:
                    # read failed -> treat as lost connection
                    raise

                if resp:
                    self.last_ok[dev_id] = now
                    logger.debug("Probe OK %s -> %s", dev_id, resp)
                else:
                    # no response — keep connection but log debug
                    logger.debug("No response from %s on probe", dev_id)

            except Exception as e:
                logger.warning("Connection error for %s: %s", dev_id, e)
                # close and mark for reopen
                try:
                    ser.close()
                except Exception:
                    pass
                self.connections[dev_id] = None
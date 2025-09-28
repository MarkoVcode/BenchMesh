import serial
import time
import logging

class OWONSPM:
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
            self.logger.info(f"Connected to OWON SPM on {self.port}")
        except serial.SerialException as e:
            self.logger.error(f"Failed to connect to OWON SPM on {self.port}: {e}")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            self.logger.info(f"Disconnected from OWON SPM on {self.port}")

    def send_command(self, command):
        if self.connected:
            self.ser.write(command.encode() + b'\r')
            time.sleep(0.1)  # wait for the command to be processed
            response = self.ser.read(1024).decode()
            return response
        else:
            self.logger.warning("Attempted to send command while not connected.")
            return None

    def check_status(self):
        if self.connected:
            self.logger.info("Checking status of OWON SPM.")
            # Implement status check logic here
        else:
            self.logger.warning("Cannot check status, not connected.")

    def __del__(self):
        self.disconnect()
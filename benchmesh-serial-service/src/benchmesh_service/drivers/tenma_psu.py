import serial
import time
import threading
from src.benchmesh_service.logger import logger

class TenmaPSU:
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_connected = False

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_connected = True
            logger.info(f"Connected to TENMA PSU on {self.port}")
        except serial.SerialException as e:
            logger.error(f"Failed to connect to TENMA PSU: {e}")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            logger.info("Disconnected from TENMA PSU")

    def send_command(self, command):
        if self.is_connected:
            self.ser.write(command.encode() + b'\r\n')
            time.sleep(0.1)  # wait for the command to be processed
            response = self.ser.readline().decode().strip()
            return response
        else:
            logger.warning("Attempted to send command while not connected")
            return None

    def check_status(self):
        if self.is_connected:
            logger.info("Checking status of TENMA PSU")
            # Example command to check status
            response = self.send_command("*IDN?")
            logger.info(f"Status response: {response}")
        else:
            logger.warning("Cannot check status, not connected")

    def start_status_check(self):
        def status_check_loop():
            while self.is_connected:
                self.check_status()
                time.sleep(0.5)  # check status every 500ms

        threading.Thread(target=status_check_loop, daemon=True).start()
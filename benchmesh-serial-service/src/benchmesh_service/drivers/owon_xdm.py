import serial
import time
import logging

class OWONXDM:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            self.connected = True
            logging.info(f"Connected to OWON XDM on {self.port}")
        except serial.SerialException as e:
            logging.error(f"Failed to connect to OWON XDM on {self.port}: {e}")
            self.connected = False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            logging.info(f"Disconnected from OWON XDM on {self.port}")

    def send_command(self, command):
        if self.connected:
            self.ser.write(command)
            time.sleep(0.1)  # wait for the command to be processed
            response = self.ser.read(1024)  # read response
            return response
        else:
            logging.warning("Attempted to send command while not connected.")
            return None

    def check_status(self):
        if self.connected:
            try:
                self.ser.write(b'*IDN?\r')
                time.sleep(0.1)
                reply = self.ser.read(1024)
                logging.info(f"Status check reply: {reply}")
                return reply
            except Exception as e:
                logging.error(f"Error checking status: {e}")
                self.disconnect()
                return None
        else:
            logging.warning("Attempted to check status while not connected.")
            return None

    def is_connected(self):
        return self.connected
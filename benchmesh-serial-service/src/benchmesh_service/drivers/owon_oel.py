import serial
import time

class OwonOEL:
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connect()

    def connect(self):
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )
        time.sleep(0.2)

    def write(self, command):
        if self.ser and self.ser.is_open:
            self.ser.write(command)

    def read(self, size=1024):
        if self.ser and self.ser.is_open:
            return self.ser.read(size)
        return None

    def check_status(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b'*IDN?\r')
                time.sleep(0.2)
                reply = self.ser.read(1024)
                return reply
            except Exception as e:
                print(f"Error checking status: {e}")
                self.connect()  # Attempt to reconnect on error
        return None

    def close(self):
        if self.ser:
            self.ser.close()
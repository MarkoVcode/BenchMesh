from ...transport import SerialTransport
from ...logger import logger

class TenmaPSU:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='', reol=''):
        # TENMA manifest declares empty EOLs
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)
    
    def read_output_voltage(self):
        self.t.write_line('VOUT1?')
        return self.t.read_until_reol(1024)
    
    def read_output_current(self):
        self.t.write_line('IOUT1?')
        return self.t.read_until_reol(1024)   

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
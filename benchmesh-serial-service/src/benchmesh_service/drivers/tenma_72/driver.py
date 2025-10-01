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

    def read_status(self):
        """
        Query and parse the binary STATUS response.

        Returns a dictionary like:
        {
            "ch1Mode": "C.V" | "C.C",
            "ch2Mode": "C.V" | "C.C",
            "Tracking": "Independent" | "Tracking Series" | "Tracking Parallel" | "Unknown",
            "BeepEnabled": bool,
            "lockEnabled": bool,
            "outEnabled": bool,
        }
        """
        # Send command without terminator (TENMA manifests typically use empty EOLs)
        self.t.write_line('STATUS?')
        # Read raw bytes and parse first status byte
        data = self.t.read(8) or b''
        if not data:
            return {}
        status = data[0]

        ch1mode = (status & 0x01) != 0
        ch2mode = (status & 0x02) != 0
        tracking_bits = (status & 0x0C) >> 2
        beep = (status & 0x10) != 0
        lock = (status & 0x20) != 0
        out = (status & 0x40) != 0

        if tracking_bits == 0:
            tracking = "Independent"
        elif tracking_bits == 1:
            tracking = "Tracking Series"
        elif tracking_bits == 3:
            tracking = "Tracking Parallel"
        else:
            tracking = "Unknown"

        return {
            "ch1Mode": "C.V" if ch1mode else "C.C",
            "ch2Mode": "C.V" if ch2mode else "C.C",
            "Tracking": tracking,
            "BeepEnabled": beep,
            "lockEnabled": lock,
            "outEnabled": out,
        }

    def poll_status(self):
        v = self.read_output_voltage()
        i = self.read_output_current()
        s = self.read_status()
        return {"VOUT1": v, "IOUT1": i, "status": s}
        

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
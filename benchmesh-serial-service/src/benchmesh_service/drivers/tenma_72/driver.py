import re
from ...transport import SerialTransport

class TenmaPSU:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='', reol=''):
        # TENMA manifest declares empty EOLs
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)
    
    def query_output_voltage(self, channel: int):
        self.t.write_line('VOUT1?')
        return self.t.read_until_reol(1024)
    
    def query_output_current(self, channel: int):
        self.t.write_line('IOUT1?')
        return self.t.read_until_reol(1024)

    def query_output_power(self, channel: int):
        v = self.query_output_voltage(channel)
        i = self.query_output_current(channel)
        fv = self._parse_numeric(v)
        fi = self._parse_numeric(i)
        if fv is None or fi is None:
            return None
        return fv * fi

    def query_voltage(self, channel: int):
        self.t.write_line('VSET1?')
        return self.t.read_until_reol(1024)
    
    def query_current(self, channel: int):
        self.t.write_line('ISET1?')
        return self.t.read_until_reol(1024)

    def set_voltage(self, channel: int, value):  #volts
        self.t.write_line('VSET1:' + str(value))
        return self.t.read_until_reol(1024)
    
    def set_current(self, channel: int, value):  #amps
        self.t.write_line('ISET1:' + str(value))
        return self.t.read_until_reol(1024)

    def query_status(self, channel: int):
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

    def poll_status(self, channel: int):
        print ("Polling status for channel", channel)
        p = None
        v = self.query_output_voltage(channel)
        i = self.query_output_current(channel)
        fv = self._parse_numeric(v)
        fi = self._parse_numeric(i)
        if fv is None or fi is None:
            p = None
        p = fv * fi
        s = self.query_status(channel)
        result = {"VOUT1": v, "IOUT1": i, "POUT1": p}
        if isinstance(s, dict):
            result.update(s)
        return result   
    
    def set_ocp(self, channel: int):
        self.t.write_line('OCP1')
        return self.t.read_until_reol(1024)
    
    def unset_ocp(self, channel: int):
        self.t.write_line('OCP0')
        return self.t.read_until_reol(1024)

    def set_ovp(self, channel: int):
        self.t.write_line('OVP1')
        return self.t.read_until_reol(1024)
    
    def unset_ovp(self, channel: int):
        self.t.write_line('OVP0')
        return self.t.read_until_reol(1024)
   
    def set_output(self, channel: int, value):
        if value == 'ON':
            self.t.write_line('OUT1')
        else:
            self.t.write_line('OUT0')
        return self.t.read_until_reol(1024)
    
    def set_beep(self, channel: int):           #doesnt work
        self.t.write_line('BEEP1')
        return self.t.read_until_reol(1024)

    def unset_beep(self, channel: int):         #doesnt work
        self.t.write_line('BEEP0')
        return self.t.read_until_reol(1024)

    def save_memory(self, channel: int, bank):  #bank 1-5 - doesnt work
        self.t.write_line('SAV' + str(bank))
        return self.t.read_until_reol(1024)

    def recall_memory(self, channel: int, bank):  #bank 1-5
        self.t.write_line('RCL' + str(bank))
        self.t.read_until_reol(1024)
        return

    def _parse_numeric(self, s):
        if s is None:
            return None
        if isinstance(s, bytes):
            try:
                s = s.decode('utf-8', 'ignore')
            except Exception:
                return None
        s = str(s).strip()
        m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
        try:
            return float(m.group(0)) if m else None
        except Exception:
            return None

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
from ...transport import SerialTransport

class OwonOEL:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def query_status(self, channel: int):
        self.t.write_line('MEAS:ALL:INFO?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int):
        raw = self.query_status(channel) or ""
        if raw is "" or raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode(errors='ignore')
        parts = raw.strip().split(',')
        result = {}
        keys = ["VOUT", "IOUT", "POUT", "OVP", "OCP", "OTP"]
        for idx, key in enumerate(keys):
            if idx < len(parts):
                val = parts[idx]
                if idx < 3:
                    try:
                        val = float(val)
                    except Exception:
                        pass
                result[key] = val
        print("POLL STATUS EXECUTED")
        return result
    
    def set_remote(self, channel: int):               #not sure about the usecase
        self.t.write_line('SYST:REM')
        return self.t.read_until_reol(1024)

    def unset_remote(self, channel: int):             #not sure about the usecase
        self.t.write_line('SYST:LOC')
        return self.t.read_until_reol(1024) 

#SYST:SENS ON/off
#SYST:SENS?

#CURRent: Constant current operation mode.
#VOLTage: Constant voltage operation mode.
#POWer: Constant power operation mode.
#RESistance: Constant resistance operation mode.
#DYNamic: Dynamic operation mode.

    def set_mode(self, channel: int, value):
        valid_modes = ["CURRent", "CURR", "VOLTage", "VOLT", "POWer", "POW", "RESistance", "RES", "DYNamic", "DYN"]
        if str(value).upper() not in [m.upper() for m in valid_modes]:
            raise ValueError(f"value must be one of {valid_modes}")
        self.t.write_line('MODE ' + str(value))
        return self.t.read_until_reol(1024)
    
    def query_mode(self, channel: int):
        self.t.write_line('MODE?')
        return self.t.read_until_reol(1024)
    
    #TODO - if query_input is 1 do not allow to enable compansation
    def set_remote_compensation(self, channel: int, value):    #value ON/OFF
        if str(value).upper() not in ("ON", "OFF"):
            raise ValueError("value must be 'ON' or 'OFF'")
        self.t.write_line('SYST:SENS ' + str(value))
        return self.t.read_until_reol(1024)

    def set_input(self, channel: int):
        self.t.write_line('INP ON')
        return self.t.read_until_reol(1024)
    
    def unset_input(self, channel: int):
        self.t.write_line('INP OFF')
        return self.t.read_until_reol(1024)

    def query_input(self, channel: int):
        self.t.write_line('INP?')
        return self.t.read_until_reol(1024)
    
    def set_short(self, channel: int):
        self.t.write_line('INP:SHOR ON')
        return self.t.read_until_reol(1024)
    
    def unset_short(self, channel: int):
        self.t.write_line('INP:SHOR OFF')
        return self.t.read_until_reol(1024)

    def query_short(self, channel: int):
        self.t.write_line('INP:SHOR?')
        return self.t.read_until_reol(1024)

    def write(self, data: bytes):
        self.t.write(data)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
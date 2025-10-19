from ...transport import SerialTransport
from ...utils.si import si_to_value

class OwonOEL:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()
        # Cache for INPUT and MODE to reduce queries during polling
        # These values rarely change (only when user calls set_input/set_mode)
        self._cached_input = None
        self._cached_mode = None

    def query_identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)
    
    def set_reset(self):
        self.t.write_line('*RST')
        return self.t.read_until_reol(1024)

    def query_status(self, channel: int):
        self.t.write_line('MEAS:ALL:INFO?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int):
        raw = self.query_status(channel) or ""
        if raw is None or raw == "":
            # Return a minimal but truthy structure to avoid dropping the connection
            return {"VOUT": si_to_value(0), "IOUT": si_to_value(0), "POUT": si_to_value(0), "OVP": "OFF", "OCP": "OFF", "OTP": "OFF", "REMOTE": "OFF", "INPUT": "OFF", "MODE": "CURR"}
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
                        val = si_to_value(val)
                    except Exception:
                        pass
                result[key] = val
        result["REMOTE"] = "ON"

        # Use cached values to avoid extra queries (3x speedup)
        # Only query if cache is empty (first poll or after invalidation)
        if self._cached_input is None:
            self._cached_input = self.query_input(1)
        if self._cached_mode is None:
            self._cached_mode = self.query_mode(1)

        result["INPUT"] = self._cached_input
        result["MODE"] = self._cached_mode
        return result
    
#SYST:SENS ON/off
#SYST:SENS?

#CURRent: Constant current operation mode.
#VOLTage: Constant voltage operation mode.
#POWer: Constant power operation mode.
#RESistance: Constant resistance operation mode.
#DYNamic: Dynamic operation mode.

    def set_mode(self, channel: int, value):
        self.t.write_line('FUNC ' + str(value))
        result = self.t.read_until_reol(1024)
        # Invalidate cache so next poll will query the new value
        self._cached_mode = None
        return result
    
    def query_mode(self, channel: int):
        self.t.write_line('FUNC?')
        raw = self.t.read_until_reol(1024)
        if raw.strip() == "current":
            return "CURR"
        elif raw.strip() == "voltage":
            return "VOLT"
        elif raw.strip() == "resistance":
            return "RES"
        elif raw.strip() == "power":
            return "POW"
        elif raw.strip() == "dynamic":
            return "DYN"
    
    #TODO - if query_input is 1 do not allow to enable compansation
    def set_remote_compensation(self, channel: int, value):    #value ON/OFF
        if str(value).upper() not in ("ON", "OFF"):
            raise ValueError("value must be 'ON' or 'OFF'")
        self.t.write_line('SYST:SENS ' + str(value))
        return self.t.read_until_reol(1024)

    def set_remote(self, channel: int, value):
        if str(value).upper() == "ON":
            self.t.write_line('SYSTem:REMote')
            return self.t.read_until_reol(1024)
        elif str(value).upper() == "OFF":
            self.t.write_line('SYSTem:LOCal')
            return self.t.read_until_reol(1024)

    def query_remote(self, channel: int):
        self.t.write_line('SYSTem:REMote?')
        if (self.t.read_until_reol(1024)).strip() == "1":
            return "ON"
        else:
            return "OFF"

    def set_input(self, channel: int, value):
        self.t.write_line('INP ' + str(value))
        result = self.t.read_until_reol(1024)
        # Invalidate cache so next poll will query the new value
        self._cached_input = None
        return result
    
    def query_input(self, channel: int):
        self.t.write_line('INP?')
        return self.t.read_until_reol(1024)
    
    def set_short(self, channel: int, value):  #ON/OFF
        self.t.write_line('INP:SHOR ' + str(value))
        return self.t.read_until_reol(1024)
    
    def query_short(self, channel: int):
        self.t.write_line('INP:SHOR?')
        return self.t.read_until_reol(1024)
    
    def set_res(self, channel: int, value):
        self.t.write_line('RES ' + str(value))
        return self.t.read_until_reol(1024)

    def set_curr(self, channel: int, value):
        self.t.write_line('CURR ' + str(value))
        return self.t.read_until_reol(1024)

    def set_volt(self, channel: int, value):
        self.t.write_line('VOLT ' + str(value))
        return self.t.read_until_reol(1024)
    
    def set_pow(self, channel: int, value):
        self.t.write_line('POW ' + str(value))
        return self.t.read_until_reol(1024)  

    def query_res(self, channel: int):
        self.t.write_line('RES?')
        return self.t.read_until_reol(1024)

    def query_curr(self, channel: int):
        self.t.write_line('CURR?')
        return self.t.read_until_reol(1024)

    def query_volt(self, channel: int):
        self.t.write_line('VOLT?')
        return self.t.read_until_reol(1024)
    
    def query_pow(self, channel: int):
        self.t.write_line('POW?')
        return self.t.read_until_reol(1024) 

    def write(self, data: bytes):
        self.t.write(data)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
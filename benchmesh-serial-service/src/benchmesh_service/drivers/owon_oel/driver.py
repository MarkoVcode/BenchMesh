from ..base import DriverBase
from ...utils.si import si_to_value

class OwonOEL(DriverBase):
    def query_status(self, channel: int):
        self.t.write_line('MEAS:ALL:INFO?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int):
        """
        Poll electronic load status.

        Exceptions propagate naturally for health monitoring.
        Returns empty dict {} if device is off/not responding.
        """
        raw = self.query_status(channel) or ""

        # Device off or not responding - return empty dict
        if raw is None or raw == "":
            return {}

        if isinstance(raw, bytes):
            raw = raw.decode(errors='ignore')

        parts = raw.strip().split(',')
        result = {}
        keys = ["VIN", "IIN", "PIN", "OVP", "OCP", "OTP"]
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
        # get_or_set: gets from cache or queries device if cache miss
        result["INPUT"] = self.cache.get_or_set("input", self.query_input, 1)
        result["MODE"] = self.cache.get_or_set("mode", self.query_mode, 1)

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
        self.cache.invalidate("mode")
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
        self.cache.invalidate("input")
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
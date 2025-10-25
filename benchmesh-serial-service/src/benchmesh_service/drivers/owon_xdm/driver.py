from ...transport import SerialTransport
from ...utils.si import format_scientific_to_si
from ...utils.si import trim_digits_to

class OWONXDM:
    def __init__(self, port=None, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r', transport=None):
        # Accept either pre-configured transport or port/baudrate for backward compatibility
        if transport is not None:
            self.t = transport
        else:
            self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def query_identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)
    
    def set_reset(self):
        self.t.write_line('*RST')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int):
        query_measurement = self.query_measurement(1)
        num_str, sym, n = format_scientific_to_si(query_measurement)
        function = self.query_function(1)
        raw = self.query_identify() or b""
        if not raw:
            return None
      #  print(num_str)
        return {"measurement1_sci": query_measurement, "measurement1_si": trim_digits_to(num_str, 5), "measurement1_symbol": sym, "measurement1_function": function}

    def set_current_dc_range(self, channel: int, value):
        self.t.write_line('CONF:CURR:DC ' + str(value))
        return self.t.read_until_reol(1024)

    def set_current_ac_range(self, channel: int, value):
        self.t.write_line('CONF:CURR:AC ' + str(value))
        return self.t.read_until_reol(1024)    

    def set_voltage_dc_range(self, channel: int, value):
        self.t.write_line('CONF:VOLT:DC ' + str(value))
        return self.t.read_until_reol(1024)

    def set_voltage_ac_range(self, channel: int, value):
        self.t.write_line('CONF:VOLT:AC ' + str(value))
        return self.t.read_until_reol(1024)
    
    def set_resistance_range(self, channel: int, value):
        self.t.write_line('CONF:RES ' + str(value))
        return self.t.read_until_reol(1024)

    def set_fresistance_range(self, channel: int, value):
        self.t.write_line('CONF:FRES ' + str(value))
        return self.t.read_until_reol(1024)   

    def set_capacitance_range(self, channel: int, value):
        self.t.write_line('CONF:CAP ' + str(value))
        return self.t.read_until_reol(1024)

    def set_frequency(self, channel: int):
        self.t.write_line('CONF:FREQ')
        return self.t.read_until_reol(1024)  

    def set_period(self, channel: int):
        self.t.write_line('CONF:PER')
        return self.t.read_until_reol(1024)  

    def set_diode(self, channel: int):
        self.t.write_line('CONF:DIOD')
        return self.t.read_until_reol(1024)  

    def set_continuity(self, channel: int):
        self.t.write_line('CONF:CONT')
        return self.t.read_until_reol(1024) 

    def set_temperature(self, channel: int, sensor):
        self.t.write_line('CONF:TEMPerature:RTD ' + str(sensor))
        return self.t.read_until_reol(1024) 

    def set_temp_sensor(self, channel: int, sensor):
        self.t.write_line('CONF:TEMPerature:RTD ' + str(sensor))
        return self.t.read_until_reol(1024)
    
    def set_temp_scale(self, channel: int, unit):
        self.t.write_line('TEMPerature:RTD:UNIT ' + str(unit))
        return self.t.read_until_reol(1024)

    def query_measurement(self, channel: int):
        self.t.write_line('MEAS1?')
        return self.t.read_until_reol(1024)    
    
    def query_function(self, channel: int):
        self.t.write_line('FUNCtion?')
        return self._clean_response(self.t.read_until_reol(1024))
    
    def set_mode(self, channel: int, value):
        if value == "CURR":
            self.set_current_dc_range(1, "AUTO")
        elif value == "CURR_AC":
            self.set_current_ac_range(1, "AUTO")
        elif value == "VOLT":
            self.set_voltage_dc_range(1, "AUTO")
        elif value == "VOLT_AC":
            self.set_voltage_ac_range(1, "AUTO")
        elif value == "RES":
            self.set_resistance_range(1, "AUTO")
        elif value == "FRESistance":
            self.set_fresistance_range(1, "AUTO")  
        elif value == "CAP":
            self.set_capacitance_range(1, "AUTO")
        elif value == "DIOD":
            self.set_diode(1)
        elif value == "CONT":
            self.set_continuity(1)  
        elif value == "FREQ":
            self.set_frequency(1)
        elif value == "TEMP":
            self.set_temperature(1, "KITS90")           
        elif value == "PER":
            self.set_period(1)                
        return

    def write(self, data: bytes):
        self.t.write(data)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()

    def is_connected(self):
        return self.t.is_open
    
    def _clean_response(self, raw):
        """Normalize device response: bytes->str, strip whitespace and remove surrounding quotes."""
        if raw is None:
            return ""
        if isinstance(raw, (bytes, bytearray)):
            try:
                s = raw.decode('utf-8', errors='ignore')
            except Exception:
                s = raw.decode('latin1', errors='ignore')
        else:
            s = str(raw)
        s = s.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1].strip()
        return s
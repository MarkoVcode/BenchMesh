from ...transport import SerialTransport

class OWONSPM:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def query_status(self):
        self.t.write_line('MEAS:ALL:INFO?')
        return self.t.read_until_reol(1024)

    def query_output_voltage(self):
        self.t.write_line('MEAS:VOLT?')
        return self.t.read_until_reol(1024)
    
    def query_output_current(self):
        self.t.write_line('MEAS:CURR?')
        return self.t.read_until_reol(1024)

    def query_output_power(self):
        self.t.write_line('MEAS:POW?')
        return self.t.read_until_reol(1024)

    def query_output_all(self):
        self.t.write_line('MEASure:ALL?')
        return self.t.read_until_reol(1024)

    def poll_status(self):
        raw = self.read_status() or ""
        if isinstance(raw, bytes):
            raw = raw.decode(errors='ignore')
        parts = raw.strip().split()
        result = {}
        keys = ["VOUT", "IOUT", "POUT", "OVP", "OCP", "OTP", "OM"]
        for idx, key in enumerate(keys):
            if idx < len(parts):
                val = parts[idx]
                if idx < 3:
                    try:
                        val = float(val)
                    except Exception:
                        pass
                result[key] = val
        return result

    def set_output(self):
        self.t.write_line('OUTP ON')
        return self.t.read_until_reol(1024)
    
    def unset_output(self):
        self.t.write_line('OUTP OFF')
        return self.t.read_until_reol(1024)

    def query_output(self):
        self.t.write_line('OUTP?')
        return self.t.read_until_reol(1024) 

    def query_voltage(self):
        self.t.write_line('VOLT?')
        return self.t.read_until_reol(1024)
    
    def query_current(self):
        self.t.write_line('CURR?')
        return self.t.read_until_reol(1024)

    def set_voltage(self, value):  #volts
        self.t.write_line('VOLT ' + value)
        return self.t.read_until_reol(1024)
    
    def set_current(self, value):  #amps
        self.t.write_line('CURR ' + value)
        return self.t.read_until_reol(1024)

    def set_remote(self):
        self.t.write_line('SYST:REM')
        return self.t.read_until_reol(1024)

    def unset_remote(self):
        self.t.write_line('SYST:LOC')
        return self.t.read_until_reol(1024)        

    def set_ocp_value(self, value):
        self.t.write_line('CURR:LIM ' + value)
        return self.t.read_until_reol(1024)
    
    def query_ocp(self):
        self.t.write_line('CURR:LIM?')
        return self.t.read_until_reol(1024)

    def set_ovp_value(self, value):
        self.t.write_line('VOLT:LIM ' + value)
        return self.t.read_until_reol(1024)
    
    def query_ovp(self):
        self.t.write_line('VOLT:LIM?')
        return self.t.read_until_reol(1024)

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
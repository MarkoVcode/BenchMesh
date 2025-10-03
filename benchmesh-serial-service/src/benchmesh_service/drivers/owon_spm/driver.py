from ...transport import SerialTransport

class OWONSPM:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def query_output_voltage(self, channel: int):
        self.t.write_line('MEAS:VOLT?')
        return self.t.read_until_reol(1024)
    
    def query_output_current(self, channel: int):
        self.t.write_line('MEAS:CURR?')
        return self.t.read_until_reol(1024)

    def query_output_power(self, channel: int):
        self.t.write_line('MEAS:POW?')
        return self.t.read_until_reol(1024)

    def query_status(self, channel: int):
        self.t.write_line('MEAS:ALL:INFO?')
        return self.t.read_until_reol(1024)

    def query_output_all(self, channel: int):
        self.t.write_line('MEASure:ALL?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int):
        raw = self.query_status(channel) or ""
        if isinstance(raw, bytes):
            raw = raw.decode(errors='ignore')
        parts = raw.strip().split(',')
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

    def set_output(self, channel: int):
        self.t.write_line('OUTP ON')
        return self.t.read_until_reol(1024)
    
    def unset_output(self, channel: int):
        self.t.write_line('OUTP OFF')
        return self.t.read_until_reol(1024)

    def query_output(self, channel: int):
        self.t.write_line('OUTP?')
        return self.t.read_until_reol(1024) 

    def query_voltage(self, channel: int):
        self.t.write_line('VOLT?')
        return self.t.read_until_reol(1024)
    
    def query_current(self, channel: int):
        self.t.write_line('CURR?')
        return self.t.read_until_reol(1024)

    def set_voltage(self, channel: int, value):  #volts
        self.t.write_line('VOLT ' + str(value))
        return self.t.read_until_reol(1024)
    
    def set_current(self, channel: int, value):  #amps
        self.t.write_line('CURR ' + str(value))
        return self.t.read_until_reol(1024)

    def set_remote(self, channel: int):               #not sure about the usecase
        self.t.write_line('SYST:REM')
        return self.t.read_until_reol(1024)

    def unset_remote(self, channel: int):             #not sure about the usecase
        self.t.write_line('SYST:LOC')
        return self.t.read_until_reol(1024)        

    def set_ocp_value(self, channel: int, value):
        self.t.write_line('CURR:LIM ' + str(value))
        return self.t.read_until_reol(1024)
    
    def query_ocp(self, channel: int):
        self.t.write_line('CURR:LIM?')
        return self.t.read_until_reol(1024)

    def set_ovp_value(self, channel: int, value):
        self.t.write_line('VOLT:LIM ' + str(value))
        return self.t.read_until_reol(1024)
    
    def query_ovp(self, channel: int):
        self.t.write_line('VOLT:LIM?')
        return self.t.read_until_reol(1024)

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
from ...transport import SerialTransport
from ...utils.si import format_scientific_to_si

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
    
    def query_measurement(self, channel: int):
        self.t.write_line('CONFigure?')
        return self.t.read_until_reol(1024)

    def poll_status_psu(self, channel: int):
        raw = self.query_status(channel) or ""
        if raw is None or raw == "":
            # Return a minimal but truthy structure to avoid dropping the connection
            return {"VOUT": None, "IOUT": None, "POUT": None}
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
        print("POLL STATUS EXECUTED")
        return result

    def poll_status_dmm(self, channel: int):
        raw = self.query_measurement(channel) or ""
        parts = raw.strip().split(' ')
        num_str, sym, n = format_scientific_to_si(parts[1])
        function = parts[0]
        if not raw:
            return None
        print(num_str)
        return {"measurement1_si": parts[1], "measurement1_num": num_str, "measurement1_symbol": sym, "measurement1_function": function}


    def set_output(self, channel: int, value):  # ON / OFF
        self.t.write_line('OUTP ' + str(value))
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

    def set_current_dc_range(self, channel: int, value):

        self.t.write_line('CURRent:DC:RANGe:AUTO ON')
        return self.t.read_until_reol(1024)

    def set_current_ac_range(self, channel: int, value):
        self.t.write_line('CURRent:AC:RANGe:AUTO ON')
        return self.t.read_until_reol(1024)    

    def set_voltage_dc_range(self, channel: int, value):
        self.t.write_line('FUNCtion:VOLTage:DC')
        self.t.read_until_reol(1024)
        self.t.write_line('VOLTage:DC:RANGe:AUTO ON')
        return self.t.read_until_reol(1024)

    def set_voltage_ac_range(self, channel: int, value):
        self.t.write_line('FUNCtion:VOLTage:AC')
        self.t.read_until_reol(1024)
        self.t.write_line('VOLTage:AC:RANGe:AUTO ON')
        return self.t.read_until_reol(1024)

    def set_mode(self, channel: int, value):
        if value == "CURRent_DC":
            self.set_current_dc_range(1, "AUTO")
        elif value == "CURRent_AC":
            self.set_current_ac_range(1, "AUTO")
        elif value == "VOLTage_DC":
            self.set_voltage_dc_range(1, "AUTO")
        elif value == "VOLTage_AC":
            self.set_voltage_ac_range(1, "AUTO")
        elif value == "RESistance":
            self.set_resistance_range(1, "AUTO")
        elif value == "CAPacitance":
            self.set_capacitance_range(1, "AUTO")
        elif value == "DIODe":
            self.set_diode(1)
        elif value == "CONTinuity":
            self.set_continuity(1)               
        return

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
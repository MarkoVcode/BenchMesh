import logging
from ...transport import SerialTransport
from ...utils.si import format_scientific_to_si
from ...utils.si import trim_digits_to
from ...utils.si import si_to_value

logger = logging.getLogger(__name__)

class OWONSPM:
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
                        val = si_to_value(val)
                    except Exception:
                        pass
                result[key] = val
        if parts[6] == '1':
            result["CV"] = True
            result["CC"] = False
            result["FAIL"] = False
            result["SBY"] = False
            result["OUTPUT"] = "ON"
        elif parts[6] == '0':
            result["CV"] = False
            result["CC"] = False
            result["FAIL"] = False
            result["SBY"] = True
            result["OUTPUT"] = "OFF"
        elif parts[6] == '2':
            result["CV"] = False
            result["CC"] = True
            result["FAIL"] = False
            result["SBY"] = False
            result["OUTPUT"] = "ON"
        elif parts[6] == '3':
            result["CV"] = False
            result["CC"] = False
            result["FAIL"] = True
            result["SBY"] = False
            result["OUTPUT"] = "ON"
        result["REMOTE"]= "OFF"
        return result

    def poll_status_dmm(self, channel: int):
        raw = self.query_measurement(channel) or ""
        parts = raw.strip().split(' ')
        num_str, sym, n = format_scientific_to_si(parts[1])
        function = parts[0]
        if not raw:
            return None
      #  print(num_str)
        return {"measurement1_sci": parts[1], "measurement1_si": trim_digits_to(num_str, 5), "measurement1_symbol": sym, "measurement1_function": function}

    def poll_status(self, channel: int):
        """
        Unified polling method for multi-class device.
        
        Polls both PSU and DMM data in a single operation to avoid
        double serial port access for devices with multiple classes
        on a single serial port.
        
        Returns dict with class-keyed data:
        {
            "PSU": {psu status data},
            "DMM": {dmm status data}
        }
        """
        result = {}
        
        # Get PSU data
        try:
            psu_data = self.poll_status_psu(channel)
            if psu_data:
                result["PSU"] = psu_data
        except Exception as e:
            logger.warning(f"Failed to poll PSU status: {e}")
            result["PSU"] = {"VOUT": None, "IOUT": None, "POUT": None}
        
        # Get DMM data  
        try:
            dmm_data = self.poll_status_dmm(channel)
            if dmm_data:
                result["DMM"] = dmm_data
        except Exception as e:
            logger.warning(f"Failed to poll DMM status: {e}")
            result["DMM"] = None
        
        return result


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
        self.t.write_line('FUNCtion:CURR:DC')
        return self.t.read_until_reol(1024)

    def set_current_ac_range(self, channel: int, value):
        self.t.write_line('FUNCtion:CURR:AC')
        return self.t.read_until_reol(1024)    

    def set_voltage_dc_range(self, channel: int, value):
        self.t.write_line('FUNCtion:VOLTage:DC')
     #   self.t.read_until_reol(1024)
      #  self.t.write_line('VOLTage:DC:RANGe:AUTO ON')
        return self.t.read_until_reol(1024)

    def set_voltage_ac_range(self, channel: int, value):
        self.t.write_line('FUNCtion:VOLTage:AC')
     #   self.t.read_until_reol(1024)
     #   self.t.write_line('VOLTage:AC:RANGe:AUTO ON')
        return self.t.read_until_reol(1024)

    def set_resistance_range(self, channel: int, value):
        self.t.write_line('FUNCtion:RESistance')
        return self.t.read_until_reol(1024)

    def set_capacitance_range(self, channel: int, value):
        self.t.write_line('FUNCtion:CAPacitance')
        return self.t.read_until_reol(1024)
    
    def set_diode(self, channel: int):
        self.t.write_line('FUNCtion:DIODe')
        return self.t.read_until_reol(1024)

    def set_continuity(self, channel: int):
        self.t.write_line('FUNCtion:CONTinuity')
        return self.t.read_until_reol(1024)    

    def set_mode(self, channel: int, value):
        if value == "CURR_DC":
            self.set_current_dc_range(1, "AUTO")
        elif value == "CURR_AC":
            self.set_current_ac_range(1, "AUTO")
        elif value == "VOLT_DC":
            self.set_voltage_dc_range(1, "AUTO")
        elif value == "VOLT_AC":
            self.set_voltage_ac_range(1, "AUTO")
        elif value == "RES":
            self.set_resistance_range(1, "AUTO")
        elif value == "CAP":
            self.set_capacitance_range(1, "AUTO")
        elif value == "DIOD":
            self.set_diode(1)
        elif value == "CONT":
            self.set_continuity(1)               
        return

    def write(self, text: str):
        self.t.write_line(text)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()
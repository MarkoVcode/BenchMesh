import logging
from ..base import DriverBase
from ...utils.si import format_scientific_to_si
from ...utils.si import trim_digits_to
from ...utils.si import si_to_value
from ...utils.si import sci_to_value

logger = logging.getLogger(__name__)

class OwonSPM(DriverBase):
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
    
    def _query_measurement(self, channel: int):
        self.t.write_line('CONFigure?')
        raw = self.t.read_until_reol(1024)
        parts = raw.strip().split(' ')
        #VOLT:DC -1.2000E-03
        self.cache.set("measurement",  parts[1], 0.6)
        self.cache.set("function",  parts[0], 5)
        return parts[1]

    def query_measurement(self, channel: int):
        measurement = self.cache.get("measurement")
        print("measurement: " + str(measurement))
        if measurement is None:
            self.t.write_line('CONFigure?')
            raw = self.t.read_until_reol(1024)
            print("raw: " + str(raw))
            parts = raw.strip().split(' ')
            measurement = parts[1]
        return sci_to_value(measurement)

    def query_function(self, channel: int):
        funct = self.cache.get("function")
        if funct is None:
            self.t.write_line('FUNCtion?')
            funct = self._clean_response(self.t.read_until_reol(1024))
        return self.normalize_spaces(funct)

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
        query_measurement = self._query_measurement(channel)
        func = self.query_function(channel)
        return {"MEAS": sci_to_value(query_measurement), "MODE": func, "RANGE": self.cache.get(func + ":RANGE")}

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
        voltage = self.t.read_until_reol(1024)
        return si_to_value(voltage)
    
    def query_current(self, channel: int):
        self.t.write_line('CURR?')
        current = self.t.read_until_reol(1024)
        return si_to_value(current)

    def query_voltage_limit(self, channel: int):
        self.t.write_line('VOLT:LIM?')
        voltage = self.t.read_until_reol(1024)
        return si_to_value(voltage)
    
    def query_current_limit(self, channel: int):
        self.t.write_line('CURR:LIM?')
        current = self.t.read_until_reol(1024)
        return si_to_value(current)

    def set_voltage(self, channel: int, value):  #volts
        self.t.write_line('VOLT ' + str(value))
        return self.t.read_until_reol(1024)
    
    def set_current(self, channel: int, value):  #amps
        self.t.write_line('CURR ' + str(value))
        return self.t.read_until_reol(1024)
    
    def set_voltage_limit(self, channel: int, value):  #volts
        self.set_ovp_value(channel, value)
    
    def set_current_limit(self, channel: int, value):  #amps
        self.set_ocp_value(channel, value)

    def query_current_limit(self, channel: int):
        return self.query_ocp_value(channel)

    def query_voltage_limit(self, channel: int):
        return self.query_ovp_value(channel)

    def set_ocp_value(self, channel: int, value):
        self.t.write_line('CURR:LIM ' + str(value))
        return self.t.read_until_reol(1024)
    
    def query_ocp_value(self, channel: int):
        self.t.write_line('CURR:LIM?')
        value = self.t.read_until_reol(1024)
        return si_to_value(value)

    def set_ovp_value(self, channel: int, value):
        self.t.write_line('VOLT:LIM ' + str(value))
        return self.t.read_until_reol(1024)
    
    def query_ovp_value(self, channel: int):
        self.t.write_line('VOLT:LIM?')
        value = self.t.read_until_reol(1024)
        return si_to_value(value)

#
#   Range Settings
#

    def set_current_dc_range(self, channel: int, value):
        funct = self.cache.get("function")
        self.cache.set(funct + ":RANGE", str(value))
        self.t.write_line('CURRent:DC:RANGe '+str(value))
        return self.t.read_until_reol(1024)

    def set_current_ac_range(self, channel: int, value):
        funct = self.cache.get("function")
        self.cache.set(funct + ":RANGE", str(value))
        self.t.write_line('CURRent:AC:RANGe '+str(value))
        return self.t.read_until_reol(1024)    

    def set_voltage_dc_range(self, channel: int, value):
        funct = self.cache.get("function")
        self.cache.set(funct + ":RANGE", str(value))
        self.t.write_line('VOLTage:DC:RANGe '+str(value))
        return self.t.read_until_reol(1024)

    def set_voltage_ac_range(self, channel: int, value):
        funct = self.cache.get("function")
        self.cache.set(funct + ":RANGE", str(value))
        self.t.write_line('VOLTage:AC:RANGe '+str(value))
        return self.t.read_until_reol(1024)

    def set_resistance_range(self, channel: int, value):
        funct = self.cache.get("function")
        self.cache.set(funct + ":RANGE", str(value))
        self.t.write_line('RESistance:RANGe '+str(value))
        return self.t.read_until_reol(1024)

    def set_capacitance_range(self, channel: int, value):
        funct = self.cache.get("function")
        self.cache.set(funct + ":RANGE", str(value))
        self.t.write_line('CAPacitance:RANGe '+str(value))
        return self.t.read_until_reol(1024)
    
#
#   Mode Settings
#

    def set_current_dc_mode(self, channel: int):
        self.t.write_line('FUNCtion:CURR:DC')
        return self.t.read_until_reol(1024)

    def set_current_ac_mode(self, channel: int):
        self.t.write_line('FUNCtion:CURR:AC')
        return self.t.read_until_reol(1024)    

    def set_voltage_dc_mode(self, channel: int):
        self.t.write_line('FUNCtion:VOLTage:DC')
        return self.t.read_until_reol(1024)

    def set_voltage_ac_mode(self, channel: int):
        self.t.write_line('FUNCtion:VOLTage:AC')
        return self.t.read_until_reol(1024)

    def set_resistance_mode(self, channel: int):
        self.t.write_line('FUNCtion:RESistance')
        return self.t.read_until_reol(1024)

    def set_capacitance_mode(self, channel: int):
        self.t.write_line('FUNCtion:CAPacitance')
        return self.t.read_until_reol(1024)
    
    def set_diode_mode(self, channel: int):
        self.t.write_line('FUNCtion:DIODe')
        return self.t.read_until_reol(1024)

    def set_continuity_mode(self, channel: int):
        self.t.write_line('FUNCtion:CONTinuity')
        return self.t.read_until_reol(1024)    

    def set_mode(self, channel: int, value):
        if value == "CURR_DC":
            self.set_current_dc_mode(1)
        elif value == "CURR_AC":
            self.set_current_ac_mode(1)
        elif value == "VOLT_DC":
            self.set_voltage_dc_mode(1)
        elif value == "VOLT_AC":
            self.set_voltage_ac_mode(1)
        elif value == "RES":
            self.set_resistance_mode(1)
        elif value == "CAP":
            self.set_capacitance_mode(1)
        elif value == "DIOD":
            self.set_diode_mode(1)
        elif value == "CONT":
            self.set_continuity_mode(1)
        return
    
    def normalize_spaces(self, s: str, search: str = ':', replacement: str = '_') -> str:
        """Replace all whitespace characters with replacement character (default '_')."""
        if not isinstance(s, str):
            return ''
        return ' '.join(s.split()).replace(search, replacement)
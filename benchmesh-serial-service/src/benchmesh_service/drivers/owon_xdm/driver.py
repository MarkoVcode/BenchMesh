from ..base import DriverBase
from ...utils.si import si_to_value

class OwonXDM(DriverBase):
    def poll_status(self, channel: int):
        query_measurement = self._query_measurement(1)
        func = self._query_function(1)
        raw = self.query_identify() or b""
        if not raw:
            return None
        return {"MEAS": si_to_value(query_measurement), "MODE": function, "RANGE": self.cache.get(func + ":RANGE")}

    def set_remote(self, channel: int, value):
        if str(value).upper() == "ON":
            self.t.write_line('SYSTem:REMote')
            return self.t.read_until_reol(1024)
        elif str(value).upper() == "OFF":
            self.t.write_line('SYSTem:LOCal')
            return self.t.read_until_reol(1024)

    def set_rate(self, channel: int, value):
        self.t.write_line('RATE ' + str(value))
        return self.t.read_until_reol(1024)

    def query_rate(self, channel: int):
        self.t.write_line('RATE?')
        return self.t.read_until_reol(1024)

    def set_current_dc_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:CURR:DC ' + range)
        return self.t.read_until_reol(1024)

    def set_current_ac_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:CURR:AC ' + range)
        return self.t.read_until_reol(1024)    

    def set_voltage_dc_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:VOLT:DC ' + range)
        return self.t.read_until_reol(1024)

    def set_voltage_ac_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:VOLT:AC ' + range)
        return self.t.read_until_reol(1024)
    
    def set_resistance_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:RES ' + range)
        return self.t.read_until_reol(1024)

    def set_fresistance_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:FRES ' + range)
        return self.t.read_until_reol(1024)   

    def set_capacitance_range(self, channel: int, value):
        self._preserve_range(value)
        self.t.write_line('CONF:CAP ' + range)
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

    def _query_measurement(self, channel: int):
        self.t.write_line('MEAS1?')
        mes = self.t.read_until_reol(1024)
        self.cache.set("measurement",  mes, 0.6)
        return mes
    
    def query_measurement(self, channel: int):
        measurement = self.cache.get("measurement")
        if measurement is not None:
            self.t.write_line('MEAS1?')
            measurement = self.t.read_until_reol(1024)
        return si_to_value(measurement)
    
    def _query_function(self, channel: int):
        self.t.write_line('FUNCtion?')
        funct = self._clean_response(self.t.read_until_reol(1024))
        self.cache.set("function",  funct)
        return funct

    def query_function(self, channel: int):
        funct = self.cache.get("function")
        if funct is not None:
            self.t.write_line('FUNCtion?')
            funct = self._clean_response(self.t.read_until_reol(1024))
        return funct
    
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
    
    def _preserve_range(self, value):
        range = str(value)
        func = self.cache.get("function")
        self.cache.set(func + ":RANGE",  func)
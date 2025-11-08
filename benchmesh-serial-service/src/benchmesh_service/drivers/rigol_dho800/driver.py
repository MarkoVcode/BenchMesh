"""
RIGOL DHO800 Series Oscilloscope Driver
Supports DHO804, DHO802, DHO814, DHO812, and other DHO800 series models
"""
from ..base import DriverBase
from ...utils.si import sci_to_value


class RigolDHO800(DriverBase):
    """Driver for RIGOL DHO800 series oscilloscopes"""

    def poll_status(self, channel: int = 1):
        """Poll device status"""
        # Query basic oscilloscope parameters
        try:
            # Get channel scale (V/div)
            self.t.write_line(f':CHANnel{channel}:SCALe?')
            scale = self.t.read_until_reol(1024)
            
            # Get channel offset
            self.t.write_line(f':CHANnel{channel}:OFFSet?')
            offset = self.t.read_until_reol(1024)
            
            # Get channel coupling
            self.t.write_line(f':CHANnel{channel}:COUPling?')
            coupling = self.t.read_until_reol(1024)
            
            # Get timebase scale
            self.t.write_line(':TIMebase:MAIN:SCALe?')
            timebase = self.t.read_until_reol(1024)
            
            return {
                "CHANNEL": channel,
                "SCALE": sci_to_value(scale),
                "OFFSET": sci_to_value(offset),
                "COUPLING": coupling,
                "TIMEBASE": sci_to_value(timebase)
            }
        except Exception as e:
            return {"ERROR": str(e)}

    def set_output(self, channel: int, state: str):
        """Enable/disable oscilloscope channel display
        
        Args:
            channel: Channel number (1-4)
            state: "ON" or "OFF"
        """
        # IMPORTANT: SCPI set commands don't return responses
        # Writing and then reading causes USB TMC timeout and corrupts the connection
        state_value = "1" if state.upper() in ("ON", "1", "TRUE") else "0"
        self.t.write_line(f':CHANnel{channel}:DISPlay {state_value}')
        # NO READ HERE - this was causing the USB TMC corruption!

    def query_output(self, channel: int):
        """Query channel display state"""
        self.t.write_line(f':CHANnel{channel}:DISPlay?')
        response = self.t.read_until_reol(1024)
        if response.strip() == '1':
            return 'ON'
        else:
            return 'OFF'
    
    def query_screenshot(self, format: str = "PNG"):
        """Capture oscilloscope screenshot
        
        Args:
            format: Image format ("PNG", "BMP", "JPEG")
            
        Returns:
            bytes: Raw image data
        """
        # Set display data format to PNG/BMP/JPEG
        self.t.write_line(f':DISPlay:DATA? ON,OFF,{format.upper()}')
        
        # Read binary data (IEEE 488.2 format: #8NNNNNNNN<data>)
        return self.t.read_binary(max_bytes=5_000_000)  # 5MB max
    
    def set_channel_scale(self, channel: int, scale: float):
        """Set channel vertical scale (V/div)"""
        self.t.write_line(f':CHANnel{channel}:SCALe {scale}')
    
    def query_channel_scale(self, channel: int):
        """Query channel vertical scale"""
        self.t.write_line(f':CHANnel{channel}:SCALe?')
        return self.t.read_until_reol(1024)
    
    def set_timebase_scale(self, scale: float):
        """Set horizontal timebase scale (s/div)"""
        self.t.write_line(f':TIMebase:MAIN:SCALe {scale}')
    
    def query_timebase_scale(self):
        """Query horizontal timebase scale"""
        self.t.write_line(':TIMebase:MAIN:SCALe?')
        return self.t.read_until_reol(1024)

"""
OWON DGE Series Function/Arbitrary Waveform Generator Driver
Supports DGE2070, DGE2035, DGE3032, DGE3062, DGE3031, DGE3061
"""
import os
from datetime import datetime
from ...transport import SerialTransport
from ...transport.utils import parse_ieee488_binary_block


class OwonDGE:
    """Driver for OWON DGE series function generators"""

    def __init__(self, port=None, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r', transport=None):
        # Accept either pre-configured transport or port/baudrate for backward compatibility
        if transport is not None:
            self.t = transport
        else:
            self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def query_identify(self):
        """Query device identification"""
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def set_reset(self):
        """Reset device to factory settings"""
        self.t.write_line('*RST')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int = 1):
        """Poll device status"""
        # For AWG, channel is typically not used (single-instrument status)
        # But we accept it for API compatibility
        shape = self.query_identify()
        return {
            "SHAPE": shape
        }

    def set_output(self, channel: int, state: str):
        """Enable/disable output channel"""
        self.t.write_line(f':CHANnel{channel}:DISPlay {state}')
        return self.t.read_until_reol(1024)

#:CHANnel1:DISPlay ON /*Enables CHANnel1.*/
#:CHANnel1:SCALe 0.1 /*Sets the vertical scale to 0.1 V/div
#for CH1.*/
#:CHANnel1:COUPling AC

    def query_output(self, channel: int):
        """Query output channel state"""
        self.t.write_line(f':CHANnel{channel}:DISPlay?')
        response = self.t.read_until_reol(1024)
        if response.strip() == '1':
            return 'ON'
        else:
            return 'OFF'
    
    def write(self, data: bytes):
        """Write raw data to transport"""
        self.t.write(data)

    def read(self, size=1024):
        """Read raw data from transport"""
        return self.t.read(size)

    def close(self):
        """Close transport connection"""
        self.t.close()

"""
OWON DGE Series Function/Arbitrary Waveform Generator Driver
Supports DGE2070, DGE2035, DGE3032, DGE3062, DGE3031, DGE3061
"""
from ...transport import SerialTransport


class OWENDGE:
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

    def poll_status(self):
        """Poll device status"""
        # For now, just return basic identification
        idn = self.query_identify()
        return {
            "idn": idn,
            "connected": True
        }

    def set_output(self, channel, state):
        """Enable/disable output channel"""
        state_val = '1' if state else '0'
        self.t.write_line(f'C{channel}:OUTP {state_val}')

    def query_output(self, channel):
        """Query output channel state"""
        self.t.write_line(f'C{channel}:OUTP?')
        response = self.t.read_until_reol(1024)
        return response.strip() == 'ON'

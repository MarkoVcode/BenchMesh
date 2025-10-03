from ...transport import SerialTransport

class OwonOEL:
    def __init__(self, port, baudrate=115200, serial_mode='8N1', seol='\r', reol='\r'):
        self.t = SerialTransport(port, baudrate, serial_mode=serial_mode, seol=seol, reol=reol).open()

    def identify(self):
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int):
        raw = self.identify() or ""
        if raw is "" or raw is None:
            return None
        return {"A": "B"}
    
    def set_remote(self, channel: int):               #not sure about the usecase
        self.t.write_line('SYST:REM')
        return self.t.read_until_reol(1024)

    def unset_remote(self, channel: int):             #not sure about the usecase
        self.t.write_line('SYST:LOC')
        return self.t.read_until_reol(1024) 

#SYST:SENS ON/off
#SYST:SENS?

    def write(self, data: bytes):
        self.t.write(data)

    def read(self, size=1024):
        return self.t.read(size)

    def close(self):
        self.t.close()  
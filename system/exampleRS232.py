import serial, time

ser = serial.Serial(
    #port='/dev/ttyOEL1515',       # or '/dev/ttyUSB0'
 #   port='/dev/ttySPM3103',
 #   port='/dev/ttyXDM1241',
    port='/dev/tty722540',
    baudrate=115200,     # match instrument
    #baudrate=9600,     # match instrument
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1.0,       # seconds
    xonxoff=False,     # set True if instrument wants software flow
    rtscts=False,      # set True if instrument wants hardware flow
    dsrdtr=False       # usually False; if needed, set True
)

# Explicitly assert control lines:
ser.setDTR(False)
ser.setRTS(False)

time.sleep(0.2)        # small settle time
#ser.reset_input_buffer()
#ser.reset_output_buffer()

# Try to "wake" with CR (then CRLF), then query ID:
#for wake in [b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n']:
#for wake in [b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n', b'\r\n']:
#    ser.write(wake)
#    time.sleep(0.9)
#    resp = ser.read(256)
#    print(resp)  # optional debugging

# SCPI identity query (common on loads)
#ser.write(b'*IDN?\r')
#ser.write(b'MEAS:ALL:INFO?\r')
#ser.write(b'VOUT1?')
#ser.write(b'IOUT1?')
ser.write(b'STATUS?')
#ser.write(b'ISET1?')
time.sleep(0.2)
reply = ser.read(1024)
print("Reply:", reply)
ser.close()

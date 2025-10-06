import serial
import time
from typing import Optional

def send_text_command(port: str, baud: int, command: str, seol: str = "\r", timeout: float = 1.0, read_size: int = 1024) -> Optional[str]:
    """
    Open serial port, send `command` as text (with `seol` appended), read response and return it decoded.
    Returns None on error.
    """
    ser = None
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        # assert control lines if desired
        try:
            ser.setDTR(False)
            ser.setRTS(False)
        except Exception:
            pass

        time.sleep(0.2)  # small settle

        text = f"{command}{seol}"
        print(f"Sending: {text!r}")
        ser.write(text.encode("ascii"))
        #ser.write(text.encode("utf-8"))
        time.sleep(0.2)
        resp = ser.read(read_size)
        if not resp:
            print("A")
            return ""
        try:
            print("B")
            #return resp.decode("utf-8", errors="ignore")
            return resp.decode("ascii", errors="ignore")
        except Exception:
            print("C")
            #return resp.decode("latin1", errors="ignore")
            return resp.decode("ascii", errors="ignore")
    except Exception as e:
        print("Serial error:", e)
        return None
    finally:
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass

if __name__ == "__main__":
    # adjust port/baud to your device
    port = "/dev/tty722540"
   # baud = 115200
    baud = 9600
    reply = send_text_command(port, baud, "*IDN?", seol="")
    print("Reply:", reply)
# ...existing code...
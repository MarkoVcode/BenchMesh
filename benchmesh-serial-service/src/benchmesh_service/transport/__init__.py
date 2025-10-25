"""
Transport layer for instrument communication.

This package provides abstract interfaces and concrete implementations for
communicating with SCPI-compatible instruments over various physical transports.

Available transports:
- SerialTransport: RS232/USB-Serial communication
- UsbTmcTransport: USB Test & Measurement Class (IEEE 488.2 over USB)
- (Future) TcpIpTransport: TCP/IP sockets for LXI/SCPI-over-TCP

Example usage:
    from benchmesh_service.transport import SerialTransport, UsbTmcTransport

    # Serial transport
    transport = SerialTransport('/dev/ttyUSB0', 9600).open()
    transport.write_line('*IDN?')
    response = transport.read_until_reol()
    transport.close()

    # USB TMC transport
    transport = UsbTmcTransport('/dev/usbtmc0').open()
    transport.write_line('*IDN?')
    response = transport.read_until_reol()
    transport.close()
"""

from .base import Transport
from .serial import SerialTransport
from .usbtmc import UsbTmcTransport, discover_usbtmc_devices

# Backward compatibility: export at package level
__all__ = ['Transport', 'SerialTransport', 'UsbTmcTransport', 'discover_usbtmc_devices']

#!/usr/bin/env python3
"""
Diagnostic script for OWON DGE screenshot command.
Tests different commands and reading strategies.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmesh_service.transport.usbtmc import UsbTmcTransport


def test_screenshot_commands(device_path):
    """Test various screenshot commands."""
    print(f"\n{'='*70}")
    print("Diagnostic Test for OWON DGE Screenshot Commands")
    print(f"{'='*70}\n")

    transport = UsbTmcTransport(device=device_path, timeout=10.0)

    try:
        transport.open()
        print("✓ Transport opened\n")

        # Test 1: Check device identity
        print("Test 1: Device Identity")
        print("-" * 40)
        transport.write_line('*IDN?')
        time.sleep(0.5)
        idn = transport.read_until_reol(1024)
        print(f"*IDN? Response: {idn}\n")

        # Test 2: Try different screenshot commands
        commands = [
            'HCOPy:SDUMp:DATA?',
            'HCOPY:SDUM:DATA?',
            'MMEM:DATA?',
            ':DISPlay:DATA?',
            'SYST:PRINT?',
        ]

        for cmd in commands:
            print(f"Test: {cmd}")
            print("-" * 40)

            # Clear buffer
            try:
                _ = transport.read(4096)
            except:
                pass

            # Send command
            transport.write_line(cmd)
            time.sleep(3)  # Wait for device to process

            # Read response
            response = transport.read_binary(max_bytes=1024)  # Just read first 1KB

            print(f"Response length: {len(response)} bytes")

            if response:
                # Check if it looks like IEEE 488.2 format
                if response[0:1] == b'#' and len(response) > 2:
                    try:
                        num_len = int(chr(response[1]))
                        if 1 <= num_len <= 9:
                            length_str = response[2:2+num_len].decode('ascii')
                            expected_size = int(length_str)
                            print(f"IEEE 488.2 format detected:")
                            print(f"  Length digits: {num_len}")
                            print(f"  Expected size: {expected_size} bytes")
                            print(f"  Header: {repr(response[:2+num_len])}")
                        else:
                            print(f"Invalid length digit: {num_len}")
                    except Exception as e:
                        print(f"Error parsing header: {e}")
                else:
                    # Show first 100 bytes as text
                    try:
                        text = response[:100].decode('utf-8', errors='ignore')
                        print(f"Text response: {repr(text)}")
                    except:
                        print(f"Binary data: {repr(response[:100])}")
            else:
                print("No response")

            print()
            time.sleep(2)  # Delay between commands

        # Test 3: Check error queue
        print("Test: System Error Queue")
        print("-" * 40)
        transport.write_line('SYST:ERR?')
        time.sleep(0.5)
        error = transport.read_until_reol(1024)
        print(f"Error queue: {error}\n")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if transport.is_open:
            transport.close()
            print("✓ Transport closed")


if __name__ == '__main__':
    device_path = '/dev/usbtmc4'

    if not os.path.exists(device_path):
        print(f"Error: Device {device_path} not found")
        sys.exit(1)

    test_screenshot_commands(device_path)

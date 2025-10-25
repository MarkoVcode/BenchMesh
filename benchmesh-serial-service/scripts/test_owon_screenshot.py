#!/usr/bin/env python3
"""
Test script for OWON DGE screenshot capture.

This script attempts to:
1. Restore basic USB TMC communication
2. Test the query_screenshot() method
3. Capture and save a screenshot from the device
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmesh_service.transport.usbtmc import UsbTmcTransport
from benchmesh_service.drivers.owon_dge.driver import OwonDGE


def test_basic_communication(device_path):
    """Test basic USB TMC communication."""
    print(f"\n{'='*70}")
    print(f"Testing basic communication with {device_path}")
    print(f"{'='*70}\n")

    transport = UsbTmcTransport(device=device_path, timeout=2.0, seol='\n', reol='\n')

    try:
        transport.open()
        print("✓ Transport opened successfully")

        # Clear any pending data first (don't send reset - it may disconnect device)
        print("\nClearing input buffer...")
        try:
            _ = transport.read(4096)
        except:
            pass

        # Test *IDN? without reset
        print("\nTesting *IDN? query (no reset)...")
        transport.write_line('*IDN?')
        time.sleep(0.5)
        idn = transport.read_until_reol(1024)

        if idn:
            print(f"✓ *IDN? Response: {repr(idn)}")
            return transport, True
        else:
            print("✗ *IDN? returned empty response")

            # Try reading raw data
            print("\nAttempting raw read...")
            raw = transport.read(1024)
            print(f"Raw data: {repr(raw[:100] if len(raw) > 100 else raw)}")

            return transport, False

    except Exception as e:
        print(f"✗ Communication error: {e}")
        return None, False


def test_screenshot_capture(device_path):
    """Test screenshot capture using the driver."""
    print(f"\n{'='*70}")
    print(f"Testing screenshot capture")
    print(f"{'='*70}\n")

    # Create transport with longer timeout for screenshot operations
    transport = UsbTmcTransport(device=device_path, timeout=10.0, seol='\n', reol='\n')

    try:
        # Open and initialize
        transport.open()
        print("✓ Transport opened")

        # Clear buffer (skip reset - it may disconnect device)
        print("\nClearing input buffer...")
        try:
            _ = transport.read(4096)
        except:
            pass

        # Verify communication
        print("\nVerifying communication with *IDN?...")
        transport.write_line('*IDN?')
        time.sleep(0.5)
        idn = transport.read_until_reol(1024)

        if not idn:
            print("✗ Cannot communicate with device")
            return False

        print(f"✓ Device identified: {idn}")

        # Create driver instance with existing transport
        print("\nCreating OWON DGE driver...")
        driver = OwonDGE(transport=transport)
        print("✓ Driver created")

        # Test screenshot capture
        print("\nCapturing screenshot...")
        print("This may take 5-10 seconds...")

        try:
            bmp_data = driver.query_screenshot()

            print(f"\n{'='*70}")
            print("Screenshot capture SUCCESSFUL!")
            print(f"{'='*70}")
            print(f"Image size: {len(bmp_data)} bytes")

            # Find the saved file
            import glob
            screenshots = sorted(glob.glob('/tmp/owon_dge_screenshot_*.bmp'))
            if screenshots:
                latest = screenshots[-1]
                print(f"Saved to: {latest}")
                print(f"\nTo view the image, run:")
                print(f"  eog {latest}")
                print(f"  # or")
                print(f"  xdg-open {latest}")

            return True

        except Exception as e:
            print(f"\n✗ Screenshot capture failed: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if transport and transport.is_open:
            transport.close()
            print("\n✓ Transport closed")


def main():
    device_path = '/dev/usbtmc4'

    if not os.path.exists(device_path):
        print(f"Error: Device {device_path} not found")
        print("\nAvailable USB TMC devices:")
        for entry in os.listdir('/dev'):
            if entry.startswith('usbtmc'):
                print(f"  /dev/{entry}")
        return 1

    # Step 1: Test basic communication
    transport, comm_ok = test_basic_communication(device_path)

    if transport:
        transport.close()

    if not comm_ok:
        print("\n" + "="*70)
        print("Basic communication failed. Possible issues:")
        print("  1. Device may need power cycle")
        print("  2. USB cable issue")
        print("  3. Device is in error state")
        print("  4. Incorrect EOL characters")
        print("\nPlease power cycle the device and try again.")
        print("="*70)
        return 1

    # Step 2: Test screenshot capture
    print("\n" + "="*70)
    print("Basic communication OK - proceeding to screenshot test")
    print("="*70)

    success = test_screenshot_capture(device_path)

    if success:
        print("\n" + "="*70)
        print("All tests PASSED!")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print("Screenshot test FAILED")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())

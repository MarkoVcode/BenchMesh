#!/usr/bin/env python3
"""
Production-ready screenshot test with retry logic.

Demonstrates the enhanced query_screenshot() method that:
- Retries multiple times on failure
- Accepts partial screenshots (>75% by default)
- Returns the best result from all attempts
- Provides detailed logging
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from benchmesh_service.transport.usbtmc import UsbTmcTransport
from benchmesh_service.drivers.owon_dge.driver import OwonDGE


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_default_retry(device_path):
    """Test screenshot capture with default retry settings (3 attempts, accept >75%)."""
    print(f"\n{'='*70}")
    print("Test 1: Default Retry Logic (3 attempts, accept >75%)")
    print(f"{'='*70}\n")

    transport = UsbTmcTransport(device=device_path, timeout=10.0)

    try:
        transport.open()
        driver = OwonDGE(transport=transport)

        print("Capturing screenshot with default settings...")
        print("- max_attempts: 3")
        print("- accept_partial: True")
        print("- min_completion: 0.75 (75%)")
        print()

        bmp_data = driver.query_screenshot()

        print(f"\n{'='*70}")
        print("SUCCESS! Screenshot captured.")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}\n")
        return False

    finally:
        if transport.is_open:
            transport.close()


def test_strict_retry(device_path):
    """Test screenshot capture requiring 100% completion."""
    print(f"\n{'='*70}")
    print("Test 2: Strict Mode (require 100% completion)")
    print(f"{'='*70}\n")

    transport = UsbTmcTransport(device=device_path, timeout=10.0)

    try:
        transport.open()
        driver = OwonDGE(transport=transport)

        print("Capturing screenshot with strict settings...")
        print("- max_attempts: 5")
        print("- accept_partial: False")
        print("- min_completion: 1.0 (100%)")
        print()

        bmp_data = driver.query_screenshot(
            max_attempts=5,
            accept_partial=False
        )

        print(f"\n{'='*70}")
        print("SUCCESS! Complete screenshot captured.")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        print(f"\n✗ Failed (expected for USB TMC): {e}")
        print("Note: This is expected due to USB TMC driver limitations.")
        print("      Use default settings for production.\n")
        return False

    finally:
        if transport.is_open:
            transport.close()


def test_aggressive_retry(device_path):
    """Test screenshot capture with aggressive retry (5 attempts, accept >60%)."""
    print(f"\n{'='*70}")
    print("Test 3: Aggressive Retry (5 attempts, accept >60%)")
    print(f"{'='*70}\n")

    transport = UsbTmcTransport(device=device_path, timeout=10.0)

    try:
        transport.open()
        driver = OwonDGE(transport=transport)

        print("Capturing screenshot with aggressive settings...")
        print("- max_attempts: 5")
        print("- accept_partial: True")
        print("- min_completion: 0.60 (60%)")
        print()

        bmp_data = driver.query_screenshot(
            max_attempts=5,
            accept_partial=True,
            min_completion=0.60
        )

        print(f"\n{'='*70}")
        print("SUCCESS! Screenshot captured (may be partial).")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}\n")
        return False

    finally:
        if transport.is_open:
            transport.close()


def main():
    device_path = '/dev/usbtmc4'

    if not os.path.exists(device_path):
        print(f"Error: Device {device_path} not found")
        print("\nAvailable USB TMC devices:")
        for entry in os.listdir('/dev'):
            if entry.startswith('usbtmc'):
                print(f"  /dev/{entry}")
        return 1

    print(f"\n{'='*70}")
    print("OWON DGE Screenshot Capture - Production Retry Test")
    print(f"{'='*70}")
    print(f"\nDevice: {device_path}")
    print("Testing screenshot capture with different retry strategies...")

    # Test 1: Default retry (recommended for production)
    success1 = test_default_retry(device_path)

    # Test 2: Strict mode (requires 100% - likely to fail with USB TMC)
    success2 = test_strict_retry(device_path)

    # Test 3: Aggressive retry (more tolerant)
    success3 = test_aggressive_retry(device_path)

    # Summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    print(f"Test 1 (Default):     {'PASS ✓' if success1 else 'FAIL ✗'}")
    print(f"Test 2 (Strict):      {'PASS ✓' if success2 else 'FAIL ✗'} (failure expected)")
    print(f"Test 3 (Aggressive):  {'PASS ✓' if success3 else 'FAIL ✗'}")

    print(f"\n{'='*70}")
    print("Recommendation for Production")
    print(f"{'='*70}")
    print("Use default settings:")
    print("  driver.query_screenshot()")
    print("    - Retries 3 times")
    print("    - Accepts partial screenshots >75%")
    print("    - Best balance of reliability and quality")
    print()
    print("For critical applications:")
    print("  driver.query_screenshot(max_attempts=5, min_completion=0.85)")
    print("    - More retries")
    print("    - Higher quality threshold (85%)")
    print(f"{'='*70}\n")

    # Check for saved screenshots
    import glob
    screenshots = sorted(glob.glob('/tmp/owon_dge_screenshot_*.bmp'))
    if screenshots:
        print("Screenshots saved:")
        for screenshot in screenshots[-5:]:  # Show last 5
            size = os.path.getsize(screenshot)
            print(f"  {screenshot} ({size:,} bytes)")
        print(f"\nTo view: xdg-open {screenshots[-1]}")

    return 0 if (success1 or success3) else 1


if __name__ == '__main__':
    sys.exit(main())

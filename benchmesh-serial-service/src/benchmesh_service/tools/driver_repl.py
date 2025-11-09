#!/usr/bin/env python3
"""
Interactive driver testing console with persistent state.

This REPL (Read-Eval-Print Loop) tool provides an interactive console for testing
driver methods while maintaining persistent driver state, transport connection,
and cache across commands.

Unlike driver_cli.py which creates a new driver instance for each command,
this tool keeps the driver alive throughout the session, allowing cache to
persist and providing a more realistic testing environment.

Usage:
    python -m benchmesh_service.tools.driver_repl --id <device-id> --config <config-file>

Example:
    python -m benchmesh_service.tools.driver_repl --id dmm-1 --config config.yaml

    (driver) call set_mode 1 RES
    (driver) call query_mode 1
    (driver) cache_stats
    (driver) exit
"""

import argparse
import cmd
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..cache import SimpleCache
from ..driver_factory import DriverFactory
from ..manifest_resolver import ManifestResolver
from ..transport.serial import SerialTransport


class DriverREPL(cmd.Cmd):
    """Interactive console for testing drivers with persistent state."""

    intro = "Driver REPL - Interactive driver testing console. Type 'help' for commands."
    prompt = "(driver) "

    def __init__(self, device_config: Dict[str, Any], config_path: Path):
        """Initialize the REPL with device configuration.

        Args:
            device_config: Device configuration dictionary
            config_path: Path to config file (for reference)
        """
        super().__init__()
        self.device_config = device_config
        self.config_path = config_path
        self.device_id = device_config['id']

        # Driver state
        self.driver = None
        self.transport = None
        self.driver_class_name = None

        # Set prompt with device ID
        self.prompt = f"({self.device_id}) "

        # Connect on startup
        self._connect()

    def _connect(self) -> bool:
        """Create driver instance and establish connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Close existing connection if any
            if self.driver:
                try:
                    self.driver.close()
                except Exception:
                    pass

            # Get driver name from config
            driver_name = self.device_config.get('driver')
            if not driver_name:
                print(f"ERROR: No driver specified in config for {self.device_id}")
                return False

            # Initialize resolver and factory
            resolver = ManifestResolver()
            factory = DriverFactory()

            # Load driver class
            try:
                driver_class = factory.load_driver_class(driver_name)
            except Exception as e:
                print(f"ERROR: Cannot load driver '{driver_name}': {e}")
                return False

            # Get EOL settings from manifest
            seol, reol = resolver.get_connection_eol(self.device_config)

            # Create transport
            transport_type = self.device_config.get('transport', 'serial')

            if transport_type == 'serial':
                self.transport = SerialTransport(
                    port=self.device_config['port'],
                    baudrate=self.device_config.get('baud', 9600),
                    timeout=0.3,
                    serial_mode=self.device_config.get('serial', '8N1'),
                    seol=seol,
                    reol=reol
                ).open()
            else:
                print(f"ERROR: Unsupported transport type: {transport_type}")
                return False

            # Create driver instance with transport
            self.driver = driver_class(transport=self.transport)
            self.driver_class_name = self.driver.__class__.__name__

            # Test connection by calling query_identify
            try:
                idn = self.driver.query_identify()
                print(f"Connected to {self.device_id}: {idn}")
                return True
            except Exception as e:
                print(f"WARNING: Connected but query_identify failed: {e}")
                return True  # Still consider connected, driver may not support IDN

        except Exception as e:
            print(f"ERROR: Failed to connect: {e}")
            self.driver = None
            self.transport = None
            return False

    def _ensure_connected(self) -> bool:
        """Ensure driver is connected, return False if not."""
        if not self.driver:
            print("ERROR: Not connected. Use 'reconnect' to establish connection.")
            return False
        return True

    def do_call(self, arg: str):
        """Call a driver method with arguments.

        Usage: call <method_name> [args...]

        Examples:
            call query_voltage 1
            call set_mode 1 RES
            call query_identify
        """
        if not self._ensure_connected():
            return

        parts = arg.split()
        if not parts:
            print("ERROR: Method name required")
            print("Usage: call <method_name> [args...]")
            return

        method_name = parts[0]
        args = parts[1:]

        # Check if method exists
        if not hasattr(self.driver, method_name):
            print(f"ERROR: Method '{method_name}' not found on driver")
            print("Use 'methods' to see available methods")
            return

        method = getattr(self.driver, method_name)
        if not callable(method):
            print(f"ERROR: '{method_name}' is not a method")
            return

        # Get method signature
        sig = inspect.signature(method)
        params = list(sig.parameters.values())

        # Parse arguments
        parsed_args = []
        for i, arg_str in enumerate(args):
            if i >= len(params):
                break  # Extra args, will be caught by call

            param = params[i]
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str

            try:
                # Try to convert to appropriate type
                if param_type == int:
                    parsed_args.append(int(arg_str))
                elif param_type == float:
                    parsed_args.append(float(arg_str))
                elif param_type == bool:
                    parsed_args.append(arg_str.lower() in ('true', '1', 'yes', 'on'))
                else:
                    # Keep as string
                    parsed_args.append(arg_str)
            except ValueError as e:
                print(f"ERROR: Cannot convert argument {i+1} to {param_type.__name__}: {e}")
                return

        # Call method
        try:
            result = method(*parsed_args)

            # Format output
            if result is not None:
                if isinstance(result, dict):
                    print(json.dumps(result, indent=2))
                else:
                    print(result)
            else:
                print("(no return value)")

        except Exception as e:
            print(f"ERROR: Method call failed: {e}")

    def do_methods(self, arg: str):
        """List all available methods on the driver.

        Usage: methods [filter]

        Examples:
            methods           # List all methods
            methods query     # List only query methods
            methods set       # List only set methods
        """
        if not self._ensure_connected():
            return

        filter_str = arg.strip().lower() if arg else None

        # Get all public methods
        methods = []
        for name in dir(self.driver):
            if name.startswith('_'):
                continue

            attr = getattr(self.driver, name)
            if not callable(attr):
                continue

            if filter_str and filter_str not in name.lower():
                continue

            # Get signature
            try:
                sig = inspect.signature(attr)
                sig_str = str(sig)
            except Exception:
                sig_str = "(...)"

            methods.append((name, sig_str))

        if not methods:
            if filter_str:
                print(f"No methods matching '{filter_str}'")
            else:
                print("No public methods found")
            return

        # Print methods
        print(f"\nAvailable methods on {self.driver_class_name}:")
        print("-" * 60)
        for name, sig_str in sorted(methods):
            print(f"  {name}{sig_str}")
        print()

    def do_cache_stats(self, arg: str):
        """Display cache statistics.

        Usage: cache_stats
        """
        if not self._ensure_connected():
            return

        if not hasattr(self.driver, 'cache') or not isinstance(self.driver.cache, SimpleCache):
            print("Driver does not have a SimpleCache instance")
            return

        stats = self.driver.cache.get_stats()

        print("\nCache Statistics:")
        print("-" * 60)
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']:.1%}")
        print(f"  Evictions: {stats['evictions']}")
        print()

        if stats['total_entries'] > 0:
            print("Cache contents:")
            for key in sorted(self.driver.cache._cache.keys()):
                entry = self.driver.cache._cache[key]
                print(f"  {key}: {entry.value} (expires in {entry.expires_at - __import__('time').time():.1f}s)")
            print()

    def do_cache_clear(self, arg: str):
        """Clear all cache entries.

        Usage: cache_clear
        """
        if not self._ensure_connected():
            return

        if not hasattr(self.driver, 'cache') or not isinstance(self.driver.cache, SimpleCache):
            print("Driver does not have a SimpleCache instance")
            return

        self.driver.cache.clear()
        print("Cache cleared")

    def do_cache_invalidate(self, arg: str):
        """Invalidate a specific cache key.

        Usage: cache_invalidate <key>

        Example:
            cache_invalidate mode_1
        """
        if not self._ensure_connected():
            return

        if not arg.strip():
            print("ERROR: Key required")
            print("Usage: cache_invalidate <key>")
            return

        if not hasattr(self.driver, 'cache') or not isinstance(self.driver.cache, SimpleCache):
            print("Driver does not have a SimpleCache instance")
            return

        key = arg.strip()
        self.driver.cache.invalidate(key)
        print(f"Invalidated cache key: {key}")

    def do_reconnect(self, arg: str):
        """Reconnect to the device.

        This closes the existing connection and creates a new driver instance.
        Cache will be reset.

        Usage: reconnect
        """
        print("Reconnecting...")
        if self._connect():
            print("Reconnected successfully")
        else:
            print("Reconnection failed")

    def do_info(self, arg: str):
        """Display device and driver information.

        Usage: info
        """
        print("\nDevice Information:")
        print("-" * 60)
        print(f"  Device ID: {self.device_id}")
        print(f"  Driver: {self.device_config.get('driver', 'unknown')}")
        print(f"  Transport: {self.device_config.get('transport', 'serial')}")

        if self.device_config.get('transport', 'serial') == 'serial':
            print(f"  Port: {self.device_config.get('port', 'unknown')}")
            print(f"  Baud: {self.device_config.get('baud', 9600)}")

        if self.driver:
            print(f"  Driver class: {self.driver_class_name}")
            print(f"  Connected: Yes")
        else:
            print(f"  Connected: No")

        print()

    def do_exit(self, arg: str):
        """Exit the REPL.

        Usage: exit
        """
        print("Closing connection and exiting...")
        return True

    def do_quit(self, arg: str):
        """Exit the REPL (alias for 'exit').

        Usage: quit
        """
        return self.do_exit(arg)

    def do_EOF(self, arg: str):
        """Handle Ctrl+D."""
        print()  # New line after ^D
        return self.do_exit(arg)

    def emptyline(self):
        """Do nothing on empty line (override default repeat behavior)."""
        pass

    def precmd(self, line: str) -> str:
        """Hook before command execution."""
        return line

    def postcmd(self, stop: bool, line: str) -> bool:
        """Hook after command execution."""
        return stop

    def __del__(self):
        """Cleanup on destruction."""
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass


def main():
    """Main entry point for driver REPL."""
    parser = argparse.ArgumentParser(
        description="Interactive driver testing console with persistent state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start REPL for DMM device
  python -m benchmesh_service.tools.driver_repl --id dmm-1 --config config.yaml

  # Then in the REPL:
  (dmm-1) call set_mode 1 RES
  (dmm-1) call query_mode 1
  (dmm-1) cache_stats
  (dmm-1) exit
        """
    )

    parser.add_argument(
        '--id',
        required=True,
        help='Device ID from config file'
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config.yaml'),
        help='Path to config file (default: config.yaml)'
    )

    args = parser.parse_args()

    # Load config
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        sys.exit(1)

    # Find device
    devices = config.get('devices', [])
    device_config = None

    for dev in devices:
        if dev.get('id') == args.id:
            device_config = dev
            break

    if not device_config:
        print(f"ERROR: Device '{args.id}' not found in config")
        print(f"\nAvailable devices:")
        for dev in devices:
            print(f"  - {dev.get('id')} ({dev.get('driver', 'unknown')})")
        sys.exit(1)

    # Start REPL
    try:
        repl = DriverREPL(device_config, args.config)
        repl.cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: REPL failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
EOL Auto-Detection for Serial Devices

This module automatically detects the correct End-Of-Line (seol/reol) settings
for serial devices when the manifest-provided settings don't work.
"""
from typing import Optional, Tuple, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EolConfig:
    """EOL configuration with human-readable name."""
    seol: str
    reol: str
    name: str

    def __str__(self):
        seol_repr = repr(self.seol) if self.seol else "''"
        reol_repr = repr(self.reol) if self.reol else "''"
        return f"{self.name} (seol={seol_repr}, reol={reol_repr})"


def get_eol_configurations(initial_seol: Optional[str], initial_reol: Optional[str]) -> List[EolConfig]:
    """
    Return list of EOL configurations to try, in order of priority.

    Priority:
    1. User-provided configuration (from manifest)
    2. Common industry standards
    3. Less common but valid combinations
    """
    configs = []

    # 1. Always try user-provided config first (if provided)
    if initial_seol is not None or initial_reol is not None:
        configs.append(EolConfig(
            seol=initial_seol or "",
            reol=initial_reol or "",
            name="Manifest-provided"
        ))

    # 2. Most common industry standard combinations
    standard_combos = [
        # CRLF - Windows standard, very common in instruments
        EolConfig("\r\n", "\r\n", "CRLF/CRLF (Windows)"),
        EolConfig("\r\n", "\n", "CRLF/LF"),

        # CR only - Classic instrument standard (HP, Agilent, Keysight)
        EolConfig("\r", "\r", "CR/CR (Classic instrument)"),

        # LF only - Unix/Linux standard
        EolConfig("\n", "\n", "LF/LF (Unix)"),
        EolConfig("\n", "\r\n", "LF/CRLF"),

        # Empty/minimal - Some devices don't use EOL
        EolConfig("", "", "None/None"),
        EolConfig("\r", "", "CR/None"),
        EolConfig("", "\r", "None/CR"),

        # Less common but valid
        EolConfig("\n\r", "\n\r", "LFCR/LFCR"),
        EolConfig("\r", "\n", "CR/LF"),
        EolConfig("\n", "\r", "LF/CR"),
        EolConfig("", "\r\n", "None/CRLF"),
        EolConfig("", "\n", "None/LF"),
    ]

    # Add only configs that are different from user-provided
    user_combo = (initial_seol or "", initial_reol or "")
    for config in standard_combos:
        if (config.seol, config.reol) != user_combo:
            configs.append(config)

    return configs


def detect_eol_for_driver(
    driver_class,
    port: str,
    baudrate: int,
    serial_mode: str,
    initial_seol: Optional[str],
    initial_reol: Optional[str],
    device_id: str
) -> Optional[Tuple[str, str]]:
    """
    Auto-detect correct EOL settings for a device by trying different configurations.

    Args:
        driver_class: The driver class to instantiate
        port: Serial port path
        baudrate: Baud rate
        serial_mode: Serial mode (e.g., "8N1")
        initial_seol: Initial send EOL from manifest
        initial_reol: Initial receive EOL from manifest
        device_id: Device ID for logging

    Returns:
        Tuple of (seol, reol) if successful, None if all attempts failed
    """
    configs = get_eol_configurations(initial_seol, initial_reol)

    logger.info(f"[{device_id}] Starting EOL auto-detection. Will try {len(configs)} configurations...")

    for i, config in enumerate(configs, 1):
        logger.debug(f"[{device_id}] [{i}/{len(configs)}] Trying {config}")

        driver = None
        try:
            # Instantiate driver with this EOL configuration
            driver = driver_class(
                port,
                baudrate,
                serial_mode=serial_mode,
                seol=config.seol,
                reol=config.reol,
            )

            # Try to identify the device using query_identify
            if hasattr(driver, 'query_identify'):
                response = driver.query_identify()

                # Validate response
                if response and _is_valid_identify_response(response):
                    logger.info(
                        f"[{device_id}] ✓ EOL AUTO-DETECTION SUCCESS: {config}\n"
                        f"[{device_id}]   Response: {response}\n"
                        f"[{device_id}]   Recommended manifest settings: "
                        f'seol="{_escape_for_log(config.seol)}", '
                        f'reol="{_escape_for_log(config.reol)}"'
                    )
                    return (config.seol, config.reol)
                else:
                    logger.debug(
                        f"[{device_id}] [{i}/{len(configs)}] ✗ Failed: "
                        f"Invalid response: {repr(response[:50]) if response else 'None'}"
                    )
            else:
                logger.debug(f"[{device_id}] [{i}/{len(configs)}] ✗ Failed: No query_identify method")

        except Exception as e:
            logger.debug(f"[{device_id}] [{i}/{len(configs)}] ✗ Failed: {e}")
        finally:
            # Clean up driver instance
            if driver:
                try:
                    driver.close()
                except Exception:
                    pass

    logger.warning(
        f"[{device_id}] EOL auto-detection FAILED - could not find working configuration. "
        f"Tried {len(configs)} combinations. Check device connection, baudrate, and serial mode."
    )
    return None


def _is_valid_identify_response(response: str) -> bool:
    """
    Validate that the response looks like a valid device identification.

    A valid response should:
    - Not be empty
    - Contain alphanumeric characters
    - Be between 3 and 500 characters
    """
    if not response:
        return False

    # Check for alphanumeric content
    if not any(c.isalnum() for c in response):
        return False

    # Check reasonable length
    if len(response) < 3 or len(response) > 500:
        return False

    return True


def _escape_for_log(s: str) -> str:
    """Escape string for readable logging output."""
    if not s:
        return ""
    return s.encode('unicode-escape').decode('ascii')

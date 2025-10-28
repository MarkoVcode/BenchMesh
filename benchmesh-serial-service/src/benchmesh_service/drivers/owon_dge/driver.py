"""
OWON DGE Series Function/Arbitrary Waveform Generator Driver
Supports DGE2070, DGE2035, DGE3032, DGE3062, DGE3031, DGE3061
"""
import os
from datetime import datetime
from ..base import DriverBase
from ...transport.utils import parse_ieee488_binary_block


class OwonDGE(DriverBase):
    """Driver for OWON DGE series function generators"""

    def query_identify(self):
        """Query device identification"""
        self.t.write_line('*IDN?')
        return self.t.read_until_reol(1024)

    def poll_status(self, channel: int = 1):
        """Poll device status - simplified to prevent USB TMC buffer issues"""
        # For AWG, channel is typically not used (single-instrument status)
        # But we accept it for API compatibility
        try:
            # Just query output state as minimal health check
            # Full status can be queried via API when needed
            output = self.query_output(channel)
            return {
                "OUTPUT": output
            }
        except Exception as e:
            # Re-raise exception to trigger health failure tracking
            raise

    def set_output(self, channel: int, state: str):
        """Enable/disable output channel"""
        # SCPI set commands don't return responses - just write, don't read
        self.t.write_line(f'OUTPut{channel}:STATe {state}')

    def query_output(self, channel: int):
        """Query output channel state"""
        self.t.write_line(f'OUTPut{channel}:STATe?')
        response = self.t.read_until_reol(1024)
        if response.strip() == '1':
            return 'ON'
        else:
            return 'OFF'
    
    def query_shape(self, channel: int):
        self.t.write_line(f'SOURce{channel}:FUNCtion:SHAPe?')
        return self.t.read_until_reol(1024)

    def query_symmetry(self, channel: int):
        self.t.write_line(f'SOURce{channel}:FUNCtion:RAMP:SYMMetry?')
        return self.t.read_until_reol(1024)

    def query_screenshot(self, save_path: str = None, max_attempts: int = 3,
                        accept_partial: bool = True, min_completion: float = 0.75) -> bytes:
        """
        Capture screenshot from device display and return BMP image data.

        The device returns data in IEEE 488.2 binary block format:
        #6377512<BMP data> where:
        - 6 = number of digits in length field
        - 377512 = length of binary data in bytes
        - <BMP data> = actual BMP image data

        Note:
            Due to USB TMC driver limitations with large binary transfers, this method
            implements retry logic and accepts partial screenshots (>75% by default).
            The best result from multiple attempts is returned.

        Args:
            save_path: Optional path to save the BMP file. If None, generates
                      a timestamped filename in /tmp/
            max_attempts: Maximum number of capture attempts (default: 3)
            accept_partial: If True, accept partial screenshots above min_completion
            min_completion: Minimum completion ratio to accept (0.0-1.0, default: 0.75)

        Returns:
            Raw BMP image data (bytes) - may be partial if accept_partial=True

        Raises:
            ValueError: If no acceptable screenshot could be captured after max_attempts

        Example:
            >>> driver = OwonDGE(transport=transport)
            >>> # Accept partial screenshots >75% complete
            >>> bmp_data = driver.query_screenshot()
            >>> # Require 95% completion
            >>> bmp_data = driver.query_screenshot(min_completion=0.95)
            >>> # Must be 100% complete
            >>> bmp_data = driver.query_screenshot(accept_partial=False)
        """
        import time
        import logging

        logger = logging.getLogger(__name__)
        best_result = None
        best_completion = 0.0
        best_size = 0

        for attempt in range(max_attempts):
            try:
                logger.info(f"Screenshot attempt {attempt + 1}/{max_attempts}")

                # Send screenshot dump command
                self.t.write_line('HCOPy:SDUMp:DATA?')

                # Wait for device to generate screenshot (can take 1-3 seconds)
                time.sleep(2)

                # Read IEEE 488.2 header first to determine total size
                header = self.t.read_binary(max_bytes=12)

                if not header or header[0:1] != b'#':
                    logger.warning(f"Attempt {attempt + 1}: Invalid header {repr(header[:50])}")
                    continue

                # Parse header to get expected data length
                num_length_digits = int(chr(header[1]))
                if num_length_digits < 1 or num_length_digits > 9:
                    logger.warning(f"Attempt {attempt + 1}: Invalid length digit {num_length_digits}")
                    continue

                header_size = 2 + num_length_digits
                expected_length = int(header[2:header_size].decode('ascii'))

                logger.info(f"Attempt {attempt + 1}: Expected {expected_length} bytes")

                # Read remaining data in chunks
                raw_response = header
                bytes_needed = expected_length - (len(header) - header_size)
                retry_count = 0
                max_retries = 15

                while bytes_needed > 0 and retry_count < max_retries:
                    chunk_size = min(bytes_needed, 65536)  # Read in 64KB chunks
                    chunk = self.t.read_binary(max_bytes=chunk_size)

                    if not chunk:
                        retry_count += 1
                        time.sleep(1.0)
                        continue

                    # Got data - reset retry counter
                    retry_count = 0
                    raw_response += chunk
                    bytes_needed -= len(chunk)

                # Calculate completion ratio
                total_received = len(raw_response) - header_size
                completion = total_received / expected_length if expected_length > 0 else 0.0

                logger.info(f"Attempt {attempt + 1}: Received {total_received}/{expected_length} bytes ({completion*100:.1f}%)")

                # Parse IEEE 488.2 binary block format
                try:
                    bmp_data = parse_ieee488_binary_block(raw_response)

                    # Full success!
                    logger.info(f"Attempt {attempt + 1}: Complete screenshot captured!")
                    best_result = bmp_data
                    best_completion = 1.0
                    best_size = len(bmp_data)
                    break

                except ValueError as e:
                    # Partial data - store if it's the best so far
                    if completion > best_completion:
                        best_result = raw_response[header_size:]  # Save raw data without header
                        best_completion = completion
                        best_size = total_received
                        logger.info(f"Attempt {attempt + 1}: Best partial result so far ({completion*100:.1f}%)")

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                continue

            # Small delay between attempts to let device/driver recover
            if attempt < max_attempts - 1:
                time.sleep(2)

        # Evaluate results
        if best_result is None:
            raise ValueError("Failed to capture any screenshot data after all attempts")

        if best_completion >= 1.0:
            logger.info(f"Screenshot capture successful: {best_size} bytes (100%)")
            bmp_data = best_result

        elif accept_partial and best_completion >= min_completion:
            logger.warning(
                f"Returning partial screenshot: {best_size} bytes ({best_completion*100:.1f}% complete). "
                f"USB TMC driver limitation - this is expected behavior."
            )
            bmp_data = best_result

        else:
            raise ValueError(
                f"Screenshot incomplete: {best_size} bytes ({best_completion*100:.1f}% complete). "
                f"Required: {min_completion*100:.0f}%. Try increasing max_attempts or lowering min_completion."
            )

        # Save to file for testing/debugging
        if save_path is None:
            # Generate timestamped filename in /tmp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            completion_suffix = "complete" if best_completion >= 1.0 else f"{int(best_completion*100)}pct"
            save_path = f'/tmp/owon_dge_screenshot_{timestamp}_{completion_suffix}.bmp'

        try:
            with open(save_path, 'wb') as f:
                f.write(bmp_data)

            completion_status = "Complete" if best_completion >= 1.0 else f"Partial ({best_completion*100:.1f}%)"
            logger.info(f"Screenshot saved to: {save_path}")
            logger.info(f"Status: {completion_status}, Size: {len(bmp_data)} bytes")

            # Also print for CLI usage
            print(f"Screenshot saved to: {save_path}")
            print(f"Status: {completion_status}")
            print(f"Image size: {len(bmp_data)} bytes")

        except Exception as e:
            logger.error(f"Could not save screenshot to {save_path}: {e}")
            print(f"Warning: Could not save screenshot to {save_path}: {e}")

        return bmp_data

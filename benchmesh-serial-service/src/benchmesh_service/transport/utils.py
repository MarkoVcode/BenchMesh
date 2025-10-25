"""
Transport utility functions for binary data handling.

This module provides utilities for parsing and handling binary data
from test instruments, particularly IEEE 488.2 definite length binary blocks.
"""


def parse_ieee488_binary_block(data: bytes) -> bytes:
    """
    Parse IEEE 488.2 definite length binary block format.

    The IEEE 488.2 standard defines a format for binary data transfer:
        #<N><LENGTH><DATA>

    Where:
        # = Header character (ASCII 35)
        <N> = Single digit (1-9) indicating number of digits in <LENGTH>
        <LENGTH> = ASCII decimal number specifying byte count of <DATA>
        <DATA> = Binary data of specified length

    Examples:
        #800001024<1024 bytes>  -> 8 digits, length 1024
        #212OK<2 bytes>         -> 2 digits, length 12, data is "OK"
        #42000<2000 bytes>      -> 4 digits, length 2000

    Args:
        data: Raw bytes from instrument including IEEE 488.2 header

    Returns:
        Binary data portion only (header removed)

    Raises:
        ValueError: If data doesn't match IEEE 488.2 binary block format

    Note:
        If data doesn't start with '#', returns data unchanged (pass-through).
        This allows calling this function even when format is uncertain.
    """
    if not data:
        return data

    # Pass through if not IEEE 488.2 format
    if data[0:1] != b'#':
        return data

    if len(data) < 2:
        raise ValueError("Invalid IEEE 488.2 binary block: too short")

    # Extract number of length digits
    try:
        num_length_digits = int(chr(data[1]))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid IEEE 488.2 binary block: bad length digit: {e}")

    if num_length_digits < 1 or num_length_digits > 9:
        raise ValueError(f"Invalid IEEE 488.2 binary block: length digit must be 1-9, got {num_length_digits}")

    # Extract length value
    length_start = 2
    length_end = 2 + num_length_digits

    if len(data) < length_end:
        raise ValueError("Invalid IEEE 488.2 binary block: incomplete length field")

    try:
        length = int(data[length_start:length_end].decode('ascii'))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid IEEE 488.2 binary block: bad length value: {e}")

    # Extract binary data
    data_start = length_end
    data_end = data_start + length

    if len(data) < data_end:
        raise ValueError(
            f"Invalid IEEE 488.2 binary block: incomplete data "
            f"(expected {length} bytes, got {len(data) - data_start})"
        )

    return data[data_start:data_end]


def looks_like_binary_data(data: bytes, threshold: float = 0.3) -> bool:
    """
    Heuristic to detect if data is likely binary rather than text.

    Checks for:
    1. IEEE 488.2 binary block header (#<digit>)
    2. High proportion of non-printable characters

    Args:
        data: Bytes to analyze
        threshold: Fraction of non-printable characters to consider binary (0.0-1.0)

    Returns:
        True if data appears to be binary, False if likely text

    Note:
        This is a heuristic, not a guarantee. Use with caution.
    """
    if not data:
        return False

    # Check for IEEE 488.2 definite length binary block header
    # Format: #<digit><length><data>
    if len(data) >= 2 and data[0:1] == b'#' and data[1:2].isdigit():
        return True

    # Count non-printable characters in first 100 bytes
    sample = data[:min(100, len(data))]
    non_printable = sum(
        1 for b in sample
        if b < 32 or b > 126  # Outside printable ASCII range
        if b not in (9, 10, 13)  # Except tab, LF, CR
    )

    return (non_printable / len(sample)) > threshold


def parse_multiple_ieee488_blocks(data: bytes) -> list[bytes]:
    """
    Parse multiple IEEE 488.2 binary blocks from single response.

    Some instruments return multiple binary blocks in one response.
    This function extracts all blocks sequentially.

    Args:
        data: Raw bytes potentially containing multiple IEEE 488.2 blocks

    Returns:
        List of binary data blocks (headers removed)

    Example:
        data = b'#212AB#13XYZ#14QRST'
        result = [b'AB', b'XYZ', b'QRST']
    """
    blocks = []
    offset = 0

    while offset < len(data):
        # Find next block header
        header_pos = data.find(b'#', offset)
        if header_pos == -1:
            break

        # Try to parse block starting at this position
        try:
            remaining = data[header_pos:]
            block = parse_ieee488_binary_block(remaining)
            blocks.append(block)

            # Calculate how many bytes this block consumed (including header)
            if remaining[0:1] == b'#':
                num_length_digits = int(chr(remaining[1]))
                length = int(remaining[2:2+num_length_digits].decode('ascii'))
                block_total_size = 2 + num_length_digits + length
                offset = header_pos + block_total_size
            else:
                break
        except ValueError:
            # Not a valid block, skip this '#' and continue searching
            offset = header_pos + 1

    return blocks

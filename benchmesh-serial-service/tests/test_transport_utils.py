"""
Tests for transport utility functions (binary data parsing).
"""

import pytest
from benchmesh_service.transport.utils import (
    parse_ieee488_binary_block,
    looks_like_binary_data,
    parse_multiple_ieee488_blocks
)


class TestParseIEEE488BinaryBlock:
    """Test IEEE 488.2 binary block parsing."""

    def test_simple_binary_block(self):
        """Test parsing a simple binary block."""
        # #12AB means: 1 digit for length, length 2, data "AB"
        data = b'#12AB'
        result = parse_ieee488_binary_block(data)
        assert result == b'AB'

    def test_binary_block_with_zeros(self):
        """Test parsing binary block containing null bytes."""
        # #48 means: 4 digits, length (calculated below)
        payload = b'\x00\x01\x02\xFF'
        header = b'#4' + f'{len(payload):04d}'.encode() + payload
        result = parse_ieee488_binary_block(header)
        assert result == payload

    def test_large_binary_block(self):
        """Test parsing large binary block (1KB)."""
        payload = b'\xFF' * 1024
        header = b'#4' + b'1024' + payload
        result = parse_ieee488_binary_block(header)
        assert result == payload
        assert len(result) == 1024

    def test_binary_block_with_waveform_data(self):
        """Test parsing typical oscilloscope waveform data."""
        # Typical waveform: 10000 samples, 2 bytes each = 20000 bytes
        payload = b'\x12\x34' * 10000
        header = b'#5' + b'20000' + payload
        result = parse_ieee488_binary_block(header)
        assert len(result) == 20000
        assert result[:2] == b'\x12\x34'

    def test_non_ieee488_data_passthrough(self):
        """Test that non-IEEE 488.2 data passes through unchanged."""
        data = b'OWON,DGE2070,SN12345'
        result = parse_ieee488_binary_block(data)
        assert result == data

    def test_empty_data(self):
        """Test handling empty data."""
        result = parse_ieee488_binary_block(b'')
        assert result == b''

    def test_invalid_length_digit(self):
        """Test error on invalid length digit."""
        data = b'#X12AB'  # 'X' is not a digit
        with pytest.raises(ValueError, match='bad length digit'):
            parse_ieee488_binary_block(data)

    def test_length_digit_out_of_range(self):
        """Test error on length digit out of range."""
        data = b'#012AB'  # 0 is invalid
        with pytest.raises(ValueError, match='length digit must be 1-9'):
            parse_ieee488_binary_block(data)

        data = b'#A12AB'  # 10 would be invalid
        with pytest.raises(ValueError, match='bad length digit'):
            parse_ieee488_binary_block(data)

    def test_incomplete_length_field(self):
        """Test error on incomplete length field."""
        data = b'#4'  # Says 4 digits but doesn't have them
        with pytest.raises(ValueError, match='incomplete length field'):
            parse_ieee488_binary_block(data)

    def test_invalid_length_value(self):
        """Test error on non-numeric length value."""
        data = b'#4ABCDXX'  # Length should be digits
        with pytest.raises(ValueError, match='bad length value'):
            parse_ieee488_binary_block(data)

    def test_incomplete_data(self):
        """Test error when data is shorter than specified length."""
        # Says 1000 bytes but only provides 10
        data = b'#410001234567890'
        with pytest.raises(ValueError, match='incomplete data'):
            parse_ieee488_binary_block(data)

    def test_exact_length_match(self):
        """Test that exact length matching works."""
        # #38 means 3 digits for length, length=100
        payload = b'X' * 100
        data = b'#3100' + payload
        result = parse_ieee488_binary_block(data)
        assert len(result) == 100
        assert result == payload


class TestLooksLikeBinaryData:
    """Test binary data detection heuristic."""

    def test_ieee488_header_detected(self):
        """Test that IEEE 488.2 headers are detected as binary."""
        data = b'#42000' + b'\x00' * 2000
        assert looks_like_binary_data(data) is True

    def test_text_data_detected(self):
        """Test that plain text is not detected as binary."""
        data = b'OWON,DGE2070,25130086,SCPI:99.0'
        assert looks_like_binary_data(data) is False

    def test_high_non_printable_ratio_detected(self):
        """Test that data with many non-printable chars is detected as binary."""
        # 80% non-printable characters
        data = b'\x00\x01\x02\xFF' * 20 + b'OK'
        assert looks_like_binary_data(data, threshold=0.3) is True

    def test_low_non_printable_ratio_not_binary(self):
        """Test that data with few non-printable chars is not detected as binary."""
        # Mostly printable with some control chars
        data = b'Normal text\nwith\nnewlines\r\n'
        assert looks_like_binary_data(data, threshold=0.3) is False

    def test_empty_data_not_binary(self):
        """Test that empty data is not considered binary."""
        assert looks_like_binary_data(b'') is False

    def test_whitespace_not_considered_non_printable(self):
        """Test that tabs, LF, CR are not counted as non-printable."""
        data = b'Text\twith\ntabs\rand\r\nnewlines'
        assert looks_like_binary_data(data) is False

    def test_threshold_adjustment(self):
        """Test that threshold parameter affects detection."""
        # 40% non-printable
        data = b'\x00\x00ABC'  # 2 out of 5 = 40%

        assert looks_like_binary_data(data, threshold=0.3) is True  # 40% > 30%
        assert looks_like_binary_data(data, threshold=0.5) is False  # 40% < 50%


class TestParseMultipleIEEE488Blocks:
    """Test parsing multiple IEEE 488.2 binary blocks from one response."""

    def test_single_block(self):
        """Test parsing single block."""
        # #12AB means: 1 digit for length, length 2, data "AB"
        data = b'#12AB'
        result = parse_multiple_ieee488_blocks(data)
        assert len(result) == 1
        assert result[0] == b'AB'

    def test_multiple_blocks(self):
        """Test parsing multiple consecutive blocks."""
        # #12AB means: 1 digit, length 2, data "AB"
        # #13XYZ means: 1 digit, length 3, data "XYZ"
        # #14QRST means: 1 digit, length 4, data "QRST"
        data = b'#12AB#13XYZ#14QRST'
        result = parse_multiple_ieee488_blocks(data)
        assert len(result) == 3
        assert result[0] == b'AB'
        assert result[1] == b'XYZ'
        assert result[2] == b'QRST'

    def test_blocks_with_separators(self):
        """Test parsing blocks separated by other data."""
        # Some instruments put commas or spaces between blocks
        # #12AB means: 1 digit, length 2, data "AB"
        # #13XYZ means: 1 digit, length 3, data "XYZ"
        data = b'#12AB,#13XYZ'
        result = parse_multiple_ieee488_blocks(data)
        # Should find both blocks despite the comma
        assert len(result) == 2
        assert result[0] == b'AB'
        assert result[1] == b'XYZ'

    def test_no_blocks(self):
        """Test parsing data without any IEEE 488.2 blocks."""
        data = b'Just normal text'
        result = parse_multiple_ieee488_blocks(data)
        assert result == []

    def test_empty_data(self):
        """Test parsing empty data."""
        result = parse_multiple_ieee488_blocks(b'')
        assert result == []

    def test_invalid_blocks_skipped(self):
        """Test that invalid blocks are skipped."""
        # Second "block" is invalid (bad format: #X instead of #digit)
        # #12AB is valid: 1 digit, length 2, data "AB"
        # #X3XYZ is invalid
        # #14QRST is valid: 1 digit, length 4, data "QRST"
        data = b'#12AB#X3XYZ#14QRST'
        result = parse_multiple_ieee488_blocks(data)
        # Should still find the valid blocks
        assert len(result) == 2
        assert result[0] == b'AB'
        assert result[1] == b'QRST'

    def test_large_multiple_blocks(self):
        """Test parsing multiple large blocks."""
        block1 = b'#41000' + b'A' * 1000
        block2 = b'#42000' + b'B' * 2000
        data = block1 + block2

        result = parse_multiple_ieee488_blocks(data)
        assert len(result) == 2
        assert len(result[0]) == 1000
        assert len(result[1]) == 2000
        assert result[0] == b'A' * 1000
        assert result[1] == b'B' * 2000

"""
Pydantic request models for FastAPI endpoints.

These models provide type-safe request validation and automatic OpenAPI documentation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Configuration Request Models
# ============================================================================

class DeviceConfig(BaseModel):
    """Device configuration for adding/updating devices."""

    id: str = Field(
        description="Unique device identifier",
        example="psu-1",
        min_length=1,
        max_length=50
    )
    name: str = Field(
        description="Human-readable device name",
        example="TENMA PSU",
        min_length=1
    )
    driver: str = Field(
        description="Driver name (matches driver folder name)",
        example="tenma_72"
    )
    port: str = Field(
        description="Serial port path or device path",
        example="/dev/ttyUSB0"
    )
    baud: int = Field(
        description="Baud rate for serial communication",
        example=9600
    )
    serial: str = Field(
        description="Serial format: data bits, parity, stop bits",
        example="8N1",
        pattern="^[5-8][NEO][1-2]$"
    )
    model: Optional[str] = Field(
        None,
        description="Model override (optional, overrides auto-detection)",
        example="72-2540"
    )
    transport: Optional[str] = Field(
        "serial",
        description="Transport type: serial or usbtmc",
        example="serial"
    )

    @field_validator('baud')
    @classmethod
    def validate_baud(cls, v: int) -> int:
        """Validate baud rate is a standard value."""
        valid_bauds = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]
        if v not in valid_bauds:
            raise ValueError(
                f"Invalid baud rate. Must be one of: {', '.join(map(str, valid_bauds))}"
            )
        return v

    @field_validator('transport')
    @classmethod
    def validate_transport(cls, v: Optional[str]) -> str:
        """Validate transport type."""
        if v is None:
            return "serial"
        if v not in ["serial", "usbtmc"]:
            raise ValueError("Transport must be 'serial' or 'usbtmc'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "psu-1",
                    "name": "TENMA PSU",
                    "driver": "tenma_72",
                    "port": "/dev/ttyUSB0",
                    "baud": 9600,
                    "serial": "8N1",
                    "transport": "serial"
                },
                {
                    "id": "awg-1",
                    "name": "OWON AWG",
                    "driver": "owon_dge",
                    "port": "/dev/usbtmc0",
                    "baud": 9600,
                    "serial": "8N1",
                    "model": "DGE2070",
                    "transport": "usbtmc"
                }
            ]
        }
    }


class ConfigUpdate(BaseModel):
    """Configuration update request with list of devices."""

    devices: List[DeviceConfig] = Field(
        description="List of device configurations. This replaces the entire configuration.",
        min_length=0
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "devices": [
                        {
                            "id": "psu-1",
                            "name": "TENMA PSU",
                            "driver": "tenma_72",
                            "port": "/dev/ttyUSB0",
                            "baud": 9600,
                            "serial": "8N1"
                        },
                        {
                            "id": "dmm-1",
                            "name": "OWON Multimeter",
                            "driver": "owon_spm",
                            "port": "/dev/ttyUSB1",
                            "baud": 115200,
                            "serial": "8N1"
                        }
                    ]
                }
            ]
        }
    }

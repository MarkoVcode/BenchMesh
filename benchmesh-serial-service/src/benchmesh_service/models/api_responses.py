"""
Pydantic response models for FastAPI endpoints.

These models provide type-safe responses and automatic OpenAPI documentation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, RootModel


# ============================================================================
# System Responses
# ============================================================================

class StatusResponse(BaseModel):
    """Service status response with device connection statistics."""

    devices_total: int = Field(
        description="Total number of configured devices",
        example=3
    )
    connected: int = Field(
        description="Number of currently connected devices",
        example=2
    )
    disconnected: int = Field(
        description="Number of disconnected devices",
        example=1
    )


class VersionResponse(BaseModel):
    """Application version information."""

    releaseVersion: str = Field(
        description="Git release tag (e.g., v0.0.51-87-g6125be0)",
        example="v0.0.51"
    )
    applicationName: str = Field(
        description="Application name",
        example="BenchMesh"
    )
    displayVersion: str = Field(
        description="Human-readable version string",
        example="BenchMesh v0.0.51"
    )
    # Legacy fields for backward compatibility
    version: Optional[str] = Field(
        None,
        description="Semantic version string (legacy)",
        example="0.0.51"
    )
    name: Optional[str] = Field(
        None,
        description="Application name (legacy)",
        example="BenchMesh"
    )
    description: Optional[str] = Field(
        None,
        description="Application description (legacy)",
        example="Lab Instrument Control System"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if version cannot be read"
    )


# ============================================================================
# Configuration Responses
# ============================================================================

class DriverInfo(BaseModel):
    """Driver information for a specific driver."""

    vendor: str = Field(
        description="Manufacturer/vendor name",
        example="OWON"
    )
    family: str = Field(
        description="Driver family name",
        example="SPM"
    )
    supported_transports: List[str] = Field(
        description="Supported transport types",
        example=["serial", "usbtmc"]
    )


class DriversResponse(RootModel[Dict[str, DriverInfo]]):
    """Map of available drivers and their information."""
    root: Dict[str, DriverInfo] = Field(
        description="Dictionary mapping driver ID to driver information",
        examples=[{
            "tenma_72": {
                "vendor": "TENMA",
                "family": "72-SERIES",
                "supported_transports": ["serial"]
            },
            "owon_spm": {
                "vendor": "OWON",
                "family": "SPM",
                "supported_transports": ["serial", "usbtmc"]
            }
        }]
    )


class SerialPortInfo(BaseModel):
    """Serial port information from system scan."""

    device: str = Field(
        description="Port device path",
        example="/dev/ttyUSB0"
    )
    description: str = Field(
        description="Human-readable device description",
        example="USB Serial Port"
    )
    manufacturer: Optional[str] = Field(
        None,
        description="Manufacturer name if available",
        example="FTDI"
    )
    serial_number: Optional[str] = Field(
        None,
        description="Device serial number if available",
        example="FT12345"
    )
    hwid: Optional[str] = Field(
        None,
        description="Hardware ID string",
        example="USB VID:PID=0403:6001 SER=FT12345"
    )


class USBTMCDeviceInfo(BaseModel):
    """USB Test & Measurement Class device information."""

    device: str = Field(
        description="Device path",
        example="/dev/usbtmc0"
    )
    name: str = Field(
        description="Device name",
        example="usbtmc0"
    )
    vendor_id: str = Field(
        description="USB vendor ID in hex format",
        example="0x1ab1"
    )
    product_id: str = Field(
        description="USB product ID in hex format",
        example="0x04ce"
    )
    manufacturer: Optional[str] = Field(
        None,
        description="Manufacturer name if available",
        example="OWON"
    )
    product: Optional[str] = Field(
        None,
        description="Product name if available",
        example="DGE2070"
    )
    serial: Optional[str] = Field(
        None,
        description="Device serial number if available"
    )


class ConfigResponse(BaseModel):
    """Current runtime configuration."""

    devices: List[Dict[str, Any]] = Field(
        description="List of configured devices",
        example=[{
            "id": "psu-1",
            "name": "TENMA PSU",
            "driver": "tenma_72",
            "port": "/dev/ttyUSB0",
            "baud": 9600,
            "serial": "8N1"
        }]
    )


class ConfigUpdateResponse(BaseModel):
    """Configuration update result."""

    status: str = Field(
        description="Operation status",
        example="success"
    )
    message: str = Field(
        description="Human-readable status message",
        example="Configuration updated with 2 device(s) and saved to /home/user/.benchmesh/config.yaml"
    )
    devices: List[Dict[str, Any]] = Field(
        description="Updated device configurations"
    )


# ============================================================================
# Instrument Responses
# ============================================================================

class InstrumentClass(BaseModel):
    """Instrument class information with channel paths."""

    class_: str = Field(
        alias="class",
        description="3-letter instrument class code",
        example="PSU"
    )
    channels: List[str] = Field(
        description="API paths for each channel",
        example=[
            "/instruments/PSU/psu-1/1",
            "/instruments/PSU/psu-1/2",
            "/instruments/PSU/psu-1/3"
        ]
    )
    ui_component: Optional[str] = Field(
        None,
        description="UI component identifier for rendering",
        example="psu_control"
    )

    class Config:
        populate_by_name = True  # Allow both 'class' and 'class_'


class HealthStatus(BaseModel):
    """Device health status information."""

    status: str = Field(
        description="Health status: healthy, degraded, or unhealthy",
        example="healthy"
    )
    consecutive_failures: int = Field(
        description="Number of consecutive poll failures",
        example=0
    )
    is_alive: bool = Field(
        description="Whether device worker thread is alive",
        example=True
    )


class InstrumentInfo(BaseModel):
    """Complete instrument information with capabilities."""

    id: str = Field(
        description="Unique device identifier",
        example="psu-1"
    )
    name: Optional[str] = Field(
        None,
        description="Human-readable device name from configuration",
        example="TENMA PSU"
    )
    IDN: Optional[str] = Field(
        None,
        description="Device identification string from *IDN? SCPI command",
        example="TENMA,72-2540,SN12345,V1.0"
    )
    health: Optional[HealthStatus] = Field(
        None,
        description="Device health status"
    )
    classes: List[InstrumentClass] = Field(
        default=[],
        description="Available instrument classes with channel information"
    )


class ManifestFeaturesResponse(RootModel[Dict[str, Any]]):
    """Manifest features for a specific instrument class."""
    root: Dict[str, Any] = Field(
        description="Features dictionary from manifest",
        examples=[{
            "channels": 3,
            "voltage_range": {"min": 0, "max": 30},
            "current_range": {"min": 0, "max": 5}
        }]
    )


# ============================================================================
# Monitoring Responses
# ============================================================================

class DeviceMetrics(BaseModel):
    """Performance metrics for a single device."""

    device_id: str = Field(
        description="Device identifier"
    )
    utilization_pct: float = Field(
        description="Serial port utilization percentage (0-100)",
        example=45.2
    )
    qps: float = Field(
        description="Queries per second",
        example=12.5
    )
    api_latency_p95_ms: float = Field(
        description="API latency 95th percentile in milliseconds",
        example=125.3
    )
    api_latency_p99_ms: float = Field(
        description="API latency 99th percentile in milliseconds",
        example=180.7
    )
    avg_queue_depth: float = Field(
        description="Average queue depth",
        example=2.3
    )
    throttle_events: int = Field(
        description="Number of throttle events",
        example=0
    )
    skip_rate_pct: float = Field(
        description="Percentage of skipped polls",
        example=0.0
    )
    backoff_multiplier: float = Field(
        description="Current backoff multiplier",
        example=1.0
    )
    quality_score: float = Field(
        description="Connection quality score (0.0-1.0)",
        example=0.95
    )
    quality_tier: str = Field(
        description="Connection quality tier (excellent/good/fair/poor)",
        example="excellent"
    )
    quality_trend: str = Field(
        description="Quality trend (improving/stable/degrading)",
        example="stable"
    )
    transport_type: str = Field(
        description="Transport type (serial/usbtmc)",
        example="serial"
    )


class MetricsSummary(BaseModel):
    """Metrics summary for all devices."""

    summary: Dict[str, Any] = Field(
        description="Device metrics keyed by device ID"
    )
    timestamp: float = Field(
        description="Unix timestamp when metrics were collected",
        example=1698765432.123
    )


# ============================================================================
# Method Discovery Responses
# ============================================================================

class MethodParameter(BaseModel):
    """Method parameter information."""

    name: str = Field(
        description="Parameter name",
        example="channel"
    )
    type: str = Field(
        description="Parameter type",
        example="int"
    )
    required: bool = Field(
        description="Whether parameter is required",
        example=True
    )
    default: Optional[Any] = Field(
        None,
        description="Default value if parameter is optional"
    )
    description: str = Field(
        description="Parameter description",
        example="Channel number (1-3)"
    )


class MethodInfo(BaseModel):
    """Method metadata with parameter information."""

    name: str = Field(
        description="Partial method name (API-friendly)",
        example="output_voltage"
    )
    full_name: str = Field(
        description="Full method name in driver",
        example="query_output_voltage"
    )
    http_method: str = Field(
        description="HTTP method to use (GET/POST)",
        example="GET"
    )
    description: str = Field(
        description="Method description",
        example="Query the actual output voltage"
    )
    parameters: List[MethodParameter] = Field(
        description="Method parameters"
    )
    returns: str = Field(
        description="Return type",
        example="str"
    )
    example: str = Field(
        description="Example API call",
        example="GET /instruments/PSU/psu-1/1/output_voltage"
    )


class MethodsResponse(BaseModel):
    """Available methods for a device."""

    device_id: str = Field(
        description="Device identifier",
        example="psu-1"
    )
    class_: str = Field(
        alias="class",
        description="Instrument class code",
        example="PSU"
    )
    methods: List[MethodInfo] = Field(
        description="List of available methods with metadata"
    )

    class Config:
        populate_by_name = True


# ============================================================================
# Instrument Control Responses
# ============================================================================

class InstrumentQueryResponse(BaseModel):
    """Response from instrument query operation."""

    path: str = Field(
        description="API path that was called",
        example="/instruments/PSU/psu-1/1/output_voltage"
    )
    value: Any = Field(
        description="Value returned by driver method",
        example="12.5V"
    )

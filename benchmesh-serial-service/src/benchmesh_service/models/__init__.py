"""
Pydantic models for API request/response validation and OpenAPI documentation.
"""

# API Response Models
from .api_responses import (
    StatusResponse,
    VersionResponse,
    DriverInfo,
    DriversResponse,
    SerialPortInfo,
    USBTMCDeviceInfo,
    InstrumentClass,
    HealthStatus,
    InstrumentInfo,
    DeviceMetrics,
    MetricsSummary,
    MethodParameter,
    MethodInfo,
    MethodsResponse,
    InstrumentQueryResponse,
    ManifestFeaturesResponse,
    ConfigResponse,
    ConfigUpdateResponse,
)

# API Request Models
from .api_requests import (
    DeviceConfig,
    ConfigUpdate,
)

__all__ = [
    # Response models
    "StatusResponse",
    "VersionResponse",
    "DriverInfo",
    "DriversResponse",
    "SerialPortInfo",
    "USBTMCDeviceInfo",
    "InstrumentClass",
    "HealthStatus",
    "InstrumentInfo",
    "DeviceMetrics",
    "MetricsSummary",
    "MethodParameter",
    "MethodInfo",
    "MethodsResponse",
    "InstrumentQueryResponse",
    "ManifestFeaturesResponse",
    "ConfigResponse",
    "ConfigUpdateResponse",
    # Request models
    "DeviceConfig",
    "ConfigUpdate",
]

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
  # Websocket broadcast interval in seconds
  ws_broadcast_interval: float = float(os.getenv('BM_WS_INTERVAL', '0.2'))
  # Placeholder for future serial manager and API timeouts/configs
  serial_open_timeout_s: float = float(os.getenv('BM_SERIAL_OPEN_TIMEOUT', '2.0'))
  serial_read_timeout_s: float = float(os.getenv('BM_SERIAL_READ_TIMEOUT', '0.3'))
  api_request_timeout_s: float = float(os.getenv('BM_API_REQUEST_TIMEOUT', '5.0'))

  # Unified polling configuration (disabled by default for backward compatibility)
  unified_polling_enabled: bool = os.getenv('BM_UNIFIED_POLLING', 'false').lower() == 'true'
  unified_poll_interval_ms: float = float(os.getenv('BM_UNIFIED_POLL_INTERVAL', '50.0'))

  # Priority queue configuration
  api_request_timeout_queue_s: float = float(os.getenv('BM_API_QUEUE_TIMEOUT', '10.0'))
  max_queue_depth_threshold: int = int(os.getenv('BM_MAX_QUEUE_DEPTH', '10'))

  # Health monitoring configuration
  health_failure_threshold: int = int(os.getenv('BM_HEALTH_FAILURE_THRESHOLD', '3'))
  health_degraded_threshold: int = int(os.getenv('BM_HEALTH_DEGRADED_THRESHOLD', '1'))

  # Adaptive throttling configuration (Phase 1: Core Throttling)
  adaptive_throttling_enabled: bool = os.getenv('BM_ADAPTIVE_THROTTLING', 'true').lower() == 'true'
  
  # Gradual queue depth throttling
  queue_throttle_start: float = float(os.getenv('BM_QUEUE_THROTTLE_START', '0.3'))  # Start at 30% full
  queue_throttle_tiers: int = int(os.getenv('BM_QUEUE_THROTTLE_TIERS', '4'))  # 4 tiers of throttling
  
  # Exponential backoff on failures
  backoff_multiplier: float = float(os.getenv('BM_BACKOFF_MULTIPLIER', '2.0'))  # Double interval on failure
  backoff_max_multiplier: float = float(os.getenv('BM_BACKOFF_MAX_MULTIPLIER', '8.0'))  # Cap at 8x
  
  # Automatic recovery
  recovery_interval_ms: float = float(os.getenv('BM_RECOVERY_INTERVAL_MS', '30000'))  # Retry dead devices every 30s
  
  # Connection quality monitoring
  quality_window_size: int = int(os.getenv('BM_QUALITY_WINDOW_SIZE', '20'))  # Track last 20 operations
  quality_success_points: int = int(os.getenv('BM_QUALITY_SUCCESS_POINTS', '5'))
  quality_timeout_penalty: int = int(os.getenv('BM_QUALITY_TIMEOUT_PENALTY', '10'))
  quality_error_penalty: int = int(os.getenv('BM_QUALITY_ERROR_PENALTY', '15'))

  # Phase 2: Transport-specific limits
  # USB TMC (IEEE 488.2 over USB) - More fragile, needs conservative limits
  usbtmc_min_interval_ms: float = float(os.getenv('BM_USBTMC_MIN_INTERVAL', '1000'))  # 1s minimum
  usbtmc_recommended_interval_ms: float = float(os.getenv('BM_USBTMC_RECOMMENDED_INTERVAL', '2000'))  # 2s recommended
  usbtmc_max_queue_depth: int = int(os.getenv('BM_USBTMC_MAX_QUEUE_DEPTH', '5'))  # Lower tolerance
  usbtmc_timeout_multiplier: float = float(os.getenv('BM_USBTMC_TIMEOUT_MULT', '1.5'))  # Longer timeouts

  # Serial (RS232/USB-Serial) - More forgiving, standard settings
  serial_min_interval_ms: float = float(os.getenv('BM_SERIAL_MIN_INTERVAL', '500'))  # 500ms minimum
  serial_recommended_interval_ms: float = float(os.getenv('BM_SERIAL_RECOMMENDED_INTERVAL', '1000'))  # 1s recommended
  serial_max_queue_depth: int = int(os.getenv('BM_SERIAL_MAX_QUEUE_DEPTH', '10'))  # Standard
  serial_timeout_multiplier: float = float(os.getenv('BM_SERIAL_TIMEOUT_MULT', '1.0'))  # Normal timeouts

  # TCP/IP (Network SCPI) - Network latency, higher buffering
  tcpip_min_interval_ms: float = float(os.getenv('BM_TCPIP_MIN_INTERVAL', '500'))  # 500ms minimum
  tcpip_recommended_interval_ms: float = float(os.getenv('BM_TCPIP_RECOMMENDED_INTERVAL', '1000'))  # 1s recommended
  tcpip_max_queue_depth: int = int(os.getenv('BM_TCPIP_MAX_QUEUE_DEPTH', '15'))  # Higher buffering
  tcpip_timeout_multiplier: float = float(os.getenv('BM_TCPIP_TIMEOUT_MULT', '2.0'))  # Network latency

settings = Settings()

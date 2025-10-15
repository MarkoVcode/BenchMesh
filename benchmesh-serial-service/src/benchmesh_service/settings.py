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

settings = Settings()

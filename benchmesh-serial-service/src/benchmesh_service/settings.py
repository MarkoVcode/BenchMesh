import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
  # Websocket broadcast interval in seconds
  ws_broadcast_interval: float = float(os.getenv('BM_WS_INTERVAL', '0.8'))
  # Placeholder for future serial manager and API timeouts/configs
  serial_open_timeout_s: float = float(os.getenv('BM_SERIAL_OPEN_TIMEOUT', '2.0'))
  serial_read_timeout_s: float = float(os.getenv('BM_SERIAL_READ_TIMEOUT', '0.3'))
  api_request_timeout_s: float = float(os.getenv('BM_API_REQUEST_TIMEOUT', '5.0'))

settings = Settings()

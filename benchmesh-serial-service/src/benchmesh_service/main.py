import argparse
import yaml
import time
import threading
from .serial_manager import SerialManager
from .config import load_config
from .logger import setup_logger

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to config YAML")
    args = parser.parse_args()

    logger = setup_logger()
    config = load_config(args.config)
    
    serial_manager = SerialManager(config['devices'])
    
    def monitor_connections():
        while True:
            serial_manager.check_status()
            time.sleep(0.5)

    monitor_thread = threading.Thread(target=monitor_connections)
    monitor_thread.daemon = True
    monitor_thread.start()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        logger.info("Shutting down service.")
        serial_manager.close_connections()

if __name__ == "__main__":
    main()
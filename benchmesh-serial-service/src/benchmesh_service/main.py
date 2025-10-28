import argparse
import time
from .serial_manager import SerialManager
from .config import load_config
from .logger import setup_logger

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to config YAML")
    args = parser.parse_args()
    logger = setup_logger()
    logger.info(f"Using config file: {args.config}")
    config = load_config(args.config)
    logger.info(f"Loaded config: {config}")
    serial_manager = SerialManager(config['devices'])
    serial_manager.start()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        logger.info("Shutting down service.")
        serial_manager.stop()

if __name__ == "__main__":
    main()
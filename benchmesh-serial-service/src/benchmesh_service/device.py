import logging

logger = logging.getLogger(__name__)


class Device:
    def __init__(self, id, name, port, baud, driver):
        self.id = id
        self.name = name
        self.port = port
        self.baud = baud
        self.driver = driver
        self.connection = None

    def connect(self):
        """Establish a serial connection using the specified driver."""
        try:
            self.connection = self.driver.connect(self.port, self.baud)
            logger.info(f"{self.name} connected on {self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")

    def send_command(self, command):
        """Send a command to the device."""
        if self.connection:
            self.connection.write(command)
        else:
            logger.warning(f"{self.name} is not connected.")

    def receive_response(self):
        """Receive a response from the device."""
        if self.connection:
            return self.connection.read()
        else:
            logger.warning(f"{self.name} is not connected.")
            return None

    def check_status(self):
        """Check the connection status of the device."""
        if self.connection:
            return self.connection.is_open
        return False

    def close(self):
        """Close the connection to the device."""
        if self.connection:
            self.connection.close()
            logger.info(f"{self.name} connection closed.")
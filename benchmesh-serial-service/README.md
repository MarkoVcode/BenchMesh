# benchmesh-serial-service

## Overview
The BenchMesh Serial Service is a Python-based application designed to manage multiple serial connections to various devices. It utilizes a configuration file to define device parameters and employs a modular architecture to facilitate easy integration of new device drivers.

## Features
- Manage multiple serial connections concurrently.
- Periodically check the status of each connection.
- Modular driver architecture for easy addition of new devices.
- Configurable via a YAML file.

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd benchmesh-serial-service
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration
The service configuration is defined in `config.yaml`. Each device is specified with parameters such as ID, name, port, baud rate, and driver. Ensure that the device ports match your system's configuration.

## Usage
To start the service, run the following command:
```
python -m src.benchmesh_service.main
```

## Directory Structure
```
benchmesh-serial-service
├── src
│   └── benchmesh_service
│       ├── __init__.py
│       ├── main.py
│       ├── serial_manager.py
│       ├── device.py
│       ├── config.py
│       ├── logger.py
│       └── drivers
│           ├── __init__.py
│           ├── owon_oel.py
│           ├── owon_spm.py
│           ├── tenma_psu.py
│           └── owon_xdm.py
├── config.yaml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
Repository summary for microagents

1) Purpose
BenchMesh provides a consistent, browser-accessible cockpit for lab instruments, enabling connection, control, logging, correlation, and automation from one place. The benchmesh-serial-service sub-project is a Python service that manages multiple serial connections to instruments defined in a YAML configuration, with a modular driver architecture to support different instrument models.

2) General setup
- Languages/Runtime: Python 3.8+
- Key libraries: pyserial (serial communication), pyyaml (config parsing), loguru/logging (logging)
- Configuration: YAML files (top-level config.yaml and benchmesh-serial-service/config.yaml) define devices and their serial parameters.
- Entry point for serial service: python -m src.benchmesh_service.main (run from benchmesh-serial-service directory)
- Packaging: pyproject.toml in benchmesh-serial-service defines a Poetry package (packages include src/benchmesh_service)

3) Repository structure (brief)
- README.md: Top-level project description
- config.yaml: Example top-level device configuration
- benchmesh-serial-service/
  - README.md: Service overview and usage
  - requirements.txt: Minimal runtime dependencies
  - pyproject.toml: Poetry configuration
  - config.yaml: Service-specific example configuration
  - src/benchmesh_service/
    - main.py: Service bootstrap; loads config and spawns connection monitor
    - serial_manager.py: Core connection manager (opens, monitors, and probes serial connections for devices)
    - config.py: YAML config loader and helper class
    - device.py: Simple device abstraction
    - logger.py: Logger setup
    - drivers/: Device-specific drivers (owon_oel, owon_spm, tenma_psu, owon_xdm)
- drivers/, system/, exampleRS232.py: Additional examples/ancillary code at repository root

CI/Workflows under .github
- No .github directory or GitHub workflows were found in this repository at the time of writing. Therefore, there are no repository-defined CI checks (e.g., linting, tests) enforced via GitHub Actions.

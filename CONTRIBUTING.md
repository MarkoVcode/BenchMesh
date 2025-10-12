# Contributing to BenchMesh

Thank you for your interest in contributing to BenchMesh! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check the [issue tracker](https://github.com/MarkoVcode/BenchMesh/issues) for existing reports
2. Ensure you're using the latest version
3. Test with a minimal configuration

**Bug Report Template:**
```
**Description**: Clear description of the bug

**To Reproduce**:
1. Step 1
2. Step 2
3. See error

**Expected Behavior**: What should happen

**Environment**:
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.12]
- BenchMesh version: [e.g., 1.0.0]

**Device Configuration**:
```yaml
# Your config.yaml excerpt
```

**Logs**: Paste relevant error messages
```

### Suggesting Features

Open a [GitHub Issue](https://github.com/MarkoVcode/BenchMesh/issues) with:
- Clear description of the feature
- Use case / motivation
- Proposed implementation (if applicable)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-new-feature`
3. **Make your changes** following the guidelines below
4. **Run tests**: `pytest benchmesh-serial-service/tests`
5. **Commit with clear messages**: `git commit -m "Add feature: my new feature"`
6. **Push to your fork**: `git push origin feature/my-new-feature`
7. **Open a Pull Request** with description of changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/BenchMesh.git
cd BenchMesh

# Install development dependencies
pip install -r benchmesh-serial-service/requirements.txt
pip install pytest pytest-cov black flake8

# Run tests
pytest benchmesh-serial-service/tests

# Run linter
black benchmesh-serial-service/src
flake8 benchmesh-serial-service/src
```

## Code Style

- **Python**: Follow PEP 8, use `black` for formatting
- **TypeScript/JavaScript**: Use existing code style (2-space indent)
- **Commits**: Use clear, descriptive commit messages

## Adding a New Driver

See [Driver Development Guide](docs/DRIVER_DEVELOPMENT.md) for detailed instructions.

### Quick Overview:

1. **Create driver structure**:
   ```
   benchmesh-serial-service/src/benchmesh_service/drivers/my_device/
   ├── __init__.py
   ├── driver.py
   └── manifest.json
   ```

2. **Implement required methods**:
   ```python
   class MyDeviceDriver:
       def __init__(self, transport: SerialTransport, config: dict):
           self.transport = transport

       def identify(self) -> str:
           """Return device identification"""

       def poll_status(self) -> dict:
           """Return current device status"""
   ```

3. **Create manifest.json**:
   ```json
   {
     "models": {
       "MY-MODEL": {
         "class": "PSU",
         "description": "My Device Model"
       }
     },
     "classes": {
       "PSU": {
         "polling": {
           "methods": ["poll_status"],
           "interval": 2.0
         }
       }
     }
   }
   ```

4. **Add tests**: Create `tests/test_my_device.py`

5. **Update documentation**: Add device to README.md and driver list

## Testing

### Unit Tests

```bash
# Run all tests
pytest benchmesh-serial-service/tests

# Run specific test file
pytest benchmesh-serial-service/tests/test_serial_manager.py

# Run with coverage
pytest --cov=benchmesh_service benchmesh-serial-service/tests
```

### Manual Testing

1. Add device to `config.yaml`
2. Run `./start.sh`
3. Verify device appears and responds in UI
4. Test control functions
5. Test Node-RED integration

## Documentation

When adding features, update:
- README.md (if user-facing)
- Relevant docs/*.md files
- Inline code comments
- Docstrings for public APIs

## Review Process

Pull requests are reviewed by maintainers. We look for:
- ✅ Tests pass
- ✅ Code follows style guidelines
- ✅ Documentation updated
- ✅ No breaking changes (or clearly documented)
- ✅ Commit history is clean

## Community Guidelines

- Be respectful and constructive
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Help newcomers
- Share knowledge

## Questions?

- Open a [Discussion](https://github.com/MarkoVcode/BenchMesh/discussions)
- Join our community chat (if applicable)
- Check the [Wiki](https://github.com/MarkoVcode/BenchMesh/wiki)

## License

By contributing, you agree that your contributions will be licensed under the project's [LICENSE](LICENSE).

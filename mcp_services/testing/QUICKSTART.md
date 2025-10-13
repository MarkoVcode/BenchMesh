# BenchMesh Testing MCP - Quick Start

## Installation (5 minutes)

```bash
# 1. Install dependencies
cd /home/marek/project/BenchMesh/mcp_services/testing
pip install -r requirements.txt --user

# 2. Test the service
cd /home/marek/project/BenchMesh
python3 mcp_services/testing/client_helper.py
```

## Usage Examples

### Example 1: Run all backend tests
```python
import asyncio
from mcp_services.testing.client_helper import test_backend

async def main():
    result = await test_backend(verbose=True)
    print(f"Tests passed: {result['success']}")

asyncio.run(main())
```

### Example 2: Run tests for changed files
```python
import asyncio
from mcp_services.testing.client_helper import test_changed

async def main():
    result = await test_changed([
        "benchmesh-serial-service/src/benchmesh_service/api.py",
        "benchmesh-serial-service/frontend/src/ui/classes/PSU/GenericPSU.tsx"
    ])

    if result['backend']:
        print(f"Backend: {'PASS' if result['backend']['success'] else 'FAIL'}")
    if result['frontend']:
        print(f"Frontend: {'PASS' if result['frontend']['success'] else 'FAIL'}")

asyncio.run(main())
```

### Example 3: Run all tests
```python
import asyncio
from mcp_services.testing.client_helper import test_all

async def main():
    result = await test_all(verbose=True)
    print(f"Backend: {'PASS' if result['backend']['success'] else 'FAIL'}")
    print(f"Frontend: {'PASS' if result['frontend']['success'] else 'FAIL'}")
    print(f"Overall: {'PASS' if result['success'] else 'FAIL'}")

asyncio.run(main())
```

### Example 4: From command line
```bash
# Run backend tests
cd /home/marek/project/BenchMesh/benchmesh-serial-service
python3 -m pytest tests/ -v

# Run frontend tests
cd frontend
npm run test:run

# Run integration tests only
cd /home/marek/project/BenchMesh/benchmesh-serial-service
python3 -m pytest tests/ -m integration -v
```

## Integration with Claude Code

Claude Code can now automatically run tests after code changes.

**Before MCP:**
```
User: "I updated the API"
Claude: "Great! Please run the tests manually"
User: [Has to context switch and run tests]
```

**After MCP:**
```
User: "I updated the API"
Claude: [Automatically runs tests via MCP]
Claude: "Tests passed! All 46 backend tests successful."
```

## Configuration for Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "benchmesh-testing": {
      "command": "python3",
      "args": ["/home/marek/project/BenchMesh/mcp_services/testing/server.py"],
      "description": "BenchMesh testing service"
    }
  }
}
```

## Test Results

Current test status:
- ✅ Backend tests: 46 tests discovered
- ✅ Frontend tests: 21 tests discovered
- ✅ MCP service: Fully operational
- ✅ Test discovery: Working
- ✅ Smart test running: Working

## Common Workflows

### Workflow 1: TDD Development
1. Write a failing test
2. Implement the feature
3. Run: `python3 mcp_services/testing/client_helper.py`
4. Fix any failures
5. Repeat

### Workflow 2: Before Commit
```bash
# Quick check - run all tests
cd /home/marek/project/BenchMesh
python3 << 'EOF'
import asyncio
from mcp_services.testing.client_helper import test_all

async def check():
    result = await test_all()
    if not result['success']:
        print("❌ Tests failed - do not commit!")
        exit(1)
    print("✅ All tests passed - safe to commit!")

asyncio.run(check())
EOF
```

### Workflow 3: CI/CD Integration
The MCP service uses standard test runners, so existing CI continues to work:

```yaml
# .github/workflows/test.yml (unchanged)
- name: Run backend tests
  run: |
    cd benchmesh-serial-service
    pytest tests/

- name: Run frontend tests
  run: |
    cd benchmesh-serial-service/frontend
    npm run test:run
```

## Troubleshooting

### MCP module not found
```bash
pip install mcp --user
```

### Tests not discovered
- Check you're in the correct directory
- Verify test paths in test runner

### Permission errors
```bash
chmod +x /home/marek/project/BenchMesh/mcp_services/testing/server.py
```

## Next Steps

1. **Try it out**: Run `python3 mcp_services/testing/client_helper.py`
2. **Integrate with workflow**: Start using it in your development
3. **Configure Claude Code**: Add MCP config to Claude Code settings
4. **Measure impact**: See how much time you save

## Success Metrics

Track these to measure value:
- Time saved per test run
- Number of test failures caught early
- Reduction in context switching
- Faster feedback loops

Enjoy automated testing! 🚀

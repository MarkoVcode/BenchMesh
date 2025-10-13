# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Key Philosophy Documents (reference these when making design decisions):

- See @ai_context/IMPLEMENTATION_PHILOSOPHY.md for core development principles
- See @ai_context/MODULAR_DESIGN_PHILOSOPHY.md for architecture patterns

## Project Overview

BenchMesh is a consistent, browser-based cockpit for lab instruments. It connects, controls, logs, correlates, and automates multiple serial devices from a single interface. The core component is `benchmesh-serial-service`, a Python backend with FastAPI that manages concurrent serial connections through a modular driver architecture.

## Architecture

The system follows a layered architecture:

- **SerialManager** (`serial_manager.py`): Central orchestrator that manages device connections, spawns per-device worker threads, maintains device registry with IDN and status data, and handles reconnection logic
- **Driver Layer** (`drivers/`): Modular device-specific drivers (tenma_72, owon_spm, owon_xdm, owon_oel, owon_dge) that implement device-specific protocols and polling
- **Transport Layer** (`transport.py`): SerialTransport abstraction over pyserial for serial communication
- **API Layer** (`api.py`): FastAPI application exposing REST endpoints and WebSocket for device status and control
- **Frontend** (`frontend/`): React+TypeScript UI built with Vite

Each device runs in its own worker thread with per-device RLock for thread safety. Devices reconnect automatically with ~2s backoff on failure. The registry maintains `IDN` (from *IDN? SCPI command on connect) and `status` (polled every ~2s) for each device.

## Common Commands

### Starting the Full System

```bash
# From repository root - starts everything (API, Frontend, Node-RED)
./start.sh

# Services will be available at:
# - Frontend: http://localhost:57666
# - API Docs: http://localhost:57666/docs
# - Node-RED: http://localhost:1880
```

### Backend Development

```bash
# From benchmesh-serial-service/ directory

# Install dependencies
pip install -r requirements.txt

# Run the service (standalone, no API)
python -m benchmesh_service.main --config config.yaml

# Run with FastAPI (includes frontend auto-start)
PYTHONPATH=src uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_serial_manager.py

# Run with verbose output
pytest -v tests/
```

### Node-RED

```bash
# From repository root

# Install Node-RED (first time only)
npm install

# Start Node-RED standalone
npm run start:nodered

# Node-RED runs on port 1880
# Data stored in .node-red/ directory
```

### Frontend Development

```bash
# From benchmesh-serial-service/frontend/ directory

# Install dependencies
npm ci

# Development server (hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Run tests once (CI mode)
npm run test:run
```

### Driver CLI Tool

Test driver methods directly from command line:

```bash
# From repository root, set PYTHONPATH if needed
export PYTHONPATH=benchmesh-serial-service/src

# List devices from config
python -m benchmesh_service.tools.driver_cli list --config benchmesh-serial-service/config.yaml

# List available methods for a device
python -m benchmesh_service.tools.driver_cli methods --id tenmapsu-1 --config benchmesh-serial-service/config.yaml

# Call a method (no args)
python -m benchmesh_service.tools.driver_cli call --id tenmapsu-1 --method query_identify --config benchmesh-serial-service/config.yaml

# Call with positional args
python -m benchmesh_service.tools.driver_cli call --id spm-1 --method set_voltage 5.0 --config benchmesh-serial-service/config.yaml

# Call with kwargs (JSON)
python -m benchmesh_service.tools.driver_cli call --id tenmapsu-1 --method set_output true --kwargs '{"ch":1}' --config benchmesh-serial-service/config.yaml
```

### CI

GitHub Actions runs on all branches and PRs:
- Backend tests: `pytest benchmesh-serial-service/tests`
- Frontend tests: `npx vitest run --reporter=dot`

## Configuration System

Devices are defined in `config.yaml` (YAML v1 schema):

```yaml
version: 1
devices:
  - id: tenmapsu-1              # Unique device ID
    name: "TENMA PSU"            # Display name
    driver: tenma_psu            # Maps to driver folder (aliased to tenma_72)
    port: /dev/tty722540         # Serial port path
    baud: 9600                   # Baud rate
    serial: 8N1                  # Data bits, parity, stop bits
    model: 72-2540               # Optional model override
```

Each driver has a `manifest.json` defining:
- Supported models and their classes (3-letter codes: PSU, SPM, XDM, OEL)
- Per-class polling methods and intervals
- Connection EOL characters (send_eol, recv_eol)
- Driver module path

Manifest aliases in `serial_manager.py` and `manifest_resolver.py` map legacy driver names (e.g., `tenma_psu` → `tenma_72`).

## Adding a New Driver

1. Create driver package: `benchmesh-serial-service/src/benchmesh_service/drivers/<driver_name>/`
2. Create `driver.py` with a class exposing:
   - `query_identify()` → returns IDN string
   - `poll_status()` → returns status dict
   - Device-specific control methods
3. Create `manifest.json` defining models, classes, polling config, and EOL characters
4. Update `drivers/classes.json` if adding new 3-letter class codes
5. Add driver instantiation logic to `driver_factory.py` if needed
6. Create tests in `tests/` using pytest and mock serial communication

Driver should accept `transport: SerialTransport` in constructor and use it for all communication.

## Key Modules

- `serial_manager.py`: SerialManager orchestrates all device connections and worker threads
- `manifest_resolver.py`: Resolves driver manifests to extract class, polling, and EOL configuration
- `driver_factory.py`: Instantiates driver classes from string names and device configs
- `poll_worker.py`: DeviceWorker runs per-device polling loop in dedicated thread
- `registry.py`: DeviceRegistry thread-safe storage for device IDN and status
- `transport.py`: SerialTransport wraps pyserial with EOL handling
- `api.py`: FastAPI app with endpoints `/status`, `/instruments`, `/api/call`, and WebSocket `/ws`
- `connection.py`: DeviceConnection tracks connection state per device
- `reconnect.py`: ReconnectPolicy implements backoff strategy

## Testing Notes

- Tests use `pytest` with fixtures in `conftest.py`
- Mock serial communication using `unittest.mock.Mock` for transport
- Tests in `tests/` cover: manifest resolution, driver factory, serial manager behavior, concurrency, polling, and edge cases
- Frontend uses `vitest` with `@testing-library/react`

## Environment Variables

- `BENCHMESH_CONFIG`: Path to config.yaml (default: `config.yaml`)
- `API_PORT`: FastAPI port (default: `57666`)
- `UI_PORT`: Frontend dev server port (default: `52893`)

## Notes

- Repository root contains example RS232 test scripts in `system/` directory
- Documentation and udev rules in `system/udev_rules.txt` for persistent device paths
- Driver manifests support per-class polling intervals (e.g., PSU class polls every 2s, SPM every 3s)
- Frontend proxies API requests to backend during development via Vite config

## Guidelines

- apply TDD principles when adding new features
- always MUST run tests after the code changes
- do not try to maintain "Fallback for legacy" we are developing a new software, there is no legacy we need to maintain
- always MUST cover new development with tests - whatever is added or improved
- always MUST validate if the documentation is still up to date
- always MUST follow single responsibility principle
- differentiate between unit tests and integration tests - integration tests should NOT run in GitHub Actions (reserve for local/staging testing only)
- all new unit tests that are suitable for GitHub Actions execution must be automatically added to the CI workflow


# Claude's Working Philosophy and Memory System

## Critical Operating Principles

- VERY IMPORTANT: Always think through a plan for every ask, and if it is more than a simple request, break it down and use TodoWrite tool to manage a todo list. When this happens, make sure to always ULTRA-THINK as you plan and populate this list.
- VERY IMPORTANT: Always consider if there is an agent available that can help with any given sub-task, they are more specialized tools designed to tackle specific challenges. Your role is to be a general coordinator. Use the Task tool to delegate specific tasks to these agents. Where possible, launch multiple agents in parallel via a single message with multiple tool uses.

<example>
User: "I need to implement a new feature that requires changes to multiple services. [details truncated for example]"
Assistant: "Let me analyze this problem before implementing. I will break it down into smaller tasks and use sub-agents where possible. I will track my plan with a TODO list."
</example>

- VERY IMPORTANT: If user has not provided enough clarity to CONFIDENTLY proceed, ask clarifying questions until you have a solid understanding of the task.

<example>
User: "I want to create a new memory system."
Assistant: "Did you have a specific design or set of requirements in mind for this memory system? Please help me understand what you're envisioning or let me know if you would like me to propose a design or even brainstorm some ideas together. Please consider switching to 'Plan Mode' until we are done (shift+tab to cycle through modes)."
Assistant: Use ExitPlanMode tool when you have finished planning and there are no further clarifying questions you need answered from the user or if they have explicitly indicated they are done planning.
</example>

## Parallel Execution Strategy

**CRITICAL**: Always ask yourself: "What can I do in parallel here?" Send ONE message with MULTIPLE tool calls, not multiple messages with single tool calls.

### When to Parallelize

Parallelize when tasks:
- Don't depend on each other's output
- Perform similar operations on different targets
- Can be delegated to different agents
- Gather independent information

### Common Patterns

#### Multiple File Edits
When fixing the same issue across files (e.g., type errors, import updates):
```
Single message with multiple Edit/MultiEdit calls:
- Edit: Fix type error in src/auth.py
- Edit: Fix type error in src/database.py
- Edit: Fix type error in src/api.py
```

#### Batch Type Error Fixes
When pyright reports multiple type errors:
```
Single message addressing all errors:
- Read: Check current implementation in affected files
- MultiEdit: Fix all type errors in utils.py
- MultiEdit: Fix all type errors in models.py
- Edit: Update type imports in __init__.py
```

#### Information Gathering
Before implementing features:
```
Single message with parallel reads and searches:
- Grep: Search for existing patterns
- Read: Main implementation file
- Read: Test file
- Read: Related configuration
```

#### Multiple Agent Analysis
For comprehensive review:
```
Single message with multiple Task calls:
- Task zen-architect: "Design approach"
- Task bug-hunter: "Identify potential issues"
- Task test-coverage: "Suggest test cases"
```

### Anti-Patterns to Avoid

**Don't do this:**
```
"Let me read the first file"
[Read file1.py]
"Now let me read the second file"  
[Read file2.py]
```

**Do this instead:**
```
"I'll examine these files in parallel"
[Single message: Read file1.py, Read file2.py, Read file3.py]
```

### Remember

- Parallel execution is the default, not an optimization
- Sequential execution needs justification (true dependencies)
- Context is preserved better with parallel operations
- Users prefer comprehensive results over watching sequential progress

### 1. Context Window Management

- **Limited context requires strategic compaction** - Details get summarized and lost
- **Two key solutions:**
  - Use memory system for critical persistent information
  - Use sub-agents to fork context and conserve space
- **Smart memory usage** - Not everything goes in memory, be selective about what's truly critical

### 2. Sub-Agent Delegation Strategy

#### Power of Sub-Agents

- Each sub-agent only returns the parts of their context that are requested or needed
- Fork context for parallel, unbiased work
- Conserve context by delegating and receiving only essential results
- Create specialized agents for reusable, focused purposes

#### When to Use Sub-Agents (HINT: ALWAYS IF POSSIBLE)

- **Analysis tasks** - Let them do deep work and return synthesis
- **Parallel exploration** - Fork for unbiased opinions
- **Complex multi-step work** - Delegate entire workflows
- **Specialized expertise** - Use focused agents over generic capability

### 3. Creating New Sub-Agents

- **Don't hesitate to request new specialized agents**
- Specialized and focused > generalized and generic
- Request that user creates them via user's `/agents` command
- You provide the user with a detailed description
- New agents undergo Claude Code optimization
- Better to have too many specialized tools than struggle with generic ones

### 4. My Role as Orchestrator

- **I am the overseer/manager/orchestrator**
- Delegate EVERYTHING possible to sub-agents
- Focus on what ONLY I can do for the user
- Be the #1 partner, not the worker

### 5. Code-Based Utilities Strategy

- Wrap sub-agent capabilities into code utilities using Claude Code SDK
  - See docs in `ai_context/claude_code/CLAUDE_CODE_SDK.md`
  - See examples in `ai_context/git_collector/CLAUDE_CODE_SDK_PYTHON.md`
- Create "recipes" for dependable workflow execution that are "more code than model"
  - Orchestrates the use of the Claude Code sub-agents for subtasks, using code where more structure is beneficial
  - Reserve use of Claude Code sub-agents for tasks that are hard to codify
- Balance structured data needs with valuable natural language
- Build these progressively as patterns emerge

### 6. Human Engagement Points

- **Clarification** - Ask when truly uncertain about direction
- **Checkpoints** - Surface completed work stages for validation
- **Proxy decisions** - Answer sub-agent questions when possible, escalate when needed
- **Learning stance** - Act as skilled new employee learning "our way"

### 7. Learning and Memory System

#### Current Learning Needs

- Track what I learn from user interactions
- Make learnings visible and actionable
- Consider memory retrieval sub-agent for context-appropriate recall
- Avoid repeated teaching of same concepts
- Become more aligned with user over time

#### Memory Architecture Ideas

- **Working Memory** - Current session critical info
- **Long-term Memory** - Persistent learnings and patterns
- **Retrieval System** - Sub-agent to pull relevant memories per task
- **Learning Log** - Track what's been learned and when

### 8. Continuous Improvement Rhythm

- Regularly mine articles for new ideas
- Run experimental implementations
- Measure and test changes systematically
- Evaluate improvements vs degradations
- Support parallel experimentation in different trees

## Key Metrics for Success

- Becoming the most valuable tool in user's arsenal
- Amplifying user's work effectively
- Acting as true partner and accelerator
- Learning and improving continuously
- Maintaining alignment with user's approach

## Philosophical Anchors

- Always reference `@ai_context/IMPLEMENTATION_PHILOSOPHY.md`
- Always reference `@ai_context/MODULAR_DESIGN_PHILOSOPHY.md`
- Embrace ruthless simplicity
- Build as bricks and studs
- Trust in emergence over control

## Next Actions

- Design comprehensive knowledge synthesis architecture
- Create specialized planning sub-agent
- Build memory retrieval system
- Establish measurement framework
- Begin continuous learning cycle

## Document Reference Protocol

When working with documents that contain references:

1. **Always check for references/citations** at the end of documents
2. **Re-read source materials** when implementing referenced concepts
3. **Understand the backstory/context** before applying ideas
4. **Track which articles informed which decisions** for learning

This ensures we build on the full depth of ideas, not just their summaries.
#!/usr/bin/env python3
"""
BenchMesh Testing MCP Server

Provides comprehensive testing tools for the BenchMesh project including:
- Backend unit tests (pytest)
- Frontend tests (vitest)
- Integration tests
- Electron tests
- Test discovery and filtering
- Coverage reporting
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Sequence
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class TestRunner:
    """Handles execution of different test types"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_root = project_root / "benchmesh-serial-service"
        self.frontend_root = self.backend_root / "frontend"

    async def run_backend_tests(
        self,
        test_path: Optional[str] = None,
        verbose: bool = False,
        markers: Optional[str] = None
    ) -> dict[str, Any]:
        """Run backend pytest tests"""

        cmd = ["python3", "-m", "pytest"]

        if test_path:
            cmd.append(test_path)
        else:
            cmd.append("tests/")

        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        if markers:
            cmd.extend(["-m", markers])

        # Add JSON reporting
        cmd.extend(["--json-report", "--json-report-file=/tmp/pytest-report.json"])

        result = await self._run_command(cmd, cwd=self.backend_root)

        # Parse JSON report if available
        report_file = Path("/tmp/pytest-report.json")
        if report_file.exists():
            with open(report_file) as f:
                test_report = json.load(f)
            report_file.unlink()
        else:
            test_report = {}

        return {
            "success": result["returncode"] == 0,
            "output": result["output"],
            "error": result["error"],
            "returncode": result["returncode"],
            "report": test_report
        }

    async def run_frontend_tests(
        self,
        watch: bool = False,
        coverage: bool = False
    ) -> dict[str, Any]:
        """Run frontend vitest tests"""

        cmd = ["npm", "run", "test:run" if not watch else "test"]

        if coverage:
            cmd.append("--", "--coverage")

        result = await self._run_command(cmd, cwd=self.frontend_root)

        return {
            "success": result["returncode"] == 0,
            "output": result["output"],
            "error": result["error"],
            "returncode": result["returncode"]
        }

    async def run_integration_tests(
        self,
        test_path: Optional[str] = None
    ) -> dict[str, Any]:
        """Run integration tests (marked with @pytest.mark.integration)"""

        return await self.run_backend_tests(
            test_path=test_path,
            markers="integration",
            verbose=True
        )

    async def run_electron_tests(self) -> dict[str, Any]:
        """Run Electron app tests"""

        # Check if Electron app has tests
        electron_test_script = self.frontend_root / "package.json"
        if not electron_test_script.exists():
            return {
                "success": False,
                "output": "",
                "error": "Electron tests not configured",
                "returncode": 1
            }

        # Try to run electron tests if configured
        cmd = ["npm", "run", "test:electron"]
        result = await self._run_command(cmd, cwd=self.frontend_root)

        return {
            "success": result["returncode"] == 0,
            "output": result["output"],
            "error": result["error"],
            "returncode": result["returncode"]
        }

    async def discover_tests(self) -> dict[str, Any]:
        """Discover all available tests"""

        # Backend tests
        backend_cmd = ["python3", "-m", "pytest", "--collect-only", "-q", "tests/"]
        backend_result = await self._run_command(backend_cmd, cwd=self.backend_root)

        # Frontend tests
        frontend_cmd = ["npm", "run", "test:run", "--", "--reporter=verbose", "--run"]
        frontend_result = await self._run_command(frontend_cmd, cwd=self.frontend_root)

        return {
            "backend": {
                "output": backend_result["output"],
                "count": self._count_tests(backend_result["output"])
            },
            "frontend": {
                "output": frontend_result["output"],
                "count": self._count_tests(frontend_result["output"])
            }
        }

    async def run_changed_tests(self, changed_files: list[str]) -> dict[str, Any]:
        """Run tests related to changed files"""

        results = {
            "backend": None,
            "frontend": None
        }

        # Determine which tests to run based on changed files
        backend_changed = any(
            f.startswith("benchmesh-serial-service/src") or
            f.startswith("benchmesh-serial-service/tests")
            for f in changed_files
        )

        frontend_changed = any(
            f.startswith("benchmesh-serial-service/frontend/src")
            for f in changed_files
        )

        # Run relevant tests
        if backend_changed:
            results["backend"] = await self.run_backend_tests()

        if frontend_changed:
            results["frontend"] = await self.run_frontend_tests()

        return results

    async def _run_command(
        self,
        cmd: list[str],
        cwd: Path
    ) -> dict[str, Any]:
        """Run a command and capture output"""

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            stdout, stderr = await process.communicate()

            return {
                "output": stdout.decode('utf-8', errors='replace'),
                "error": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode
            }
        except Exception as e:
            return {
                "output": "",
                "error": str(e),
                "returncode": 1
            }

    def _count_tests(self, output: str) -> int:
        """Parse test count from output"""
        # Simple heuristic - count lines that look like test names
        lines = output.split('\n')
        count = sum(1 for line in lines if 'test_' in line or '.test.' in line)
        return count


# Initialize MCP server
server = Server("benchmesh-testing")

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
test_runner = TestRunner(PROJECT_ROOT)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available testing tools"""

    return [
        Tool(
            name="run_backend_tests",
            description="Run backend pytest tests with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Specific test file or directory (relative to tests/)"
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output",
                        "default": False
                    },
                    "markers": {
                        "type": "string",
                        "description": "Pytest markers to filter tests (e.g., 'integration', 'unit')"
                    }
                }
            }
        ),
        Tool(
            name="run_frontend_tests",
            description="Run frontend vitest tests",
            inputSchema={
                "type": "object",
                "properties": {
                    "watch": {
                        "type": "boolean",
                        "description": "Run in watch mode",
                        "default": False
                    },
                    "coverage": {
                        "type": "boolean",
                        "description": "Generate coverage report",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="run_integration_tests",
            description="Run integration tests only (marked with @pytest.mark.integration)",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Specific test file or directory"
                    }
                }
            }
        ),
        Tool(
            name="run_electron_tests",
            description="Run Electron app tests",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="run_all_tests",
            description="Run all tests (backend + frontend)",
            inputSchema={
                "type": "object",
                "properties": {
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="discover_tests",
            description="Discover all available tests without running them",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="run_changed_tests",
            description="Run tests for changed files",
            inputSchema={
                "type": "object",
                "properties": {
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of changed file paths"
                    }
                },
                "required": ["changed_files"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls"""

    try:
        if name == "run_backend_tests":
            result = await test_runner.run_backend_tests(
                test_path=arguments.get("test_path"),
                verbose=arguments.get("verbose", False),
                markers=arguments.get("markers")
            )

        elif name == "run_frontend_tests":
            result = await test_runner.run_frontend_tests(
                watch=arguments.get("watch", False),
                coverage=arguments.get("coverage", False)
            )

        elif name == "run_integration_tests":
            result = await test_runner.run_integration_tests(
                test_path=arguments.get("test_path")
            )

        elif name == "run_electron_tests":
            result = await test_runner.run_electron_tests()

        elif name == "run_all_tests":
            verbose = arguments.get("verbose", False)
            backend = await test_runner.run_backend_tests(verbose=verbose)
            frontend = await test_runner.run_frontend_tests()

            result = {
                "backend": backend,
                "frontend": frontend,
                "success": backend["success"] and frontend["success"]
            }

        elif name == "discover_tests":
            result = await test_runner.discover_tests()

        elif name == "run_changed_tests":
            result = await test_runner.run_changed_tests(
                arguments.get("changed_files", [])
            )

        else:
            result = {"error": f"Unknown tool: {name}"}

        # Format output
        output = json.dumps(result, indent=2)

        return [TextContent(
            type="text",
            text=output
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "tool": name,
                "arguments": arguments
            }, indent=2)
        )]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

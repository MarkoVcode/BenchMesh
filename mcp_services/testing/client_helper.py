"""
Client helper for Claude Code to interact with BenchMesh Testing MCP

This module provides a simple interface for Claude Code to run tests
via the MCP service.

Usage in Claude Code context:
    from mcp_services.testing.client_helper import TestClient

    client = TestClient()
    results = await client.run_backend_tests()
    results = await client.run_all_tests()
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Optional


class TestClient:
    """Client for interacting with BenchMesh Testing MCP"""

    def __init__(self, server_path: Optional[Path] = None):
        """
        Initialize test client

        Args:
            server_path: Path to the MCP server script (auto-detected if not provided)
        """
        if server_path is None:
            server_path = Path(__file__).parent / "server.py"

        self.server_path = server_path

    async def run_backend_tests(
        self,
        test_path: Optional[str] = None,
        verbose: bool = False,
        markers: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Run backend pytest tests

        Args:
            test_path: Specific test file or directory
            verbose: Enable verbose output
            markers: Pytest markers to filter tests

        Returns:
            Test results with success status, output, and report
        """
        return await self._call_tool("run_backend_tests", {
            "test_path": test_path,
            "verbose": verbose,
            "markers": markers
        })

    async def run_frontend_tests(
        self,
        watch: bool = False,
        coverage: bool = False
    ) -> dict[str, Any]:
        """
        Run frontend vitest tests

        Args:
            watch: Run in watch mode
            coverage: Generate coverage report

        Returns:
            Test results
        """
        return await self._call_tool("run_frontend_tests", {
            "watch": watch,
            "coverage": coverage
        })

    async def run_integration_tests(
        self,
        test_path: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Run integration tests only

        Args:
            test_path: Specific test file or directory

        Returns:
            Test results
        """
        return await self._call_tool("run_integration_tests", {
            "test_path": test_path
        })

    async def run_all_tests(self, verbose: bool = False) -> dict[str, Any]:
        """
        Run all tests (backend + frontend)

        Args:
            verbose: Enable verbose output

        Returns:
            Combined test results
        """
        return await self._call_tool("run_all_tests", {
            "verbose": verbose
        })

    async def discover_tests(self) -> dict[str, Any]:
        """
        Discover all available tests

        Returns:
            Test discovery results
        """
        return await self._call_tool("discover_tests", {})

    async def run_changed_tests(self, changed_files: list[str]) -> dict[str, Any]:
        """
        Run tests for changed files

        Args:
            changed_files: List of changed file paths

        Returns:
            Test results for affected tests
        """
        return await self._call_tool("run_changed_tests", {
            "changed_files": changed_files
        })

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Internal method to call MCP tool

        This is a simplified implementation. In production, you'd use
        proper MCP client libraries.
        """
        # For now, we'll import and call the test runner directly
        # In a real MCP setup, this would go through the MCP protocol
        from server import test_runner

        if tool_name == "run_backend_tests":
            return await test_runner.run_backend_tests(**arguments)
        elif tool_name == "run_frontend_tests":
            return await test_runner.run_frontend_tests(**arguments)
        elif tool_name == "run_integration_tests":
            return await test_runner.run_integration_tests(**arguments)
        elif tool_name == "run_all_tests":
            verbose = arguments.get("verbose", False)
            backend = await test_runner.run_backend_tests(verbose=verbose)
            frontend = await test_runner.run_frontend_tests()
            return {
                "backend": backend,
                "frontend": frontend,
                "success": backend["success"] and frontend["success"]
            }
        elif tool_name == "discover_tests":
            return await test_runner.discover_tests()
        elif tool_name == "run_changed_tests":
            return await test_runner.run_changed_tests(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


# Convenience functions for quick access
async def test_backend(test_path: Optional[str] = None, verbose: bool = False):
    """Quick function to run backend tests"""
    client = TestClient()
    return await client.run_backend_tests(test_path=test_path, verbose=verbose)


async def test_frontend(coverage: bool = False):
    """Quick function to run frontend tests"""
    client = TestClient()
    return await client.run_frontend_tests(coverage=coverage)


async def test_all(verbose: bool = False):
    """Quick function to run all tests"""
    client = TestClient()
    return await client.run_all_tests(verbose=verbose)


async def test_changed(changed_files: list[str]):
    """Quick function to test changed files"""
    client = TestClient()
    return await client.run_changed_tests(changed_files)


# Example usage
if __name__ == "__main__":
    async def demo():
        client = TestClient()

        print("Running backend tests...")
        results = await client.run_backend_tests(verbose=True)
        print(json.dumps(results, indent=2))

        print("\nDiscovering tests...")
        discovery = await client.discover_tests()
        print(json.dumps(discovery, indent=2))

    asyncio.run(demo())

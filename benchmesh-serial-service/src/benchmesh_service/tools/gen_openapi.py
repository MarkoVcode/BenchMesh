"""
Generate OpenAPI specification from FastAPI app.

This tool extracts the OpenAPI schema from a FastAPI application and writes
it to JSON and/or YAML files. Used during build process to create static
OpenAPI documentation.

Usage:
    python -m benchmesh_service.tools.gen_openapi --app benchmesh_service.api:app
"""

import argparse
import json
import os
import sys
from importlib import import_module


def _default_out_dir() -> str:
    """Get default output directory (static/openapi in package root)."""
    pkg_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(pkg_root, 'static', 'openapi')


def _load_app(app_path: str):
    """
    Load FastAPI app from module:attribute path.

    Args:
        app_path: Path in form 'module:var', e.g. 'benchmesh_service.api:app'

    Returns:
        FastAPI application instance

    Raises:
        SystemExit: If app_path format is invalid or app not found
    """
    if ':' not in app_path:
        raise SystemExit(
            "Error: --app must be in the form 'module:var', e.g. benchmesh_service.api:app"
        )

    mod_name, var_name = app_path.split(':', 1)

    try:
        mod = import_module(mod_name)
    except ImportError as e:
        raise SystemExit(f"Error: Could not import module '{mod_name}': {e}")

    app = getattr(mod, var_name, None)
    if app is None:
        raise SystemExit(
            f"Error: Could not find attribute '{var_name}' in module '{mod_name}'"
        )

    return app


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI."""
    p = argparse.ArgumentParser(
        description="Generate OpenAPI spec from FastAPI app",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate both JSON and YAML (default)
  python -m benchmesh_service.tools.gen_openapi

  # Generate only JSON
  python -m benchmesh_service.tools.gen_openapi --formats json

  # Custom output directory
  python -m benchmesh_service.tools.gen_openapi --out-dir /tmp/openapi
        """
    )
    p.add_argument(
        '--app',
        default='benchmesh_service.api:app',
        help="App path in form module:var (default: benchmesh_service.api:app)"
    )
    p.add_argument(
        '--out-dir',
        default=_default_out_dir(),
        help="Output directory for spec files (default: static/openapi)"
    )
    p.add_argument(
        '--basename',
        default='openapi',
        help="Base filename without extension (default: openapi)"
    )
    p.add_argument(
        '--formats',
        choices=['json', 'yaml', 'both'],
        default='both',
        help="Output formats to generate (default: both)"
    )
    return p


def main(argv=None) -> int:
    """
    Main entry point for OpenAPI generation tool.

    Args:
        argv: Command line arguments (None = sys.argv)

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    args = build_parser().parse_args(argv)

    # Load app lazily to avoid side effects on import
    print(f"Loading FastAPI app from {args.app}...")
    try:
        app = _load_app(args.app)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 1

    # Generate OpenAPI schema
    print("Generating OpenAPI schema...")
    try:
        spec = app.openapi()
    except Exception as e:
        print(f"Error: Failed to generate OpenAPI schema: {e}", file=sys.stderr)
        return 1

    # Create output directory
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}")

    wrote_any = False

    # Write JSON format
    if args.formats in ('json', 'both'):
        json_path = os.path.join(out_dir, f"{args.basename}.json")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
            print(f"✓ Wrote JSON: {json_path}")
            wrote_any = True
        except Exception as e:
            print(f"Error: Failed to write JSON: {e}", file=sys.stderr)
            return 1

    # Write YAML format
    if args.formats in ('yaml', 'both'):
        try:
            import yaml  # type: ignore
        except ImportError:
            print(
                "Warning: PyYAML not installed, skipping YAML output. "
                "Install with: pip install pyyaml",
                file=sys.stderr
            )
        else:
            yaml_path = os.path.join(out_dir, f"{args.basename}.yaml")
            try:
                with open(yaml_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(spec, f, sort_keys=False, allow_unicode=True)
                print(f"✓ Wrote YAML: {yaml_path}")
                wrote_any = True
            except Exception as e:
                print(f"Error: Failed to write YAML: {e}", file=sys.stderr)
                return 1

    if not wrote_any:
        print("Error: No output files were written", file=sys.stderr)
        return 1

    print("✅ OpenAPI generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())

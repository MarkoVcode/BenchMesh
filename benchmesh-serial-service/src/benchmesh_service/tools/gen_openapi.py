import argparse
import json
import os
import sys
from importlib import import_module


def _default_out_dir() -> str:
    # tools/ -> package root = benchmesh_service
    pkg_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(pkg_root, 'doc')


def _load_app(app_path: str):
    # app_path format: module:var, e.g. benchmesh_service.api:app
    if ':' not in app_path:
        raise SystemExit("--app must be in the form 'module:var', e.g. benchmesh_service.api:app")
    mod_name, var_name = app_path.split(':', 1)
    mod = import_module(mod_name)
    app = getattr(mod, var_name, None)
    if app is None:
        raise SystemExit(f"Could not find attribute '{var_name}' in module '{mod_name}'")
    return app


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate OpenAPI spec from FastAPI app")
    p.add_argument('--app', default='benchmesh_service.api:app', help="App path in form module:var")
    p.add_argument('--out-dir', default=_default_out_dir(), help="Output directory for spec files")
    p.add_argument('--basename', default='openapi', help="Base filename without extension")
    p.add_argument('--formats', choices=['json','yaml','both'], default='both', help="Formats to write")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    # Load app lazily to avoid side effects on import
    app = _load_app(args.app)
    spec = app.openapi()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    wrote_any = False

    if args.formats in ('json', 'both'):
        json_path = os.path.join(out_dir, f"{args.basename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        print(f"Wrote: {json_path}")
        wrote_any = True

    if args.formats in ('yaml', 'both'):
        try:
            import yaml  # type: ignore
        except Exception as e:
            print(f"Warning: PyYAML not available, skipping YAML output: {e}", file=sys.stderr)
        else:
            yaml_path = os.path.join(out_dir, f"{args.basename}.yaml")
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(spec, f, sort_keys=False, allow_unicode=True)
            print(f"Wrote: {yaml_path}")
            wrote_any = True

    return 0 if wrote_any else 1


if __name__ == '__main__':
    raise SystemExit(main())

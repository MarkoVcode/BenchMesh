import argparse
import json
import sys
from typing import Any, Dict, List

from ..serial_manager import SerialManager, _repo_root
import os
import yaml


def _resolve_config_path(config: str | None) -> str:
    if config is None:
        # default to repo-root config.yaml
        return os.path.join(_repo_root(), 'config.yaml')
    if not os.path.isabs(config):
        return os.path.join(_repo_root(), config)
    return config


def _load_devices_from_config(config_path: str) -> List[Dict[str, Any]]:
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get('devices', []) or []


def _find_device(devices: List[Dict[str, Any]], device_id: str) -> Dict[str, Any] | None:
    for d in devices:
        if d.get('id') == device_id:
            return d
    return None


def cmd_list(args: argparse.Namespace) -> int:
    cfg_path = _resolve_config_path(args.config)
    devices = _load_devices_from_config(cfg_path)
    for d in devices:
        print(json.dumps({
            'id': d.get('id'),
            'name': d.get('name'),
            'driver': d.get('driver'),
            'port': d.get('port'),
            'model': d.get('model'),
        }, ensure_ascii=False))
    return 0


def _parse_kwargs(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError('kwargs must be a JSON object')
        return data
    except Exception as e:
        raise SystemExit(f"Invalid --kwargs JSON: {e}")


def _coerce_args(args: List[str]) -> List[Any]:
    out: List[Any] = []
    for a in args:
        # Try int, then float, then bool-like, then leave as string
        try:
            out.append(int(a))
            continue
        except Exception:
            pass
        try:
            out.append(float(a))
            continue
        except Exception:
            pass
        if a.lower() in ('true', 'false'):
            out.append(a.lower() == 'true')
            continue
        out.append(a)
    return out


def cmd_call(args: argparse.Namespace) -> int:
    cfg_path = _resolve_config_path(args.config)
    devices = _load_devices_from_config(cfg_path)
    dev = _find_device(devices, args.id)
    if not dev:
        print(f"Device id '{args.id}' not found in {cfg_path}", file=sys.stderr)
        return 2

    # Create a SerialManager with only this device to avoid connecting others
    mgr = SerialManager([dev])

    try:
        # Ensure connected (SerialManager.__init__ already connects)
        drv = mgr.connections.get(args.id)
        if not drv:
            # try reconnect explicitly
            drv = mgr.reconnect(args.id)
        if not drv:
            print(f"Failed to connect to device '{args.id}'", file=sys.stderr)
            return 3

        method_name = args.method
        if not hasattr(drv, method_name):
            print(f"Driver has no method '{method_name}'", file=sys.stderr)
            return 4

        method = getattr(drv, method_name)
        if not callable(method):
            print(f"Attribute '{method_name}' is not callable", file=sys.stderr)
            return 5

        pos_args = _coerce_args(args.args or [])
        kw_args = _parse_kwargs(args.kwargs)

        result = method(*pos_args, **kw_args)
        # Normalize bytes to text
        if isinstance(result, (bytes, bytearray)):
            try:
                result = result.decode()
            except Exception:
                result = result.hex()

        if isinstance(result, (dict, list, tuple)):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
        return 0
    finally:
        try:
            mgr.stop()
        except Exception:
            pass


def cmd_methods(args: argparse.Namespace) -> int:
    cfg_path = _resolve_config_path(args.config)
    devices = _load_devices_from_config(cfg_path)
    dev = _find_device(devices, args.id)
    if not dev:
        print(f"Device id '{args.id}' not found in {cfg_path}", file=sys.stderr)
        return 2

    mgr = SerialManager([dev])
    try:
        drv = mgr.connections.get(args.id) or mgr.reconnect(args.id)
        if not drv:
            print(f"Failed to connect to device '{args.id}'", file=sys.stderr)
            return 3
        names = []
        for n in dir(drv):
            if n.startswith('_'):
                continue
            obj = getattr(drv, n)
            if callable(obj):
                names.append(n)
        for n in sorted(names):
            print(n)
        return 0
    finally:
        try:
            mgr.stop()
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='BenchMesh driver manual test tool')
    p.add_argument('--config', help='Path to config.yaml (default: repo root config.yaml)')
    sub = p.add_subparsers(dest='cmd', required=True)

    p_list = sub.add_parser('list', help='List devices from config')
    p_list.set_defaults(func=cmd_list)

    p_methods = sub.add_parser('methods', help='List public methods of a device driver')
    p_methods.add_argument('--id', required=True, help='Device id (from config)')
    p_methods.set_defaults(func=cmd_methods)

    p_call = sub.add_parser('call', help='Call a method on a device driver')
    p_call.add_argument('--id', required=True, help='Device id (from config)')
    p_call.add_argument('--method', required=True, help='Method name to call')
    p_call.add_argument('args', nargs='*', help='Positional args (auto-coerced)')
    p_call.add_argument('--kwargs', help='JSON object of keyword args, e.g. {"ch":1}')
    p_call.set_defaults(func=cmd_call)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    return ns.func(ns)


if __name__ == '__main__':
    raise SystemExit(main())

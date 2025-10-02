# BenchMesh Tools – OpenAPI Generator

This folder contains helper scripts for the BenchMesh Serial Service.

- `driver_cli.py` – Manual driver testing utility
- `gen_openapi.py` – Generate the OpenAPI specification from the FastAPI app

## gen_openapi.py

Generate the OpenAPI specification (JSON and/or YAML) for the BenchMesh FastAPI app.

By default it writes into:

```
benchmesh-serial-service/src/benchmesh_service/doc/
```

with filenames `openapi.json` and `openapi.yaml`.

### Prerequisites

- Python 3.10+
- PyYAML (optional, only needed to emit YAML):
  - `pip install pyyaml`

### Running from the repo root

Most commonly you’ll run the script from the repository root and point `PYTHONPATH` at the package source directory so Python imports the in-repo code:

```
PYTHONPATH=benchmesh-serial-service/src \
  python3 -m benchmesh_service.tools.gen_openapi --help
```

Generate both JSON and YAML (defaults):

```
PYTHONPATH=benchmesh-serial-service/src \
  python3 -m benchmesh_service.tools.gen_openapi
```

Explicit output directory and formats:

```
# Write into the default doc folder (explicit), both formats
PYTHONPATH=benchmesh-serial-service/src \
  python3 -m benchmesh_service.tools.gen_openapi \
  --out-dir benchmesh-serial-service/src/benchmesh_service/doc \
  --basename openapi \
  --formats both

# JSON only
PYTHONPATH=benchmesh-serial-service/src \
  python3 -m benchmesh_service.tools.gen_openapi --formats json

# YAML only (requires PyYAML)
PYTHONPATH=benchmesh-serial-service/src \
  python3 -m benchmesh_service.tools.gen_openapi --formats yaml
```

### Options

- `--app` – App path in the form `module:var` (default: `benchmesh_service.api:app`)
- `--out-dir` – Output directory (default: `src/benchmesh_service/doc` inside the package)
- `--basename` – Base filename without extension (default: `openapi`)
- `--formats` – One of `json`, `yaml`, `both` (default: `both`)

### Notes

- The script imports the FastAPI app and calls `app.openapi()`. It does not run the server or start background threads, and it does not require hardware connections.
- If you have a non-default configuration path for the service at runtime, it does not affect spec generation. The OpenAPI definition is static relative to the defined routes.
- If PyYAML is not installed, the script will still write JSON and will print a warning about skipping YAML output.

### Troubleshooting

- If Python seems to import an older installed version of the package, ensure you set `PYTHONPATH=benchmesh-serial-service/src` when invoking the module.
- If you modify routes in `benchmesh_service/api.py`, re-run this script to regenerate the spec.

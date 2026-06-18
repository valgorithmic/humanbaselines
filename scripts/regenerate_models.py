#!/usr/bin/env python3
"""Regenerate src/humanbaselines/_generated.py from the live API's OpenAPI schema.

The Human Crash Baselines API's published OpenAPI schema is the single source of
truth for the client's types — no hand-maintained mirror, no drift. Run this
whenever the API contract changes:

    python scripts/regenerate_models.py
    python scripts/regenerate_models.py --url http://localhost:8000   # local server

It fetches GET <base>/openapi.json and runs datamodel-code-generator. The base
URL defaults to https://humanbaselines.com (override with --url or the
HUMANBASELINES_OPENAPI_URL env var). Requires the dev deps: `pip install -e '.[dev]'`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

DEFAULT_BASE_URL = "https://humanbaselines.com"

# Fixed input filename so codegen's `# filename:` comment stays stable across
# runs (a random temp name would make every regeneration a spurious diff).
SPEC_PATH = Path(tempfile.gettempdir()) / "humanbaselines_openapi.json"

OUT = Path(__file__).resolve().parents[1] / "src/humanbaselines/_generated.py"

HEADER = (
    "# AUTO-GENERATED -- DO NOT EDIT.\n"
    "# Generated from the live Human Crash Baselines OpenAPI schema by\n"
    "# scripts/regenerate_models.py.\n"
    "# Re-run that script after any API contract change.\n\n"
)


def _base_url() -> str:
    # --url <value> (or --url=<value>) > env var > default.
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--url" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--url="):
            return arg.split("=", 1)[1]
    return os.environ.get("HUMANBASELINES_OPENAPI_URL", DEFAULT_BASE_URL)


def main() -> None:
    base = _base_url().rstrip("/")
    url = f"{base}/openapi.json"
    print(f"fetching {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    spec = resp.json()
    SPEC_PATH.write_text(json.dumps(spec))

    cmd = [
        sys.executable, "-m", "datamodel_code_generator",
        "--input", str(SPEC_PATH), "--input-file-type", "openapi",
        "--output", str(OUT),
        "--output-model-type", "pydantic_v2.BaseModel",
        "--use-standard-collections", "--use-union-operator",
        "--use-default", "--field-constraints", "--strict-nullable",
        "--target-python-version", "3.10",
        "--formatters", "black", "isort",
        "--disable-timestamp",
    ]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)
    # Prepend a commented do-not-edit header (comments may precede `from
    # __future__`, so this stays valid).
    OUT.write_text(HEADER + OUT.read_text())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

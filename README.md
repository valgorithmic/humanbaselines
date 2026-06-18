# humanbaselines

[![CI](https://github.com/valgorithmic/humanbaselines/actions/workflows/test.yml/badge.svg)](https://github.com/valgorithmic/humanbaselines/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/humanbaselines.svg)](https://pypi.org/project/humanbaselines/)
[![docs](https://img.shields.io/badge/docs-humanbaselines.com-blue)](https://docs.humanbaselines.com)

Python client for the Human Crash Baselines API: typed access to human-driver crash-rate baselines by region, route, and filter.

It wraps the `/v1` REST API: construct a client with your key, call typed methods, get typed results back (no hand-built JSON, no remembering the auth header).

## Install

```bash
pip install humanbaselines
```

Or install the latest from source:

```bash
pip install "git+https://github.com/valgorithmic/humanbaselines.git"
# or, from a checkout:
pip install .
```

## Quickstart

```python
from humanbaselines import HumanBaselines

hb = HumanBaselines(api_key="hbk_...")          # or set HUMANBASELINES_API_KEY

# Geofence crash rate (kwargs are validated client-side):
r = hb.compute(county="travis", outcome="police_reported", ego_vehicle=["cars", "light_trucks"])
print(r.rate, r.rate_low, r.rate_high)          # 4.055 4.0 4.1
print(r.N, r.D_miles, len(r.cells))             # 24617.0 6.07e9 1795

# Discover valid filters + defaults at runtime:
for f in hb.filters().modes["geofence"]:
    print(f.id, "→", [o.id for o in f.options], "default:", f.default)

# Which regions / modes are available:
hb.regions()
```

### Filters

Pass filters three ways - keyword args (simplest), a typed `Selections` model,
or a plain dict. All are validated **before** the request, so a bad value fails
fast locally:

```python
from humanbaselines import GeofenceSelections, Outcome

hb.compute(outcome="fatal", road_type=["interstate"])           # kwargs
hb.compute(selections=GeofenceSelections(outcome=Outcome.fatal)) # typed model
hb.compute(selections={"outcome": "fatal"})                      # dict
```

Omitted filters fall back to the API's defaults (these reproduce the web UI's
headline numbers).

### Binding a baseline definition

The filter selections are really a *methodological definition* - what counts as
a crash and what you're baselining against. Bind that definition to the client
once and every call inherits it; per-call args override individual fields:

```python
hb = HumanBaselines(api_key="hbk_...", config={
    "county": "travis",
    "outcome": "fatal",
    "ego_vehicle": ["cars", "light_trucks"],
})

hb.compute().rate                  # uses the bound definition
hb.compute(weather=["rain"]).rate  # override just one field for this call

hb.config()                        # full effective config (bound + every default)
hb.changes()                       # only the settings that differ from the defaults
```

`config(mode="geofence")` and `changes(mode="geofence")` take an optional mode
(each mode exposes different fields). `config()` is the complete definition a
compute call would use; `changes()` is just your deviations from the defaults.

The bound config is validated when you create the client (unknown fields or bad
values raise immediately). It applies to **all modes** - each compute mode uses
the subset of fields it understands (e.g. `road_type` only affects geofence,
`ci_method` only affects route/depot), so you can keep one definition across
modes.

Derive variants immutably, and version definitions as JSON:

```python
strict = hb.with_config(under_reporting="adjusted")   # new client; hb is unchanged

hb.save_config("odd_fatal_cars.json")        # full config snapshot (check into a repo, share, diff)

# Load it back - pass the path straight to the constructor:
hb2 = HumanBaselines(api_key="hbk_...", config="odd_fatal_cars.json")
# (HumanBaselines.from_config(path, api_key=...) is an equivalent, explicit alias.)
```

### Route & depot modes

Available for route/depot-capable regions - `travis` and `ca_az_interstates`
(check `hb.regions()`). Route/depot count Class-8 combination
trucks, so `ego_vehicle` defaults to `["combination"]` in these modes.

```python
hb.compute_route(segment_ids=[("I-35", 250), ("I-35", 251)], ego_vehicle=["combination"])

hb.compute_depot_route(
    depot_a=(30.25, -97.75),     # (lat, lon)
    depot_b=(30.40, -97.70),
    ci_method="fay_feuer",
)
```

## Errors

Non-2xx responses raise typed exceptions you can catch:

```python
from humanbaselines import AuthenticationError, ValidationError, ServiceUnavailableError

try:
    hb.compute(outcome="fatal")
except AuthenticationError:        # 401 - bad/missing key
    ...
except ValidationError as e:       # 422 - e.errors has the field-level detail
    print(e.errors)
except ServiceUnavailableError:    # 503 - service warming up (auto-retried first)
    ...
```

All inherit from `HumanBaselinesError`. The base `APIError` carries `.status_code`
and `.body`.

## Configuration

| arg | default | notes |
|---|---|---|
| `api_key` | `$HUMANBASELINES_API_KEY` | sent as `X-API-Key` |
| `base_url` | `https://humanbaselines.com` | proxies `/v1/*`; use the Cloud Run URL for `/health` |
| `timeout` | `30` | seconds per request |
| `max_retries` | `2` | exponential backoff on 502/503/504 (handles cold-start warm-up) |

`HumanBaselines` is also a context manager (`with HumanBaselines(...) as hb:`).

## Notes

- The typed models in `_generated.py` are **generated from the server's OpenAPI
  schema** - the server's Pydantic models are the single source of truth, so the
  client can't drift from the API. `GET /v1/filters` is the authoritative
  runtime source for valid values and defaults.
- Interactive API docs: the `/docs` page on the API host.

## Development

```bash
pip install -e '.[dev]'
pytest -q                                  # mocked tests
HUMANBASELINES_API_KEY=hbk_... pytest -q    # also runs the live smoke test
python -m build                            # build wheel + sdist into dist/
```

### Regenerating models after an API change

`src/humanbaselines/_generated.py` is generated - never hand-edit it. When the
API contract changes, regenerate from the live OpenAPI schema:

```bash
python scripts/regenerate_models.py
# point at a different host (e.g. local dev server):
python scripts/regenerate_models.py --url http://localhost:8000
```

This fetches `<host>/openapi.json` (default `https://humanbaselines.com`) and runs
`datamodel-code-generator`. Output is deterministic (no timestamps), so a clean
`git diff` means the client is in sync with the API.

> Releases are automated: a version bump in the upstream app dispatches a release
> here, which tags `v<version>` and publishes to PyPI via Trusted Publishing.

## License

Apache-2.0 © Valgorithmic, Inc. (d.b.a. Valgo)

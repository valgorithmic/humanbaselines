"""Synchronous client for the Human Crash Baselines API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .models import (
    DEFAULT_COUNTY,
    ComputeResult,
    DepotComputeResult,
    DepotPin,
    DepotSelections,
    FiltersResponse,
    GeofenceSelections,
    RegionsResponse,
    RouteComputeResult,
    RouteSelections,
)

DEFAULT_BASE_URL = "https://humanbaselines.com"

# tuple/list of (lat, lon), a DepotPin, or a {"lat","lon"} dict
PinLike = tuple[float, float] | list[float] | DepotPin | dict

_MODE_MODELS = {
    "geofence": GeofenceSelections,
    "route": RouteSelections,
    "depot": DepotSelections,
}
# Every valid key a bound config may carry: "county" plus the union of all
# modes' selection fields.
_KNOWN_CONFIG_KEYS = {"county"} | {
    f for m in _MODE_MODELS.values() for f in m.model_fields
}


class HumanBaselines:
    """Client for the Human Crash Baselines `/v1` API.

    >>> hb = HumanBaselines(api_key="hbk_...")          # or env HUMANBASELINES_API_KEY
    >>> hb.compute(outcome="police_reported").rate
    4.05
    >>> hb.filters().modes.keys()
    dict_keys(['geofence', 'route', 'depot'])

    Args:
        api_key:    your API key. Falls back to the ``HUMANBASELINES_API_KEY``
                    env var. Sent as the ``X-API-Key`` header.
        base_url:   API host. Defaults to https://humanbaselines.com (which
                    proxies ``/v1/*``). Point at the Cloud Run URL for non-/v1
                    paths like ``/health``.
        timeout:    per-request timeout in seconds.
        max_retries: automatic retries for transient 5xx / 503 warm-up, with
                    exponential backoff.
        session:    bring your own ``requests.Session`` (otherwise one is made).
        config:     a baseline definition bound to this client — a dict of
                    ``"county"`` plus any filter fields, OR a path to a JSON file
                    written by ``save_config`` (a ``"mode"`` key is ignored).
                    Every ``compute*`` call inherits it (each mode uses the
                    subset of fields it understands); per-call args override it.
                    Validated here, so bad fields/values fail fast.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
        session: requests.Session | None = None,
        config: dict | str | Path | None = None,
    ):
        api_key = api_key or os.environ.get("HUMANBASELINES_API_KEY")
        if not api_key:
            raise ValueError(
                "API key required: pass api_key=... or set HUMANBASELINES_API_KEY."
            )
        # Retained so with_config() can rebuild a sibling client.
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries

        self._root = base_url.rstrip("/")
        self._v1 = f"{self._root}/v1"
        self._config = self._validate_config(self._load_config(config))

        self._session = session or requests.Session()
        self._session.headers.update({"X-API-Key": api_key})
        retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    @staticmethod
    def _load_config(config: dict | str | Path | None) -> dict:
        """Normalize the `config=` argument into a plain dict. Accepts a dict, a
        path to a JSON file (written by save_config), or None. A top-level
        ``"mode"`` key (save_config metadata) is stripped."""
        if config is None:
            return {}
        if isinstance(config, (str, Path)):
            config = json.loads(Path(config).read_text())
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, path, or None (got {type(config).__name__})")
        return {k: v for k, v in config.items() if k != "mode"}

    @staticmethod
    def _validate_config(config: dict) -> dict:
        """Validate a bound config: known field names + valid values. County is
        allowed but not value-checked here (the server resolves it)."""
        unknown = set(config) - _KNOWN_CONFIG_KEYS
        if unknown:
            raise ValueError(
                f"unknown config field(s): {sorted(unknown)}. "
                f"Valid keys: {sorted(_KNOWN_CONFIG_KEYS)}"
            )
        # Value-check each field by building the mode model(s) that own it.
        for mode, model in _MODE_MODELS.items():
            subset = {k: v for k, v in config.items() if k in model.model_fields}
            if subset:
                model(**subset)  # raises on a bad value
        return dict(config)

    # -- transport ----------------------------------------------------------

    def _request(self, method: str, path: str, *, versioned: bool = True,
                 json: Any = None, params: Any = None) -> Any:
        base = self._v1 if versioned else self._root
        resp = self._session.request(method, base + path, json=json,
                                     params=params, timeout=self._timeout)
        self._raise_for_status(resp)
        try:
            return resp.json()
        except ValueError:
            raise APIError(
                f"expected JSON from {path} but got "
                f"{resp.headers.get('content-type')!r}. If base_url is "
                "humanbaselines.com, only /v1/* is proxied there — use the "
                "Cloud Run URL for non-/v1 paths like /health.",
                status_code=resp.status_code, body=resp.text[:200],
            )

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.ok:
            return
        try:
            body: Any = resp.json()
        except ValueError:
            body = resp.text
        detail = body.get("detail") if isinstance(body, dict) else body
        msg = f"{resp.status_code} {resp.reason}: {detail}"
        exc = {
            401: AuthenticationError,
            422: ValidationError,
            404: NotFoundError,
            503: ServiceUnavailableError,
        }.get(resp.status_code, APIError)
        raise exc(msg, status_code=resp.status_code, body=body)

    def _overrides(self, model_cls, selections, filters: dict) -> dict:
        """Per-call overrides as a plain dict: kwargs, a dict, or a model's
        *explicitly-set* fields (so a model's own defaults don't clobber the
        bound config)."""
        if selections is not None and filters:
            raise TypeError("pass either `selections` or filter kwargs, not both")
        if selections is None:
            return dict(filters)
        if isinstance(selections, dict):
            return dict(selections)
        if isinstance(selections, model_cls):
            return selections.model_dump(exclude_unset=True)
        raise TypeError(
            f"selections must be a {model_cls.__name__}, dict, or omitted "
            f"(got {type(selections).__name__})"
        )

    def _resolve_selections(self, model_cls, selections, filters: dict) -> dict:
        """Merge the bound config (subset valid for this mode) under the per-call
        overrides, validate via the mode model, and serialize for the wire."""
        bound = {k: v for k, v in self._config.items() if k in model_cls.model_fields}
        overrides = self._overrides(model_cls, selections, filters)
        # extra="forbid" keeps per-call overrides strict (a bad/foreign field
        # errors); bound fields were already filtered to this mode.
        model = model_cls(**{**bound, **overrides})
        # mode="json" coerces enums to strings; warnings=False silences the
        # str-vs-Enum default notice (generated defaults are strings, emitted
        # value is correct).
        return model.model_dump(mode="json", exclude_none=True, warnings=False)

    def _county(self, county: str | None) -> str:
        """Per-call county wins, else the bound config's, else the default."""
        return county or self._config.get("county") or DEFAULT_COUNTY

    @staticmethod
    def _pin(p: PinLike) -> dict:
        if isinstance(p, DepotPin):
            return p.model_dump()
        if isinstance(p, dict):
            return DepotPin(**p).model_dump()
        lat, lon = p  # (lat, lon) tuple/list
        return {"lat": float(lat), "lon": float(lon)}

    # -- discovery ----------------------------------------------------------

    def filters(self) -> FiltersResponse:
        """Catalog of every filter, its valid options, and per-mode defaults."""
        return FiltersResponse.model_validate(self._request("GET", "/filters"))

    def regions(self) -> RegionsResponse:
        """Counties available on the server and which compute modes each supports."""
        return RegionsResponse.model_validate(self._request("GET", "/regions"))

    def manifest(self) -> dict:
        """Dataset metadata (schema version, row counts, availability)."""
        return self._request("GET", "/manifest")

    def health(self) -> dict:
        """Service status, e.g. ``{"status": "ready"}``.

        Hits the unversioned ``/health`` endpoint, which is NOT proxied by
        humanbaselines.com — use a Cloud Run ``base_url`` for this call.
        """
        return self._request("GET", "/health", versioned=False)

    # -- compute ------------------------------------------------------------

    def compute(self, selections: GeofenceSelections | dict | None = None, *,
                county: str | None = None, **filters) -> ComputeResult:
        """Geofence (S2-cell) crash rate. Inherits the bound config; per-call
        args override it."""
        sel = self._resolve_selections(GeofenceSelections, selections, filters)
        data = self._request("POST", "/compute",
                             json={"county": self._county(county), "selections": sel})
        return ComputeResult.model_validate(data)

    def compute_route(self, segment_ids: list[tuple[str, int]],
                      selections: RouteSelections | dict | None = None, *,
                      county: str | None = None, **filters) -> RouteComputeResult:
        """Crash rate over a sequence of interstate (route, milepost) segments.
        For route-capable regions (``travis``, ``ca_interstates``,
        ``sw_interstates`` — see ``regions()``). Inherits the bound config;
        per-call args override it."""
        sel = self._resolve_selections(RouteSelections, selections, filters)
        data = self._request("POST", "/compute/route", json={
            "county": self._county(county),
            "segment_ids": [list(s) for s in segment_ids],
            "selections": sel,
        })
        return RouteComputeResult.model_validate(data)

    def compute_depot_route(self, depot_a: PinLike, depot_b: PinLike,
                            selections: DepotSelections | dict | None = None, *,
                            county: str | None = None, **filters) -> DepotComputeResult:
        """Full depot-to-depot trip rate (access + interstate + access legs).
        For depot-capable regions (``travis``, ``ca_interstates``,
        ``sw_interstates`` — see ``regions()``). Pins are (lat, lon) tuples,
        DepotPins, or dicts. Inherits the bound config; per-call args override it."""
        sel = self._resolve_selections(DepotSelections, selections, filters)
        data = self._request("POST", "/compute/depot-route", json={
            "county": self._county(county),
            "depot_a": self._pin(depot_a),
            "depot_b": self._pin(depot_b),
            "selections": sel,
        })
        return DepotComputeResult.model_validate(data)

    # -- bound config (the baseline "definition") ---------------------------

    def config(self, mode: str = "geofence") -> dict:
        """The full effective config for a mode — your bound values plus every
        default filled in, with county. This is the complete definition a
        compute call in this mode would use."""
        if mode not in _MODE_MODELS:
            raise ValueError(f"unknown mode {mode!r}; choose from {sorted(_MODE_MODELS)}")
        model_cls = _MODE_MODELS[mode]
        bound = {k: v for k, v in self._config.items() if k in model_cls.model_fields}
        sel = model_cls(**bound).model_dump(mode="json", warnings=False)
        return {"county": self._county(None), **sel}

    def changes(self, mode: str = "geofence") -> dict:
        """Only the settings that differ from this mode's defaults (the
        deviations), including county if you've changed it."""
        full = self.config(mode)
        defaults = _MODE_MODELS[mode]().model_dump(mode="json", warnings=False)
        defaults["county"] = DEFAULT_COUNTY
        return {k: v for k, v in full.items() if v != defaults.get(k)}

    def with_config(self, config: dict | None = None, **fields) -> "HumanBaselines":
        """Return a NEW client with the bound config updated (this one is left
        unchanged). Per-field merge: ``{**current, **config, **fields}``. The
        underlying HTTP session is shared."""
        merged = {**self._config, **(config or {}), **fields}
        return HumanBaselines(
            self._api_key, base_url=self._base_url, timeout=self._timeout,
            max_retries=self._max_retries, session=self._session, config=merged,
        )

    def save_config(self, path: str | Path, mode: str = "geofence") -> None:
        """Write the FULL effective config (every default filled in) to a JSON
        file — a complete, self-documenting snapshot of the definition, not just
        the deviations. A top-level ``"mode"`` key records which mode's field set
        it captures. Defaults to geofence; pass ``mode`` for route/depot. Reload
        with ``from_config``."""
        payload = {"mode": mode, **self.config(mode)}
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")

    @classmethod
    def from_config(cls, source: str | Path | dict, api_key: str | None = None,
                    **client_kwargs) -> "HumanBaselines":
        """Explicit alternative constructor from a saved definition (path or
        dict). Equivalent to ``HumanBaselines(api_key, config=source)`` — the
        constructor accepts a path directly — kept for readable intent."""
        return cls(api_key, config=source, **client_kwargs)

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HumanBaselines":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __repr__(self) -> str:
        cfg = f", config={self._config}" if self._config else ""
        return f"HumanBaselines(base_url={self._root!r}{cfg})"

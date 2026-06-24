"""Public model surface for the Human Crash Baselines client.

The types are GENERATED from the server's OpenAPI schema into `_generated.py`
(do not edit that file by hand). The server's Pydantic models
(`data-prep/server/schemas.py` + `catalog.py`) are the single source of truth;
regenerate with `scripts/regenerate_models.py` after any API change. At runtime,
`HumanBaselines.filters()` returns the live catalog of valid values + defaults.

This module just re-exports the generated names the client and public API use
(notably NOT the generated `ValidationError`/`HTTPValidationError` models, which
would collide with the client's `ValidationError` *exception*).
"""

from __future__ import annotations

from ._generated import (  # noqa: F401
    BatchComputeResult,
    BatchItemResult,
    CiMethod,
    ComputeResult,
    DepotComputeResult,
    DepotPin,
    DepotSelections,
    DriverImpairment,
    FilterDef,
    FilterOption,
    FiltersResponse,
    GeofenceSelections,
    InTransport,
    LightFilter,
    MultiplierVmt,
    Outcome,
    PerCellResult,
    PerSegmentResult,
    RegionInfo,
    RegionsResponse,
    RoadGroup,
    OperatorWeighting,
    RouteComputeResult,
    RouteSelections,
    Tier3Mode,
    UnderReporting,
    VehicleClass,
    WeatherFilter,
)

# Client-side constant (not part of the wire schema).
DEFAULT_COUNTY = "travis"

__all__ = [
    "DEFAULT_COUNTY",
    # request models
    "GeofenceSelections",
    "RouteSelections",
    "DepotSelections",
    "DepotPin",
    # response models
    "ComputeResult",
    "BatchComputeResult",
    "BatchItemResult",
    "PerCellResult",
    "RouteComputeResult",
    "PerSegmentResult",
    "DepotComputeResult",
    "FiltersResponse",
    "FilterDef",
    "FilterOption",
    "RegionsResponse",
    "RegionInfo",
    # enums
    "Outcome",
    "VehicleClass",
    "RoadGroup",
    "Tier3Mode",
    "InTransport",
    "OperatorWeighting",
    "MultiplierVmt",
    "WeatherFilter",
    "LightFilter",
    "DriverImpairment",
    "UnderReporting",
    "CiMethod",
]

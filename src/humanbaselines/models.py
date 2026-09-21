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
    SpeedBand,
    Tier3Mode,
    UnderReporting,
    VehicleClass,
    WeatherFilter,
)

# Client-side constant (not part of the wire schema).
DEFAULT_REGION = "travis"

#: The posted-speed steps the API serves, in mph. `le15` is an open tail below,
#: `ge70` an open tail above, and every step between is one 5 mph band.
SPEED_STEPS_MPH = (15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70)
_SPEED_BAND_IDS = ("le15",) + tuple(f"s{m}" for m in SPEED_STEPS_MPH[1:-1]) + ("ge70",)


def speed_bands_up_to(max_mph: int) -> list[str]:
    """The `posted_speed` bands for roads posted at `max_mph` or less.

    Operating domains are stated as a cap ("posted 45 mph or under"), so this
    turns the cap into the contiguous run of bands the API takes:
    ``speed_bands_up_to(45)`` is ``["le15", "s20", ..., "s45"]``. The lowest band
    is an open tail, so a cap of 15 also covers anything posted below 15.

    Raises ``ValueError`` for a cap that is not one of the 5 mph steps from 15 to
    65, and for 70 or more, which is every band and therefore the same as no
    filter. Leave `posted_speed` unset for that.
    """
    if isinstance(max_mph, bool) or not isinstance(max_mph, int):
        raise TypeError(f"posted_speed_max must be an int in mph (got {type(max_mph).__name__})")
    if max_mph >= SPEED_STEPS_MPH[-1]:
        raise ValueError(
            f"posted_speed_max={max_mph} covers every band, which is the unfiltered "
            "rate. Leave posted_speed unset instead.")
    if max_mph not in SPEED_STEPS_MPH[:-1]:
        raise ValueError(
            f"posted_speed_max must be one of {list(SPEED_STEPS_MPH[:-1])} mph "
            f"(got {max_mph}). The API serves 5 mph steps.")
    return list(_SPEED_BAND_IDS[: SPEED_STEPS_MPH.index(max_mph) + 1])
#: Deprecated alias of DEFAULT_REGION. The API's area identifier was renamed
#: from "county" to "region", because most served areas are not counties: `sf`
#: is three of them, the Massachusetts entries are municipalities, and
#: `interstates` is a multi-state corridor. The old name keeps working.
DEFAULT_COUNTY = DEFAULT_REGION

__all__ = [
    "DEFAULT_REGION",
    "DEFAULT_COUNTY",
    "SPEED_STEPS_MPH",
    "speed_bands_up_to",
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
    "SpeedBand",
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

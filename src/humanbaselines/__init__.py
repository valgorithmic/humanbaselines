"""humanbaselines — Python client for the Human Crash Baselines API.

>>> from humanbaselines import HumanBaselines
>>> hb = HumanBaselines(api_key="hbk_...")        # or env HUMANBASELINES_API_KEY
>>> hb.compute(outcome="police_reported").rate
"""

from __future__ import annotations

__version__ = "0.1.4"

from .client import HumanBaselines
from .exceptions import (
    APIError,
    AuthenticationError,
    HumanBaselinesError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .models import (
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

__all__ = [
    "__version__",
    "HumanBaselines",
    # exceptions
    "HumanBaselinesError",
    "APIError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "ServiceUnavailableError",
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
    "UnderReporting",
    "WeatherFilter",
    "LightFilter",
    "DriverImpairment",
    "CiMethod",
]

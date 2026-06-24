"""Tests for the humanbaselines client.

Mocked tests (no network) via `responses`, plus one opt-in live smoke test
against humanbaselines.com that runs only when HUMANBASELINES_API_KEY is set.

    pip install -e '.[dev]'
    pytest -q                                   # mocked only
    HUMANBASELINES_API_KEY=hbk_... pytest -q     # also runs the live smoke test
"""

from __future__ import annotations

import os

import pytest
import responses

from humanbaselines import (
    AuthenticationError,
    ComputeResult,
    GeofenceSelections,
    HumanBaselines,
    ServiceUnavailableError,
    ValidationError,
)

BASE = "https://humanbaselines.com"
V1 = f"{BASE}/v1"

_COMPUTE_BODY = {
    "N": 24617.0, "D_miles": 6.07e9, "D_billions": 6.07,
    "rate": 4.055, "rate_low": 4.0, "rate_high": 4.1,
    "rate_non_dyn": 4.055, "rate_dyn": None, "multiplier": None,
    "cells": [{"s2_cell": "123", "count": 45.2, "vmt": 1.2e7, "mult_contrib": 0.0}],
}


def client(**kw):
    # max_retries=0 keeps the mocked transport deterministic.
    return HumanBaselines(api_key="testkey", max_retries=0, **kw)


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("HUMANBASELINES_API_KEY", raising=False)
    with pytest.raises(ValueError):
        HumanBaselines()


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("HUMANBASELINES_API_KEY", "envkey")
    assert HumanBaselines().__class__ is HumanBaselines  # no error


@responses.activate
def test_compute_sends_key_and_parses():
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    result = client().compute(outcome="police_reported", ego_vehicle=["cars", "light_trucks"])
    assert isinstance(result, ComputeResult)
    assert result.rate == pytest.approx(4.055)
    assert len(result.cells) == 1 and result.cells[0].s2_cell == "123"
    # auth header was sent
    assert responses.calls[0].request.headers["X-API-Key"] == "testkey"
    # selections serialized with the UI-aligned weather default
    import json
    sent = json.loads(responses.calls[0].request.body)
    assert sent["county"] == "travis"
    assert sent["selections"]["weather"] == ["dry", "rain", "fog"]


@responses.activate
def test_compute_summary_only_sends_flag():
    responses.post(f"{V1}/compute", json={**_COMPUTE_BODY, "cells": []}, status=200)
    result = client().compute(summary_only=True)
    assert result.cells == []
    import json
    assert json.loads(responses.calls[0].request.body)["summary_only"] is True


@responses.activate
def test_compute_batch_parses_per_county_results():
    from humanbaselines import BatchComputeResult
    body = {
        "results": [
            {"county": "travis", "result": {**_COMPUTE_BODY, "cells": []}, "error": None},
            {"county": "houston", "result": None, "error": "no HPMS columns"},
        ]
    }
    responses.post(f"{V1}/compute/batch", json=body, status=200)
    out = client().compute_batch(["travis", "houston"], outcome="police_reported")
    assert isinstance(out, BatchComputeResult)
    assert len(out.results) == 2
    assert out.results[0].county == "travis"
    assert out.results[0].result.rate == pytest.approx(4.055)
    assert out.results[1].result is None and out.results[1].error == "no HPMS columns"
    import json
    sent = json.loads(responses.calls[0].request.body)
    assert sent["summary_only"] is True
    assert [it["county"] for it in sent["items"]] == ["travis", "houston"]
    # same (resolved) selections applied to every county
    assert sent["items"][0]["selections"] == sent["items"][1]["selections"]


@responses.activate
def test_typed_selections_accepted():
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    sel = GeofenceSelections(outcome="fatal", road_type=["interstate"])
    assert client().compute(selections=sel).rate == pytest.approx(4.055)


@responses.activate
def test_crash_year_and_denominator_vmt_kwargs():
    # Both are geofence filters added to the contract; they must validate
    # client-side and serialize onto the request body.
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    client().compute(crash_year=[2023], denominator_vmt="calibrated")
    import json
    sent = json.loads(responses.calls[0].request.body)["selections"]
    assert sent["crash_year"] == [2023]
    assert sent["denominator_vmt"] == "calibrated"


@responses.activate
def test_operator_weighting_and_operator_weight_kwargs():
    # The renamed weighting toggle (operator_weighting=robotaxi) and the optional
    # numeric override (operator_weight) must validate client-side and serialize
    # onto the request body.
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    client().compute(operator_weighting="robotaxi", operator_weight=2.5)
    import json
    sent = json.loads(responses.calls[0].request.body)["selections"]
    assert sent["operator_weighting"] == "robotaxi"
    assert sent["operator_weight"] == 2.5


@responses.activate
def test_401_raises_authentication_error():
    responses.post(f"{V1}/compute", json={"detail": "bad key"}, status=401)
    with pytest.raises(AuthenticationError) as e:
        client().compute()
    assert e.value.status_code == 401


@responses.activate
def test_422_raises_validation_error_with_detail():
    detail = [{"loc": ["body", "selections", "outcome"], "msg": "bad value"}]
    responses.post(f"{V1}/compute", json={"detail": detail}, status=422)
    # send a raw dict so the bad value reaches the server instead of being
    # caught client-side.
    with pytest.raises(ValidationError) as e:
        client().compute(selections={"outcome": "police_reported"})
    assert e.value.errors == detail


@responses.activate
def test_503_raises_service_unavailable():
    responses.get(f"{V1}/filters", json={"detail": "loading"}, status=503)
    with pytest.raises(ServiceUnavailableError):
        client().filters()


def test_bad_enum_fails_client_side_before_request():
    # No responses registered: if this hit the network it would error loudly.
    with pytest.raises(Exception):  # pydantic ValidationError
        client().compute(outcome="not-a-real-outcome")


def test_selections_and_kwargs_conflict():
    with pytest.raises(TypeError):
        client().compute(selections=GeofenceSelections(), outcome="fatal")


@responses.activate
def test_filters_parses():
    body = {"modes": {"geofence": [
        {"id": "weather", "label": "Weather", "affects": "both", "multiselect": True,
         "description": "...", "options": [{"id": "dry", "label": "Dry"}],
         "default": ["dry", "rain", "fog"]},
    ]}}
    responses.get(f"{V1}/filters", json=body, status=200)
    fr = client().filters()
    assert "geofence" in fr.modes
    assert fr.modes["geofence"][0].id == "weather"


@responses.activate
def test_route_serializes_segment_ids():
    body = {"N": 1.0, "trip_miles": 10.0, "rate": 0.1, "segments": []}
    responses.post(f"{V1}/compute/route", json=body, status=200)
    client().compute_route(segment_ids=[("I-35", 250), ("I-35", 251)])
    import json
    sent = json.loads(responses.calls[0].request.body)
    assert sent["segment_ids"] == [["I-35", 250], ["I-35", 251]]


@responses.activate
def test_depot_pin_coercion():
    body = {"total": {"rate": 1.0}}
    responses.post(f"{V1}/compute/depot-route", json=body, status=200)
    client().compute_depot_route((30.25, -97.75), (30.4, -97.7))
    import json
    sent = json.loads(responses.calls[0].request.body)
    assert sent["depot_a"] == {"lat": 30.25, "lon": -97.75}


# --- bound config (the baseline "definition") -------------------------------

def _sent(call):
    import json
    return json.loads(call.request.body)


@responses.activate
def test_bound_config_is_sent():
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    hb = client(config={"county": "travis", "outcome": "fatal", "ego_vehicle": ["cars"]})
    hb.compute()
    sent = _sent(responses.calls[0])
    assert sent["county"] == "travis"
    assert sent["selections"]["outcome"] == "fatal"
    assert sent["selections"]["ego_vehicle"] == ["cars"]


@responses.activate
def test_per_call_kwargs_override_bound():
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    hb = client(config={"outcome": "fatal", "weather": ["dry"]})
    hb.compute(weather=["rain"])
    sent = _sent(responses.calls[0])["selections"]
    assert sent["outcome"] == "fatal"        # bound survives
    assert sent["weather"] == ["rain"]        # per-call overrides


@responses.activate
def test_model_override_only_sets_explicit_fields():
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    hb = client(config={"outcome": "fatal"})
    # A model sets every field to a default unless overridden; exclude_unset
    # means only explicitly-passed fields should override the bound config.
    hb.compute(selections=GeofenceSelections(weather=["rain"]))
    sent = _sent(responses.calls[0])["selections"]
    assert sent["outcome"] == "fatal"        # bound NOT clobbered by model default
    assert sent["weather"] == ["rain"]


def test_with_config_is_immutable():
    hb = client(config={"outcome": "fatal"})
    hb2 = hb.with_config(outcome="ka", under_reporting="adjusted")
    assert hb.changes() == {"outcome": "fatal"}           # original untouched
    assert hb2.changes() == {"outcome": "ka", "under_reporting": "adjusted"}


@responses.activate
def test_cross_mode_field_filtering():
    responses.post(f"{V1}/compute", json=_COMPUTE_BODY, status=200)
    responses.post(f"{V1}/compute/route",
                   json={"N": 1.0, "trip_miles": 1.0, "rate": 0.1, "segments": []}, status=200)
    # road_type is geofence-only; ci_method is route/depot-only.
    hb = client(config={"road_type": ["interstate"], "ci_method": "empirical_bayes"})
    hb.compute()
    geo = _sent(responses.calls[0])["selections"]
    assert geo["road_type"] == ["interstate"] and "ci_method" not in geo
    hb.compute_route(segment_ids=[("I-35", 250)])
    route = _sent(responses.calls[1])["selections"]
    assert route["ci_method"] == "empirical_bayes" and "road_type" not in route


def test_bind_time_validation():
    with pytest.raises(ValueError):           # unknown field name
        client(config={"outcom": "fatal"})
    with pytest.raises(Exception):            # bad value (pydantic ValidationError)
        client(config={"outcome": "not-real"})


@responses.activate
def test_per_call_invalid_field_for_mode_raises():
    responses.post(f"{V1}/compute/route", json={"N": 1.0, "trip_miles": 1.0, "rate": 0.1}, status=200)
    hb = client()
    with pytest.raises(Exception):            # road_type isn't a route field
        hb.compute_route(segment_ids=[("I-35", 250)], road_type=["interstate"])


def test_county_precedence():
    hb = client(config={"county": "sf", "outcome": "fatal"})
    assert hb._county(None) == "sf"           # bound
    assert hb._county("travis") == "travis"   # per-call wins
    assert client()._county(None) == "travis"  # default


def test_save_and_from_config_roundtrip(tmp_path):
    import json
    cfg = {"county": "travis", "outcome": "fatal", "ego_vehicle": ["cars", "light_trucks"]}
    hb = client(config=cfg)
    p = tmp_path / "odd.json"
    hb.save_config(p)
    # save_config writes the FULL config (defaults filled) + a "mode" key,
    # not just the changes.
    saved = json.loads(p.read_text())
    assert saved["mode"] == "geofence"
    assert {k: v for k, v in saved.items() if k != "mode"} == hb.config()
    assert saved["weather"] == ["dry", "rain", "fog"]              # a filled default
    # Both load paths work: from_config(path) and config=path on the constructor.
    hb2 = HumanBaselines.from_config(p, api_key="testkey", max_retries=0)
    hb3 = HumanBaselines(api_key="testkey", max_retries=0, config=p)
    assert hb2.config() == hb.config() and hb2.changes() == hb.changes()
    assert hb3.config() == hb.config()              # constructor accepts a path
    assert "mode" not in hb3.changes()              # the "mode" metadata is stripped


def test_config_fills_defaults():
    hb = client(config={"outcome": "fatal"})
    full = hb.config("geofence")
    assert full["outcome"] == "fatal"                 # bound override
    assert full["weather"] == ["dry", "rain", "fog"]  # filled default
    assert full["county"] == "travis"
    assert len(full) == len(GeofenceSelections.model_fields) + 1  # +county
    # route mode exposes ci_method, not road_type
    route = hb.config("route")
    assert "ci_method" in route and "road_type" not in route
    with pytest.raises(ValueError):
        hb.config("bogus")


def test_changes_shows_only_deviations():
    hb = client(config={"county": "travis", "outcome": "fatal", "weather": ["dry", "rain", "fog"]})
    # outcome differs from default; weather equals default; county equals default
    assert hb.changes() == {"outcome": "fatal"}
    # a non-default county shows up
    assert client(config={"county": "sf"}).changes() == {"county": "sf"}
    # no bound config → no changes
    assert client().changes() == {}


# --- opt-in live smoke test -------------------------------------------------

@pytest.mark.skipif(not os.environ.get("HUMANBASELINES_API_KEY"),
                    reason="set HUMANBASELINES_API_KEY to run the live smoke test")
def test_live_smoke():
    hb = HumanBaselines()  # key + default base_url from env/defaults
    assert "geofence" in hb.filters().modes
    result = hb.compute(county="travis", outcome="police_reported")
    assert result.rate > 0 and result.N > 0

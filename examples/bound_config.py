"""Bind a baseline definition to the client and reuse it across calls.

Run with your key in the environment (never hardcode it):

    HUMANBASELINES_API_KEY=hbk_... python examples/bound_config.py
"""

from humanbaselines import HumanBaselines

# The "ODD" — what counts as a crash and what we baseline against.
config = {
    "county": "travis",
    "outcome": "police_reported",
    "ego_vehicle": ["cars"],
}

hb = HumanBaselines(config=config)  # api_key read from HUMANBASELINES_API_KEY

print(hb.compute().rate)                   # every call inherits the bound definition
print(hb.compute(weather=["rain"]).rate)   # override one field for this call

print(hb.config())                         # full effective config (bound + every default)
print(hb.changes())                        # only what differs from the defaults

hb.save_config("odd.json")                 # version the definition

hb_new = hb.with_config(under_reporting="adjusted")  # derive a variant; hb is unchanged

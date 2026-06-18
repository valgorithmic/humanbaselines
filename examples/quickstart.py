"""Quickstart: compute a geofence rate and discover filters.

Run with your key in the environment (never hardcode it):

    HUMANBASELINES_API_KEY=hbk_... python examples/quickstart.py
"""

from humanbaselines import HumanBaselines

hb = HumanBaselines()  # api_key read from HUMANBASELINES_API_KEY

config = {
    "county": "travis",
    "outcome": "police_reported",
    "ego_vehicle": ["cars", "light_trucks"],
}

# Geofence crash rate (kwargs are validated client-side):
r = hb.compute(**config)
print(r.rate, r.rate_low, r.rate_high)   # e.g. 4.055 4.005 4.106
print(r.N, r.D_miles, len(r.cells))      # e.g. 24617.0 6.07e9 1794

# Discover valid filters + defaults at runtime:
for f in hb.filters().modes["geofence"]:
    print(f.id, "→", [o.id for o in f.options], "default:", f.default)

# Which regions / modes are available:
print(hb.regions())

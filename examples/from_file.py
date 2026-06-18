"""Load a saved baseline definition from odd.json and compute with it.

odd.json is the full-config snapshot written by save_config (see
bound_config.py). The point of this example: you can pass the file path
straight to the constructor — no manual JSON parsing.

Run with your key in the environment (never hardcode it):
    HUMANBASELINES_API_KEY=hbk_... python examples/from_file.py
"""

from pathlib import Path

from humanbaselines import HumanBaselines

ODD = Path(__file__).parent / "odd.json"

# Create the definition file if it doesn't exist yet (normally bound_config.py
# writes it via hb.save_config("odd.json")).
if not ODD.exists():
    HumanBaselines(config={
        "county": "travis",
        "outcome": "fatal",
        "ego_vehicle": ["cars", "light_trucks"],
    }).save_config(ODD)

# Construct a client straight from the saved definition file.
hb = HumanBaselines(config=ODD)            # api_key read from HUMANBASELINES_API_KEY
# (HumanBaselines.from_config(ODD) is an equivalent, explicit alias.)

print("loaded from:", ODD.name)
print("deviations from defaults:", hb.changes())   # what this ODD changes
print("full config:", hb.config())                 # every assumption, spelled out
print("rate under this ODD:", hb.compute().rate)

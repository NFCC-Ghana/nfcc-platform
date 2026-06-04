"""
Dam configuration for spillage prediction.
Contains thresholds and parameters for each dam.
"""

DAM_CONFIG = {
    "akosombo": {
        "name": "Akosombo",
        "country": "Ghana",
        "capacity": 100,
        "risk_threshold": 75,
        "spill_level_meters": 84.0,
        "max_capacity_meters": 84.73,
        "description": "Akosombo Dam on the Volta River",
    },
    "bagre": {
        "name": "Bagre",
        "country": "Burkina Faso",
        "capacity": 100,
        "risk_threshold": 70,
        "spill_level_meters": 233.0,
        "max_capacity_meters": 235.0,
        "description": "Bagre Dam on the Nakambe River",
    },
}

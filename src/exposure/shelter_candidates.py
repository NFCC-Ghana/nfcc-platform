"""Real, named public buildings per district that could serve as flood
shelters - not a live or officially-designated shelter registry (none
exists publicly for Ghana; NADMO designates schools/community buildings
ad-hoc during an actual emergency rather than maintaining one - see
docs/CLOUD_RUN_DEPLOY.md's research notes), but genuine places that exist,
queried live from OpenStreetMap (Overpass API, amenity=school, ODbL-licensed
data from openstreetmap.org contributors) for each district's area on
2026-09-16, favoring larger/more substantial-sounding institutions
(secondary schools, colleges) over small daycare/nursery entries.

Capacity/occupancy figures shown alongside these names in the dashboard
remain illustrative - no real shelter capacity data exists anywhere either.
"""

from typing import Dict, List

SHELTER_CANDIDATES: Dict[str, List[str]] = {
    "Accra Central": [
        "Ghana School of Law",
        "Osu Ringway Estate Basic School",
        "Aggrey Memorial International School",
    ],
    "Accra West": [
        "Bluecrest College",
        "Laterbiokorshie Primary School",
        "Otublohum Secondary School",
    ],
    "Accra East": [
        "Dannaks Senior High School",
        "Aggrey Memorial International School",
        "Golden Mission International School",
    ],
    "Tema": [
        "Tema First Baptist School",
        "Deks Educational Institute",
        "ECG Training School",
    ],
    "Kumasi": [
        "State Boys Primary and Junior High School",
        "The Hilltop Platinum Schools",
        "Ramseyer Institute",
    ],
    "Tamale": [
        "Tamale Girls International School",
        "Tamale Nurses & Midwifery Training College",
        "Lamashegu Experimental Primary & Junior High School",
    ],
    "Cape Coast": [
        "University Practice Senior High School",
        "Aggrey College",
        "Christ Church Anglican Basic School",
    ],
    "Ho": [
        "EP University College",
        "School of Hygiene, Ho",
        "Victoria Memorial School",
    ],
    "Sunyani": [
        "Business Senior High School",
        "Sacred Heart High School",
        "Presby Preparatory School",
    ],
}


def get_shelter_names(district: str) -> List[str]:
    """Real venue names for a district, or a generic placeholder list if
    the district isn't covered (matches the previous behavior for any
    district not in this table)."""
    return SHELTER_CANDIDATES.get(
        district,
        [
            f"{district} Senior High School",
            f"{district} Community Center",
            f"{district} Trade Fair Centre",
        ],
    )

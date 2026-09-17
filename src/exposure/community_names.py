"""Real named neighborhoods/communities within each tracked district - used
for geotargeting in the Alert Review Queue (src/api/routes/alert_review.py),
so a reviewer sees the actual places an alert would reach ("Alajo, Kaneshie,
Circle...") instead of only a district name covering a much larger area.

These names previously existed only inside
hackathon/app/pages/dashboard.py's get_district_data() (frontend-only, used
for the broadcast/demo view) - duplicated here as the backend's own copy
because the dashboard and API are separate deployments (Streamlit Community
Cloud vs. Cloud Run) with no shared Python import path between them. Keep
both lists in sync if either changes; this one is the source of truth for
anything the API returns.
"""

from typing import Dict, List

DISTRICT_COMMUNITIES: Dict[str, List[str]] = {
    "Accra Central": ["Alajo", "Kaneshie", "Circle", "Achimota", "Adabraka"],
    "Accra West": ["Dansoman", "Korle Bu", "Mamprobi", "Chorkor", "Awoshie"],
    "Accra East": ["Labone", "East Legon", "Osu", "Cantonments", "Airport"],
    "Tema": [
        "Tema Community 1",
        "Tema Community 2",
        "Tema Industrial",
        "Sakumono",
        "Ashaiman",
    ],
    "Kumasi": ["Asokwa", "Bantama", "Ayigya", "Danyame", "Kwadaso"],
    "Tamale": [
        "Tamale Central",
        "Tamale North",
        "Sagnarigu",
        "Gurugu",
        "Lamashegu",
    ],
    "Cape Coast": ["Pedu", "Abura", "Kakumdo", "Amamoma", "Kotokuraba"],
    "Ho": ["Bankoe", "Heve", "Ahoe", "Dome", "Hliha"],
    "Sunyani": ["Abesim", "Atronie", "New Dormaa", "Penkwase", "Kotokrom"],
}


def get_affected_communities(district: str) -> List[str]:
    """Real named communities for a district, or [] if the district isn't
    one of the 9 this platform tracks."""
    return DISTRICT_COMMUNITIES.get(district, [])

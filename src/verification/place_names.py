"""The place name a news or humanitarian report would actually use for a
tracked district, for the outcome-verification searches
(src/verification/reliefweb_client.py, gdelt_client.py).

"Accra Central", "Accra West" and "Accra East" are this platform's own
split of the Accra urban area; reports say "Accra". A search for the
project's district label would miss them, and an unquoted one matches
"Central" or "West" anywhere. So the three resolve to "Accra", and news
evidence for any of them is evidence for the city as a whole - a real
limit on how finely news can verify an outcome.
"""

_ACCRA_SPLIT = {"Accra Central", "Accra West", "Accra East"}


def search_place(district: str) -> str:
    return "Accra" if district in _ACCRA_SPLIT else district

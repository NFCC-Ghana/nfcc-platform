"""NADMO flood incident records (optional input).

NADMO does not publish its incident database. When the formal request in
nadmo_data_request.md is granted, save the records as
data/<study>/raw/nadmo_incidents.csv with these columns:

    date            YYYY-MM-DD the flooding was reported
    district        district name as NADMO writes it
    region          region name (used to resolve duplicate district names)
    deaths          integer, blank if unknown
    affected        people affected, blank if unknown
    houses_damaged  integer, blank if unknown

Each row is matched to a GAUL 2015 district: exact name, then the same
name without a "Municipal"/"Metropolitan"/"District" suffix, then
config.CURATED_DISTRICT_NAMES. Rows that match no district are written
to nadmo_unmatched.csv for a person to map by hand, never guessed.

Matched incidents are added to the news label, and their `affected`
counts enable E8 (impact layers).
"""

import logging
import re

import pandas as pd

from research.flood_experiments import config as C

logger = logging.getLogger("nfcc.research.nadmo")
COLUMNS = ["date", "district", "region", "deaths", "affected", "houses_damaged"]
_SUFFIX = re.compile(
    r"\s+(municipal|metropolitan|metropolis|metro|district|assembly)\b.*$", re.I
)


def _key(name: str) -> str:
    return _SUFFIX.sub("", str(name)).strip().lower()


def load_incidents(static: pd.DataFrame) -> pd.DataFrame:
    """Matched incidents with a district_code; empty if no file."""
    path = C.DATA_DIR / "raw" / "nadmo_incidents.csv"
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS + ["district_code"])
    df = pd.read_csv(path)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")

    exact = {
        (r.district.lower(), r.region.lower()): r.district_code
        for r in static.itertuples()
    }
    loose = {}
    for r in static.itertuples():
        loose.setdefault((_key(r.district), r.region.lower()), []).append(
            r.district_code
        )
    alias = {k.lower(): v for k, v in C.CURATED_DISTRICT_NAMES.items()}
    name_to_code = static.set_index("district")["district_code"].to_dict()

    codes = []
    for r in df.itertuples():
        d, reg = str(r.district).lower(), str(r.region).lower()
        code = exact.get((d, reg))
        if code is None and len(loose.get((_key(d), reg), [])) == 1:
            code = loose[(_key(d), reg)][0]
        if code is None and d in alias:
            code = name_to_code.get(alias[d][0])
        codes.append(code)
    df["district_code"] = codes
    unmatched = df[df["district_code"].isna()]
    if len(unmatched):
        unmatched.to_csv(path.with_name("nadmo_unmatched.csv"), index=False)
        logger.warning(
            f"{len(unmatched)} of {len(df)} NADMO rows match no GAUL district; "
            "see nadmo_unmatched.csv"
        )
    return df.dropna(subset=["district_code"])

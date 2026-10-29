# Request for NADMO flood incident records

A template letter to send to NADMO. It is addressed to the Director-General,
with a copy to the Director of Research, Information and Technology.
NADMO does not publish its incident database, so it must be requested.
Once the records are received, save them as
`data/v2/raw/nadmo_incidents.csv` in the format below and re-run
`build_dataset` and `experiments`. The records feed the flood labels,
and their `affected` counts make experiment E8 (impact layers) runnable.

---

**Subject: Request for district-level flood incident records, 2015–2025, for flood early-warning research**

Dear Director-General,

We are the research team behind NFCC/CivicFlood AI, a flood early-warning platform for Ghanaian districts. We are writing to request NADMO's district-level flood incident records for 2015–2025, for a peer-reviewed study of flood prediction in Ghana.

Our current evaluation uses open satellite and news-derived flood records. These miss many floods that NADMO responds to, especially short urban floods and floods in districts with little media coverage. NADMO's records would let us measure how well flood warnings perform against what actually happened on the ground. This is the evidence NADMO and district assemblies need before relying on any warning system.

**What we are asking for:** one row per flood incident, with as many of these fields as are recorded:

| Field | Description |
| --- | --- |
| date | Date the flooding was reported (YYYY-MM-DD) |
| district | District (MMDA) name |
| region | Region name |
| deaths | Number of deaths |
| affected | Number of people affected |
| houses_damaged | Houses damaged or destroyed |

Community names, incident type (flash, riverine, coastal, dam spillage) and coordinates would also help, if they are available.

**How we will handle the data:**
- We will use it only for this research.
- We will not publish individual records, and no personal information is needed.
- Published results will report aggregate statistics only, and will acknowledge NADMO as the data source.
- We will share the analysis and results with NADMO before publication.

We would welcome a meeting to discuss the request and how the results could support NADMO's early-warning work.

Yours faithfully,

[Name, title, institution, contact]

---

## File format expected by `nadmo.py`

```
date,district,region,deaths,affected,houses_damaged
2022-06-14,Accra Metropolitan,Greater Accra,2,1500,40
```

Districts are matched to the GAUL 2015 district list in three steps:
1. Exact name.
2. The name without its "Municipal", "Metropolitan" or "District" suffix.
3. The aliases in `config.CURATED_DISTRICT_NAMES`.

Districts created after 2015 do not appear in GAUL 2015. Rows for them are written to `nadmo_unmatched.csv` so a person can map each one to its parent district by hand. They are never guessed.

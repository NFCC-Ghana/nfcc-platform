"""Aggregate record of how the deployed platform has actually operated -
review queue, alerts sent, subscribers, citizen reports, prediction
ledger, observation archive and scheduled-job history - for the system
report (research/flood_experiments/reference.py).

Counts only: no phone numbers, names, messages or report text are kept.

    NFCC_API_KEY=... python scripts/operations_snapshot.py [out.json]
"""

import collections
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import requests

API = os.getenv("NFCC_API_URL", "https://nfcc-platform-355353600602.europe-west1.run.app")
HEADERS = {"X-API-Key": os.getenv("NFCC_API_KEY", "")}
DISTRICTS = [
    "Accra Central", "Accra West", "Accra East", "Tema", "Kumasi",
    "Tamale", "Cape Coast", "Ho", "Sunyani",
]
WORKFLOWS = [
    "automated_risk_assessment.yml", "verify_predictions.yml", "daily_chirps.yml",
    "model_validation.yml", "weekly_shadow_forecast.yml", "elite-resilience.yml", "ci.yml",
]


def get(path, **params):
    r = requests.get(API + path, headers=HEADERS, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def span(values):
    values = sorted(v for v in values if v)
    return {"first": values[0], "last": values[-1]} if values else None


def counts(rows, key):
    return dict(collections.Counter(str(r.get(key)) for r in rows).most_common())


def main(out):
    snap = {"taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "api": API}

    queue = get("/v1/alerts/pending", status="all")["alerts"]
    snap["review_queue"] = {
        "total": len(queue),
        "created": span(a["created_at"] for a in queue),
        "by_status": counts(queue, "status"),
        "by_basis": counts(queue, "basis"),
        "by_tier": counts(queue, "risk_tier"),
        "by_cap_status": counts(queue, "cap_status"),
        "by_district": counts(queue, "location"),
        "reviewed_by_a_person": sum(
            1 for a in queue
            if a.get("reviewed_by") and "test" not in a["reviewed_by"] and a.get("cap_status") != "Exercise"
        ),
        "last_created_by_basis": {
            b: max(a["created_at"] for a in queue if a.get("basis") == b)
            for b in {a.get("basis") for a in queue}
        },
    }

    hist = get("/v1/alerts/history", limit=10000)["data"]
    snap["alerts_sent"] = {
        "records": len(hist),
        "delivered": sum(1 for a in hist if a.get("alert_sent")),
        "by_provider": counts(hist, "provider"),
    }
    snap["subscribers"] = get("/v1/alert-subscriptions")["count"]

    reports = get("/v1/community-reports", limit=10000)["reports"]
    snap["community_reports"] = {
        "total": len(reports),
        "validated": sum(1 for r in reports if r["validated"]),
        "created": span(r["created_at"] for r in reports),
    }

    ledger = get("/v1/predictions", limit=1000000)["predictions"]
    snap["prediction_ledger"] = {
        "total": len(ledger),
        "predicted": span(p["predicted_at"] for p in ledger),
        "by_risk_tier": counts(ledger, "risk_tier"),
        "by_fused_tier": counts(ledger, "fused_risk_tier"),
        "by_outcome": counts(ledger, "outcome"),
        "by_outcome_source": counts(ledger, "outcome_source"),
    }

    archive = {}
    for d in DISTRICTS:
        rows = get(f"/v1/districts/{d}/observations", limit=5000).get("observations", [])
        for r in rows:
            a = archive.setdefault(r["source"], {"rows": 0, "with_value": 0, "last_with_value": None})
            a["rows"] += 1
            if r.get("value") is not None:
                a["with_value"] += 1
                a["last_with_value"] = max(a["last_with_value"] or "", r["recorded_at"])
    snap["observation_archive"] = archive

    risk = [r for d in DISTRICTS for r in get(f"/v1/districts/{d}/risk/history", limit=1000).get("history", [])]
    snap["risk_history"] = {"rows": len(risk), "recorded": span(r.get("recorded_at") for r in risk)}

    runs = {}
    for wf in WORKFLOWS:
        res = subprocess.run(
            ["gh", "run", "list", "--workflow", wf, "--limit", "1000", "--json", "conclusion,createdAt,event"],
            capture_output=True, text=True, check=True,
        )
        rows = json.loads(res.stdout)
        runs[wf] = {
            "runs": len(rows),
            "by_conclusion": counts(rows, "conclusion"),
            "scheduled": sum(1 for r in rows if r["event"] == "schedule"),
            "created": span(r["createdAt"] for r in rows),
        }
    snap["workflow_runs"] = runs

    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    print(json.dumps(snap, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "research/flood_experiments/results/operations/snapshot.json")

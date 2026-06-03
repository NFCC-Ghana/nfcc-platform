#!/usr/bin/env python3
"""Replay historical rows through forecast fusion and report accuracy metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.models.forecast_fusion import ForecastFusionInput, fuse_forecasts


def _row_to_input(row: pd.Series) -> ForecastFusionInput:
    def g(col: str) -> Optional[float]:
        if col not in row.index:
            return None
        v = row[col]
        if pd.isna(v):
            return None
        return float(v)

    return ForecastFusionInput(
        chirps_risk=g("chirps_risk"),
        glofas_risk=g("glofas_risk"),
        flood_hub_risk=g("flood_hub_risk"),
    )


def validate(
    path: Path,
    target_col: str = "realized_risk",
) -> Dict[str, Any]:
    df = pd.read_csv(path)
    if target_col not in df.columns:
        raise SystemExit(f"Missing target column {target_col!r} in {path}")

    preds: List[float] = []
    for _, row in df.iterrows():
        preds.append(fuse_forecasts(_row_to_input(row)).unified_risk)
    y = df[target_col].astype(float).values
    p = np.array(preds, dtype=float)
    err = p - y
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    bias = float(np.mean(err))
    return {
        "rows": int(len(df)),
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "target_col": target_col,
        "source_csv": str(path.resolve()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate fused forecast vs realized risk column.")
    ap.add_argument("csv", type=Path, help="CSV with chirps_risk,glofas_risk,flood_hub_risk (optional) and target")
    ap.add_argument("--target", default="realized_risk", help="Column name for observed 0–100 risk")
    ap.add_argument("--out", type=Path, default=None, help="Optional JSON path to write metrics")
    args = ap.parse_args()

    metrics = validate(args.csv, target_col=args.target)
    line = json.dumps(metrics, indent=2)
    print(line)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(line + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

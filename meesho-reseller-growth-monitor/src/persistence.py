import json
import os

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")


def _ensure_parent(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def save_alerts(alerts, path):
    _ensure_parent(path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return path


def load_alerts(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_report(report, path):
    _ensure_parent(path)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
        if not report.endswith("\n"):
            f.write("\n")

    return path


def build_regional_summary(region_df, region_mom_df):
    """One row per region: totals from SQL plus each month's SQL change.

    Values are copied from the SQL results; this only reshapes them.
    """
    summary = region_df.copy()

    for month in ("May", "June"):
        month_df = region_mom_df[region_mom_df["month"] == month]
        month_df = month_df[["region", "change_pct", "change_amount"]].rename(
            columns={
                "change_pct": f"{month.lower()}_change_pct",
                "change_amount": f"{month.lower()}_change_amount",
            }
        )
        summary = summary.merge(month_df, on="region", how="left")

    return summary


def save_regional_summary(region_df, region_mom_df, path):
    _ensure_parent(path)
    summary = build_regional_summary(region_df, region_mom_df)
    summary.to_csv(path, index=False, lineterminator="\n")
    return path

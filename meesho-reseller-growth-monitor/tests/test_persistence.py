import json
import os

import pandas as pd

from persistence import (
    build_regional_summary,
    load_alerts,
    save_alerts,
    save_regional_summary,
    save_report,
)


def test_alerts_roundtrip_exactly(alerts, tmp_path):
    path = save_alerts(alerts, str(tmp_path / "alerts.json"))
    assert load_alerts(path) == alerts


def test_alerts_json_keeps_values_unchanged(alerts, tmp_path):
    path = save_alerts(alerts, str(tmp_path / "alerts.json"))

    with open(path, encoding="utf-8") as f:
        saved = json.load(f)

    first = saved[0]
    assert first["data"]["change_pct"] == 42.23
    assert first["data"]["change_amount"] == 92270.0
    assert first["data"]["previous_gmv"] == 218497.0


def test_save_alerts_creates_missing_folders(alerts, tmp_path):
    path = save_alerts(alerts, str(tmp_path / "a" / "b" / "alerts.json"))
    assert os.path.exists(path)


def test_save_report_writes_text(tmp_path):
    path = save_report("hello", str(tmp_path / "report.txt"))
    with open(path, encoding="utf-8") as f:
        assert f.read() == "hello\n"


def test_regional_summary_has_one_row_per_region(region_metrics, region_mom):
    summary = build_regional_summary(region_metrics, region_mom)
    assert len(summary) == 4
    assert list(summary.columns) == [
        "region", "reseller_count", "delivered_orders", "gmv",
        "may_change_pct", "may_change_amount",
        "june_change_pct", "june_change_amount"]


def test_regional_summary_values_come_straight_from_sql(
        region_metrics, region_mom, tmp_path):
    path = save_regional_summary(
        region_metrics, region_mom, str(tmp_path / "regional_summary.csv"))
    saved = pd.read_csv(path).set_index("region")

    assert saved.loc["South", "gmv"] == 743211.0
    assert saved.loc["South", "may_change_pct"] == -21.07
    assert saved.loc["West", "june_change_amount"] == -31455.0

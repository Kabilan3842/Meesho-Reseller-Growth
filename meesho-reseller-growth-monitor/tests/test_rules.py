import pandas as pd
import pytest

import rules
from rules import (
    SEVERITY_HIGH,
    SEVERITY_NORMAL,
    check_category_change,
    check_region_change,
    classify_change,
    create_alerts,
    find_category_alerts,
    find_inactive_resellers,
    find_region_alerts,
    previous_month,
)

ALERT_KEYS = {"alert_type", "severity", "period", "entity_type", "entity", "data"}


def _row(pct, amount, **extra):
    row = {"change_pct": pct, "change_amount": amount,
           "current_gmv": 1.0, "previous_gmv": 1.0, "month": "May"}
    row.update(extra)
    return pd.Series(row)


def _change_df(pct, amount, key="category", name="Test Cat", month="May"):
    return pd.DataFrame([{
        key: name, "month": month, "current_gmv": 200000.0,
        "previous_gmv": 100000.0, "change_pct": pct, "change_amount": amount,
    }])


# ---- required minimum tests -----------------------------------------------

def test_7_category_alerts_are_generated(category_mom):
    assert len(find_category_alerts(category_mom)) == 7


def test_1_inactive_reseller_alert_is_generated(reseller_activity):
    assert len(find_inactive_resellers(reseller_activity)) == 1


def test_r024_is_the_inactive_reseller(reseller_activity):
    alert = find_inactive_resellers(reseller_activity)[0]
    assert alert["entity"] == "R024"
    assert alert["alert_type"] == "RESELLER_INACTIVE"
    assert alert["data"]["city"] == "Ahmedabad"
    assert alert["data"]["region"] == "West"
    assert alert["data"]["delivered_orders"] == 0
    assert alert["data"]["gmv"] == 0.0


# ---- category alerts match the README ---------------------------------------

def test_category_alerts_match_readme_table(category_mom):
    got = [
        (a["period"], a["entity"], a["alert_type"],
         a["data"]["change_pct"], a["data"]["change_amount"])
        for a in find_category_alerts(category_mom)
    ]
    assert got == [
        ("May", "Ethnic Wear", "CATEGORY_GROWTH", 42.23, 92270.0),
        ("May", "Home & Kitchen", "CATEGORY_DECLINE", -18.84, -36275.0),
        ("June", "Beauty & Personal Care", "CATEGORY_GROWTH", 42.65, 46509.0),
        ("June", "Ethnic Wear", "CATEGORY_DECLINE", -46.68, -145052.0),
        ("June", "Home & Kitchen", "CATEGORY_GROWTH", 96.31, 150471.0),
        ("June", "Kids Wear", "CATEGORY_GROWTH", 33.47, 39323.0),
        ("June", "Western Wear", "CATEGORY_DECLINE", -15.04, -32489.0),
    ]


def test_category_alert_values_are_copied_not_recalculated(category_mom):
    alert = find_category_alerts(category_mom)[0]
    assert alert["data"] == {
        "current_gmv": 310767.0, "previous_gmv": 218497.0,
        "change_pct": 42.23, "change_amount": 92270.0,
        "previous_period": "April",
    }


# ---- thresholds ------------------------------------------------------------

def test_thresholds_are_the_documented_values():
    assert rules.PERCENT_THRESHOLD == 15.0
    assert rules.GMV_THRESHOLD == 30000.0


@pytest.mark.parametrize("pct, amount, expected", [
    (15.0, 30000.0, True),      # exactly on both thresholds
    (-15.0, -30000.0, True),    # same, declining
    (14.99, 50000.0, False),    # % too small
    (40.0, 29999.0, False),     # amount too small
    (0.0, 0.0, False),
])
def test_category_rule_needs_both_conditions(pct, amount, expected):
    assert check_category_change(_row(pct, amount)) is expected


def test_nan_change_is_never_an_alert():
    assert check_category_change(_row(float("nan"), 0.0)) is False
    assert check_region_change(_row(float("nan"), 0.0)) is False


def test_growth_and_decline_classification():
    assert classify_change(_row(20.0, 40000.0)) == "CATEGORY_GROWTH"
    assert classify_change(_row(-20.0, -40000.0)) == "CATEGORY_DECLINE"
    assert classify_change(_row(5.0, 1000.0)) is None


# ---- regional alerts ---------------------------------------------------------

def test_5_region_alerts_are_generated(region_mom):
    assert len(find_region_alerts(region_mom)) == 5


def test_region_alerts_values(region_mom):
    got = [
        (a["period"], a["entity"], a["alert_type"], a["severity"],
         a["data"]["change_pct"], a["data"]["change_amount"])
        for a in find_region_alerts(region_mom)
    ]
    assert got == [
        ("May", "East", "REGION_GROWTH", SEVERITY_NORMAL, 24.72, 49900.0),
        ("May", "North", "REGION_GROWTH", SEVERITY_HIGH, 41.19, 69928.0),
        ("May", "South", "REGION_DECLINE", SEVERITY_NORMAL, -21.07, -57702.0),
        ("June", "South", "REGION_GROWTH", SEVERITY_NORMAL, 17.11, 36990.0),
        ("June", "West", "REGION_DECLINE", SEVERITY_NORMAL, -15.58, -31455.0),
    ]


def test_east_june_just_misses_the_threshold(region_mom):
    east_june = region_mom[
        (region_mom["region"] == "East") & (region_mom["month"] == "June")
    ].iloc[0]
    assert east_june["change_pct"] == 14.92  # < 15%, so no alert
    assert not check_region_change(east_june)


# ---- severity ----------------------------------------------------------------

def test_severity_thresholds_are_double_the_alert_thresholds():
    assert rules.SEVERITY_HIGH_PERCENT == 30.0
    assert rules.SEVERITY_HIGH_GMV == 60000.0


@pytest.mark.parametrize("pct, amount, expected", [
    (30.0, 60000.0, SEVERITY_HIGH),
    (-30.0, -60000.0, SEVERITY_HIGH),
    (29.99, 90000.0, SEVERITY_NORMAL),   # % below high bar
    (80.0, 59999.0, SEVERITY_NORMAL),    # amount below high bar
    (16.0, 31000.0, SEVERITY_NORMAL),
])
def test_severity_rule(pct, amount, expected):
    alerts = find_category_alerts(_change_df(pct, amount))
    assert alerts[0]["severity"] == expected


def test_inactive_reseller_severity_is_normal(reseller_activity):
    assert find_inactive_resellers(reseller_activity)[0]["severity"] == SEVERITY_NORMAL


# ---- structure and combination -------------------------------------------------

def test_all_13_alerts_are_created(alerts):
    assert len(alerts) == 13
    types = [a["alert_type"] for a in alerts]
    assert sum(t.startswith("CATEGORY_") for t in types) == 7
    assert sum(t.startswith("REGION_") for t in types) == 5
    assert types.count("RESELLER_INACTIVE") == 1


def test_every_alert_has_the_same_structure(alerts):
    for alert in alerts:
        assert set(alert) == ALERT_KEYS
        assert alert["severity"] in {SEVERITY_HIGH, SEVERITY_NORMAL}
        assert alert["entity_type"] in {"category", "region", "reseller"}
        assert isinstance(alert["data"], dict)


def test_create_alerts_orders_sources_category_inactive_region(alerts):
    kinds = [a["entity_type"] for a in alerts]
    assert kinds == ["category"] * 7 + ["reseller"] + ["region"] * 5


def test_create_alerts_with_no_significant_changes_is_empty():
    empty_changes = _change_df(1.0, 100.0)
    no_inactive = pd.DataFrame([{
        "reseller_id": "R001", "reseller_name": "Reseller 1", "region": "North",
        "city": "Delhi", "delivered_orders": 5, "gmv": 1000.0}])
    region_df = _change_df(1.0, 100.0, key="region", name="North")
    assert create_alerts(empty_changes, no_inactive, region_df) == []


def test_previous_month_helper():
    assert previous_month("May") == "April"
    assert previous_month("June") == "May"
    with pytest.raises(ValueError):
        previous_month("April")

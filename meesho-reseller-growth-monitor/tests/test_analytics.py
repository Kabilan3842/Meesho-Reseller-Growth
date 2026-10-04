import pandas as pd
import pytest

from analytics import get_region_mom

MONTHS = ["April", "May", "June"]


def _expected_mom(orders_df, resellers_df, group_col):
    """Independent pandas recomputation used only to cross-check SQL."""
    delivered = orders_df[orders_df["status"] == "Delivered"].copy()
    delivered["gmv"] = delivered["quantity"] * delivered["unit_price"]

    if group_col == "region":
        delivered = delivered.merge(
            resellers_df[["reseller_id", "region"]], on="reseller_id")

    pivot = delivered.pivot_table(
        index=group_col, columns="month", values="gmv", aggfunc="sum")
    return pivot[MONTHS]


# ---- delivered orders / totals -------------------------------------------

def test_644_delivered_orders_in_category_metrics(category_metrics):
    assert category_metrics["order_count"].sum() == 644


def test_644_delivered_orders_in_reseller_activity(reseller_activity):
    assert reseller_activity["delivered_orders"].sum() == 644


def test_644_delivered_orders_in_region_metrics(region_metrics):
    assert region_metrics["delivered_orders"].sum() == 644


def test_total_gmv_agrees_across_queries(
        category_metrics, reseller_activity, region_metrics):
    totals = {
        category_metrics["gmv"].sum(),
        reseller_activity["gmv"].sum(),
        region_metrics["gmv"].sum(),
    }
    assert len(totals) == 1


def test_only_delivered_orders_count(db, category_metrics):
    expected = db.execute(
        "SELECT SUM(quantity*unit_price) FROM orders WHERE status='Delivered'"
    ).fetchone()[0]
    assert category_metrics["gmv"].sum() == expected


# ---- category metrics ------------------------------------------------------

def test_category_metrics_columns(category_metrics):
    assert list(category_metrics.columns) == [
        "month", "category", "order_count", "units_sold", "gmv"]


def test_category_metrics_has_every_month_and_category(category_metrics):
    assert len(category_metrics) == 15
    assert set(category_metrics["month"]) == set(MONTHS)
    assert category_metrics["category"].nunique() == 5


# ---- reseller activity ------------------------------------------------------

def test_reseller_activity_keeps_all_24_resellers(reseller_activity):
    assert len(reseller_activity) == 24


def test_r024_has_zero_delivered_orders(reseller_activity):
    r024 = reseller_activity[reseller_activity["reseller_id"] == "R024"].iloc[0]
    assert r024["delivered_orders"] == 0
    assert r024["gmv"] == 0
    assert r024["city"] == "Ahmedabad"
    assert r024["region"] == "West"


def test_only_r024_has_zero_delivered_orders(reseller_activity):
    zero = reseller_activity[reseller_activity["delivered_orders"] == 0]
    assert list(zero["reseller_id"]) == ["R024"]


# ---- region metrics ---------------------------------------------------------

def test_regional_gmv_matches_readme(region_metrics):
    gmv = dict(zip(region_metrics["region"], region_metrics["gmv"]))
    assert gmv == {
        "South": 743211.0, "East": 742880.0,
        "North": 664797.0, "West": 560339.0,
    }


def test_each_region_has_six_resellers(region_metrics):
    assert list(region_metrics["reseller_count"]) == [6, 6, 6, 6]


# ---- category month-over-month ----------------------------------------------

def test_category_mom_columns(category_mom):
    assert list(category_mom.columns) == [
        "category", "month", "current_gmv", "previous_gmv",
        "change_pct", "change_amount"]


def test_category_mom_has_ten_rows_and_no_april(category_mom):
    assert len(category_mom) == 10
    assert "April" not in set(category_mom["month"])


def test_category_mom_known_values(category_mom):
    row = category_mom[
        (category_mom["category"] == "Ethnic Wear")
        & (category_mom["month"] == "May")
    ].iloc[0]
    assert row["current_gmv"] == 310767.0
    assert row["previous_gmv"] == 218497.0
    assert row["change_pct"] == 42.23
    assert row["change_amount"] == 92270.0


def test_category_mom_matches_independent_calculation(
        category_mom, orders_df, resellers_df):
    gmv = _expected_mom(orders_df, resellers_df, "category")

    for _, row in category_mom.iterrows():
        previous_month = MONTHS[MONTHS.index(row["month"]) - 1]
        current = gmv.loc[row["category"], row["month"]]
        previous = gmv.loc[row["category"], previous_month]

        assert row["current_gmv"] == current
        assert row["previous_gmv"] == previous
        assert row["change_amount"] == current - previous
        assert row["change_pct"] == pytest.approx(
            (current - previous) * 100 / previous, abs=0.005)


# ---- region month-over-month ------------------------------------------------

def test_region_mom_columns(region_mom):
    assert list(region_mom.columns) == [
        "region", "month", "current_gmv", "previous_gmv",
        "change_pct", "change_amount"]


def test_region_mom_has_eight_rows_and_no_april(region_mom):
    assert len(region_mom) == 8
    assert set(region_mom["month"]) == {"May", "June"}
    assert set(region_mom["region"]) == {"North", "South", "East", "West"}


def test_region_mom_known_values(region_mom):
    row = region_mom[
        (region_mom["region"] == "North") & (region_mom["month"] == "May")
    ].iloc[0]
    assert row["current_gmv"] == 239687.0
    assert row["previous_gmv"] == 169759.0
    assert row["change_pct"] == 41.19
    assert row["change_amount"] == 69928.0


def test_region_mom_matches_independent_calculation(
        region_mom, orders_df, resellers_df):
    gmv = _expected_mom(orders_df, resellers_df, "region")

    for _, row in region_mom.iterrows():
        previous_month = MONTHS[MONTHS.index(row["month"]) - 1]
        current = gmv.loc[row["region"], row["month"]]
        previous = gmv.loc[row["region"], previous_month]

        assert row["current_gmv"] == current
        assert row["previous_gmv"] == previous
        assert row["change_amount"] == current - previous
        assert row["change_pct"] == pytest.approx(
            (current - previous) * 100 / previous, abs=0.005)


def test_region_mom_months_chain_to_regional_total(region_mom, region_metrics):
    for region in region_metrics["region"]:
        rows = region_mom[region_mom["region"] == region].set_index("month")
        april = rows.loc["May", "previous_gmv"]
        may = rows.loc["May", "current_gmv"]
        june = rows.loc["June", "current_gmv"]

        assert rows.loc["June", "previous_gmv"] == may
        total = region_metrics.set_index("region").loc[region, "gmv"]
        assert april + may + june == total


def test_get_region_mom_accepts_a_database_path(data_dir):
    import os
    df = get_region_mom(os.path.join(data_dir, "meesho_reseller.db"))
    assert isinstance(df, pd.DataFrame) and len(df) == 8

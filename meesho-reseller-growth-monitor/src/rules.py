import pandas as pd


# Alert thresholds: a change is significant only when BOTH are met.
PERCENT_THRESHOLD = 15.0
GMV_THRESHOLD = 30000.0

# Regional changes use the same thresholds as category changes.
REGION_PERCENT_THRESHOLD = PERCENT_THRESHOLD
REGION_GMV_THRESHOLD = GMV_THRESHOLD

# Severity: HIGH when BOTH are met (2x the alert thresholds).
SEVERITY_HIGH_PERCENT = 2 * PERCENT_THRESHOLD
SEVERITY_HIGH_GMV = 2 * GMV_THRESHOLD

SEVERITY_HIGH = "HIGH"
SEVERITY_NORMAL = "NORMAL"

MONTH_ORDER = ["April", "May", "June"]
MONITORING_PERIOD = "April-June"


def previous_month(month):
    index = MONTH_ORDER.index(month)
    if index == 0:
        raise ValueError(f"{month} has no previous month in the dataset")
    return MONTH_ORDER[index - 1]


def _is_significant(row, percent_threshold, gmv_threshold):
    change_pct = row["change_pct"]
    change_amount = row["change_amount"]

    if pd.isna(change_pct):
        return False

    return (
        abs(change_pct) >= percent_threshold
        and abs(change_amount) >= gmv_threshold
    )


def _severity_for_change(row):
    if (
        abs(row["change_pct"]) >= SEVERITY_HIGH_PERCENT
        and abs(row["change_amount"]) >= SEVERITY_HIGH_GMV
    ):
        return SEVERITY_HIGH

    return SEVERITY_NORMAL


def check_category_change(row):
    return _is_significant(row, PERCENT_THRESHOLD, GMV_THRESHOLD)


def classify_change(row):
    if not check_category_change(row):
        return None

    if row["change_pct"] > 0:
        return "CATEGORY_GROWTH"

    return "CATEGORY_DECLINE"


def check_region_change(row):
    return _is_significant(row, REGION_PERCENT_THRESHOLD, REGION_GMV_THRESHOLD)


def classify_region_change(row):
    if not check_region_change(row):
        return None

    if row["change_pct"] > 0:
        return "REGION_GROWTH"

    return "REGION_DECLINE"


def _change_data(row):
    month = str(row["month"])

    return {
        "current_gmv": float(row["current_gmv"]),
        "previous_gmv": float(row["previous_gmv"]),
        "change_pct": float(row["change_pct"]),
        "change_amount": float(row["change_amount"]),
        "previous_period": previous_month(month),
    }


def find_category_alerts(df):
    alerts = []

    for _, row in df.iterrows():

        if not check_category_change(row):
            continue

        alerts.append({
            "alert_type": classify_change(row),
            "severity": _severity_for_change(row),
            "period": str(row["month"]),
            "entity_type": "category",
            "entity": str(row["category"]),
            "data": _change_data(row),
        })

    return alerts


def find_region_alerts(df):
    alerts = []

    for _, row in df.iterrows():

        if not check_region_change(row):
            continue

        alerts.append({
            "alert_type": classify_region_change(row),
            "severity": _severity_for_change(row),
            "period": str(row["month"]),
            "entity_type": "region",
            "entity": str(row["region"]),
            "data": _change_data(row),
        })

    return alerts


def find_inactive_resellers(df):
    alerts = []

    for _, row in df.iterrows():
        if row["delivered_orders"] == 0:
            alerts.append({
                "alert_type": "RESELLER_INACTIVE",
                "severity": SEVERITY_NORMAL,
                "period": MONITORING_PERIOD,
                "entity_type": "reseller",
                "entity": str(row["reseller_id"]),
                "data": {
                    "reseller_name": str(row["reseller_name"]),
                    "region": str(row["region"]),
                    "city": str(row["city"]),
                    "delivered_orders": int(row["delivered_orders"]),
                    "gmv": float(row["gmv"]),
                },
            })

    return alerts


def create_alerts(category_mom_df, reseller_df, region_mom_df):
    """Combine every alert source into one list with a shared structure."""
    alerts = []
    alerts.extend(find_category_alerts(category_mom_df))
    alerts.extend(find_inactive_resellers(reseller_df))
    alerts.extend(find_region_alerts(region_mom_df))
    return alerts

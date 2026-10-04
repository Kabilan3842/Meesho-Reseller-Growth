import os
import sqlite3

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

EXPECTED_RESELLERS = 24
EXPECTED_ORDERS = 900
EXPECTED_ORDERS_PER_MONTH = {"April": 300, "May": 300, "June": 300}
EXPECTED_STATUS_COUNTS = {
    "Delivered": 644,
    "Returned": 118,
    "Cancelled": 93,
    "Pending": 45,
}
EXPECTED_ZERO_ORDER_RESELLERS = ["R024"]


class DataValidationError(Exception):
    """Raised when one or more dataset checks fail."""


def validate_data(data_dir=DATA_DIR, verbose=True):
    """Run all dataset checks.

    Returns a dict of the measured values. Raises DataValidationError,
    listing every failed check, if anything is wrong.
    """
    def log(*args):
        if verbose:
            print(*args)

    resellers_file = os.path.join(data_dir, "resellers.csv")
    orders_file = os.path.join(data_dir, "orders.csv")
    db_file = os.path.join(data_dir, "meesho_reseller.db")

    for path in (resellers_file, orders_file, db_file):
        if not os.path.exists(path):
            raise DataValidationError(f"Missing data file: {path}")

    resellers = pd.read_csv(resellers_file)
    orders = pd.read_csv(orders_file)

    failures = []

    def check(name, actual, expected):
        status = "OK" if actual == expected else "FAIL"
        log(f"  [{status}] {name}: {actual}")
        if actual != expected:
            failures.append(f"{name}: expected {expected}, got {actual}")

    results = {}

    log("Row counts")
    results["resellers"] = len(resellers)
    results["orders"] = len(orders)
    check("Resellers", len(resellers), EXPECTED_RESELLERS)
    check("Orders", len(orders), EXPECTED_ORDERS)

    log("Missing values")
    results["missing_values"] = int(
        resellers.isnull().sum().sum() + orders.isnull().sum().sum()
    )
    check("Missing values", results["missing_values"], 0)

    log("Duplicate IDs")
    results["duplicate_reseller_ids"] = int(
        resellers["reseller_id"].duplicated().sum()
    )
    results["duplicate_order_ids"] = int(orders["order_id"].duplicated().sum())
    check("Duplicate reseller IDs", results["duplicate_reseller_ids"], 0)
    check("Duplicate order IDs", results["duplicate_order_ids"], 0)

    log("Orders per month")
    monthly = orders["month"].value_counts().to_dict()
    results["orders_per_month"] = {k: int(v) for k, v in monthly.items()}
    check("Orders per month", results["orders_per_month"],
          EXPECTED_ORDERS_PER_MONTH)

    log("Order statuses")
    statuses = orders["status"].value_counts().to_dict()
    results["status_counts"] = {k: int(v) for k, v in statuses.items()}
    check("Status counts", results["status_counts"], EXPECTED_STATUS_COUNTS)

    log("Reseller references")
    invalid_refs = set(orders["reseller_id"]) - set(resellers["reseller_id"])
    results["invalid_reseller_references"] = len(invalid_refs)
    check("Orders with invalid reseller IDs", len(invalid_refs), 0)

    log("Zero-order resellers")
    with_orders = set(orders["reseller_id"])
    zero_order = sorted(set(resellers["reseller_id"]) - with_orders)
    results["zero_order_resellers"] = zero_order
    check("Resellers with no orders", zero_order,
          EXPECTED_ZERO_ORDER_RESELLERS)

    log("Database")
    conn = sqlite3.connect(db_file)
    try:
        db_resellers = conn.execute(
            "SELECT COUNT(*) FROM resellers"
        ).fetchone()[0]
        db_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()

    results["db_resellers"] = db_resellers
    results["db_orders"] = db_orders
    results["db_foreign_key_violations"] = len(fk_violations)
    check("DB resellers match CSV", db_resellers, len(resellers))
    check("DB orders match CSV", db_orders, len(orders))
    check("DB foreign key violations", len(fk_violations), 0)

    if failures:
        raise DataValidationError(
            "Dataset validation failed:\n  - " + "\n  - ".join(failures)
        )

    log("All dataset checks passed.")
    return results


if __name__ == "__main__":
    validate_data()

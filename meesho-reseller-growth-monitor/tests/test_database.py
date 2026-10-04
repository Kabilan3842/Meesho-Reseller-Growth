import sqlite3

import pandas as pd


def test_db_counts_match_csv(db, resellers_df, orders_df):
    assert db.execute("SELECT COUNT(*) FROM resellers").fetchone()[0] == len(resellers_df)
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == len(orders_df)


def test_db_rows_match_csv(db, orders_df):
    db_orders = pd.read_sql_query("SELECT * FROM orders ORDER BY order_id", db)
    csv_orders = orders_df.sort_values("order_id").reset_index(drop=True)

    assert list(db_orders["order_id"]) == list(csv_orders["order_id"])
    assert list(db_orders["status"]) == list(csv_orders["status"])
    assert list(db_orders["unit_price"]) == list(csv_orders["unit_price"])


def test_foreign_keys_are_valid(db):
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_orders_table_declares_foreign_key_to_resellers(db):
    keys = db.execute("PRAGMA foreign_key_list(orders)").fetchall()
    assert [(k[2], k[3], k[4]) for k in keys] == [
        ("resellers", "reseller_id", "reseller_id")
    ]


def test_tables_and_primary_keys(db):
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"resellers", "orders"} <= tables

    def pk(table):
        return [c[1] for c in db.execute(f"PRAGMA table_info({table})") if c[5]]

    assert pk("resellers") == ["reseller_id"]
    assert pk("orders") == ["order_id"]


def test_300_orders_per_month_in_db(db):
    rows = dict(db.execute("SELECT month, COUNT(*) FROM orders GROUP BY month"))
    assert rows == {"April": 300, "May": 300, "June": 300}


def test_r024_exists_in_db_without_orders(db):
    assert db.execute(
        "SELECT COUNT(*) FROM resellers WHERE reseller_id='R024'"
    ).fetchone()[0] == 1
    assert db.execute(
        "SELECT COUNT(*) FROM orders WHERE reseller_id='R024'"
    ).fetchone()[0] == 0

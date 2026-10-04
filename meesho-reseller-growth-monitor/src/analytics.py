import os
import sqlite3
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")

DB_FILE = os.path.join(DATA_DIR, "meesho_reseller.db")


def run_query(sql_file, db_file=DB_FILE):
    path = os.path.join(SQL_DIR, sql_file)

    with open(path, "r", encoding="utf-8") as f:
        query = f.read()

    conn = sqlite3.connect(db_file)

    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def get_category_metrics(db_file=DB_FILE):
    return run_query("01_category_metrics.sql", db_file)


def get_reseller_activity(db_file=DB_FILE):
    return run_query("02_reseller_activity.sql", db_file)


def get_region_metrics(db_file=DB_FILE):
    return run_query("03_region_metrics.sql", db_file)


def get_category_mom(db_file=DB_FILE):
    return run_query("04_category_mom.sql", db_file)


def get_region_mom(db_file=DB_FILE):
    return run_query("05_region_mom.sql", db_file)

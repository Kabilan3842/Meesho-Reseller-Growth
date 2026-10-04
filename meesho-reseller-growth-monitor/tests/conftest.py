import os
import shutil
import sqlite3

import pandas as pd
import pytest

from analytics import (
    DATA_DIR,
    DB_FILE,
    get_category_metrics,
    get_category_mom,
    get_region_metrics,
    get_region_mom,
    get_reseller_activity,
)
from rules import create_alerts


@pytest.fixture(scope="session")
def data_dir():
    return DATA_DIR


@pytest.fixture(scope="session")
def resellers_df():
    return pd.read_csv(os.path.join(DATA_DIR, "resellers.csv"))


@pytest.fixture(scope="session")
def orders_df():
    return pd.read_csv(os.path.join(DATA_DIR, "orders.csv"))


@pytest.fixture(scope="session")
def db():
    conn = sqlite3.connect(DB_FILE)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def category_metrics():
    return get_category_metrics()


@pytest.fixture(scope="session")
def category_mom():
    return get_category_mom()


@pytest.fixture(scope="session")
def reseller_activity():
    return get_reseller_activity()


@pytest.fixture(scope="session")
def region_metrics():
    return get_region_metrics()


@pytest.fixture(scope="session")
def region_mom():
    return get_region_mom()


@pytest.fixture(scope="session")
def alerts(category_mom, reseller_activity, region_mom):
    return create_alerts(category_mom, reseller_activity, region_mom)


@pytest.fixture
def copied_data_dir(tmp_path):
    """A scratch copy of data/ that tests may safely tamper with."""
    target = tmp_path / "data"
    shutil.copytree(DATA_DIR, target)
    return str(target)

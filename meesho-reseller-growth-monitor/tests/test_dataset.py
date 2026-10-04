import filecmp
import os

import pytest

from generate_dataset import generate_data
from validate_dataset import DataValidationError, validate_data


def test_24_resellers_exist(resellers_df):
    assert len(resellers_df) == 24


def test_900_orders_exist(orders_df):
    assert len(orders_df) == 900


@pytest.mark.parametrize("month", ["April", "May", "June"])
def test_300_orders_per_month(orders_df, month):
    assert (orders_df["month"] == month).sum() == 300


def test_644_delivered_orders(orders_df):
    assert (orders_df["status"] == "Delivered").sum() == 644


def test_status_distribution(orders_df):
    counts = orders_df["status"].value_counts().to_dict()
    assert counts == {
        "Delivered": 644, "Returned": 118, "Cancelled": 93, "Pending": 45,
    }


def test_six_resellers_per_region(resellers_df):
    assert resellers_df["region"].value_counts().to_dict() == {
        "North": 6, "South": 6, "East": 6, "West": 6,
    }


def test_no_missing_values(resellers_df, orders_df):
    assert resellers_df.isnull().sum().sum() == 0
    assert orders_df.isnull().sum().sum() == 0


def test_no_duplicate_ids(resellers_df, orders_df):
    assert not resellers_df["reseller_id"].duplicated().any()
    assert not orders_df["order_id"].duplicated().any()


def test_every_order_references_a_real_reseller(resellers_df, orders_df):
    assert set(orders_df["reseller_id"]) <= set(resellers_df["reseller_id"])


def test_r024_has_no_orders_at_all(resellers_df, orders_df):
    no_orders = set(resellers_df["reseller_id"]) - set(orders_df["reseller_id"])
    assert no_orders == {"R024"}


def test_intentional_ethnic_wear_spike(orders_df):
    share = (
        orders_df[orders_df["category"] == "Ethnic Wear"]
        .groupby("month").size() / 300
    )
    assert share["May"] > share["April"] > share["June"]


def test_validate_data_passes_on_committed_dataset(data_dir):
    results = validate_data(data_dir, verbose=False)
    assert results["resellers"] == 24
    assert results["orders"] == 900
    assert results["zero_order_resellers"] == ["R024"]


def test_validate_data_fails_loudly_on_tampered_data(copied_data_dir):
    path = os.path.join(copied_data_dir, "orders.csv")

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines[:-1])  # drop one order

    with pytest.raises(DataValidationError) as error:
        validate_data(copied_data_dir, verbose=False)

    assert "Orders" in str(error.value)


def test_validate_data_fails_when_files_are_missing(tmp_path):
    with pytest.raises(DataValidationError):
        validate_data(str(tmp_path), verbose=False)


def test_generation_is_deterministic(tmp_path, data_dir):
    generate_data(str(tmp_path), verbose=False)

    for name in ("resellers.csv", "orders.csv"):
        assert filecmp.cmp(
            os.path.join(str(tmp_path), name),
            os.path.join(data_dir, name),
            shallow=False,
        ), f"{name} differs from the committed dataset"

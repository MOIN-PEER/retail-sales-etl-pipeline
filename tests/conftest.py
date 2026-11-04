import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def products():
    return pd.DataFrame({
        "product_code": ["P0001", "P0002"],
        "product_name": ["Kettle", "Mug"],
        "category": ["Kitchen", "Kitchen"],
        "unit_price_gbp": ["20.00", "5.00"],
        "unit_cost_gbp": ["10.00", "2.00"],
    })


@pytest.fixture
def stores():
    return pd.DataFrame({
        "store_id": ["S001"], "store_name": ["Belfast City Centre"],
        "city": ["Belfast"], "region": ["Northern Ireland"],
    })


def _row(tid, **overrides):
    row = {
        "transaction_id": tid, "transaction_datetime": "2025-03-01 10:15:00", "store_id": "S001",
        "store_name": "Belfast City Centre", "product_code": "P0001", "quantity": "2",
        "unit_price_gbp": "20.00", "discount_pct": "0.10", "payment_method": "card",
        "channel": "in_store", "source_file": "sales_2025_03.csv",
    }
    row.update(overrides)
    return row


@pytest.fixture
def make_row():
    return _row

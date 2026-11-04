import pandas as pd
import pytest

from retail_etl.validate import DataQualityError, check_reject_threshold, validate_sales


def test_clean_row_passes(products, stores, make_row):
    result = validate_sales(pd.DataFrame([make_row("T1")]), products, stores)
    assert len(result.clean) == 1 and result.rejected.empty


def test_duplicates_removed_once(products, stores, make_row):
    sales = pd.DataFrame([make_row("T1"), make_row("T1"), make_row("T2")])
    result = validate_sales(sales, products, stores)
    assert result.duplicates_removed == 1
    assert len(result.clean) == 2


@pytest.mark.parametrize("override, reason", [
    ({"store_id": None}, "missing_store_id"),
    ({"store_id": "S999"}, "unknown_store_id"),
    ({"product_code": "P9999"}, "unknown_product_code"),
    ({"quantity": "-1"}, "invalid_quantity"),
    ({"quantity": "two"}, "invalid_quantity"),
    ({"transaction_datetime": "31/02/2025 10:00"}, "invalid_datetime"),
    ({"unit_price_gbp": "9999.99"}, "price_out_of_range"),
    ({"discount_pct": "1.5"}, "invalid_discount"),
])
def test_each_rule_rejects_with_reason(products, stores, make_row, override, reason):
    result = validate_sales(pd.DataFrame([make_row("T1", **override)]), products, stores)
    assert result.clean.empty
    assert reason in result.rejected.iloc[0]["rejection_reason"]


def test_multiple_reasons_recorded(products, stores, make_row):
    row = make_row("T1", quantity="0", product_code="P9999")
    reason = validate_sales(pd.DataFrame([row]), products, stores).rejected.iloc[0]["rejection_reason"]
    assert "invalid_quantity" in reason and "unknown_product_code" in reason


def test_reject_threshold_stops_bad_batch(products, stores, make_row):
    sales = pd.DataFrame([make_row("T1"), make_row("T2", quantity="x")])
    result = validate_sales(sales, products, stores)
    with pytest.raises(DataQualityError):
        check_reject_threshold(result, max_reject_rate=0.10)

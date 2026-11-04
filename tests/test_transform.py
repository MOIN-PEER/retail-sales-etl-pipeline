import pandas as pd

from retail_etl.transform import transform
from retail_etl.validate import validate_sales


def test_amounts_are_calculated_correctly(products, stores, make_row):
    clean = validate_sales(pd.DataFrame([make_row("T1")]), products, stores).clean
    fact = transform(clean, products, stores).fact_sales.iloc[0]
    assert fact["gross_amount_gbp"] == 40.00          # 2 x £20
    assert fact["discount_amount_gbp"] == 4.00        # 10%
    assert fact["net_amount_gbp"] == 36.00
    assert fact["cost_amount_gbp"] == 20.00           # 2 x £10 cost
    assert fact["gross_margin_gbp"] == 16.00
    assert fact["date_key"] == 20250301


def test_text_fields_are_standardised(products, stores, make_row):
    stores = stores.assign(store_name=["  Belfast City Centre  "])
    sales = pd.DataFrame([make_row("T1", payment_method="Card ", channel=" In_Store")])
    schema = transform(validate_sales(sales, products, stores).clean, products, stores)
    assert schema.dim_store.iloc[0]["store_name"] == "Belfast City Centre"
    assert schema.fact_sales.iloc[0]["payment_method"] == "card"
    assert schema.fact_sales.iloc[0]["channel"] == "in_store"


def test_date_dimension_covers_every_day(products, stores, make_row):
    sales = pd.DataFrame([make_row("T1", transaction_datetime="2025-03-01 10:00:00"),
                          make_row("T2", transaction_datetime="2025-03-10 10:00:00")])
    clean = validate_sales(sales, products, stores).clean
    assert len(transform(clean, products, stores).dim_date) == 10

"""Transform step: build a star schema (3 dimensions + 1 fact table)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger("retail_etl.transform")


@dataclass
class StarSchema:
    dim_date: pd.DataFrame
    dim_store: pd.DataFrame
    dim_product: pd.DataFrame
    fact_sales: pd.DataFrame


def build_dim_date(timestamps: pd.Series) -> pd.DataFrame:
    days = pd.date_range(timestamps.min().normalize(), timestamps.max().normalize(), freq="D")
    return pd.DataFrame({
        "date_key": days.strftime("%Y%m%d").astype(int),
        "full_date": days.date,
        "year": days.year,
        "quarter": days.quarter,
        "month": days.month,
        "month_name": days.strftime("%B"),
        "week_of_year": days.isocalendar().week.astype(int).to_numpy(),
        "day_of_week": days.strftime("%A"),
        "is_weekend": days.day_of_week >= 5,
    })


def build_dim_store(stores: pd.DataFrame) -> pd.DataFrame:
    dim = stores.copy()
    dim["store_name"] = dim["store_name"].str.strip()
    dim.insert(0, "store_key", range(1, len(dim) + 1))
    return dim[["store_key", "store_id", "store_name", "city", "region"]]


def build_dim_product(products: pd.DataFrame) -> pd.DataFrame:
    dim = products.copy()
    dim["unit_price_gbp"] = dim["unit_price_gbp"].astype(float)
    dim["unit_cost_gbp"] = dim["unit_cost_gbp"].astype(float)
    dim.insert(0, "product_key", range(1, len(dim) + 1))
    return dim[["product_key", "product_code", "product_name", "category", "unit_price_gbp", "unit_cost_gbp"]]


def build_fact_sales(clean: pd.DataFrame, dim_store: pd.DataFrame, dim_product: pd.DataFrame) -> pd.DataFrame:
    df = clean.merge(dim_store[["store_key", "store_id"]], on="store_id", how="left")
    df = df.merge(dim_product[["product_key", "product_code", "unit_cost_gbp"]], on="product_code", how="left")

    qty = df["quantity_num"].astype(int)
    gross = (qty * df["unit_price_num"]).round(2)
    discount = (gross * df["discount_num"]).round(2)
    net = (gross - discount).round(2)
    cost = (qty * df["unit_cost_gbp"]).round(2)

    fact = pd.DataFrame({
        "transaction_id": df["transaction_id"],
        "date_key": df["txn_ts"].dt.strftime("%Y%m%d").astype(int),
        "transaction_hour": df["txn_ts"].dt.hour,
        "store_key": df["store_key"].astype(int),
        "product_key": df["product_key"].astype(int),
        "quantity": qty,
        "unit_price_gbp": df["unit_price_num"].round(2),
        "discount_pct": df["discount_num"],
        "gross_amount_gbp": gross,
        "discount_amount_gbp": discount,
        "net_amount_gbp": net,
        "cost_amount_gbp": cost,
        "gross_margin_gbp": (net - cost).round(2),
        "payment_method": df["payment_method"].str.strip().str.lower(),
        "channel": df["channel"].str.strip().str.lower(),
        "source_file": df["source_file"],
    })
    return fact.sort_values(["date_key", "transaction_id"]).reset_index(drop=True)


def transform(clean: pd.DataFrame, products: pd.DataFrame, stores: pd.DataFrame) -> StarSchema:
    dim_store = build_dim_store(stores)
    dim_product = build_dim_product(products)
    dim_date = build_dim_date(clean["txn_ts"])
    fact = build_fact_sales(clean, dim_store, dim_product)
    logger.info(
        "Built star schema: %d dates, %d stores, %d products, %d fact rows",
        len(dim_date), len(dim_store), len(dim_product), len(fact),
    )
    return StarSchema(dim_date, dim_store, dim_product, fact)

"""Validation step: enforce data-quality rules and quarantine bad rows.

Every rejected row is kept (not silently dropped) together with the reason, so
the business can see exactly what went wrong and fix it at source.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger("retail_etl.validate")

PRICE_CEILING_GBP = 500.0


@dataclass
class ValidationResult:
    clean: pd.DataFrame
    rejected: pd.DataFrame
    duplicates_removed: int
    rule_counts: dict[str, int] = field(default_factory=dict)

    @property
    def input_rows(self) -> int:
        return len(self.clean) + len(self.rejected) + self.duplicates_removed

    @property
    def reject_rate(self) -> float:
        return len(self.rejected) / self.input_rows if self.input_rows else 0.0


def validate_sales(sales: pd.DataFrame, products: pd.DataFrame, stores: pd.DataFrame) -> ValidationResult:
    df = sales.copy()

    # 1. Exact duplicate transactions (double scans) are removed, keeping the first.
    before = len(df)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")
    duplicates_removed = before - len(df)

    # 2. Type conversion - failures become NaN/NaT and are caught by the rules below.
    df["quantity_num"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price_num"] = pd.to_numeric(df["unit_price_gbp"], errors="coerce")
    df["discount_num"] = pd.to_numeric(df["discount_pct"], errors="coerce").fillna(0.0)
    df["txn_ts"] = pd.to_datetime(df["transaction_datetime"], format="%Y-%m-%d %H:%M:%S", errors="coerce")

    known_products = set(products["product_code"])
    known_stores = set(stores["store_id"])

    rules: dict[str, pd.Series] = {
        "missing_store_id": df["store_id"].isna(),
        "unknown_store_id": df["store_id"].notna() & ~df["store_id"].isin(known_stores),
        "unknown_product_code": ~df["product_code"].isin(known_products),
        "invalid_quantity": df["quantity_num"].isna() | (df["quantity_num"] <= 0),
        "invalid_datetime": df["txn_ts"].isna(),
        "price_out_of_range": df["unit_price_num"].isna()
        | (df["unit_price_num"] <= 0)
        | (df["unit_price_num"] > PRICE_CEILING_GBP),
        "invalid_discount": (df["discount_num"] < 0) | (df["discount_num"] > 0.9),
    }

    reasons = pd.Series("", index=df.index)
    rule_counts = {}
    for name, mask in rules.items():
        rule_counts[name] = int(mask.sum())
        reasons = reasons.where(~mask, reasons + name + ";")

    bad = reasons != ""
    rejected = df.loc[bad, list(sales.columns)].copy()
    rejected["rejection_reason"] = reasons[bad].str.rstrip(";")
    clean = df.loc[~bad].copy()

    for name, count in rule_counts.items():
        if count:
            logger.info("Rule %-22s flagged %6d rows", name, count)
    logger.info(
        "Validation: %d clean, %d rejected, %d duplicates removed",
        len(clean), len(rejected), duplicates_removed,
    )
    return ValidationResult(clean, rejected, duplicates_removed, rule_counts)


class DataQualityError(RuntimeError):
    """Raised when too many rows fail validation - the batch is probably broken."""


def check_reject_threshold(result: ValidationResult, max_reject_rate: float) -> None:
    if result.reject_rate > max_reject_rate:
        raise DataQualityError(
            f"Reject rate {result.reject_rate:.1%} exceeds threshold {max_reject_rate:.0%}; "
            "load aborted so bad data never reaches the warehouse."
        )

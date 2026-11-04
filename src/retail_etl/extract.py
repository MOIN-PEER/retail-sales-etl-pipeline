"""Extract step: read raw CSV exports from the landing folder."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .utils import retry

logger = logging.getLogger("retail_etl.extract")

# Read everything as text first; types are enforced in the validation step,
# so a single bad value can never crash the load.
SALES_COLUMNS = [
    "transaction_id", "transaction_datetime", "store_id", "store_name", "product_code",
    "quantity", "unit_price_gbp", "discount_pct", "payment_method", "channel",
]


@dataclass
class RawData:
    sales: pd.DataFrame
    products: pd.DataFrame
    stores: pd.DataFrame
    files_read: list[str]


@retry(attempts=3, backoff_seconds=1.0, exceptions=(OSError,))
def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], **kwargs)


def extract(raw_dir: Path) -> RawData:
    sales_files = sorted(raw_dir.glob("sales_*.csv"))
    if not sales_files:
        raise FileNotFoundError(
            f"No sales_*.csv files found in {raw_dir}. Run `python -m retail_etl generate` first."
        )

    frames = []
    for path in sales_files:
        df = read_csv(path)
        missing = set(SALES_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
        df["source_file"] = path.name
        frames.append(df)
        logger.info("Read %-22s %7d rows", path.name, len(df))

    sales = pd.concat(frames, ignore_index=True)
    products = read_csv(raw_dir / "products.csv")
    stores = read_csv(raw_dir / "stores.csv")
    logger.info("Extracted %d sales rows from %d files", len(sales), len(sales_files))
    return RawData(sales, products, stores, [p.name for p in sales_files])

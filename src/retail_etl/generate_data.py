"""Generate a realistic *synthetic* raw dataset for a fictional UK retail chain.

The files imitate what a retailer's till system exports each month, including the
kind of data-quality problems real exports contain (duplicates, missing IDs,
bad dates, negative quantities, unknown products, messy text). The pipeline's job
is to catch and handle all of these.

All data is randomly generated - no real company or customer data is used.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("retail_etl.generate")

STORES = [
    ("S001", "Belfast City Centre", "Belfast", "Northern Ireland", 1.30),
    ("S002", "Lisburn Retail Park", "Lisburn", "Northern Ireland", 0.90),
    ("S003", "Newry Quays", "Newry", "Northern Ireland", 0.75),
    ("S004", "Glasgow Buchanan St", "Glasgow", "Scotland", 1.20),
    ("S005", "Edinburgh Princes St", "Edinburgh", "Scotland", 1.10),
    ("S006", "Manchester Arndale", "Manchester", "North West", 1.25),
    ("S007", "Liverpool One", "Liverpool", "North West", 1.00),
    ("S008", "Leeds Trinity", "Leeds", "Yorkshire", 0.95),
    ("S009", "Birmingham Bullring", "Birmingham", "West Midlands", 1.15),
    ("S010", "London Oxford St", "London", "London", 1.60),
    ("S011", "Bristol Cabot Circus", "Bristol", "South West", 0.85),
    ("S012", "Cardiff St Davids", "Cardiff", "Wales", 0.80),
]

CATEGORIES = {
    "Electronics": ["Wireless Earbuds", "Bluetooth Speaker", "Phone Charger", "Smart Watch", "USB-C Hub",
                    "Power Bank", "Laptop Stand", "HD Webcam", "Gaming Mouse", "Keyboard"],
    "Home": ["Scented Candle", "Throw Blanket", "Table Lamp", "Photo Frame", "Storage Box",
             "Wall Clock", "Cushion Cover", "Plant Pot", "Bath Towel", "Mirror"],
    "Kitchen": ["Coffee Mug", "Chef Knife", "Frying Pan", "Blender", "Kettle",
                "Toaster", "Mixing Bowl Set", "Cutting Board", "Water Bottle", "Lunch Box"],
    "Clothing": ["Cotton T-Shirt", "Denim Jeans", "Wool Jumper", "Rain Jacket", "Running Shoes",
                 "Baseball Cap", "Scarf", "Gloves", "Socks 5-Pack", "Hoodie"],
    "Beauty": ["Face Moisturiser", "Shampoo", "Hand Cream", "Lip Balm", "Body Wash",
               "Sun Cream", "Perfume", "Hair Dryer", "Makeup Brush Set", "Face Mask"],
    "Toys": ["Building Blocks", "Puzzle 1000pc", "Board Game", "Plush Bear", "Remote Car",
             "Art Set", "Card Game", "Kite", "Science Kit", "Doll House"],
}

PRICE_RANGE = {
    "Electronics": (12, 120), "Home": (6, 60), "Kitchen": (5, 80),
    "Clothing": (8, 70), "Beauty": (3, 45), "Toys": (6, 55),
}

# Seasonality index by month (Nov/Dec peak for Christmas, Jan sales dip).
MONTH_FACTOR = {1: 0.80, 2: 0.78, 3: 0.88, 4: 0.92, 5: 0.95, 6: 0.97,
                7: 1.00, 8: 1.02, 9: 0.94, 10: 1.00, 11: 1.30, 12: 1.55}


def build_products(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    pid = 1
    for category, names in CATEGORIES.items():
        low, high = PRICE_RANGE[category]
        for name in names:
            price = round(float(rng.uniform(low, high)), 2)
            rows.append({
                "product_code": f"P{pid:04d}",
                "product_name": name,
                "category": category,
                "unit_price_gbp": price,
                "unit_cost_gbp": round(price * float(rng.uniform(0.45, 0.70)), 2),
            })
            pid += 1
    return pd.DataFrame(rows)


def build_stores() -> pd.DataFrame:
    return pd.DataFrame(
        [{"store_id": s[0], "store_name": s[1], "city": s[2], "region": s[3], "size_factor": s[4]}
         for s in STORES]
    )


def build_month_sales(year: int, month: int, products: pd.DataFrame, stores: pd.DataFrame,
                      rng: np.random.Generator, start_id: int, base_rows: int) -> pd.DataFrame:
    n = int(base_rows * MONTH_FACTOR[month])
    days = pd.Period(f"{year}-{month:02d}").days_in_month
    store_weights = stores["size_factor"] / stores["size_factor"].sum()
    store_idx = rng.choice(len(stores), size=n, p=store_weights)
    prod_idx = rng.integers(0, len(products), size=n)
    day = rng.integers(1, days + 1, size=n)
    hour = rng.choice(np.arange(9, 21), size=n)
    minute = rng.integers(0, 60, size=n)
    qty = rng.choice([1, 1, 1, 1, 2, 2, 3, 4], size=n)
    discount = rng.choice([0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25], size=n)
    if month in (1, 7):  # seasonal sales
        discount = np.maximum(discount, rng.choice([0.0, 0.20, 0.30], size=n))

    df = pd.DataFrame({
        "transaction_id": [f"T{start_id + i:08d}" for i in range(n)],
        "transaction_datetime": [
            f"{year}-{month:02d}-{d:02d} {h:02d}:{m:02d}:00" for d, h, m in zip(day, hour, minute)
        ],
        "store_id": stores["store_id"].to_numpy()[store_idx],
        "store_name": stores["store_name"].to_numpy()[store_idx],
        "product_code": products["product_code"].to_numpy()[prod_idx],
        "quantity": qty,
        "unit_price_gbp": products["unit_price_gbp"].to_numpy()[prod_idx],
        "discount_pct": discount,
        "payment_method": rng.choice(["card", "card", "card", "contactless", "cash", "gift_card"], size=n),
        "channel": rng.choice(["in_store", "in_store", "in_store", "click_and_collect"], size=n),
    })
    return inject_quality_issues(df, rng)


def inject_quality_issues(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Deliberately corrupt a small share of rows, as real exports would be."""
    df = df.copy()
    df["quantity"] = df["quantity"].astype(object)
    df["unit_price_gbp"] = df["unit_price_gbp"].astype(object)
    n = len(df)

    def pick(rate: float) -> np.ndarray:
        return rng.choice(n, size=max(1, int(n * rate)), replace=False)

    df.loc[pick(0.006), "store_id"] = None                                   # missing store
    df.loc[pick(0.004), "product_code"] = "P9999"                            # unknown product
    df.loc[pick(0.005), "quantity"] = -1                                     # returns keyed wrongly
    df.loc[pick(0.003), "quantity"] = "two"                                  # free-text quantity
    df.loc[pick(0.003), "transaction_datetime"] = "31/02/2025 10:00"         # impossible date
    df.loc[pick(0.002), "unit_price_gbp"] = 9999.99                          # price outlier
    idx = pick(0.05)
    df.loc[idx, "store_name"] = df.loc[idx, "store_name"].str.upper() + "  "  # messy text
    duplicates = df.loc[pick(0.01)]                                          # double-scanned rows
    return pd.concat([df, duplicates], ignore_index=True).sample(frac=1, random_state=7)


def generate(raw_dir: Path, year: int = 2025, base_rows: int = 9000, seed: int = 42) -> list[Path]:
    """Write stores.csv, products.csv and one sales_YYYY_MM.csv per month to raw_dir."""
    rng = np.random.default_rng(seed)
    raw_dir.mkdir(parents=True, exist_ok=True)
    products = build_products(rng)
    stores = build_stores()

    written = []
    products.to_csv(raw_dir / "products.csv", index=False)
    stores.drop(columns="size_factor").to_csv(raw_dir / "stores.csv", index=False)
    written += [raw_dir / "products.csv", raw_dir / "stores.csv"]

    next_id = 1
    for month in range(1, 13):
        sales = build_month_sales(year, month, products, stores, rng, next_id, base_rows)
        next_id += len(sales)
        path = raw_dir / f"sales_{year}_{month:02d}.csv"
        sales.to_csv(path, index=False)
        written.append(path)
        logger.info("Generated %s (%d rows)", path.name, len(sales))
    return written

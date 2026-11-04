"""Load step: write the star schema into the warehouse inside one transaction."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from .config import PROJECT_ROOT
from .transform import StarSchema
from .utils import retry

logger = logging.getLogger("retail_etl.load")

SCHEMA_FILE = PROJECT_ROOT / "sql" / "schema.sql"


def get_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///"):
        Path(database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, future=True)


def _statements(sql: str) -> list[str]:
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


@retry(attempts=3, backoff_seconds=2.0, exceptions=(OSError, ConnectionError))
def load(schema: StarSchema, rejected: pd.DataFrame, engine: Engine, chunksize: int = 5000) -> int:
    """Rebuild all warehouse tables in a single transaction (all-or-nothing)."""
    with engine.begin() as conn:
        for statement in _statements(SCHEMA_FILE.read_text(encoding="utf-8")):
            conn.execute(text(statement))
        # Load order respects foreign keys: dimensions first, then facts.
        for name, frame in (
            ("dim_date", schema.dim_date),
            ("dim_store", schema.dim_store),
            ("dim_product", schema.dim_product),
            ("fact_sales", schema.fact_sales),
        ):
            frame.to_sql(name, conn, if_exists="append", index=False, chunksize=chunksize)
            logger.info("Loaded %-12s %7d rows", name, len(frame))
        rejected.to_sql("dq_rejected_sales", conn, if_exists="append", index=False, chunksize=chunksize)
        logger.info("Loaded %-12s %7d rows", "dq_rejected", len(rejected))
    return len(schema.fact_sales)


def write_run_log(engine: Engine, record: dict) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS etl_run_log (run_id VARCHAR(40) PRIMARY KEY, started_at VARCHAR(30) NOT NULL, "
            "finished_at VARCHAR(30), status VARCHAR(20) NOT NULL, files_processed INTEGER, rows_extracted INTEGER, "
            "duplicates_removed INTEGER, rows_rejected INTEGER, rows_loaded INTEGER, message VARCHAR(500))"
        ))
        conn.execute(text(
            "INSERT INTO etl_run_log VALUES (:run_id, :started_at, :finished_at, :status, :files_processed, "
            ":rows_extracted, :duplicates_removed, :rows_rejected, :rows_loaded, :message)"
        ), record)


def reconcile(engine: Engine, expected_rows: int, expected_net: float) -> None:
    """Post-load check: what is in the database must match what we transformed."""
    with engine.connect() as conn:
        rows, net = conn.execute(text("SELECT COUNT(*), SUM(net_amount_gbp) FROM fact_sales")).one()
    if rows != expected_rows or abs(float(net) - expected_net) > 0.05:
        raise RuntimeError(
            f"Reconciliation failed: db has {rows} rows / £{float(net):,.2f}, "
            f"expected {expected_rows} rows / £{expected_net:,.2f}"
        )
    logger.info("Reconciliation passed: %d rows, £%s net revenue", rows, f"{float(net):,.2f}")

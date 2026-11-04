"""Orchestrates one full pipeline run: extract -> validate -> transform -> load -> report."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from .analytics import dq_chart, make_charts, run_queries, write_reports
from .config import Settings
from .extract import extract
from .load import get_engine, load, reconcile, write_run_log
from .transform import transform
from .utils import timed
from .validate import check_reject_threshold, validate_sales

logger = logging.getLogger("retail_etl.pipeline")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_pipeline(settings: Settings) -> dict:
    settings.ensure_dirs()
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    started_at, t0 = _now(), time.perf_counter()
    engine = get_engine(settings.database_url)
    record = {
        "run_id": run_id, "started_at": started_at, "finished_at": None, "status": "FAILED",
        "files_processed": 0, "rows_extracted": 0, "duplicates_removed": 0,
        "rows_rejected": 0, "rows_loaded": 0, "message": "",
    }
    logger.info("Pipeline run %s started (target: %s)", run_id, engine.url.render_as_string(hide_password=True))

    try:
        with timed("extract", logger):
            raw = extract(settings.raw_dir)
        record.update(files_processed=len(raw.files_read), rows_extracted=len(raw.sales))

        with timed("validate", logger):
            result = validate_sales(raw.sales, raw.products, raw.stores)
            record.update(duplicates_removed=result.duplicates_removed, rows_rejected=len(result.rejected))
            check_reject_threshold(result, settings.max_reject_rate)

        with timed("transform", logger):
            schema = transform(result.clean, raw.products, raw.stores)
            schema.fact_sales.to_csv(settings.processed_dir / "fact_sales.csv", index=False)

        with timed("load", logger):
            loaded = load(schema, result.rejected, engine)
            reconcile(engine, loaded, float(schema.fact_sales["net_amount_gbp"].sum()))
        record["rows_loaded"] = loaded

        with timed("report", logger):
            tables = run_queries(engine, settings.output_dir / "tables")
            make_charts(tables, settings.output_dir / "charts")
            dq_chart(result, settings.output_dir / "charts")
            runtime = round(time.perf_counter() - t0, 2)
            kpis = write_reports(result, tables, settings.output_dir / "reports",
                                 {"run_id": run_id, "files_processed": len(raw.files_read),
                                  "runtime_seconds": runtime})

        record.update(status="SUCCESS", message="OK")
        logger.info("Pipeline run %s SUCCEEDED in %.2fs", run_id, runtime)
        return kpis
    except Exception as exc:
        record["message"] = str(exc)[:500]
        logger.exception("Pipeline run %s FAILED: %s", run_id, exc)
        raise
    finally:
        record["finished_at"] = _now()
        try:
            write_run_log(engine, record)
        except Exception:  # never hide the original error because logging failed
            logger.exception("Could not write run log")

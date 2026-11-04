import json

from sqlalchemy import create_engine, text

from retail_etl.config import Settings
from retail_etl.generate_data import generate
from retail_etl.pipeline import run_pipeline


def test_full_run_on_small_dataset(tmp_path):
    db = tmp_path / "test.db"
    settings = Settings(
        database_url=f"sqlite:///{db.as_posix()}",
        raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed",
        output_dir=tmp_path / "outputs", log_dir=tmp_path / "logs",
    )
    generate(settings.raw_dir, base_rows=300, seed=1)
    kpis = run_pipeline(settings)

    engine = create_engine(f"sqlite:///{db.as_posix()}")
    with engine.connect() as conn:
        facts = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar()
        orphans = conn.execute(text(
            "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p ON p.product_key = f.product_key "
            "WHERE p.product_key IS NULL")).scalar()
        status = conn.execute(text("SELECT status FROM etl_run_log")).scalar()

    assert facts == kpis["rows_loaded"] > 0
    assert orphans == 0
    assert status == "SUCCESS"
    assert kpis["reject_rate_pct"] < 10
    assert json.loads((settings.output_dir / "reports" / "kpi_summary.json").read_text())["run_id"]
    assert (settings.output_dir / "charts" / "01_monthly_revenue.png").exists()


def test_rerun_is_idempotent(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'w.db').as_posix()}",
        raw_dir=tmp_path / "raw", processed_dir=tmp_path / "p",
        output_dir=tmp_path / "o", log_dir=tmp_path / "l",
    )
    generate(settings.raw_dir, base_rows=200, seed=2)
    first = run_pipeline(settings)
    second = run_pipeline(settings)
    assert first["rows_loaded"] == second["rows_loaded"]
    assert first["net_revenue_gbp"] == second["net_revenue_gbp"]

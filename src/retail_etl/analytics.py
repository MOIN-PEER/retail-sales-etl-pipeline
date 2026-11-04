"""Reporting layer: run the SQL in sql/analytics against the warehouse and save
result tables (CSV), charts (PNG) and a data-quality report (Markdown)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import Engine, text  # noqa: E402

from .config import PROJECT_ROOT  # noqa: E402
from .validate import ValidationResult  # noqa: E402

logger = logging.getLogger("retail_etl.analytics")
QUERY_DIR = PROJECT_ROOT / "sql" / "analytics"
COLOURS = ["#1f4e79", "#2e75b6", "#9dc3e6", "#c55a11", "#70ad47", "#7f7f7f"]

plt.rcParams.update({
    "figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 12, "font.size": 10,
})


def run_queries(engine: Engine, tables_dir: Path) -> dict[str, pd.DataFrame]:
    results = {}
    with engine.connect() as conn:
        for sql_file in sorted(QUERY_DIR.glob("*.sql")):
            df = pd.read_sql(text(sql_file.read_text(encoding="utf-8")), conn)
            name = sql_file.stem[3:]
            df.to_csv(tables_dir / f"{name}.csv", index=False)
            results[name] = df
            logger.info("Query %-20s -> %d rows", name, len(df))
    return results


def _gbp_k(x, _pos=None):
    return f"£{x / 1000:,.0f}k"


def make_charts(results: dict[str, pd.DataFrame], charts_dir: Path) -> list[Path]:
    paths = []

    m = results["monthly_revenue"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(m["month_name"].str[:3], m["net_revenue_gbp"], color=COLOURS[1])
    ax2 = ax.twinx()
    ax2.plot(m["month_name"].str[:3], m["margin_pct"], color=COLOURS[3], marker="o", label="Margin %")
    ax2.set_ylim(0, max(60, m["margin_pct"].max() + 5))
    ax2.set_ylabel("Gross margin %")
    ax.yaxis.set_major_formatter(_gbp_k)
    ax.set_title("Monthly net revenue and gross margin, 2025")
    fig.tight_layout()
    paths.append(_save(fig, charts_dir / "01_monthly_revenue.png"))

    s = results["store_performance"].sort_values("net_revenue_gbp")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(s["store_name"], s["net_revenue_gbp"], color=COLOURS[0])
    ax.xaxis.set_major_formatter(_gbp_k)
    ax.set_title("Net revenue by store")
    fig.tight_layout()
    paths.append(_save(fig, charts_dir / "02_store_revenue.png"))

    c = results["category_mix"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(c["category"], c["net_revenue_gbp"], color=COLOURS[1], label="Net revenue")
    ax.bar(c["category"], c["gross_margin_gbp"], color=COLOURS[0], label="Gross margin")
    ax.yaxis.set_major_formatter(_gbp_k)
    ax.legend(frameon=False)
    ax.set_title("Revenue and margin by category")
    fig.tight_layout()
    paths.append(_save(fig, charts_dir / "03_category_mix.png"))

    h = results["hourly_pattern"].pivot(index="transaction_hour", columns="day_type", values="transactions")
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, col in enumerate(h.columns):
        ax.plot(h.index, h[col], marker="o", color=COLOURS[i * 3 % len(COLOURS)], label=col)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Transactions")
    ax.legend(frameon=False)
    ax.set_title("Transactions by hour of day")
    fig.tight_layout()
    paths.append(_save(fig, charts_dir / "04_hourly_pattern.png"))

    t = results["top_products"].sort_values("net_revenue_gbp")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(t["product_name"], t["net_revenue_gbp"], color=COLOURS[4])
    ax.xaxis.set_major_formatter(_gbp_k)
    ax.set_title("Top 10 products by net revenue")
    fig.tight_layout()
    paths.append(_save(fig, charts_dir / "05_top_products.png"))
    return paths


def dq_chart(result: ValidationResult, charts_dir: Path) -> Path:
    counts = {k: v for k, v in result.rule_counts.items() if v}
    counts["duplicate_transaction"] = result.duplicates_removed
    s = pd.Series(counts).sort_values()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(s.index, s.values, color=COLOURS[3])
    for y, v in enumerate(s.values):
        ax.text(v, y, f" {v:,}", va="center")
    ax.set_title("Data-quality issues caught by the pipeline")
    fig.tight_layout()
    return _save(fig, charts_dir / "00_data_quality_issues.png")


def _save(fig, path: Path) -> Path:
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def write_reports(result: ValidationResult, results: dict[str, pd.DataFrame], reports_dir: Path,
                  run_meta: dict) -> dict:
    m = results["monthly_revenue"]
    stores = results["store_performance"]
    cats = results["category_mix"]
    total_net = float(m["net_revenue_gbp"].sum())
    kpis = {
        "run_id": run_meta["run_id"],
        "rows_extracted": result.input_rows,
        "duplicates_removed": result.duplicates_removed,
        "rows_rejected": len(result.rejected),
        "reject_rate_pct": round(100 * result.reject_rate, 2),
        "rows_loaded": len(result.clean),
        "net_revenue_gbp": round(total_net, 2),
        "gross_margin_gbp": round(float(m["gross_margin_gbp"].sum()), 2),
        "gross_margin_pct": round(100 * float(m["gross_margin_gbp"].sum()) / total_net, 1),
        "transactions": int(m["transactions"].sum()),
        "avg_transaction_gbp": round(total_net / int(m["transactions"].sum()), 2),
        "best_month": m.loc[m["net_revenue_gbp"].idxmax(), "month_name"],
        "best_month_share_pct": round(100 * float(m["net_revenue_gbp"].max()) / total_net, 1),
        "top_store": stores.iloc[0]["store_name"],
        "top_category": cats.iloc[0]["category"],
        "runtime_seconds": run_meta.get("runtime_seconds"),
    }
    (reports_dir / "kpi_summary.json").write_text(json.dumps(kpis, indent=2), encoding="utf-8")

    result.rejected.to_csv(reports_dir / "rejected_rows.csv", index=False)
    reason_counts = result.rejected["rejection_reason"].str.split(";").explode().value_counts()

    lines = [
        "# Data Quality Report",
        "",
        f"Run ID: `{run_meta['run_id']}`  ",
        f"Files processed: {run_meta['files_processed']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Rows extracted | {result.input_rows:,} |",
        f"| Duplicate transactions removed | {result.duplicates_removed:,} |",
        f"| Rows rejected (quarantined) | {len(result.rejected):,} |",
        f"| Reject rate | {100 * result.reject_rate:.2f}% |",
        f"| Rows loaded to warehouse | {len(result.clean):,} |",
        "",
        "## Rejections by rule",
        "",
        "| Rule | Rows |",
        "|---|---|",
        *[f"| {rule} | {count:,} |" for rule, count in reason_counts.items()],
        "",
        "All rejected rows, with the reason, are saved in `rejected_rows.csv` and in the",
        "`dq_rejected_sales` table so they can be corrected at source and reloaded.",
    ]
    (reports_dir / "data_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Reports written to %s", reports_dir)
    return kpis

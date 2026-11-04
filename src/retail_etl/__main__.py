"""Command-line entry point.

Usage:
    python -m retail_etl generate      # create synthetic raw files in data/raw
    python -m retail_etl run           # run the full ETL pipeline
    python -m retail_etl all           # generate + run
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import get_settings
from .generate_data import generate
from .logging_setup import setup_logging
from .pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="retail_etl", description="Retail sales ETL pipeline")
    parser.add_argument("command", choices=["generate", "run", "all"])
    parser.add_argument("--rows", type=int, default=9000, help="base sales rows per month (generate)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (generate)")
    args = parser.parse_args(argv)

    settings = get_settings()
    settings.ensure_dirs()
    log = setup_logging(settings.log_dir, settings.log_level)

    if args.command in ("generate", "all"):
        files = generate(settings.raw_dir, base_rows=args.rows, seed=args.seed)
        log.info("Generated %d raw files in %s", len(files), settings.raw_dir)

    if args.command in ("run", "all"):
        kpis = run_pipeline(settings)
        print("\nKPI summary:\n" + json.dumps(kpis, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

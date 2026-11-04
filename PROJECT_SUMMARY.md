# Project Summary - Retail Sales ETL Pipeline & Data Warehouse

**Problem.** Retailers export sales from till systems as monthly CSV files. These files are messy:
double-scanned transactions, missing store IDs, impossible dates, free-text quantities and
mistyped prices. Loading them straight into reports produces wrong numbers and lost trust.

**Solution.** A modular Python + SQL pipeline that turns raw exports into a trusted star-schema
warehouse in five stages: extract, validate, transform, load and report. Bad rows are never silently
dropped; they are quarantined with the reason so they can be fixed at source.

**Data.** One year (2025) of synthetic sales for a fictional UK chain: 12 stores, 6 categories,
60 products, ~110,000 raw rows with ~3% deliberately injected data-quality problems.

**Key engineering features**
- 7 validation rules plus de-duplication; quarantine table with reasons; automatic stop if > 10% of rows fail
- Star schema (`fact_sales` + date, store, product dimensions) with keys, constraints and indexes
- All-or-nothing transactional load, safe to re-run (idempotent full refresh)
- Post-load reconciliation of row counts and £ totals
- Retry with exponential backoff, structured logging, and an `etl_run_log` audit table
- Works on SQLite with zero setup, or PostgreSQL via one environment variable
- 19 automated tests, including end-to-end and re-run (idempotency) tests

**Results (latest run)**
- 110,076 rows extracted -> 1,086 duplicates removed -> 2,457 rejected (2.23%) -> 106,533 loaded
- Reconciliation passed; full run in ~5 seconds on a laptop
- Net revenue £6.94m, margin 34.8%; December was the peak month (13% of revenue); London Oxford St
  was the top store; Electronics the top category. These figures reflect the synthetic data's built-in
  seasonality and store sizes, so they show the reporting works rather than real market insight.

**Skills shown.** Python, pandas, SQL, data modelling (star schema), data-quality engineering,
SQLAlchemy, SQLite/PostgreSQL, testing with pytest, logging, configuration management, Git, documentation.

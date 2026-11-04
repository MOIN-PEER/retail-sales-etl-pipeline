"""Quick way to explore the warehouse: python scripts/query_warehouse.py "SELECT * FROM dim_store" """

import sys

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, "src")
from retail_etl.config import get_settings  # noqa: E402

sql = sys.argv[1] if len(sys.argv) > 1 else "SELECT * FROM etl_run_log ORDER BY started_at DESC"
engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    print(pd.read_sql(text(sql), conn).to_string(index=False))

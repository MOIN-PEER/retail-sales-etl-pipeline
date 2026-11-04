-- Warehouse schema (works on both SQLite and PostgreSQL).
-- Star schema: fact_sales at the centre, joined to date, store and product dimensions.
-- The pipeline fully rebuilds these tables each run (idempotent full refresh).

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dq_rejected_sales;

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,      -- e.g. 20251224
    full_date     DATE        NOT NULL,
    year          INTEGER     NOT NULL,
    quarter       INTEGER     NOT NULL,
    month         INTEGER     NOT NULL,
    month_name    VARCHAR(12) NOT NULL,
    week_of_year  INTEGER     NOT NULL,
    day_of_week   VARCHAR(10) NOT NULL,
    is_weekend    BOOLEAN     NOT NULL
);

CREATE TABLE dim_store (
    store_key   INTEGER PRIMARY KEY,
    store_id    VARCHAR(10)  NOT NULL UNIQUE,
    store_name  VARCHAR(100) NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    region      VARCHAR(50)  NOT NULL
);

CREATE TABLE dim_product (
    product_key     INTEGER PRIMARY KEY,
    product_code    VARCHAR(10)   NOT NULL UNIQUE,
    product_name    VARCHAR(100)  NOT NULL,
    category        VARCHAR(50)   NOT NULL,
    unit_price_gbp  NUMERIC(10,2) NOT NULL,
    unit_cost_gbp   NUMERIC(10,2) NOT NULL
);

CREATE TABLE fact_sales (
    transaction_id       VARCHAR(20) PRIMARY KEY,
    date_key             INTEGER NOT NULL REFERENCES dim_date(date_key),
    transaction_hour     INTEGER NOT NULL,
    store_key            INTEGER NOT NULL REFERENCES dim_store(store_key),
    product_key          INTEGER NOT NULL REFERENCES dim_product(product_key),
    quantity             INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_gbp       NUMERIC(10,2) NOT NULL,
    discount_pct         NUMERIC(4,2)  NOT NULL,
    gross_amount_gbp     NUMERIC(12,2) NOT NULL,
    discount_amount_gbp  NUMERIC(12,2) NOT NULL,
    net_amount_gbp       NUMERIC(12,2) NOT NULL,
    cost_amount_gbp      NUMERIC(12,2) NOT NULL,
    gross_margin_gbp     NUMERIC(12,2) NOT NULL,
    payment_method       VARCHAR(20) NOT NULL,
    channel              VARCHAR(20) NOT NULL,
    source_file          VARCHAR(50) NOT NULL
);

CREATE INDEX idx_fact_sales_date    ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_store   ON fact_sales(store_key);
CREATE INDEX idx_fact_sales_product ON fact_sales(product_key);

-- Quarantine table: every rejected row with the reason it failed validation.
CREATE TABLE dq_rejected_sales (
    transaction_id        VARCHAR(20),
    transaction_datetime  VARCHAR(30),
    store_id              VARCHAR(10),
    store_name            VARCHAR(100),
    product_code          VARCHAR(10),
    quantity              VARCHAR(10),
    unit_price_gbp        VARCHAR(20),
    discount_pct          VARCHAR(10),
    payment_method        VARCHAR(20),
    channel               VARCHAR(30),
    source_file           VARCHAR(50),
    rejection_reason      VARCHAR(200)
);

-- Audit table: one row per pipeline run (never dropped).
CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id              VARCHAR(40) PRIMARY KEY,
    started_at          VARCHAR(30) NOT NULL,
    finished_at         VARCHAR(30),
    status              VARCHAR(20) NOT NULL,
    files_processed     INTEGER,
    rows_extracted      INTEGER,
    duplicates_removed  INTEGER,
    rows_rejected       INTEGER,
    rows_loaded         INTEGER,
    message             VARCHAR(500)
);

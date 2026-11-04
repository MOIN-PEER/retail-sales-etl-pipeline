-- Monthly revenue, margin and order volume
SELECT d.year, d.month, d.month_name,
       COUNT(*)                         AS transactions,
       SUM(f.quantity)                  AS units_sold,
       ROUND(SUM(f.net_amount_gbp), 2)  AS net_revenue_gbp,
       ROUND(SUM(f.gross_margin_gbp), 2) AS gross_margin_gbp,
       ROUND(100.0 * SUM(f.gross_margin_gbp) / SUM(f.net_amount_gbp), 1) AS margin_pct
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

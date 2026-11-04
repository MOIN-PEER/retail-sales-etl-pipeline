-- Store league table
SELECT s.store_id, s.store_name, s.region,
       COUNT(*)                          AS transactions,
       ROUND(SUM(f.net_amount_gbp), 2)   AS net_revenue_gbp,
       ROUND(AVG(f.net_amount_gbp), 2)   AS avg_transaction_gbp,
       ROUND(SUM(f.gross_margin_gbp), 2) AS gross_margin_gbp
FROM fact_sales f
JOIN dim_store s ON s.store_key = f.store_key
GROUP BY s.store_id, s.store_name, s.region
ORDER BY net_revenue_gbp DESC;

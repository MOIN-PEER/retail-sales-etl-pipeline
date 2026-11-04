-- Revenue and margin by product category
SELECT p.category,
       SUM(f.quantity)                   AS units_sold,
       ROUND(SUM(f.net_amount_gbp), 2)   AS net_revenue_gbp,
       ROUND(SUM(f.gross_margin_gbp), 2) AS gross_margin_gbp,
       ROUND(100.0 * SUM(f.gross_margin_gbp) / SUM(f.net_amount_gbp), 1) AS margin_pct,
       ROUND(100.0 * SUM(f.discount_amount_gbp) / SUM(f.gross_amount_gbp), 1) AS avg_discount_pct
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category
ORDER BY net_revenue_gbp DESC;

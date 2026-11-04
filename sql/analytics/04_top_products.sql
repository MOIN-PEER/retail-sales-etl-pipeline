-- Top 10 products by net revenue
SELECT p.product_code, p.product_name, p.category,
       SUM(f.quantity)                 AS units_sold,
       ROUND(SUM(f.net_amount_gbp), 2) AS net_revenue_gbp
FROM fact_sales f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.product_code, p.product_name, p.category
ORDER BY net_revenue_gbp DESC
LIMIT 10;

-- Sales channel and payment method split
SELECT f.channel, f.payment_method,
       COUNT(*)                        AS transactions,
       ROUND(SUM(f.net_amount_gbp), 2) AS net_revenue_gbp
FROM fact_sales f
GROUP BY f.channel, f.payment_method
ORDER BY net_revenue_gbp DESC;

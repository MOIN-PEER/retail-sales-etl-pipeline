-- Trading pattern by hour of day and weekday/weekend
SELECT f.transaction_hour,
       CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       COUNT(*)                        AS transactions,
       ROUND(SUM(f.net_amount_gbp), 2) AS net_revenue_gbp
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY f.transaction_hour, CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END
ORDER BY f.transaction_hour, day_type;

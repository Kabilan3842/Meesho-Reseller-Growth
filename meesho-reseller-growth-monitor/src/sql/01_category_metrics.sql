SELECT
    month,
    category,
    COUNT(*) AS order_count,
    SUM(quantity) AS units_sold,
    ROUND(SUM(quantity * unit_price), 2) AS gmv
FROM orders
WHERE status = 'Delivered'
GROUP BY month, category
ORDER BY
    CASE month
        WHEN 'April' THEN 1
        WHEN 'May' THEN 2
        WHEN 'June' THEN 3
    END,
    category;

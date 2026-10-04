SELECT
    r.region,
    COUNT(DISTINCT r.reseller_id) AS reseller_count,
    COUNT(o.order_id) AS delivered_orders,
    ROUND(
        COALESCE(SUM(o.quantity * o.unit_price), 0),
        2
    ) AS gmv
FROM resellers r
LEFT JOIN orders o
    ON r.reseller_id = o.reseller_id
    AND o.status = 'Delivered'
GROUP BY r.region
ORDER BY gmv DESC;
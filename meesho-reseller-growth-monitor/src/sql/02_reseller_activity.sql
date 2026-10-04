SELECT
    r.reseller_id,
    r.reseller_name,
    r.region,
    r.city,
    COUNT(o.order_id) AS delivered_orders,
    ROUND(
        COALESCE(SUM(o.quantity * o.unit_price), 0),
        2
    ) AS gmv
FROM resellers r
LEFT JOIN orders o
    ON r.reseller_id = o.reseller_id
    AND o.status = 'Delivered'
GROUP BY
    r.reseller_id,
    r.reseller_name,
    r.region,
    r.city
ORDER BY gmv DESC;
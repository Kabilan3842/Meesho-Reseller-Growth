WITH monthly_gmv AS (
    SELECT
        r.region,
        o.month,
        SUM(o.quantity * o.unit_price) AS gmv
    FROM orders o
    JOIN resellers r
        ON o.reseller_id = r.reseller_id
    WHERE o.status = 'Delivered'
    GROUP BY r.region, o.month
),

region_mom AS (
    SELECT
        region,
        month,
        gmv,
        LAG(gmv) OVER (
            PARTITION BY region
            ORDER BY
                CASE month
                    WHEN 'April' THEN 1
                    WHEN 'May' THEN 2
                    WHEN 'June' THEN 3
                END
        ) AS previous_gmv
    FROM monthly_gmv
)

SELECT
    region,
    month,
    ROUND(gmv, 2) AS current_gmv,
    ROUND(COALESCE(previous_gmv, 0), 2) AS previous_gmv,
    CASE
        WHEN previous_gmv IS NULL OR previous_gmv = 0
            THEN NULL
        ELSE ROUND(
            ((gmv - previous_gmv) * 100.0) / previous_gmv,
            2
        )
    END AS change_pct,
    ROUND(
        gmv - COALESCE(previous_gmv, 0),
        2
    ) AS change_amount
FROM region_mom
WHERE previous_gmv IS NOT NULL
ORDER BY
    CASE month
        WHEN 'May' THEN 1
        WHEN 'June' THEN 2
    END,
    region;

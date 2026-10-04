WITH monthly_gmv AS (
    SELECT
        month,
        category,
        SUM(quantity * unit_price) AS gmv
    FROM orders
    WHERE status = 'Delivered'
    GROUP BY month, category
),

category_mom AS (
    SELECT
        category,
        month,
        gmv,
        LAG(gmv) OVER (
            PARTITION BY category
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
    category,
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
FROM category_mom
WHERE previous_gmv IS NOT NULL
ORDER BY
    CASE month
        WHEN 'May' THEN 1
        WHEN 'June' THEN 2
    END,
    category;
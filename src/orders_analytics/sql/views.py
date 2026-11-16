"""SQL view definitions for the analytical layer."""

from __future__ import annotations

SALES_BY_MONTH_COUNTRY_VIEW_SQL = """
CREATE VIEW sales_by_month_country AS
WITH monthly_totals AS (
    SELECT
        substr(date, 1, 7) AS month,
        country,
        SUM(
            CAST(amount AS INTEGER) * 100
            + CASE WHEN substr(amount, 1, 1) = '-' THEN -1 ELSE 1 END
                * CAST(substr(amount, instr(amount, '.') + 1) AS INTEGER)
        ) AS total_cents,
        COUNT(*) AS order_count
    FROM orders
    GROUP BY substr(date, 1, 7), country
)
SELECT
    month,
    country,
    CASE WHEN total_cents < 0 THEN '-' ELSE '' END
        || printf('%d.%02d', abs(total_cents) / 100, abs(total_cents) % 100) AS total_amount,
    order_count
FROM monthly_totals
ORDER BY month, country;
""".strip()

TOP_CUSTOMERS_VIEW_SQL = """
CREATE VIEW top_customers AS
WITH customer_totals AS (
    SELECT
        customer,
        SUM(
            CAST(amount AS INTEGER) * 100
            + CASE WHEN substr(amount, 1, 1) = '-' THEN -1 ELSE 1 END
                * CAST(substr(amount, instr(amount, '.') + 1) AS INTEGER)
        ) AS total_cents,
        COUNT(*) AS order_count
    FROM orders
    GROUP BY customer
)
SELECT
    customer,
    CASE WHEN total_cents < 0 THEN '-' ELSE '' END
        || printf('%d.%02d', abs(total_cents) / 100, abs(total_cents) % 100) AS total_amount,
    order_count
FROM customer_totals
ORDER BY total_cents DESC, customer
LIMIT 10;
""".strip()

VALID_VIEW_STATEMENTS = {
    "sales_by_month_country": SALES_BY_MONTH_COUNTRY_VIEW_SQL,
    "top_customers": TOP_CUSTOMERS_VIEW_SQL,
}

"""SQL view definitions for the analytical layer."""

from __future__ import annotations

SALES_BY_MONTH_COUNTRY_VIEW_SQL = """
CREATE VIEW sales_by_month_country AS
SELECT
    substr(date, 1, 7) AS month,
    country,
    ROUND(SUM(CAST(amount AS DECIMAL(18, 2))), 2) AS total_amount,
    COUNT(*) AS order_count
FROM orders
GROUP BY substr(date, 1, 7), country
ORDER BY month, country;
""".strip()

TOP_CUSTOMERS_VIEW_SQL = """
CREATE VIEW top_customers AS
SELECT
    customer,
    ROUND(SUM(CAST(amount AS DECIMAL(18, 2))), 2) AS total_amount,
    COUNT(*) AS order_count
FROM orders
GROUP BY customer
ORDER BY total_amount DESC, customer
LIMIT 10;
""".strip()

VALID_VIEW_STATEMENTS = {
    "sales_by_month_country": SALES_BY_MONTH_COUNTRY_VIEW_SQL,
    "top_customers": TOP_CUSTOMERS_VIEW_SQL,
}

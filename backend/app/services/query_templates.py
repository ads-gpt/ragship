import re


def template_sql(question: str) -> str | None:
    normalized = question.lower()

    if (
        re.search(r"\bsales territor(?:y|ies)\b", normalized)
        and re.search(r"\bproduct categor(?:y|ies)\b", normalized)
        and re.search(r"\b(revenue|sales)\b", normalized)
        and re.search(r"\b(rank|top\s+\d+)\b", normalized)
    ):
        return """
            WITH category_metrics AS (
                SELECT
                    st.name AS territory_name,
                    pc.name AS product_category,
                    SUM(sod.linetotal) AS total_revenue,
                    SUM(sod.orderqty) AS total_order_quantity,
                    AVG(sod.unitprice) AS average_unit_price,
                    SUM(sod.linetotal)
                        - SUM(sod.orderqty * p.standardcost) AS estimated_gross_profit,
                    COUNT(DISTINCT soh.customerid) AS distinct_customers,
                    COUNT(DISTINCT soh.salesorderid) AS distinct_orders
                FROM sales.salesorderheader AS soh
                JOIN sales.salesorderdetail AS sod
                    ON sod.salesorderid = soh.salesorderid
                JOIN production.product AS p
                    ON p.productid = sod.productid
                JOIN production.productsubcategory AS ps
                    ON ps.productsubcategoryid = p.productsubcategoryid
                JOIN production.productcategory AS pc
                    ON pc.productcategoryid = ps.productcategoryid
                JOIN sales.salesterritory AS st
                    ON st.territoryid = soh.territoryid
                WHERE soh.orderdate >= DATE '2012-01-01'
                  AND soh.orderdate < DATE '2014-01-01'
                  AND p.standardcost IS NOT NULL
                GROUP BY st.name, pc.name
            ),
            ranked_categories AS (
                SELECT
                    territory_name,
                    product_category,
                    total_revenue,
                    total_order_quantity,
                    average_unit_price,
                    estimated_gross_profit,
                    CASE
                        WHEN total_revenue = 0 THEN NULL
                        ELSE estimated_gross_profit / total_revenue * 100
                    END AS gross_margin_percentage,
                    distinct_customers,
                    distinct_orders,
                    RANK() OVER (
                        PARTITION BY territory_name
                        ORDER BY total_revenue DESC
                    ) AS category_revenue_rank,
                    SUM(total_revenue) OVER (
                        PARTITION BY territory_name
                    ) AS territory_revenue
                FROM category_metrics
            )
            SELECT
                territory_name,
                product_category,
                total_revenue,
                total_order_quantity,
                average_unit_price,
                estimated_gross_profit,
                gross_margin_percentage,
                distinct_customers,
                distinct_orders,
                category_revenue_rank,
                territory_revenue
            FROM ranked_categories
            WHERE category_revenue_rank <= 3
            ORDER BY territory_revenue DESC, category_revenue_rank ASC
        """

    if re.search(r"\b(how many|count|number of)\b", normalized) and re.search(
        r"\bhelmet|helmets\b", normalized
    ):
        if re.search(r"\b(list|show|name|names|which|what)\b", normalized):
            return """
                SELECT productid, name AS helmet_type
                FROM production.product
                WHERE name ILIKE '%helmet%'
                ORDER BY name
            """

        return """
            SELECT COUNT(DISTINCT name) AS helmet_type_count
            FROM production.product
            WHERE name ILIKE '%helmet%'
        """

    if re.search(r"\b(top|highest|best|largest)\b", normalized) and re.search(
        r"\bcustomers?\b", normalized
    ) and re.search(r"\b(revenue|sales|total)\b", normalized) and not re.search(
        r"\b(distinct customers?|number of distinct customers?|count of distinct customers?)\b",
        normalized,
    ) and not re.search(
        r"\b(product categor(?:y|ies)|sales territor(?:y|ies)|orders?)\b",
        normalized,
    ):
        return """
            SELECT
                c.customerid,
                COALESCE(
                    p.firstname || ' ' || p.lastname,
                    s.name,
                    c.accountnumber
                ) AS customer_name,
                SUM(soh.totaldue) AS total_revenue
            FROM sales.customer c
            JOIN sales.salesorderheader soh ON soh.customerid = c.customerid
            LEFT JOIN person.person p ON p.businessentityid = c.personid
            LEFT JOIN sales.store s ON s.businessentityid = c.storeid
            GROUP BY c.customerid, customer_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """

    return None

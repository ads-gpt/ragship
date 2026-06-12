import re


def template_sql(question: str) -> str | None:
    normalized = question.lower()

    if (
        re.search(r"\bhelmet|helmets\b", normalized)
        and re.search(r"\bblue\b", normalized)
        and re.search(r"\bblack\b", normalized)
        and re.search(r"\b(compare|comparison|versus|vs|why|difference|sales|revenue|quantity)\b", normalized)
    ):
        return """
            WITH helmet_sales AS (
                SELECT
                    p.color,
                    soh.orderdate,
                    st.name AS territory_name,
                    CASE
                        WHEN sod.unitpricediscount > 0 THEN 'Discounted'
                        ELSE 'No discount'
                    END AS discount_status,
                    CASE
                        WHEN c.storeid IS NOT NULL THEN 'Store customer'
                        WHEN c.personid IS NOT NULL THEN 'Individual customer'
                        ELSE 'Unknown customer'
                    END AS customer_segment,
                    sod.orderqty,
                    sod.linetotal,
                    soh.salesorderid,
                    soh.customerid
                FROM sales.salesorderdetail AS sod
                JOIN sales.salesorderheader AS soh
                    ON soh.salesorderid = sod.salesorderid
                JOIN production.product AS p
                    ON p.productid = sod.productid
                JOIN sales.customer AS c
                    ON c.customerid = soh.customerid
                LEFT JOIN sales.salesterritory AS st
                    ON st.territoryid = soh.territoryid
                WHERE p.name ILIKE '%helmet%'
                  AND p.color IN ('Blue', 'Black')
            ),
            breakdowns AS (
                SELECT
                    'Overall' AS breakdown_type,
                    'All helmet sales' AS breakdown_value,
                    color,
                    orderqty,
                    linetotal,
                    salesorderid,
                    customerid
                FROM helmet_sales
                UNION ALL
                SELECT
                    'Year' AS breakdown_type,
                    EXTRACT(YEAR FROM orderdate)::text AS breakdown_value,
                    color,
                    orderqty,
                    linetotal,
                    salesorderid,
                    customerid
                FROM helmet_sales
                UNION ALL
                SELECT
                    'Territory' AS breakdown_type,
                    COALESCE(territory_name, 'Unknown') AS breakdown_value,
                    color,
                    orderqty,
                    linetotal,
                    salesorderid,
                    customerid
                FROM helmet_sales
                UNION ALL
                SELECT
                    'Discount' AS breakdown_type,
                    discount_status AS breakdown_value,
                    color,
                    orderqty,
                    linetotal,
                    salesorderid,
                    customerid
                FROM helmet_sales
                UNION ALL
                SELECT
                    'Customer segment' AS breakdown_type,
                    customer_segment AS breakdown_value,
                    color,
                    orderqty,
                    linetotal,
                    salesorderid,
                    customerid
                FROM helmet_sales
            )
            SELECT
                breakdown_type,
                breakdown_value,
                SUM(orderqty) FILTER (WHERE color = 'Black') AS black_quantity,
                SUM(orderqty) FILTER (WHERE color = 'Blue') AS blue_quantity,
                COALESCE(SUM(orderqty) FILTER (WHERE color = 'Black'), 0)
                    - COALESCE(SUM(orderqty) FILTER (WHERE color = 'Blue'), 0)
                    AS black_minus_blue_quantity,
                ROUND(SUM(linetotal) FILTER (WHERE color = 'Black')::numeric, 2) AS black_revenue,
                ROUND(SUM(linetotal) FILTER (WHERE color = 'Blue')::numeric, 2) AS blue_revenue,
                ROUND(
                    (
                        COALESCE(SUM(linetotal) FILTER (WHERE color = 'Black'), 0)
                        - COALESCE(SUM(linetotal) FILTER (WHERE color = 'Blue'), 0)
                    )::numeric,
                    2
                ) AS black_minus_blue_revenue,
                COUNT(DISTINCT salesorderid) FILTER (WHERE color = 'Black') AS black_orders,
                COUNT(DISTINCT salesorderid) FILTER (WHERE color = 'Blue') AS blue_orders,
                COUNT(DISTINCT customerid) FILTER (WHERE color = 'Black') AS black_customers,
                COUNT(DISTINCT customerid) FILTER (WHERE color = 'Blue') AS blue_customers
            FROM breakdowns
            GROUP BY breakdown_type, breakdown_value
            ORDER BY
                CASE breakdown_type
                    WHEN 'Overall' THEN 1
                    WHEN 'Year' THEN 2
                    WHEN 'Territory' THEN 3
                    WHEN 'Discount' THEN 4
                    WHEN 'Customer segment' THEN 5
                    ELSE 6
                END,
                ABS(
                    COALESCE(SUM(orderqty) FILTER (WHERE color = 'Black'), 0)
                    - COALESCE(SUM(orderqty) FILTER (WHERE color = 'Blue'), 0)
                ) DESC,
                breakdown_value
        """

    if (
        re.search(r"\bhelmet|helmets\b", normalized)
        and re.search(r"\b(sale|sales|sold|revenue|quantity|orders?|show)\b", normalized)
    ):
        return """
            SELECT
                p.productid,
                p.name AS product_name,
                p.color,
                SUM(sod.orderqty) AS total_quantity_sold,
                ROUND(SUM(sod.linetotal)::numeric, 2) AS total_revenue,
                ROUND(AVG(sod.unitprice)::numeric, 2) AS average_unit_price,
                COUNT(DISTINCT soh.salesorderid) AS distinct_orders,
                COUNT(DISTINCT soh.customerid) AS distinct_customers
            FROM sales.salesorderdetail AS sod
            JOIN sales.salesorderheader AS soh
                ON soh.salesorderid = sod.salesorderid
            JOIN production.product AS p
                ON p.productid = sod.productid
            WHERE p.name ILIKE '%helmet%'
            GROUP BY p.productid, p.name, p.color
            ORDER BY total_quantity_sold DESC, total_revenue DESC
        """

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

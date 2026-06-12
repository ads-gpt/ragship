import json
import re
from decimal import Decimal
from functools import lru_cache
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.db import engine


CORE_TABLES_BY_TOPIC = {
    "product": [
        "production.product",
        "production.productsubcategory",
        "production.productcategory",
        "sales.salesorderdetail",
    ],
    "sales": [
        "sales.salesorderheader",
        "sales.salesorderdetail",
        "sales.customer",
        "sales.salesperson",
        "sales.salesterritory",
    ],
    "profit": [
        "sales.salesorderheader",
        "sales.salesorderdetail",
        "production.product",
    ],
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "exists",
    "for",
    "is",
    "made",
    "me",
    "of",
    "profit",
    "show",
    "the",
    "this",
    "was",
    "what",
    "who",
}


def build_schema_context(question: str, retrieved_docs: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    documents_by_table = _documents_by_table()
    ordered_tables = [item["table"] for item in retrieved_docs if item.get("table")]

    for table in _topic_tables(question):
        if table not in ordered_tables:
            ordered_tables.append(table)

    schema_docs = [
        documents_by_table[table]
        for table in ordered_tables
        if table in documents_by_table
    ]
    hints = _database_hints(question)
    return schema_docs, hints


@lru_cache
def _documents_by_table() -> dict[str, str]:
    settings = get_settings()
    with settings.schema_documents_path.open("r", encoding="utf-8") as file:
        documents = json.load(file)
    return {item["table"]: item["document"] for item in documents}


def _topic_tables(question: str) -> list[str]:
    normalized = question.lower()
    tables: list[str] = []

    if re.search(r"\bhelmet|helmets|product|products\b", normalized):
        tables.extend(CORE_TABLES_BY_TOPIC["product"])
    if re.search(r"\bsale|sales|revenue|customer|customers|made by\b", normalized):
        tables.extend(CORE_TABLES_BY_TOPIC["sales"])
    if re.search(r"\bprofit|margin|cost\b", normalized):
        tables.extend(CORE_TABLES_BY_TOPIC["profit"])
    if re.search(r"\d+\.\d+|\b\d{4,}\b", normalized):
        tables.extend(CORE_TABLES_BY_TOPIC["sales"])

    return list(dict.fromkeys(tables))


def _database_hints(question: str) -> list[str]:
    hints: list[str] = []
    normalized = question.lower()
    if re.search(r"\bprofit|margin\b", question.lower()):
        hints.append(
            "For estimated gross profit, use SUM(sales.salesorderdetail.linetotal) - "
            "SUM(sales.salesorderdetail.orderqty * production.product.standardcost)."
        )
    if re.search(r"\b(product|products|helmet|helmets|bike|bikes|part|parts)\b", normalized):
        hints.extend(_product_hints(question))
    hints.extend(_numeric_sales_hints(question))
    return hints[:12]


def _product_hints(question: str) -> list[str]:
    terms = _search_terms(question)
    if not terms:
        return []

    hints: list[str] = []
    with engine.connect() as connection:
        for term in terms[:5]:
            rows = connection.execute(
                text(
                    """
                    SELECT productid, name, productnumber, standardcost, listprice
                    FROM production.product
                    WHERE name ILIKE :pattern OR productnumber ILIKE :pattern
                    ORDER BY name
                    LIMIT 8
                    """
                ),
                {"pattern": f"%{term}%"},
            ).mappings()
            matches = [dict(row) for row in rows]
            if matches:
                hints.append(f"Products matching '{term}': {_compact(matches)}")
    return hints


def _numeric_sales_hints(question: str) -> list[str]:
    values = [Decimal(match) for match in re.findall(r"\b\d+(?:\.\d+)?\b", question)]
    values = [value for value in values if value >= 100]
    if not values:
        return []

    hints: list[str] = []
    with engine.connect() as connection:
        for value in values[:3]:
            rows = connection.execute(
                text(
                    """
                    WITH customer_revenue AS (
                        SELECT
                            c.customerid,
                            c.accountnumber,
                            c.personid,
                            c.storeid,
                            SUM(soh.subtotal) AS subtotal_revenue,
                            SUM(soh.totaldue) AS totaldue_revenue
                        FROM sales.customer c
                        JOIN sales.salesorderheader soh ON soh.customerid = c.customerid
                        GROUP BY c.customerid, c.accountnumber, c.personid, c.storeid
                    )
                    SELECT *
                    FROM customer_revenue
                    WHERE ABS(subtotal_revenue - :value) < 0.05
                       OR ABS(totaldue_revenue - :value) < 0.05
                    LIMIT 5
                    """
                ),
                {"value": value},
            ).mappings()
            customer_matches = [dict(row) for row in rows]
            if customer_matches:
                hints.append(
                    f"Customer revenue aggregates near {value}: {_compact(customer_matches)}"
                )
                hints.append(
                    f"The number {value} matches customer revenue. If the question asks "
                    "who made it or what profit it is, filter to that customerid and compute "
                    "profit for that customer; do not compare profit to this number."
                )

            rows = connection.execute(
                text(
                    """
                    SELECT salesorderid, customerid, salespersonid, subtotal, totaldue
                    FROM sales.salesorderheader
                    WHERE ABS(subtotal - :value) < 0.05
                       OR ABS(totaldue - :value) < 0.05
                    LIMIT 5
                    """
                ),
                {"value": value},
            ).mappings()
            order_matches = [dict(row) for row in rows]
            if order_matches:
                hints.append(f"Sales orders near {value}: {_compact(order_matches)}")
    return hints


def _search_terms(question: str) -> list[str]:
    terms = []
    for raw_term in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", question.lower()):
        if raw_term in STOPWORDS:
            continue
        term = raw_term[:-1] if raw_term.endswith("s") else raw_term
        if term not in STOPWORDS and term not in terms:
            terms.append(term)
    return terms


def _compact(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows, default=str, separators=(",", ":"))

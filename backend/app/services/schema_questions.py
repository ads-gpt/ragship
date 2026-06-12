import json
import re
from functools import lru_cache
from typing import Any

from app.config import get_settings


COMMON_TABLES = [
    "sales.salesorderheader",
    "sales.salesorderdetail",
    "sales.customer",
    "sales.salesterritory",
    "production.product",
    "production.productcategory",
    "person.person",
]


def answer_schema_question(question: str) -> tuple[str, str, list[dict[str, Any]]] | None:
    if not _looks_like_table_detail_request(question):
        return None

    metadata = _schema_metadata()
    matched_table = _find_table(question, metadata)
    if matched_table:
        return _describe_table(matched_table)

    normalized = question.lower()
    if re.search(r"\b(the|this|that)?\s*table\b", normalized):
        examples = ", ".join(COMMON_TABLES[:5])
        answer = (
            "Which table do you want me to describe? I can summarize columns, primary keys, "
            f"foreign keys, and useful context once you name one. Try one of these: {examples}."
        )
        rows = [{"table": table} for table in COMMON_TABLES]
        return "-- No SQL executed. The table name is ambiguous.", answer, rows

    return None


def _looks_like_table_detail_request(question: str) -> bool:
    normalized = question.lower()
    has_table_word = re.search(r"\btable\b", normalized) is not None
    has_detail_intent = re.search(
        r"\b(describe|detail|details|schema|columns?|everything|structure|metadata|about)\b",
        normalized,
    )
    return has_table_word and has_detail_intent is not None


def _find_table(question: str, metadata: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = question.lower()
    matches = []

    for item in metadata:
        full_name = item["full_table_name"].lower()
        table_name = item["table"].lower()

        if re.search(rf"\b{re.escape(full_name)}\b", normalized):
            return item
        if re.search(rf"\b{re.escape(table_name)}\b", normalized):
            matches.append(item)

    return matches[0] if len(matches) == 1 else None


def _describe_table(table: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    full_name = table["full_table_name"]
    columns = table.get("columns", [])
    primary_key = table.get("primary_key") or []
    foreign_keys = table.get("foreign_keys") or []

    rows = [
        {
            "column": column["name"],
            "type": column["type"],
            "nullable": column["nullable"],
            "default": column["default"],
        }
        for column in columns
    ]

    pk_text = ", ".join(primary_key) if primary_key else "no declared primary key"
    fk_text = (
        f"{len(foreign_keys)} foreign key relationship{'s' if len(foreign_keys) != 1 else ''}"
        if foreign_keys
        else "no foreign keys"
    )
    column_names = ", ".join(column["name"] for column in columns[:8])
    extra_columns = "" if len(columns) <= 8 else f", plus {len(columns) - 8} more"
    answer = (
        f"{full_name} has {len(columns)} columns. Its primary key is {pk_text}, and it has {fk_text}. "
        f"Important columns include {column_names}{extra_columns}. The column-level details are in the table."
    )
    sql = f"-- Schema summary for {full_name}. No database query was executed."
    return sql, answer, rows


@lru_cache
def _schema_metadata() -> list[dict[str, Any]]:
    settings = get_settings()
    path = settings.schema_documents_path.with_name("schema_metadata.json")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

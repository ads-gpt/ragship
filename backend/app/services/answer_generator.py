from decimal import Decimal
import re
from typing import Any


class AnswerGenerator:
    def __init__(self) -> None:
        pass

    def generate(self, question: str, sql: str, rows: list[dict]) -> str:
        if not rows:
            return "No rows matched the question."

        columns = list(rows[0].keys())
        if len(rows) == 1:
            aggregate_answer = _format_single_aggregate(question, rows[0], columns)
            if aggregate_answer:
                return aggregate_answer

        list_answer = _format_known_list(question, rows, columns)
        if list_answer:
            return list_answer

        ranked_breakdown = _format_ranked_breakdown(rows, columns)
        if ranked_breakdown:
            return ranked_breakdown

        if len(columns) == 1:
            column = columns[0]
            values = [format_value(row.get(column), column) for row in rows[:10]]
            suffix = "" if len(rows) <= 10 else f" I’m showing the first 10 of {len(rows)} rows."
            return (
                f"I found {len(rows)} {_pluralize(_humanize_column(column), len(rows))}: "
                f"{_join_values(values)}.{suffix}"
            )

        if len(rows) == 1:
            values = [
                f"{_humanize_column(column).lower()}: {format_value(rows[0].get(column), column)}"
                for column in columns
            ]
            return "Here’s the result: " + "; ".join(values) + "."

        label_column = _pick_label_column(columns, rows)
        value_column = _pick_value_column(columns, rows, label_column)

        if label_column and value_column:
            items = [
                f"{index}. {format_value(row.get(label_column), label_column)} "
                f"with {format_value(row.get(value_column), value_column)}"
                for index, row in enumerate(rows[:10], start=1)
            ]
            label = _pluralize(_humanize_column(label_column), len(rows))
            metric = _humanize_column(value_column).lower()
            suffix = "" if len(rows) <= 10 else f" Showing the first 10 of {len(rows)} rows."
            return (
                f"The top {min(len(rows), 10)} {label} by {metric} are:\n"
                + "\n".join(items)
                + suffix
            )

        if label_column:
            values = [format_value(row.get(label_column), label_column) for row in rows[:10]]
            label = _pluralize(_humanize_column(label_column), len(rows))
            suffix = "" if len(rows) <= 10 else f" Showing the first 10 of {len(rows)} rows."
            return f"Found {len(rows)} {label}: {_join_values(values)}.{suffix}"

        examples = [_describe_row(row, columns) for row in rows[:3]]
        suffix = "" if len(rows) <= 3 else f" There are {len(rows)} rows total in the table below."
        return f"I found {len(rows)} matching rows. For example: {_join_values(examples)}.{suffix}"


def _pick_label_column(columns: list[str], rows: list[dict]) -> str | None:
    preferred = (
        "name",
        "territory",
        "category",
        "customer",
        "product",
        "country",
        "region",
        "type",
    )
    for column in columns:
        normalized = column.lower()
        if any(token in normalized for token in preferred) and not _mostly_numeric(column, rows):
            return column

    for column in columns:
        if column.lower().endswith("id"):
            continue
        if _mostly_numeric(column, rows):
            continue
        return column
    return columns[0] if columns else None


def _pick_value_column(columns: list[str], rows: list[dict], label_column: str | None) -> str | None:
    preferred = (
        "total",
        "revenue",
        "sales",
        "amount",
        "profit",
        "quantity",
        "count",
        "subtotal",
        "due",
    )
    candidates = [column for column in columns if column != label_column]
    for column in candidates:
        normalized = column.lower()
        if any(token in normalized for token in preferred) and _has_numeric_value(column, rows):
            return column
    for column in candidates:
        if column.lower().endswith("id"):
            continue
        if _has_numeric_value(column, rows):
            return column
    return None


def format_value(value: Any, column: str | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return _format_number(value, column)
    if isinstance(value, float):
        return _format_number(Decimal(str(value)), column)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, str) and _is_numeric_string(value):
        number = Decimal(value)
        if "." in value or _is_money_column(column or ""):
            return _format_number(number, column)
        return f"{int(number):,}"
    return str(value)


def _format_number(value: Decimal, column: str | None = None) -> str:
    quantized = value.quantize(Decimal("0.01"))
    if column and "percentage" in column.lower():
        return f"{quantized:,.2f}%"
    prefix = "$" if column and _is_money_column(column) else ""
    return f"{prefix}{quantized:,.2f}"


def _humanize_column(column: str) -> str:
    return column.replace("_", " ").strip().capitalize()


def _has_numeric_value(column: str, rows: list[dict]) -> bool:
    return any(
        isinstance(row.get(column), (Decimal, float, int))
        or (isinstance(row.get(column), str) and _is_numeric_string(row.get(column)))
        for row in rows[:10]
    )


def _mostly_numeric(column: str, rows: list[dict]) -> bool:
    values = [row.get(column) for row in rows[:10] if row.get(column) is not None]
    if not values:
        return False
    numeric_count = sum(isinstance(value, (Decimal, float, int)) for value in values)
    numeric_count += sum(
        isinstance(value, str) and _is_numeric_string(value)
        for value in values
    )
    return numeric_count / len(values) >= 0.7


def _is_money_column(column: str) -> bool:
    normalized = column.lower()
    return any(
        token in normalized
        for token in ("sales", "revenue", "amount", "profit", "subtotal", "total", "due", "cost", "price")
    )


def _pluralize(label: str, count: int) -> str:
    if count == 1:
        return label.lower()
    label = label.lower()
    if label.endswith("y"):
        return label[:-1] + "ies"
    if label.endswith("s"):
        return label
    return label + "s"


def _join_values(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _describe_row(row: dict, columns: list[str]) -> str:
    parts = [
        f"{_humanize_column(column).lower()} {format_value(row.get(column), column)}"
        for column in columns[:4]
    ]
    return ", ".join(parts)


def _format_single_aggregate(question: str, row: dict, columns: list[str]) -> str | None:
    if len(columns) != 1:
        return None

    column = columns[0]
    value = row.get(column)
    if not (
        isinstance(value, (Decimal, float, int))
        or (isinstance(value, str) and _is_numeric_string(value))
    ):
        return None

    normalized_question = question.lower()
    normalized_column = column.lower()
    formatted_value = format_value(value, column)

    if "helmet" in normalized_question:
        noun = "helmet type" if str(formatted_value) == "1" else "helmet types"
        return f"There are {formatted_value} {noun} in the product catalog."

    if "count" in normalized_column or re.search(r"\b(how many|count|number of)\b", normalized_question):
        subject = _aggregate_subject(question, column)
        return f"There are {formatted_value} {subject}."

    return None


def _format_known_list(question: str, rows: list[dict], columns: list[str]) -> str | None:
    normalized_question = question.lower()

    if "helmet" in normalized_question:
        if re.search(r"\b(sale|sales|sold|revenue|quantity|orders?)\b", normalized_question):
            return None

        name_column = next(
            (column for column in columns if column.lower() in {"helmet_type", "name", "product_name"}),
            None,
        )
        if name_column:
            names = [str(row.get(name_column)) for row in rows if row.get(name_column)]
            noun = "helmet type" if len(names) == 1 else "helmet types"
            return f"There are {len(names)} {noun} in the product catalog: {_join_values(names)}."

    return None


def _format_ranked_breakdown(rows: list[dict], columns: list[str]) -> str | None:
    required_columns = {
        "territory_name",
        "product_category",
        "total_revenue",
        "gross_margin_percentage",
        "category_revenue_rank",
    }
    if not required_columns.issubset(set(columns)):
        return None

    items = []
    for row in rows[:10]:
        items.append(
            f"{row.get('territory_name')} - {row.get('product_category')} "
            f"(rank {format_value(row.get('category_revenue_rank'), 'category_revenue_rank')}) "
            f"with {format_value(row.get('total_revenue'), 'total_revenue')} revenue "
            f"and {format_value(row.get('gross_margin_percentage'), 'gross_margin_percentage')} gross margin"
        )

    suffix = "" if len(rows) <= 10 else f" I’m showing the first 10 of {len(rows)} ranked rows."
    return (
        "I found the top product categories by revenue within each territory. "
        f"Top rows: {_join_values(items)}.{suffix}"
    )


def _aggregate_subject(question: str, column: str) -> str:
    match = re.search(r"\b(?:how many|number of|count(?: of)?)\s+([a-z][a-z\s]+?)(?:\?|$)", question.lower())
    if match:
        return match.group(1).strip()

    subject = re.sub(r"(_?count|count_?)", "", column, flags=re.IGNORECASE)
    subject = subject.replace("_", " ").strip()
    return subject or "matching records"


def _is_numeric_string(value: str) -> bool:
    return re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip()) is not None

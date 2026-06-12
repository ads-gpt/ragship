import re

import sqlglot
from sqlglot import exp


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    return sql.strip()


def validate_read_only_sql(sql: str) -> str:
    cleaned = _strip_comments(sql).strip()
    cleaned = re.sub(r"^```(?:sql)?|```$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = _extract_statement(cleaned)

    if not cleaned:
        raise ValueError("SQL is empty.")

    try:
        parsed_statements = sqlglot.parse(cleaned, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Invalid SQL: {exc}") from exc

    statements = [statement for statement in parsed_statements if statement is not None]
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")

    parsed = statements[0]
    if not isinstance(parsed, (exp.Select, exp.Union)):
        raise ValueError("Only SELECT and WITH queries are allowed.")

    blocked_expression = _find_blocked_expression(parsed)
    if blocked_expression:
        raise ValueError(f"Blocked SQL keyword: {blocked_expression}")

    _reject_undefined_helper_tables(parsed)
    return parsed.sql(dialect="postgres")


def _extract_statement(text: str) -> str:
    if "</think>" in text:
        text = text.split("</think>", maxsplit=1)[1].strip()
    text = re.sub(r"<think>.*?</think>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = text.strip()

    if re.match(r"(?is)^(WITH|SELECT)\b", text):
        return text

    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    line_matches = list(re.finditer(r"(?im)^\s*(WITH|SELECT)\b", text))
    if line_matches:
        return text[line_matches[-1].start() :].strip()

    loose_matches = list(re.finditer(r"\b(WITH|SELECT)\b", text, flags=re.IGNORECASE))
    if loose_matches:
        return text[loose_matches[-1].start() :].strip()

    return text


def _find_blocked_expression(statement: exp.Expression) -> str | None:
    blocked_types = (
        exp.Alter,
        exp.Command,
        exp.Create,
        exp.Delete,
        exp.Drop,
        exp.Insert,
        exp.Update,
    )
    for node in statement.walk():
        if isinstance(node, blocked_types):
            return node.key.upper()
    return None


def _reject_undefined_helper_tables(statement: exp.Expression) -> None:
    ctes = {
        cte.alias.lower()
        for cte in statement.find_all(exp.CTE)
        if cte.alias
    }
    undefined_helpers = sorted(
        {
            table.name.lower()
            for table in statement.find_all(exp.Table)
            if table.name and not table.db and table.name.lower() not in ctes
        }
    )
    if undefined_helpers:
        raise ValueError(
            "Undefined helper table or CTE: "
            + ", ".join(undefined_helpers)
            + ". Use real schema-qualified tables or define the helper in WITH."
        )

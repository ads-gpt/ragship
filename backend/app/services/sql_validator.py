import re

import sqlparse
from sqlparse import tokens as T

_BLOCKED = frozenset({"INSERT", "UPDATE", "DELETE", "TRUNCATE", "ALTER", "CREATE", "DROP"})

_FROM_JOIN_TABLE = re.compile(
    r"\b(?:FROM|JOIN)\s+"
    r"(?!LATERAL\s|UNNEST\s|\()"
    r"([A-Za-z_]\w*)\b(?!\s*\.\s*\w)",
    re.IGNORECASE,
)

_CTE_NAME = re.compile(r"(?:WITH|,)\s+([A-Za-z_]\w*)\s+AS\s*\(", re.IGNORECASE)


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

    if not re.search(r"\b(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("No SQL query found in model response.")

    statements = [s for s in sqlparse.parse(cleaned) if s.value.strip()]
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")

    stmt = statements[0]
    stmt_type = stmt.get_type()
    # WITH…SELECT queries report type "SELECT"; plain None means unrecognised
    if stmt_type not in (None, "SELECT"):
        raise ValueError("Only SELECT and WITH queries are allowed.")

    blocked = _find_blocked_keyword(stmt)
    if blocked:
        raise ValueError(f"Blocked SQL keyword: {blocked}")

    _reject_undefined_helper_tables(cleaned)
    return cleaned.rstrip().rstrip(";").rstrip()


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
        return text[line_matches[-1].start():].strip()

    loose_matches = list(re.finditer(r"\b(WITH|SELECT)\b", text, flags=re.IGNORECASE))
    if loose_matches:
        return text[loose_matches[-1].start():].strip()

    return text


def _find_blocked_keyword(stmt) -> str | None:
    for token in stmt.flatten():
        if token.ttype in (T.Keyword.DDL, T.Keyword.DML):
            upper = token.normalized.upper()
            if upper in _BLOCKED:
                return upper
    return None


def _reject_undefined_helper_tables(sql: str) -> None:
    ctes = {m.group(1).lower() for m in _CTE_NAME.finditer(sql)}
    undefined = sorted(
        {
            m.group(1).lower()
            for m in _FROM_JOIN_TABLE.finditer(sql)
            if m.group(1).lower() not in ctes
        }
    )
    if undefined:
        raise ValueError(
            "Undefined helper table or CTE: "
            + ", ".join(undefined)
            + ". Use real schema-qualified tables or define the helper in WITH."
        )

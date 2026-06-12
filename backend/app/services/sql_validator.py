import re


BLOCKED_KEYWORDS = {
    "ALTER",
    "CREATE",
    "DELETE",
    "DROP",
    "INSERT",
    "TRUNCATE",
    "UPDATE",
}


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

    statements = [part.strip() for part in cleaned.split(";") if part.strip()]
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")

    statement = statements[0]
    first_token = statement.split(maxsplit=1)[0].upper()
    if first_token not in {"SELECT", "WITH"}:
        raise ValueError("Only SELECT and WITH queries are allowed.")

    keyword_pattern = r"\b(" + "|".join(sorted(BLOCKED_KEYWORDS)) + r")\b"
    match = re.search(keyword_pattern, statement, flags=re.IGNORECASE)
    if match:
        raise ValueError(f"Blocked SQL keyword: {match.group(1).upper()}")

    _reject_undefined_helper_tables(statement)
    return statement


def _extract_statement(text: str) -> str:
    if "</think>" in text:
        text = text.split("</think>", maxsplit=1)[1].strip()
    text = re.sub(r"<think>.*?</think>", " ", text, flags=re.IGNORECASE | re.DOTALL)

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


def _reject_undefined_helper_tables(statement: str) -> None:
    ctes = {
        match.group(1).lower()
        for match in re.finditer(
            r"(?:WITH|,)\s+([a-z_][a-z0-9_]*)\s+AS\s*\(",
            statement,
            flags=re.IGNORECASE,
        )
    }
    references = {
        match.group(2).lower()
        for match in re.finditer(
            r"\b(FROM|JOIN)\s+((?!LATERAL\b)[a-z_][a-z0-9_]*)\b(?!\s*\.)",
            statement,
            flags=re.IGNORECASE,
        )
    }
    undefined_helpers = sorted(reference for reference in references if reference not in ctes)
    if undefined_helpers:
        raise ValueError(
            "Undefined helper table or CTE: "
            + ", ".join(undefined_helpers)
            + ". Use real schema-qualified tables or define the helper in WITH."
        )

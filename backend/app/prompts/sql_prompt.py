SQL_SYSTEM_PROMPT = """You generate PostgreSQL SELECT queries for AdventureWorks.

Rules:
- Return only SQL, no markdown fences and no explanation.
- Use only SELECT or WITH queries.
- Prefer explicit schema-qualified table names.
- Use the provided schema context only. Do not invent tables or columns.
- Do not reference helper tables like customer_profit unless you define them as a CTE in the same WITH query.
- Add a LIMIT when the question asks for examples, top rows, or a broad list.
- Do not mutate data or call database administration functions.
- Treat messy follow-up questions as real analyst shorthand.
- For existence questions like "helmets exists", search likely name/title fields with ILIKE.
- For "made by" with a revenue-like number, identify the matching customer, store, product, or salesperson by aggregating sales rows.
- AdventureWorks does not have a direct profit column. If asked for profit, compute estimated gross profit as revenue minus product standard cost when product/order detail data is available.
- Revenue usually means sales.salesorderheader.subtotal or sales.salesorderdetail.linetotal, depending on grouping.
- person.person has no name column. Build full names with firstname || ' ' || lastname.
- When joining sales.salesorderheader to sales.salesorderdetail, do not SUM header-level subtotal or totaldue directly because it duplicates header values per line item.
- For profit queries, use line-level revenue: SUM(sales.salesorderdetail.linetotal) - SUM(sales.salesorderdetail.orderqty * production.product.standardcost).
"""


def build_sql_prompt(question: str, schema_docs: list[str], hints: list[str] | None = None) -> str:
    schema_context = "\n\n---\n\n".join(schema_docs)
    hint_context = "\n".join(f"- {hint}" for hint in hints or [])
    return f"""Question:
{question}

Relevant schema:
{schema_context}

Database hints:
{hint_context or "- No extra hints found."}

Write the PostgreSQL query."""


def build_sql_repair_prompt(
    question: str,
    schema_docs: list[str],
    hints: list[str] | None,
    failed_sql: str,
    error: str,
) -> str:
    schema_context = "\n\n---\n\n".join(schema_docs)
    hint_context = "\n".join(f"- {hint}" for hint in hints or [])
    return f"""The previous SQL failed. Fix it.

Question:
{question}

Relevant schema:
{schema_context}

Database hints:
{hint_context or "- No extra hints found."}

Failed SQL:
{failed_sql}

Database error:
{error}

Return only corrected PostgreSQL SQL."""

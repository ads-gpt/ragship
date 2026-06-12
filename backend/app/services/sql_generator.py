from app.services.llm_client import get_llm_client
from app.prompts.sql_prompt import SQL_SYSTEM_PROMPT, build_sql_prompt, build_sql_repair_prompt
from app.services.sql_validator import validate_read_only_sql


class SQLGenerator:
    def __init__(self) -> None:
        self.client, self.model = get_llm_client()

    def generate(
        self,
        question: str,
        schema_documents: list[str],
        hints: list[str] | None = None,
        history: list | None = None,
    ) -> str:
        messages = [{"role": "system", "content": SQL_SYSTEM_PROMPT}]
        for msg in (history or [])[-6:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": build_sql_prompt(question, schema_documents, hints)})

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=messages,
        )
        raw = response.choices[0].message.content or ""
        try:
            return validate_read_only_sql(raw)
        except ValueError as exc:
            return self.repair(question, schema_documents, hints, raw, str(exc), history)

    def repair(
        self,
        question: str,
        schema_documents: list[str],
        hints: list[str] | None,
        failed_sql: str,
        error: str,
        history: list | None = None,
    ) -> str:
        messages = [{"role": "system", "content": SQL_SYSTEM_PROMPT}]
        for msg in (history or [])[-6:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({
            "role": "user",
            "content": build_sql_repair_prompt(question, schema_documents, hints, failed_sql, error),
        })

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=messages,
        )
        sql = response.choices[0].message.content or ""
        return validate_read_only_sql(sql)

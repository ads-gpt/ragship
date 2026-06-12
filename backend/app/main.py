from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_serializer

from app.rag.retriever import get_schema_retriever
from app.services.answer_generator import AnswerGenerator
from app.services.query_templates import template_sql
from app.services.query_executor import QueryExecutor
from app.services.schema_context import build_schema_context
from app.services.schema_questions import answer_schema_question
from app.services.sql_generator import SQLGenerator


app = FastAPI(title="Ragship API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class ChatResponse(BaseModel):
    sql: str
    answer: str
    rows: list[dict]

    @field_serializer("rows")
    def serialize_rows(self, rows: list[dict]) -> list[dict[str, Any]]:
        return [
            {str(key): to_json_safe(value) for key, value in row.items()}
            for row in rows
        ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        schema_answer = answer_schema_question(request.question)
        if schema_answer:
            sql, answer, rows = schema_answer
            return ChatResponse(sql=sql, answer=answer, rows=rows)

        query_executor = QueryExecutor()
        templated_sql = template_sql(request.question)
        if templated_sql:
            rows = query_executor.execute(templated_sql)
            answer = AnswerGenerator().generate(request.question, templated_sql, rows)
            return ChatResponse(sql=templated_sql.strip(), answer=answer, rows=rows)

        retriever = get_schema_retriever()
        retrieved_docs = retriever.retrieve(request.question)
        schema_documents, hints = build_schema_context(request.question, retrieved_docs)

        sql_generator = SQLGenerator()

        sql = sql_generator.generate(request.question, schema_documents, hints)
        try:
            rows = query_executor.execute(sql)
        except Exception as sql_error:
            sql = sql_generator.repair(
                request.question,
                schema_documents,
                hints,
                sql,
                str(sql_error),
            )
            rows = query_executor.execute(sql)
        answer = AnswerGenerator().generate(request.question, sql, rows)

        return ChatResponse(sql=sql, answer=answer, rows=rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def to_json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, memoryview):
        return f"<binary {value.nbytes:,} bytes>"
    if isinstance(value, bytes):
        return f"<binary {len(value):,} bytes>"
    return str(value)

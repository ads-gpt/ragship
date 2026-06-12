from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text

from app.db import engine


class QueryExecutor:
    def execute(self, sql: str, limit: int = 200) -> list[dict]:
        wrapped_sql = f"SELECT * FROM ({sql}) AS ragship_query LIMIT :limit"
        with engine.connect() as connection:
            result = connection.execute(text(wrapped_sql), {"limit": limit})
            return [
                {key: _to_json_safe(value) for key, value in row._mapping.items()}
                for row in result
            ]


def _to_json_safe(value):
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
        return _describe_binary(value.nbytes)
    if isinstance(value, bytes):
        return _describe_binary(len(value))
    return str(value)


def _describe_binary(size: int) -> str:
    return f"<binary {size:,} bytes>"

from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import get_settings


def _database_url() -> str:
    settings = get_settings()
    if settings.aiven_database_url:
        if settings.aiven_database_url.startswith("postgres://"):
            return settings.aiven_database_url.replace(
                "postgres://",
                "postgresql+psycopg2://",
                1,
            )
        if settings.aiven_database_url.startswith("postgresql://"):
            return settings.aiven_database_url.replace(
                "postgresql://",
                "postgresql+psycopg2://",
                1,
            )
        return settings.aiven_database_url

    required = {
        "AIVEN_HOST": settings.aiven_host,
        "AIVEN_DB": settings.aiven_db,
        "AIVEN_USER": settings.aiven_user,
        "AIVEN_PASSWORD": settings.aiven_password,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing database settings: {', '.join(missing)}")

    user = quote_plus(settings.aiven_user or "")
    password = quote_plus(settings.aiven_password or "")
    host = settings.aiven_host
    port = settings.aiven_port
    db = settings.aiven_db
    sslmode = settings.aiven_sslmode
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?sslmode={sslmode}"


engine: Engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

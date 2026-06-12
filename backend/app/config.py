from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"

load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    aiven_database_url: str | None = Field(default=None, alias="AIVEN_DATABASE_URL")
    aiven_host: str | None = Field(default=None, alias="AIVEN_HOST")
    aiven_port: int = Field(default=5432, alias="AIVEN_PORT")
    aiven_db: str | None = Field(default=None, alias="AIVEN_DB")
    aiven_user: str | None = Field(default=None, alias="AIVEN_USER")
    aiven_password: str | None = Field(default=None, alias="AIVEN_PASSWORD")
    aiven_sslmode: str = Field(default="require", alias="AIVEN_SSLMODE")

    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")

    groq_key: str | None = Field(default=None, alias="GROQ_KEY")
    groq_model: str = Field(default="qwen/qwen3-32b", alias="GROQ_MODEL")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        alias="GROQ_BASE_URL",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    schema_documents_path: Path = DATA_DIR / "schema_documents.json"
    chroma_path: Path = DATA_DIR / "chroma"
    schema_collection_name: str = "adventureworks_schema"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.llm_provider = settings.llm_provider.lower().strip()
    return settings

import json
from dataclasses import dataclass

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config import get_settings


@dataclass(frozen=True)
class SchemaDocument:
    table: str
    document: str


class SchemaIndex:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.settings.chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.settings.schema_collection_name,
            metadata={"description": "AdventureWorks schema documents"},
        )
        self.embedding_model = SentenceTransformer(self.settings.embedding_model_name)

    def load_documents(self) -> list[SchemaDocument]:
        with self.settings.schema_documents_path.open("r", encoding="utf-8") as file:
            raw_documents = json.load(file)

        return [
            SchemaDocument(table=item["table"], document=item["document"])
            for item in raw_documents
        ]

    def build(self, force: bool = False) -> Collection:
        documents = self.load_documents()
        expected_count = len(documents)

        if not force and self.collection.count() == expected_count:
            return self.collection

        if force or self.collection.count() > 0:
            self.client.delete_collection(self.settings.schema_collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.settings.schema_collection_name,
                metadata={"description": "AdventureWorks schema documents"},
            )

        texts = [doc.document for doc in documents]
        embeddings = self.embedding_model.encode(texts, normalize_embeddings=True).tolist()
        ids = [doc.table for doc in documents]
        metadatas = [{"table": doc.table} for doc in documents]

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return self.collection


def build_schema_index(force: bool = False) -> int:
    index = SchemaIndex()
    collection = index.build(force=force)
    return collection.count()


if __name__ == "__main__":
    count = build_schema_index(force=True)
    print(f"Indexed {count} schema documents.")

from functools import lru_cache
import re
from typing import Any

from app.rag.schema_index import SchemaIndex


class SchemaRetriever:
    def __init__(self) -> None:
        self.index = SchemaIndex()
        self.collection = self.index.build()

    def retrieve(self, question: str, top_k: int = 8) -> list[dict[str, Any]]:
        query_embedding = self.index.embedding_model.encode(
            [question],
            normalize_embeddings=True,
        ).tolist()[0]

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k * 3, 12),
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        retrieved: list[dict[str, Any]] = []
        query_terms = _terms(question)
        for document, metadata, distance in zip(documents, metadatas, distances):
            table = metadata.get("table", "")
            keyword_score = _keyword_score(query_terms, table, document)
            domain_penalty = _domain_penalty(query_terms, table)
            retrieved.append(
                {
                    "table": table,
                    "document": document,
                    "distance": distance,
                    "keyword_score": keyword_score,
                    "domain_penalty": domain_penalty,
                    "score": distance - keyword_score + domain_penalty,
                }
            )
        return sorted(retrieved, key=lambda item: item["score"])[:top_k]


@lru_cache
def get_schema_retriever() -> SchemaRetriever:
    return SchemaRetriever()


def _terms(text: str) -> set[str]:
    aliases = {
        "customers": "customer",
        "orders": "order",
        "sales": "sale",
        "revenue": "totaldue",
        "helmet": "product",
        "helmets": "product",
        "profit": "standardcost",
    }
    terms = set(re.findall(r"[a-z0-9_]+", text.lower()))
    return terms | {aliases[term] for term in terms if term in aliases}


def _keyword_score(query_terms: set[str], table: str, document: str) -> float:
    haystack = f"{table} {document}".lower()
    score = 0.0
    for term in query_terms:
        if term in table.lower():
            score += 0.18
        elif term in haystack:
            score += 0.08
    if {"helmet", "helmets", "product"} & query_terms and table == "production.product":
        score += 0.55
    if {"revenue", "profit", "totaldue", "customer"} & query_terms and table in {
        "sales.salesorderheader",
        "sales.salesorderdetail",
        "sales.customer",
        "production.product",
    }:
        score += 0.35
    return min(score, 0.6)


def _domain_penalty(query_terms: set[str], table: str) -> float:
    sales_terms = {"customer", "sale", "order", "revenue", "totaldue"}
    if query_terms & sales_terms and table.startswith("purchasing."):
        return 0.25
    return 0.0

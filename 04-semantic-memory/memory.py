import os
import voyageai
from dotenv import load_dotenv

load_dotenv()

VOYAGE_MODEL = "voyage-3-large"
EMBEDDING_DIM = 1024
USE_PGVECTOR = os.getenv("USE_PGVECTOR", "false").lower() == "true"


def _embed(text: str) -> list[float]:
    client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    result = client.embed([text], model=VOYAGE_MODEL, input_type="document")
    return result.embeddings[0]


def _embed_query(text: str) -> list[float]:
    client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    result = client.embed([text], model=VOYAGE_MODEL, input_type="query")
    return result.embeddings[0]


class SemanticMemory:
    def __init__(self):
        if USE_PGVECTOR:
            self._backend = _PgvectorBackend()
        else:
            self._backend = _PineconeBackend()

    def store_fact(self, fact_id: str, text: str, metadata: dict | None = None) -> None:
        embedding = _embed(text)
        self._backend.upsert(fact_id, embedding, text, metadata or {})

    def retrieve_facts(self, query: str, top_k: int = 3) -> list[dict]:
        embedding = _embed_query(query)
        return self._backend.query(embedding, top_k)

    def close(self) -> None:
        self._backend.close()


class _PineconeBackend:
    def __init__(self):
        from pinecone import Pinecone

        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self._index = pc.Index("agent-semantic-memory")

    def upsert(self, fact_id: str, embedding: list[float], text: str, metadata: dict) -> None:
        metadata["text"] = text
        self._index.upsert(vectors=[{"id": fact_id, "values": embedding, "metadata": metadata}])

    def query(self, embedding: list[float], top_k: int) -> list[dict]:
        result = self._index.query(vector=embedding, top_k=top_k, include_metadata=True)
        return [
            {"id": m["id"], "score": m["score"], "text": m["metadata"].get("text", ""), "metadata": m["metadata"]}
            for m in result["matches"]
        ]

    def close(self) -> None:
        pass


class _PgvectorBackend:
    def __init__(self):
        import psycopg2
        from pgvector.psycopg2 import register_vector

        conn_str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_memory")
        self._conn = psycopg2.connect(conn_str)
        self._conn.autocommit = True
        register_vector(self._conn)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    id       TEXT PRIMARY KEY,
                    content  TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector({EMBEDDING_DIM})
                )
                """
            )

    def upsert(self, fact_id: str, embedding: list[float], text: str, metadata: dict) -> None:
        import json
        import numpy as np

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO semantic_facts (id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                    SET content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                """,
                (fact_id, text, json.dumps(metadata), np.array(embedding)),
            )

    def query(self, embedding: list[float], top_k: int) -> list[dict]:
        import numpy as np

        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM semantic_facts
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (np.array(embedding), np.array(embedding), top_k),
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "score": float(r[3]), "text": r[1], "metadata": r[2] or {}}
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()

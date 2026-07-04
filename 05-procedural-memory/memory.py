import json
import psycopg2
import psycopg2.extras


class ProceduralMemory:
    def __init__(self, conn_str: str):
        self._conn = psycopg2.connect(conn_str)
        self._conn.autocommit = True

    def store_procedure(self, name: str, description: str, steps: list[dict]) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO procedures (name, description, steps)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                    SET description = EXCLUDED.description,
                        steps = EXCLUDED.steps
                """,
                (name, description, json.dumps(steps)),
            )

    def load_procedure(self, name: str) -> list[dict] | None:
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT steps FROM procedures WHERE name = %s", (name,)
            )
            row = cur.fetchone()
            return row["steps"] if row else None

    def increment_usage(self, name: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE procedures SET used_count = used_count + 1 WHERE name = %s",
                (name,),
            )

    def list_procedures(self) -> list[dict]:
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT name, description, used_count FROM procedures ORDER BY name"
            )
            return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

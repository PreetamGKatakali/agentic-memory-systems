import psycopg2
import psycopg2.extras


class ExternalMemory:
    def __init__(self, conn_str: str):
        self._conn = psycopg2.connect(conn_str)
        self._conn.autocommit = True

    def add_order(self, customer_id: str, item: str, quantity: int = 1) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (customer_id, item, quantity) VALUES (%s, %s, %s) RETURNING id",
                (customer_id, item, quantity),
            )
            return cur.fetchone()[0]

    def get_orders(self, customer_id: str) -> list[dict]:
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, item, quantity, status, created_at FROM orders "
                "WHERE customer_id = %s ORDER BY created_at",
                (customer_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def update_status(self, order_id: int, status: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = %s WHERE id = %s", (status, order_id)
            )

    def close(self) -> None:
        self._conn.close()

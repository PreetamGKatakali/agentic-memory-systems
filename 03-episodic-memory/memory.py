import json
import psycopg2
import psycopg2.extras
import redis

REDIS_CACHE_SIZE = 20


class EpisodicMemory:
    def __init__(self, pg_conn_str: str, redis_url: str):
        self._pg = psycopg2.connect(pg_conn_str)
        self._pg.autocommit = True
        self._redis = redis.from_url(redis_url)

    def save_event(self, user_id: str, session_id: str, role: str, content: str) -> None:
        with self._pg.cursor() as cur:
            cur.execute(
                "INSERT INTO episodes (user_id, session_id, role, content) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, session_id, role, content),
            )

        key = f"episodes:{user_id}"
        event = json.dumps({"session_id": session_id, "role": role, "content": content})
        self._redis.rpush(key, event)
        # keep only the most recent REDIS_CACHE_SIZE events in Redis
        self._redis.ltrim(key, -REDIS_CACHE_SIZE, -1)

    def get_recent_events(self, user_id: str, n: int = REDIS_CACHE_SIZE) -> list[dict]:
        key = f"episodes:{user_id}"
        cached = self._redis.lrange(key, 0, -1)

        if cached:
            print(f"  [cache] Loading from Redis ({len(cached)} events)")
            events = [json.loads(e) for e in cached]
            return events[-n:]

        print("  [cache] Cache miss — loading from Postgres")
        with self._pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT session_id, role, content FROM episodes "
                "WHERE user_id = %s ORDER BY occurred_at DESC LIMIT %s",
                (user_id, n),
            )
            rows = [dict(r) for r in cur.fetchall()]
            rows.reverse()

        # repopulate cache
        if rows:
            pipe = self._redis.pipeline()
            pipe.delete(key)
            for r in rows:
                pipe.rpush(key, json.dumps(r))
            pipe.ltrim(key, -REDIS_CACHE_SIZE, -1)
            pipe.execute()

        return rows

    def get_session_events(self, user_id: str, session_id: str) -> list[dict]:
        with self._pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT role, content, occurred_at FROM episodes "
                "WHERE user_id = %s AND session_id = %s ORDER BY occurred_at",
                (user_id, session_id),
            )
            return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        self._pg.close()
        self._redis.close()

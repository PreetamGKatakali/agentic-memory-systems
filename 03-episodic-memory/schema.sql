CREATE TABLE IF NOT EXISTS episodes (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT        NOT NULL,
    session_id  TEXT        NOT NULL,
    role        TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_episodes_user    ON episodes(user_id);
CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(user_id, session_id);

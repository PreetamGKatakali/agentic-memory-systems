CREATE TABLE IF NOT EXISTS procedures (
    id          SERIAL PRIMARY KEY,
    name        TEXT        NOT NULL UNIQUE,
    description TEXT        NOT NULL,
    steps       JSONB       NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_count  INT         NOT NULL DEFAULT 0
);

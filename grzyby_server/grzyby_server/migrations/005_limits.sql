-- Limits for a public address (TODO, „Przed publicznym startem”).

-- When a tile first came in, which the monthly refresh leaves alone: the daily limit of new tiles
-- (lasy/tiles.py) counts these. Tiles fetched before the limit existed count from their last fetch.
ALTER TABLE fetched_tiles ADD COLUMN first_fetched_at timestamptz;
UPDATE fetched_tiles SET first_fetched_at = fetched_at;
ALTER TABLE fetched_tiles ALTER COLUMN first_fetched_at SET NOT NULL;

-- Finished answers for a while (miejsca/cache.py), so the same question is not worked out again.
-- The answer as the tool's JSON, kept as text: jsonb would reorder its keys.
CREATE TABLE answer_cache (
    query text PRIMARY KEY,
    answer text NOT NULL,
    created_at timestamptz NOT NULL
);

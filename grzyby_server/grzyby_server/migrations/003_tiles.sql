-- Forest data comes in on demand, tile by tile (lasy/tiles.py): a fixed grid over Poland, each
-- tile fetched from BDL and GDOŚ the first time someone asks about a place near it, and kept
-- fresh by the monthly job. The pilot area's rows predate the grid; they are dropped and come
-- back on the first question about Suwałki.
TRUNCATE wydzielenia, obszary_chronione;

-- A stand belongs to the one tile its inner point lies in, whichever tile's fetch brought it, so
-- refreshing a tile replaces exactly its own stands.
ALTER TABLE wydzielenia ADD COLUMN tile text NOT NULL;
CREATE INDEX wydzielenia_tile ON wydzielenia (tile);

-- Parks and reserves reach across many tiles; GDOŚ's own id keeps one row per area, however
-- many tiles fetch it.
ALTER TABLE obszary_chronione ADD COLUMN gdos_id text NOT NULL UNIQUE;

CREATE TABLE fetched_tiles (
    tile text PRIMARY KEY,
    fetched_at timestamptz NOT NULL
);

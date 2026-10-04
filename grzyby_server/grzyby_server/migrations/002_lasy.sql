-- Forest data copied from public services (grzyby_server/lasy/), all in WGS84 (SRID 4326) —
-- the coordinates the services send and the map draws. Distances are taken on geography, in
-- metres.

-- Forest stands from the Bank Danych o Lasach: only real stands (area_type D-STAN), refreshed
-- in full by the monthly import.
CREATE TABLE wydzielenia (
    adres_lesny text PRIMARY KEY,         -- adr_for without its padding, e.g. 01-12-1-03-226-a-00
    gatunek text,                         -- species_cd: dominant species (SO, ŚW, BRZ…)
    wiek integer NOT NULL,                -- spec_age: age of the dominant species
    siedlisko text,                       -- site_type: forest site type (BMŚW, LMŚW…)
    funkcja text,                         -- forest_fun: GOSP, REZ (reserve)…
    powierzchnia_ha double precision NOT NULL,
    data_year integer NOT NULL,           -- a_year: when BDL made the record (attribution)
    geom geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX wydzielenia_geom ON wydzielenia USING gist (geom);

-- National parks and nature reserves from GDOŚ — no picking there. Buffer zones (otulina) are
-- not parks and are left out by the import.
CREATE TABLE obszary_chronione (
    id serial PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('park_narodowy', 'rezerwat')),
    name text NOT NULL,
    geom geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX obszary_chronione_geom ON obszary_chronione USING gist (geom);

-- Temporary entry bans from BDL, the whole country, refreshed when older than 4 hours.
CREATE TABLE zakazy_wstepu (
    id bigint PRIMARY KEY,                -- objectid in BDL
    nadlesnictwo text,
    valid_until text,                     -- data_koncowa as BDL writes it (no single format)
    geom geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX zakazy_wstepu_geom ON zakazy_wstepu USING gist (geom);

-- When each source was last fetched: the freshness check for the entry bans, and the
-- "time of acquisition" the BDL terms require in the attribution.
CREATE TABLE fetches (
    source text PRIMARY KEY,
    fetched_at timestamptz NOT NULL
);

-- Nominatim answers, kept for good: place names do not move, and the usage policy asks not to
-- repeat a query. A name that found nothing is kept too (lat and lon NULL).
CREATE TABLE geocoding_cache (
    query text PRIMARY KEY,               -- the name as asked, trimmed and lower-cased
    lat double precision,
    lon double precision,
    display_name text,
    fetched_at timestamptz NOT NULL DEFAULT now()
);

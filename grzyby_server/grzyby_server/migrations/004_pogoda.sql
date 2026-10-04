-- Weather per tile of the grid (lasy/tiles.py) and day, from Open-Meteo (pogoda/): the days
-- behind a question and the days ahead, refreshed when older than a few hours.
CREATE TABLE pogoda (
    tile text NOT NULL,
    dzien date NOT NULL,
    opad double precision NOT NULL,        -- mm, the day's sum
    temperatura double precision NOT NULL, -- °C, the day's mean at 2 m
    temperatura_min double precision NOT NULL,
    wilgotnosc_gleby double precision,     -- m³/m³, the day's mean at 3 to 9 cm; NULL when the model has none
    PRIMARY KEY (tile, dzien)
);

CREATE TABLE weather_fetches (
    tile text PRIMARY KEY,
    fetched_at timestamptz NOT NULL
);

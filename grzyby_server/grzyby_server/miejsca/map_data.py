"""The data the map widget colours: every scored stand around the place, the areas one may not
enter, and the scoring rules — within the size a chatbot passes on to a widget.
"""

import json

from grzyby_server.lasy.model import Obszar
from grzyby_server.miejsca import scoring
from grzyby_server.miejsca.model import Drzewostany, Mapa, ObszarNaMapie, Reguly

# Characters of outlines and attributes the stands may take. A tool result above ~150 000
# characters never reaches the widget in claude.ai (docs/mcp-apps.md); the rest of the answer is
# a few thousand. A 15 km circle near Suwałki is ~1800 stands and ~110 000; a bigger one leaves
# out its weakest stands, which the map would show faintest anyway.
BUDGET = 120_000
# A stand's attributes as JSON, besides its outline: `87,"SO","BMŚW",67,` and the like.
ATTRIBUTES_SIZE = 20


def build_map(scores: list[scoring.Score], obszary: list[Obszar], lat: float, lon: float) -> Mapa:
    on_map: list[scoring.Score] = []
    used = 0
    for s in sorted(scores, key=lambda s: s.points, reverse=True):
        size = len(json.dumps(s.wydzielenie.shape, separators=(",", ":"))) + ATTRIBUTES_SIZE
        if used + size > BUDGET:
            break
        on_map.append(s)
        used += size
    return Mapa(
        lat=lat,
        lon=lon,
        drzewostany=Drzewostany(
            ksztalt=[s.wydzielenie.shape for s in on_map],
            wynik=[round(s.points * 100) for s in on_map],
            gatunek=[scoring.species(s.wydzielenie.gatunek) for s in on_map],
            siedlisko=[s.wydzielenie.siedlisko for s in on_map],
            wiek=[s.wydzielenie.wiek for s in on_map],
        ),
        pominiete=len(scores) - len(on_map),
        obszary=[ObszarNaMapie(rodzaj=o.kind, nazwa=o.name, ksztalt=o.shape) for o in obszary],
        reguly=Reguly(
            gatunki=scoring.GATUNKI,
            inny_gatunek=scoring.INNY_GATUNEK,
            siedliska=scoring.SIEDLISKA,
            nieznane_siedlisko=scoring.NIEZNANE_SIEDLISKO,
            wiek=scoring.WIEK,
        ),
    )

"""The data the map widget colours: every scored stand around the place, the areas one may not
enter, and the scoring rules — within the size a chatbot passes on to a widget.
"""

import json
from collections.abc import Sequence

from grzyby_server.lasy.model import Obszar
from grzyby_server.miejsca import grzyby, scoring
from grzyby_server.miejsca.model import Drzewostany, Grzyb, Mapa, Miesiac, ObszarNaMapie, Reguly

# Characters of outlines and attributes the stands may take. A tool result above ~150 000
# characters never reaches the widget in claude.ai (docs/mcp-apps.md); the rest of the answer is
# a few thousand. A 15 km circle near Suwałki (pine country) is ~1800 stands and ~110 000; a
# bigger one leaves out its weakest stands, which the map would show faintest anyway.
BUDGET = 120_000


def build_map(
    scores: list[scoring.Score], obszary: list[Obszar], center: tuple[float, float], wanted: Sequence[Grzyb], month: Miesiac
) -> Mapa:
    # A stand's attributes as JSON, besides its outline: `"SO","BMŚW",67,` and a score per mushroom.
    attributes_size = 16 + 4 * len(wanted)
    on_map: list[scoring.Score] = []
    used = 0
    for s in sorted(scores, key=lambda s: s.points, reverse=True):
        size = len(json.dumps(s.wydzielenie.shape, separators=(",", ":"))) + attributes_size
        if used + size > BUDGET:
            break
        on_map.append(s)
        used += size
    return Mapa(
        lat=center[0],
        lon=center[1],
        drzewostany=Drzewostany(
            ksztalt=[s.wydzielenie.shape for s in on_map],
            wynik={g: [round(s.per_grzyb[g] * 100) for s in on_map] for g in wanted},
            gatunek=[scoring.species(s.wydzielenie.gatunek) for s in on_map],
            siedlisko=[s.wydzielenie.siedlisko for s in on_map],
            wiek=[s.wydzielenie.wiek for s in on_map],
        ),
        pominiete=len(scores) - len(on_map),
        obszary=[ObszarNaMapie(rodzaj=o.kind, nazwa=o.name, ksztalt=o.shape) for o in obszary],
        reguly=Reguly(
            drzewa=grzyby.DRZEWA,
            siedliska=grzyby.SIEDLISKA,
            grupy_siedlisk=grzyby.GRUPY_SIEDLISK,
            klasy_wieku=grzyby.KLASY_WIEKU,
            grzyby={g: grzyby.PROFILE[g] for g in wanted},
            miesiac=month,
        ),
    )

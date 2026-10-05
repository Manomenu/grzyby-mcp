"""The MCP server: one tool, the best forest stands near a place, with a map.

The search itself is search.py; here it is wired to MCP — the database connection, the
network, the clock, and the two forms of the answer.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from mcp.server.apps import Apps, ResourceCsp
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent
from pydantic import Field

from grzyby_server import db
from grzyby_server.fetch import get_json
from grzyby_server.miejsca.best_day import best_day
from grzyby_server.miejsca.model import Answer, Grzyb, Prognoza, as_text, forecast_text
from grzyby_server.miejsca.search import MAX_DAY, MIN_DAY, Query, search
from grzyby_server.settings import settings

# The tiles' key goes in as the widget is read, so a new key also gets a new address (below).
MAP_HTML = Path(__file__).with_name("mapa.html").read_text(encoding="utf-8").replace("__CARTO_KEY__", settings.carto_key)
# The content's hash is part of the address: hosts cache a widget by its URI (Claude kept showing
# a broken old version of mapa.html after it was fixed), so every change gets a new one.
MAP_URI = f"ui://grzyby/mapa-{hashlib.sha256(MAP_HTML.encode()).hexdigest()[:12]}.html"

# Each spot is a paragraph of text for the chatbot and a numbered marker: fifteen per view at most —
# with several mushrooms the text grows to ~18 KB, and a busier map stops being readable.
MAX_SPOTS = 15

apps = Apps()

# The parameters both tools take, described once.
Miejscowosc = Annotated[str, Field(description="Nazwa miejscowości w Polsce, np. „Suwałki” albo „Bryzgiel”")]
Grzyby = Annotated[
    list[Grzyb],
    Field(
        min_length=1,
        description=(
            "Grzyby, których szuka użytkownik — co najmniej jeden. Każda nazwa to grupa, jak mówią grzybiarze: "
            "borowik = prawdziwki (borowik szlachetny, sosnowy, usiatkowany, ciemnobrązowy); "
            "podgrzybek = podgrzybek brunatny; kurka = pieprznik jadalny; "
            "kozlarz = koźlarze (babka; koźlarz czerwony — osikowy i dębowy; grabowy); "
            "maslak = maślaki (zwyczajny, modrzewiowy); rydz = rydze (mleczaj rydz, rydz świerkowy). "
            "Grzyba spoza listy (np. kania, gąska) nie zgaduj — powiedz użytkownikowi, że go nie znam."
        ),
    ),
]
Promien = Annotated[int, Field(ge=1, le=30, description="Promień poszukiwań w km")]


@apps.tool(
    resource_uri=MAP_URI,
    # The same address under the older flat key too. The Python SDK sets only _meta.ui.resourceUri;
    # the official TypeScript helper (registerAppTool) sets both, and Claude reads this one —
    # without it Claude never fetches the map and shows the text alone.
    meta={"ui/resourceUri": MAP_URI},
    name="gdzie_na_grzyby",
    title="Gdzie na grzyby",
    description=(
        "Wskazuje drzewostany najbardziej obiecujące na wybrane grzyby (domyślnie 3 miejsca, na prośbę do 15) "
        "w promieniu promien_km od podanej miejscowości: drzewa, siedlisko, wiek, sezon, uzasadnienie i link "
        "do trasy. Ocena jest osobna dla każdego grzyba — według jego drzew, siedlisk, wieku lasu i miesiąca. "
        "Jeśli użytkownik nie powiedział, jakich grzybów szuka, zapytaj go albo zaproponuj (np. borowik, "
        "podgrzybek, kurka) i wywołaj narzędzie dopiero po jego zgodzie. Pomija parki narodowe, rezerwaty "
        "i lasy z aktualnym zakazem wstępu. Przy kilku grzybach daje miejsca na wszystkie naraz (średnia ocen) "
        "i osobno na każdy — zwykle różne. Mapa pod odpowiedzią koloruje wszystkie drzewostany w promieniu, "
        "z przełącznikiem grzybów i trybami: wynik, drzewa, wiek, siedlisko; kliknięcie w las pokazuje, skąd "
        "jego ocena. Działa w całej Polsce, "
        "ale zna tylko Lasy Państwowe; pierwsze pytanie o nową okolicę trwa kilka sekund, bo "
        "dane dopiero przychodzą. Uwzględnia pogodę ostatnich dni: deszcz sprzed 3–14 dni, wilgotność gleby, "
        "temperaturę i przymrozki. Domyślnie na dziś; parametr za_ile_dni pozwala zapytać o inny dzień "
        "(od 3 dni wstecz do 5 naprzód). Na pytanie „kiedy najlepiej?” użyj najpierw kiedy_na_grzyby."
    ),
)
def gdzie_na_grzyby(
    miejscowosc: Miejscowosc,
    grzyby: Grzyby,
    promien_km: Promien = 15,
    ile_miejsc: Annotated[int, Field(ge=1, le=MAX_SPOTS, description="Ile najlepszych miejsc wskazać")] = 3,
    za_ile_dni: Annotated[
        int,
        Field(
            ge=MIN_DAY,
            le=MAX_DAY,
            description=(
                "Na który dzień: 0 = dziś, 1 = jutro, -1 = wczoraj; od -3 do 5. Gdy użytkownik mówi o dniu "
                "tygodnia (np. „w sobotę”), przelicz go na liczbę dni od dziś."
            ),
        ),
    ] = 0,
) -> Annotated[CallToolResult, Answer]:
    """Two forms of one answer: readable text (the chatbot quotes it; a client without the map
    shows only it) and the data the map draws (structuredContent, schema = Answer)."""
    with db.pool.connection() as conn:
        answer = search(conn, get_json, Query(miejscowosc, grzyby, promien_km, ile_miejsc, za_ile_dni), datetime.now(UTC))
    return CallToolResult(content=[TextContent(type="text", text=as_text(answer))], structured_content=answer.model_dump(mode="json"))


apps.add_html_resource(
    MAP_URI,
    MAP_HTML,
    title="Mapa miejsc na grzyby",
    # The widget loads Leaflet and raster tiles from these hosts; the host's sandbox blocks
    # everything else — including blob: workers, which is why the map is Leaflet (plain images)
    # and not a WebGL library.
    csp=ResourceCsp(resource_domains=["https://unpkg.com", "https://basemaps.cartocdn.com"]),
    prefers_border=True,
)

server = MCPServer(
    name="grzyby",
    title="Gdzie na grzyby",
    instructions=(
        "Odpowiadaj po polsku. Zanim wywołasz narzędzie, ustal z użytkownikiem, jakich grzybów szuka (albo zaproponuj "
        "i poczekaj na zgodę). Pytanie „gdzie” → gdzie_na_grzyby (mapa z miejscami); pytanie „kiedy” → kiedy_na_grzyby, "
        "a potem, jeśli użytkownik chce, gdzie_na_grzyby z za_ile_dni najlepszego dnia. Krótko streść uzasadnienie. "
        "Zawsze podaj link do trasy i źródło danych."
    ),
    extensions=[apps],
)


@server.tool(
    name="kiedy_na_grzyby",
    title="Kiedy na grzyby",
    description=(
        "Który dzień — od dziś do 5 dni naprzód — będzie najlepszy na wybrane grzyby wokół miejscowości: ocena "
        "okolicy na każdy dzień (średnia z najlepszych drzewostanów) i pogoda w skrócie, z najlepszym dniem. "
        "Pogoda działa z opóźnieniem: deszcz sprzed kilku dni daje grzyby dziś. Od 3. dnia to prognoza, mniej "
        "pewna. Bez mapy — miejsca na wybrany dzień pokaże gdzie_na_grzyby z za_ile_dni."
    ),
)
def kiedy_na_grzyby(miejscowosc: Miejscowosc, grzyby: Grzyby, promien_km: Promien = 15) -> Annotated[CallToolResult, Prognoza]:
    with db.pool.connection() as conn:
        prognoza = best_day(conn, get_json, Query(miejscowosc, grzyby, promien_km), datetime.now(UTC))
    return CallToolResult(
        content=[TextContent(type="text", text=forecast_text(prognoza))], structured_content=prognoza.model_dump(mode="json")
    )

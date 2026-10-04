"""The MCP server: one tool for now, answering with a fixed stand near Suwałki.

A "hello world" that proves the whole chain — chatbot → /mcp → tool → map — before the real
scoring arrives (TODO, stage 1). The stand is real: Nadleśnictwo Suwałki, from the Bank Danych
o Lasach sample.
"""

from pathlib import Path
from typing import Annotated

from mcp.server.apps import Apps, ResourceCsp
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from grzyby_server.miejsca.model import Miejsce, Odpowiedz, opis, trasa

MAP_URI = "ui://grzyby/mapa.html"
SOURCES = "Drzewostany: Bank Danych o Lasach (bdl.lasy.gov.pl), stan na 2026, licencja CC BY 4.0."

apps = Apps()


@apps.tool(
    resource_uri=MAP_URI,
    name="gdzie_na_grzyby",
    title="Gdzie na grzyby",
    description=(
        "Wskazuje lasy w okolicy podanej miejscowości, w których teraz najpewniej rosną grzyby, "
        "z uzasadnieniem i linkiem do trasy. Na razie działa tylko dla okolic Suwałk."
    ),
)
def gdzie_na_grzyby(miejscowosc: str, promien_km: int = 15) -> Annotated[CallToolResult, Odpowiedz]:
    """Spots near `miejscowosc` within `promien_km`. Hello world: always the same stand.

    Two forms of one answer: readable text (the chatbot quotes it; a client without the map shows
    only it) and the data the map draws (structuredContent, schema = Odpowiedz)."""
    _ = (miejscowosc, promien_km)
    odpowiedz = _hello_world()
    return CallToolResult(content=[TextContent(type="text", text=opis(odpowiedz))], structured_content=odpowiedz.model_dump(mode="json"))


def _hello_world() -> Odpowiedz:
    lat, lon = 54.051247, 22.965699
    return Odpowiedz(
        miejsca=[
            Miejsce(
                nazwa="Bór sosnowy, 76 lat, 28 ha",
                lat=lat,
                lon=lon,
                dlaczego=(
                    "Sosna w wieku 76 lat na borze mieszanym świeżym — typowe miejsce borowika, "
                    "podgrzybka i kurki. Las gospodarczy, poza parkiem narodowym."
                ),
                trasa=trasa(lat, lon),
                adres_lesny="01-26-2-01-215-a-00",
            )
        ],
        zrodla=SOURCES,
    )


apps.add_html_resource(
    MAP_URI,
    (Path(__file__).with_name("mapa.html")).read_text(encoding="utf-8"),
    title="Mapa miejsc na grzyby",
    # The widget loads Leaflet and raster tiles from these hosts; the host's sandbox blocks
    # everything else — including blob: workers, which is why the map is Leaflet (plain images)
    # and not a WebGL library.
    csp=ResourceCsp(resource_domains=["https://unpkg.com", "https://tile.openstreetmap.org"]),
    prefers_border=True,
)

server = MCPServer(
    name="grzyby",
    title="Gdzie na grzyby",
    instructions=("Odpowiadaj po polsku. Pokaż mapę z miejscami i krótko streść uzasadnienie. Zawsze podaj link do trasy i źródło danych."),
    extensions=[apps],
)

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
from grzyby_server.miejsca.model import Answer, as_text
from grzyby_server.miejsca.search import Query, search

MAP_HTML = Path(__file__).with_name("mapa.html").read_text(encoding="utf-8")
# The content's hash is part of the address: hosts cache a widget by its URI (Claude kept showing
# a broken old version of mapa.html after it was fixed), so every change gets a new one.
MAP_URI = f"ui://grzyby/mapa-{hashlib.sha256(MAP_HTML.encode()).hexdigest()[:12]}.html"

# Each spot is a paragraph of text for the chatbot and a numbered marker; past ten neither reads well.
MAX_SPOTS = 10

apps = Apps()


@apps.tool(
    resource_uri=MAP_URI,
    # The same address under the older flat key too. The Python SDK sets only _meta.ui.resourceUri;
    # the official TypeScript helper (registerAppTool) sets both, and Claude reads this one —
    # without it Claude never fetches the map and shows the text alone.
    meta={"ui/resourceUri": MAP_URI},
    name="gdzie_na_grzyby",
    title="Gdzie na grzyby",
    description=(
        "Wskazuje najbardziej obiecujące dla grzybiarza drzewostany (domyślnie 3, na prośbę do 10) w promieniu "
        "promien_km od podanej miejscowości: gatunek drzew, wiek, siedlisko, uzasadnienie i link "
        "do trasy. Pomija parki narodowe, rezerwaty i lasy z aktualnym zakazem wstępu. Mapa pod "
        "odpowiedzią koloruje wszystkie drzewostany w promieniu według oceny, z trybami: wynik, "
        "drzewa, wiek, siedlisko; kliknięcie w las pokazuje, skąd jego ocena. Na razie zna tylko "
        "okolice Suwałk i Wigier (lasy państwowe), a pogody jeszcze nie bierze pod uwagę."
    ),
)
def gdzie_na_grzyby(
    miejscowosc: Annotated[str, Field(description="Nazwa miejscowości w Polsce, np. „Suwałki” albo „Bryzgiel”")],
    promien_km: Annotated[int, Field(ge=1, le=30, description="Promień poszukiwań w km")] = 15,
    ile_miejsc: Annotated[int, Field(ge=1, le=MAX_SPOTS, description="Ile najlepszych miejsc wskazać")] = 3,
) -> Annotated[CallToolResult, Answer]:
    """Two forms of one answer: readable text (the chatbot quotes it; a client without the map
    shows only it) and the data the map draws (structuredContent, schema = Answer)."""
    with db.pool.connection() as conn:
        answer = search(conn, get_json, Query(miejscowosc, promien_km, ile_miejsc), datetime.now(UTC))
    return CallToolResult(content=[TextContent(type="text", text=as_text(answer))], structured_content=answer.model_dump(mode="json"))


apps.add_html_resource(
    MAP_URI,
    MAP_HTML,
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

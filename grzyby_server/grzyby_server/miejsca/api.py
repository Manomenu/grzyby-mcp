"""The same search for the web page, for people without a chatbot: the answer as JSON and the
map widget that draws it — the page hosts the widget the way a chatbot does (grzyby_web/src/miejsca/).

Same search, same limits and cache as the MCP tool (tools.py); only the transport differs.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from grzyby_server import db
from grzyby_server.fetch import get_json
from grzyby_server.miejsca import search
from grzyby_server.miejsca.model import Answer, Grzyb
from grzyby_server.miejsca.tools import MAP_HTML, MAX_SPOTS

router = APIRouter()


@router.get("/miejsca")
def miejsca(
    miejscowosc: Annotated[str, Query(min_length=2, max_length=100)],
    grzyby: Annotated[list[Grzyb], Query(min_length=1)],
    promien_km: Annotated[int, Query(ge=1, le=30)] = 15,
    ile_miejsc: Annotated[int, Query(ge=1, le=MAX_SPOTS)] = 3,
    za_ile_dni: Annotated[int, Query(ge=search.MIN_DAY, le=search.MAX_DAY)] = 0,
) -> Answer:
    with db.pool.connection() as conn:
        return search.search(conn, get_json, search.Query(miejscowosc, grzyby, promien_km, ile_miejsc, za_ile_dni), datetime.now(UTC))


@router.get("/mapa.html", response_class=HTMLResponse)
def mapa() -> HTMLResponse:
    # The page asks for it on every visit: a deploy that changes the widget shows at once.
    return HTMLResponse(MAP_HTML, headers={"cache-control": "no-cache"})

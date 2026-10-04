"""The MCP endpoint as a chatbot sees it: JSON-RPC over HTTP at /mcp."""

import hashlib
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from grzyby_server import db
from grzyby_server.app import mcp_http
from grzyby_server.miejsca import tools
from grzyby_server.miejsca.model import Answer, Grzyb, Miejsce
from grzyby_server.miejsca.search import Query
from grzyby_server.miejsca.tools import MAP_HTML, MAP_URI

# Streamable HTTP: the client accepts both, the server answers with JSON (json_response=True).
HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json", "host": "localhost:6210"}


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """The MCP app with its transport running. Session-wide: the SDK's session manager starts
    once per process (in production that is the FastAPI lifespan). Needs no database."""
    with TestClient(mcp_http) as client:
        yield client


def rpc(client: TestClient, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.post("/mcp", headers=HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert "error" not in body, body
    return body["result"]


def test_the_tool_is_listed_with_its_map(client: TestClient) -> None:
    tools = rpc(client, "tools/list")["tools"]

    tool = next(tool for tool in tools if tool["name"] == "gdzie_na_grzyby")
    assert tool["_meta"]["ui"]["resourceUri"] == MAP_URI
    # The older flat key, which Claude reads (see tools.py).
    assert tool["_meta"]["ui/resourceUri"] == MAP_URI


def test_the_tool_answers_in_text_and_as_data_for_the_map(
    client: TestClient, pool: ConnectionPool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The search has tests of its own (test_search.py); here only what MCP makes of its answer.
    spot = Miejsce(nazwa="Las sosnowy", lat=54.1, lon=22.9, dlaczego="sosna.", trasa="https://maps.example", adres_lesny="a")
    asked: list[Query] = []

    def search(_conn: object, _get_json: object, query: Query, _now: object) -> Answer:
        asked.append(query)
        return Answer(szukano_wokol="Suwałki", grzyby=["kurka"], promien_km=query.promien_km, miejsca=[spot], uwagi=[], zrodla="BDL.")

    monkeypatch.setattr(tools, "search", search)
    monkeypatch.setattr(db, "pool", pool)

    result = rpc(client, "tools/call", {"name": "gdzie_na_grzyby", "arguments": {"miejscowosc": "Suwałki", "grzyby": ["kurka"]}})

    assert asked == [Query("Suwałki", [Grzyb.KURKA], 15, 3)]  # the defaults
    assert result["structuredContent"]["miejsca"][0]["trasa"] == "https://maps.example"
    # The readable form for the chatbot and for clients without the map — not a JSON dump.
    assert "**Las sosnowy**" in result["content"][0]["text"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"grzyby": ["kurka"], "promien_km": 500},
        {"grzyby": ["kurka"], "ile_miejsc": 11},
        {"grzyby": ["kurka"], "ile_miejsc": 0},
        {},  # no mushrooms: the chatbot has to ask the user first
        {"grzyby": []},
        {"grzyby": ["prawdziwek"]},  # not on the list
    ],
)
def test_the_arguments_are_checked(client: TestClient, arguments: dict[str, object]) -> None:
    response = client.post(
        "/mcp",
        headers=HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "gdzie_na_grzyby", "arguments": {"miejscowosc": "Suwałki", **arguments}},
        },
    )

    assert response.json()["result"]["isError"] is True


def test_the_map_address_changes_with_its_content() -> None:
    # Hosts cache widgets by URI; a changed mapa.html must not be served under the old address.
    assert hashlib.sha256(MAP_HTML.encode()).hexdigest()[:12] in MAP_URI


def test_the_map_is_served_as_an_mcp_app(client: TestClient) -> None:
    contents = rpc(client, "resources/read", {"uri": MAP_URI})["contents"][0]

    assert contents["mimeType"] == "text/html;profile=mcp-app"
    assert "ontoolresult" in contents["text"]


def test_an_unknown_host_is_refused(client: TestClient) -> None:
    # DNS rebinding guard: only the hosts in settings.mcp_allowed_hosts reach the tools.
    response = client.post(
        "/mcp", headers={**HEADERS, "host": "evil.example.com"}, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )

    assert response.status_code in {400, 421}

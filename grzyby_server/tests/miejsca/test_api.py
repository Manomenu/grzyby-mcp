from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from grzyby_server import db
from grzyby_server.app import app
from grzyby_server.miejsca import api, geocoding
from grzyby_server.miejsca.search import POLAND
from grzyby_server.miejsca.tools import MAP_HTML
from tests.fake_web import FakeWeb, forest_services, open_meteo, stand

# Without the lifespan: these routes need no MCP session, and the pool is the tests' own.
client = TestClient(app)


@pytest.mark.usefixtures("clean_tables")
def test_the_page_gets_the_same_answer_as_a_chatbot(pool: ConnectionPool, monkeypatch: pytest.MonkeyPatch) -> None:
    services = FakeWeb(
        {
            geocoding.NOMINATIM: [{"lat": "54.10", "lon": "22.93", "display_name": "Suwałki, województwo podlaskie, Polska"}],
            **forest_services(stands=[stand("pine", 22.93, 54.10)], weather=open_meteo(datetime.now(POLAND).date())),
        }
    )
    monkeypatch.setattr(api, "get_json", services)
    monkeypatch.setattr(db, "pool", pool)

    response = client.get("/miejsca", params={"miejscowosc": "Suwałki", "grzyby": ["borowik", "kurka"], "promien_km": 5, "ile_miejsc": 15})

    assert response.status_code == 200, response.text
    answer = response.json()
    assert [m["adres_lesny"] for m in answer["miejsca"]] == ["pine"]
    assert set(answer["miejsca_na_grzyb"]) == {"borowik", "kurka"}
    assert answer["mapa"]["drzewostany"]["wiek"] == [70]
    assert "Bank Danych o Lasach" in answer["zrodla"]


@pytest.mark.parametrize(
    "params",
    [
        {"miejscowosc": "Suwałki"},  # no mushroom
        {"miejscowosc": "Suwałki", "grzyby": ["kania"]},  # not one we know
        {"miejscowosc": "Suwałki", "grzyby": ["borowik"], "ile_miejsc": 16},
        {"miejscowosc": "Suwałki", "grzyby": ["borowik"], "za_ile_dni": 6},
    ],
)
def test_the_question_is_checked_before_anything_is_fetched(params: dict[str, str | int | list[str]]) -> None:
    assert client.get("/miejsca", params=params).status_code == 422


def test_the_page_gets_the_chatbots_widget() -> None:
    response = client.get("/mapa.html")

    assert response.status_code == 200
    assert response.text == MAP_HTML
    assert response.headers["content-type"].startswith("text/html")
